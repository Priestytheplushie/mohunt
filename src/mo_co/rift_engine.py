import discord
from discord.ui import View, Button
import asyncio
import random
import json
import time
from mo_co import config, database, utils, game_data
from mo_co.game_data import scaling
from mo_co import pedia


TICK_RATE = 2.0

RIFT_STABILITY_MAX = 150
RESPAWN_TIME = 15.0


class RiftStats:
    def __init__(self):
        self.dmg_boss = 0
        self.dmg_mobs = 0
        self.dmg_tanked = 0
        self.healing = 0
        self.mob_kills = {}
        self.heal_sources = {}
        self.damage_sources = {}


class RiftInstance:
    def __init__(self, bot, channel, lobby_data):
        self.bot = bot
        self.channel = channel
        self.leader_id = lobby_data["leader"]
        self.rift_key = lobby_data["rift"]
        self.lobby_data = lobby_data

        self.difficulty = lobby_data.get("difficulty", "Normal")

        self.rift_def = game_data.RIFTS.get(self.rift_key)
        self.rec_gp = self.rift_def.get("recommended_gp", 1000)
        self.base_mob_lvl = max(10, int(self.rec_gp / 70))

        self.players = []
        self.player_stats = {}

        human_gps = []
        human_hps = []
        human_lvls = []

        for uid in lobby_data["members"]:
            member_info = lobby_data["member_info"].get(uid, {})
            p_name = member_info.get("name", "Hunter")
            p = RiftPlayer(bot, uid, self.rec_gp, name=p_name)
            self.players.append(p)
            self.player_stats[uid] = RiftStats()

            human_gps.append(p.gp)
            human_hps.append(p.max_hp)
            human_lvls.append(p.level)

        avg_gp = int(sum(human_gps) / len(human_gps)) if human_gps else self.rec_gp
        avg_hp = int(sum(human_hps) / len(human_hps)) if human_hps else 1500
        avg_lvl = int(sum(human_lvls) / len(human_lvls)) if human_lvls else 10

        if len(self.players) < 4:
            bot_names = ["Jax", "Luna", "Manny"]
            existing_bot_names = [
                p.name for p in self.players if isinstance(p, RiftBot)
            ]
            available_bots = [n for n in bot_names if n not in existing_bot_names]
            needed = 4 - len(self.players)
            while len(available_bots) < needed:
                available_bots.append(random.choice(bot_names))
            selected_bots = available_bots[:needed]

            for name in selected_bots:

                b = RiftBot(bot, name, avg_lvl, avg_gp, avg_hp)
                self.players.append(b)
                self.player_stats[name] = RiftStats()

        self.active = True
        self.turn_count = 0
        self.wave_index = 0
        self.stability = RIFT_STABILITY_MAX
        self.logs = []
        self.message = None
        self.banked_loot = {"xp": 0, "shards": 0, "cores": 0}

        if self.rift_key == "rift_van_defense":
            van = RiftSummon("Research Van", 50000, 0, 9999, "🚐", 0, "system")
            van.taunt = True
            self.players.append(van)

        self.allies = list(self.players)
        self.mobs = self._spawn_wave(0)

    def _spawn_wave(self, index):
        if index >= len(self.rift_def["waves"]):
            return []
        wave_desc = self.rift_def["waves"][index]
        new_mobs = []
        parts = wave_desc.split(" + ")
        wave_lvl = self.base_mob_lvl + index

        hp_mult = 1.0
        if self.difficulty == "Hard":
            hp_mult = 1.5
        elif self.difficulty == "Nightmare":
            hp_mult = 2.5

        for part in parts:
            part = part.strip()
            if "BOSS" in part:
                boss_name = part.replace("BOSS: ", "")

                m = RiftMob(self.bot, boss_name, wave_lvl + 2, is_boss=True)
                m.max_hp = int(m.max_hp * hp_mult)
                m.hp = m.max_hp
                new_mobs.append(m)
            else:
                try:
                    count_str, name = part.split(" ", 1)
                    count = int(count_str)
                    clean_name = name.rstrip("s")
                    for _ in range(count):
                        m = RiftMob(self.bot, clean_name, wave_lvl, is_boss=False)
                        m.max_hp = int(m.max_hp * hp_mult)
                        m.hp = m.max_hp
                        new_mobs.append(m)
                except:
                    m = RiftMob(self.bot, "Minion", wave_lvl, is_boss=False)
                    m.max_hp = int(m.max_hp * hp_mult)
                    m.hp = m.max_hp
                    new_mobs.append(m)
        return new_mobs

    def advance_zone_manual(self):
        if not self.active:
            return
        skipped_mobs = [m for m in self.mobs if m.hp > 0]
        self.wave_index += 1
        if self.wave_index >= len(self.rift_def["waves"]):
            self.logs.append("🏁 **Final Zone reached! Clear the remaining monsters!**")
            self.wave_index -= 1
            return
        leader_info = self.lobby_data["member_info"].get(self.leader_id, {})
        leader_name = leader_info.get("name", "Leader")
        self.logs.append(f"⏩ **{leader_name}** pushed the squad forward!")
        if skipped_mobs:
            self.logs.append(f"⚠️ **{len(skipped_mobs)}** monsters followed you!")
        new_wave = self._spawn_wave(self.wave_index)
        self.mobs = new_wave + skipped_mobs

    async def start_loop(self):
        view = RiftCombatView(self)
        self.message = await self.channel.send(embed=self._build_embed(), view=view)
        while self.active:
            await asyncio.sleep(TICK_RATE)
            await self._tick()
            if not self.active:
                break
            try:
                new_view = RiftCombatView(self)
                await self.message.edit(embed=self._build_embed(), view=new_view)
            except discord.NotFound:
                self.active = False
            except Exception as e:
                print(f"Rift Loop Error: {e}")

    async def _tick(self):
        self.turn_count += 1

        decay = 1
        if self.difficulty == "Nightmare":
            decay = 2
        self.stability = max(0, self.stability - decay)

        if self.stability <= 0:
            self.logs.append("🌀 **Rift Collapsed due to instability!**")
            self.active = False
            await self._end_game(success=False)
            return

        if len(self.logs) > 8:
            self.logs = self.logs[-8:]

        for entity in self.allies:
            if hasattr(entity, "total_healed_this_tick"):
                entity.total_healed_this_tick = 0
            if hasattr(entity, "hits_taken_this_tick"):
                entity.hits_taken_this_tick = 0

        for m in self.mobs:
            if hasattr(m, "hits_taken_this_tick"):
                m.hits_taken_this_tick = 0

        current_allies = list(self.allies)
        for entity in current_allies:
            if entity.hp > 0:
                entity.tick(self)
            elif isinstance(entity, (RiftPlayer, RiftBot)):
                if time.time() - entity.death_time >= RESPAWN_TIME:
                    entity.hp = int(entity.max_hp * 0.5)
                    self.logs.append(f"🛡️ **{entity.name}** has returned to the fight!")

        self.allies = [
            e
            for e in self.allies
            if (isinstance(e, (RiftPlayer, RiftBot)))
            or (e.hp > 0 and not getattr(e, "expired", False))
        ]

        if self.rift_key == "rift_van_defense":
            van = next((a for a in self.allies if a.name == "Research Van"), None)
            if not van or van.hp <= 0:
                self.logs.append("🔥 **Research Van Destroyed!**")
                self.active = False
                await self._end_game(success=False)
                return

        if not any(
            p.hp > 0 for p in self.allies if isinstance(p, (RiftPlayer, RiftBot))
        ):
            self.logs.append("💀 **Squad Wiped!**")
            self.active = False
            await self._end_game(success=False)
            return

        dead_mobs = [m for m in self.mobs if m.hp <= 0 and not m.loot_awarded]
        for m in dead_mobs:
            self._award_mob_loot(m)
            m.loot_awarded = True

            for p in self.players:
                if isinstance(p, RiftPlayer) and p.hp > 0:
                    if any(mod["id"] == "speed_kill" for mod in p.modules):

                        if random.random() < 0.5:
                            p.apply_status("HASTE", 4.0, "⚡", instance=self)

        alive_mobs = [m for m in self.mobs if m.hp > 0]
        if not alive_mobs:
            self.wave_index += 1
            if self.wave_index >= len(self.rift_def["waves"]):
                self.logs.append("🏆 **Rift Cleared!**")
                self.active = False
                await self._end_game(success=True)
                return
            else:
                self.mobs = self._spawn_wave(self.wave_index)
                self.logs.append(
                    f"⏩ **Area Cleared! Advancing to Zone {self.wave_index+1}...**"
                )
                return

        targets = [a for a in self.allies if a.hp > 0 and not a.has_status("INVISIBLE")]
        if not targets:
            targets = [a for a in self.allies if a.hp > 0]

        new_summons = []
        for mob in alive_mobs:
            if mob.hp > 0:
                summon = mob.tick(self, targets)
                if summon:
                    new_summons.append(summon)

        self.mobs.extend(new_summons)

    def _award_mob_loot(self, mob):
        xp = 50 + (mob.level * 10)
        if mob.is_boss:
            xp *= 15
        shards = random.randint(1, 3) if random.random() < 0.3 else 0
        if mob.is_boss:
            shards = random.randint(10, 20)
        cores = 1 if random.random() < 0.05 else 0
        if mob.is_boss:
            cores = random.randint(1, 2)

        bonus_mult = 1.0
        if self.difficulty == "Hard":
            bonus_mult = 1.2
        elif self.difficulty == "Nightmare":
            bonus_mult = 1.5

        self.banked_loot["xp"] += int(xp * bonus_mult)
        self.banked_loot["shards"] += int(shards * bonus_mult)
        self.banked_loot["cores"] += cores

        for p in self.players:
            if isinstance(p, RiftPlayer):
                pedia.track_kill(
                    p.user_id,
                    mob.name,
                    is_overcharged=False,
                    is_chaos=False,
                    is_megacharged=False,
                )

        if cores > 0 or mob.is_boss:
            msg = f"{config.XP_EMOJI} +{int(xp*bonus_mult)}"
            if shards > 0:
                msg += f" {config.CHAOS_SHARD_EMOJI} +{int(shards*bonus_mult)}"
            if cores > 0:
                msg += f" {config.CHAOS_CORE_EMOJI} +{cores}"
            self.logs.append(f"{mob.icon} **{mob.name}** dropped {msg}")

    def _distribute_loot(self, partial):
        real_players = [p for p in self.allies if isinstance(p, RiftPlayer)]
        for p in real_players:
            u = database.get_user_data(p.user_id)
            raw_xp = int(self.banked_loot["xp"] * (0.5 if partial else 1.0))
            current_daily = u["daily_xp_total"]
            can_gain = max(0, config.XP_DAILY_CAP - current_daily)
            actual_raw = min(raw_xp, can_gain)
            if actual_raw <= 0:
                continue

            fuel_available = u["daily_xp_boosted"]

            xp_to_boost = min(actual_raw, fuel_available)
            xp_unboosted = actual_raw - xp_to_boost

            final_xp = (xp_to_boost * config.XP_BOOST_MULT) + xp_unboosted
            fuel_consumed = xp_to_boost

            current_xp = u["xp"]
            current_elite = u["elite_xp"]
            max_base = utils.get_max_base_xp()
            is_elite = bool(u["is_elite"])

            xp_to_base = 0
            xp_to_elite = 0

            if current_xp < max_base:
                space = max_base - current_xp
                if final_xp <= space:
                    xp_to_base = final_xp
                else:
                    xp_to_base = space
                    if is_elite:
                        xp_to_elite = final_xp - space
            else:
                if is_elite:
                    xp_to_elite = final_xp

            updates = {
                "xp": current_xp + xp_to_base,
                "elite_xp": current_elite + xp_to_elite,
                "daily_xp_total": max(0, u["daily_xp_total"] - actual_raw),
                "daily_xp_boosted": max(0, u["daily_xp_boosted"] - fuel_consumed),
                "chaos_shards": u["chaos_shards"] + self.banked_loot["shards"],
                "chaos_cores": u["chaos_cores"] + self.banked_loot["cores"],
            }
            database.update_user_stats(p.user_id, updates)
            hunt_cog = self.bot.get_cog("Hunting")
            if hunt_cog:
                p_stats = self.player_stats.get(p.user_id) or RiftStats()
                rift_boss_name = self.rift_def["boss"]
                hunt_cog.update_progression(
                    p.user_id,
                    rift_boss_name,
                    self.rift_key,
                    f"Standard-{self.difficulty}",
                    "Boss",
                    damage_sources=p_stats.damage_sources,
                    heal_sources=p_stats.heal_sources,
                    loot_xp=final_xp,
                )

    async def _end_game(self, success):
        if self.message:
            try:
                await self.message.delete()
            except:
                pass
        clear_time = int(self.turn_count * TICK_RATE)
        if success:
            hunt_cog = self.bot.get_cog("Hunting")
            for p in self.allies:
                if isinstance(p, RiftPlayer):
                    if hunt_cog:
                        p_stats = self.player_stats.get(p.user_id) or RiftStats()
                        rift_boss_name = self.rift_def["boss"]
                        mod_str = f"Standard-{self.difficulty}"
                        hunt_cog.update_progression(
                            p.user_id,
                            rift_boss_name,
                            self.rift_key,
                            mod_str,
                            "Boss",
                            rift_time=clear_time,
                            damage_sources=p_stats.damage_sources,
                            heal_sources=p_stats.heal_sources,
                        )
                    u = database.get_user_data(p.user_id)
                    comps = json.loads(u["completed_rifts"])
                    if self.rift_key not in comps:
                        comps.append(self.rift_key)
                        database.update_user_stats(
                            p.user_id, {"completed_rifts": json.dumps(comps)}
                        )
        view = RiftResultsView(self, success)
        await self.channel.send(embed=view.get_embed(), view=view)

    def spawn_summon(self, summon):
        owner = next((p for p in self.players if p.owner_id == summon.owner_id), None)
        if owner:
            if owner.has_status("POWER"):
                summon.apply_status(
                    "POWER",
                    10.0,
                    utils.get_emoji(self.bot, "really_cool_sticker"),
                )
            if owner.has_status("HASTE"):
                summon.apply_status(
                    "HASTE", 5.0, utils.get_emoji(self.bot, "vitamin_shot")
                )
        self.allies.append(summon)

    def record_damage(self, uid_or_name, amount, is_boss, source=None):
        if uid_or_name in self.player_stats:
            if is_boss:
                self.player_stats[uid_or_name].dmg_boss += amount
            else:
                self.player_stats[uid_or_name].dmg_mobs += amount
            if source:
                stats = self.player_stats[uid_or_name]
                stats.damage_sources[source] = (
                    stats.damage_sources.get(source, 0) + amount
                )

    def record_tank(self, uid_or_name, amount):
        if uid_or_name in self.player_stats:
            self.player_stats[uid_or_name].dmg_tanked += amount

    def record_healing(self, uid_or_name, amount, source=None):
        if uid_or_name in self.player_stats:
            stats = self.player_stats[uid_or_name]
            stats.healing += amount
            key = source or "direct"
            stats.heal_sources[key] = stats.heal_sources.get(key, 0) + amount

    def _build_embed(self):
        color = (
            0x2ECC71
            if self.stability > 50
            else (0xE67E22 if self.stability > 20 else 0xE74C3C)
        )
        title = f"{config.RIFTS_EMOJI} {self.rift_def['name']} - Zone {self.wave_index + 1} ({self.difficulty})"
        embed = discord.Embed(title=title, color=color)
        stab_pct = int(self.stability / 15)
        stab_bar = "🟦" * stab_pct + "⬛" * (10 - stab_pct)

        display_pct = int((self.stability / RIFT_STABILITY_MAX) * 100)
        embed.description = f"**Stability:** `{stab_bar}` {display_pct}%"
        mob_display = []
        for m in [m for m in self.mobs if m.hp > 0]:
            status = m.get_status_str()
            if m.state == "WINDUP":
                status += " ⚠️"
            if m.name == "Dragon Egg":
                status += f" (Hatch: {m.ability_cd}s)"
            mob_display.append(f"{m.icon} **{m.name}**: {m.hp}/{m.max_hp} HP {status}")
        embed.add_field(
            name="Enemies",
            value="\n".join(mob_display) if mob_display else "None",
            inline=False,
        )
        team_display = []
        for p in [p for p in self.allies if isinstance(p, (RiftPlayer, RiftBot))]:
            status = p.get_status_str()
            if p.hp <= 0:
                rem = int(RESPAWN_TIME - (time.time() - p.death_time))
                team_display.append(f"💀 **{p.name}** (Returning in {max(0, rem)}s)")
            else:
                if getattr(p, "is_dashing", False):
                    status += f" {config.DASH_EMOJI}"
                team_display.append(
                    f"{p.emblem} **{p.name}**: {p.hp}/{p.max_hp} HP {status}"
                )

        if self.rift_key == "rift_van_defense":
            van = next((a for a in self.allies if a.name == "Research Van"), None)
            if van:
                team_display.insert(0, f"🚐 **Research Van**: {van.hp}/{van.max_hp} HP")

        embed.add_field(name="Team", value="\n".join(team_display), inline=False)
        if self.logs:
            embed.add_field(
                name="Combat Log",
                value="\n".join(self.logs[-6:]),
                inline=False,
            )
        return embed


class RiftEntity:
    def __init__(self, name, hp, gp):
        self.name, self.max_hp, self.hp, self.gp = name, int(hp), int(hp), gp
        (
            self.owner_id,
            self.stunned,
            self.stun_duration,
            self.status_effects,
        ) = (
            None,
            False,
            0,
            [],
        )
        self.is_dashing, self.death_time = False, 0
        self.total_healed_this_tick = 0
        self.hits_taken_this_tick = 0
        self.is_boss = False
        self.defense_mult = 1.0

    def apply_status(self, s_type, duration, icon, instance=None):
        if self.is_boss and s_type in ["STUN", "SLOW"]:
            if instance and random.random() < 0.5:
                instance.logs.append(
                    f"⚠️ {getattr(self, 'icon', '👹')} **{self.name}** RESISTED the effect!"
                )
                return

        for s in self.status_effects:
            if s["type"] == s_type:
                s["duration"] = max(s["duration"], duration)
                return
        self.status_effects.append({"type": s_type, "duration": duration, "icon": icon})

    def has_status(self, s_type):
        return any(s["type"] == s_type for s in self.status_effects)

    def tick_status(self):
        for s in self.status_effects:
            s["duration"] -= TICK_RATE
            if s["type"] == "POISON":
                self.take_damage(50)
            if s["type"] == "REGEN":
                self.register_heal(50)
        self.status_effects = [s for s in self.status_effects if s["duration"] > 0]
        if self.stun_duration > 0:
            self.stun_duration -= TICK_RATE
            self.stunned = True
        else:
            self.stunned = False

    def register_heal(self, amount):
        cap = int(self.max_hp * 0.45)
        can_heal = cap - self.total_healed_this_tick
        actual = min(amount, max(0, can_heal))
        self.hp = min(self.max_hp, self.hp + actual)
        self.total_healed_this_tick += actual
        return actual

    def take_damage(self, amount, stun=False, instance=None):
        if (
            self.is_dashing
            or self.has_status("SHIELDED")
            or self.has_status("DODGE")
            or self.has_status("INVISIBLE")
            or self.has_status("AIRBORNE")
        ):
            return

        dmg_reduced = int(amount * self.defense_mult)

        if self.hits_taken_this_tick > 0 and (
            hasattr(self, "user_id") or hasattr(self, "bot")
        ):
            reduction_factor = 0.85**self.hits_taken_this_tick
            dmg_reduced = int(dmg_reduced * reduction_factor)

        self.hits_taken_this_tick += 1

        self.hp -= dmg_reduced
        if self.hp <= 0:
            self.hp = 0
            self.death_time = time.time()
            if hasattr(self, "user_id") and self.user_id:
                pedia.track_death(self.user_id, "Rift Monster")
        elif stun:
            if self.is_boss:
                if instance and random.random() < 0.5:
                    instance.logs.append(
                        f"⚠️ {getattr(self, 'icon', '👹')} **{self.name}** RESISTED the stun!"
                    )
                else:
                    self.stun_duration, self.stunned = 2.0, True
            else:
                self.stun_duration, self.stunned = 4.0, True

    def get_status_str(self):
        icons = [s["icon"] for s in self.status_effects]
        if self.stunned:
            icons.append("💫")
        return " ".join(icons)


class RiftSummon(RiftEntity):
    def __init__(self, name, hp, gp, duration, emblem, owner_id, source_id):
        super().__init__(name, hp, gp)
        self.duration, self.emblem, self.expired = duration, emblem, False
        self.taunt, self.owner_id, self.source_id = False, owner_id, source_id
        if source_id == "sheldon":
            self.taunt = True
        if source_id == "system":
            self.taunt = True

    def tick(self, instance):
        if self.source_id == "system":
            return
        self.tick_status()
        self.duration -= TICK_RATE
        if self.duration <= 0 or self.hp <= 0:
            self.expired = True
            return

        if self.source_id in ["wolf_stick", "buzz_kill", "pew3000", "sheldon"]:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)

                dmg = int(100 * (1 + (self.gp / 1500)))
                t.take_damage(dmg)
                instance.logs.append(
                    f"{self.emblem} **{self.name}** hit **{t.name}** ({dmg})"
                )


class RiftBot(RiftEntity):
    def __init__(self, bot, name, level, rec_gp, avg_hp):

        hp = int(avg_hp * 1.1)
        super().__init__(name, hp, rec_gp)
        self.bot, self.level, self.owner_id = bot, level, name
        self.emblem = config.BOT_EMOJIS.get(name, "🤖")
        self.dash_cd, self.combo_count, self.passives = 0, 0, {}
        self.rec_gp = rec_gp
        self.defense_mult = 0.8

        if name == "Manny":
            self.weapon_id = "techno_fists"
            self.gadgets = [
                {
                    "id": "smart_fireworks",
                    "name": "Smart Fireworks",
                    "cd": 0,
                    "max_cd": 20,
                    "lvl": level,
                }
            ]
        elif name == "Jax":
            self.weapon_id = "spinsickle"
            self.gadgets = [
                {
                    "id": "monster_taser",
                    "name": "Monster Taser",
                    "cd": 0,
                    "max_cd": 12,
                    "lvl": level,
                }
            ]
        else:
            self.weapon_id = "staff_of_good_vibes"
            self.gadgets = [
                {
                    "id": "smart_fireworks",
                    "name": "Smart Fireworks",
                    "cd": 0,
                    "max_cd": 20,
                    "lvl": level,
                }
            ]

    def get_weapon_emoji(self):
        return utils.get_emoji(self.bot, self.weapon_id)

    def tick(self, instance):
        self.tick_status()
        self.is_dashing = False
        if self.stunned or self.hp <= 0:
            return
        if self.dash_cd > 0:
            self.dash_cd -= TICK_RATE
        for g in self.gadgets:
            if g and g["cd"] > 0:
                g["cd"] -= TICK_RATE

        if random.random() < 0.30:
            return

        if self.dash_cd <= 0 and any(m.state == "WINDUP" for m in instance.mobs):
            self.is_dashing, self.dash_cd = True, 6.0
            return

        if self.weapon_id == "staff_of_good_vibes":
            for g in self.gadgets:
                if (
                    g
                    and g["cd"] <= 0
                    and g["id"] in ["vitamin_shot", "revitalizing_mist", "splash_heal"]
                ):
                    self._use_gadget(g, instance)
                    return
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                self._perform_attack(random.choice(targets), instance)
            return

        for g in self.gadgets:
            if g and g["cd"] <= 0 and random.random() < 0.6:
                self._use_gadget(g, instance)

        targets = [m for m in instance.mobs if m.hp > 0]
        if targets:
            self._perform_attack(random.choice(targets), instance)

    def _use_gadget(self, gadget, instance):
        gadget["cd"] = gadget["max_cd"]
        icon = utils.get_emoji(self.bot, gadget["id"])

        base_g_dmg = int((self.rec_gp / 8) + 200)

        if gadget["id"] == "monster_taser":
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                take = base_g_dmg
                t.take_damage(take, stun=True, instance=instance)
                instance.logs.append(
                    f"{icon} **{self.name}** used **{gadget['name']}**: Stunned {t.name}!"
                )
        else:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                t.take_damage(base_g_dmg)
                instance.logs.append(
                    f"{icon} **{self.name}** used **{gadget['name']}** ({base_g_dmg})"
                )

    def _perform_attack(self, target, instance):
        self.combo_count += 1

        base_dmg = int((self.rec_gp / 10) + (self.level * 10))
        final_primary = 0
        log_msg = f"{self.get_weapon_emoji()} **{self.name}** "

        if self.weapon_id == "techno_fists":
            bounces = 1
            other_mobs = [m for m in instance.mobs if m.hp > 0 and m != target]
            if other_mobs:
                hit_mobs = random.sample(other_mobs, min(bounces, len(other_mobs)))
                for m in hit_mobs:
                    bd = int(base_dmg * 0.5)
                    m.take_damage(bd)
            pd = int(base_dmg)
            target.take_damage(pd)
            final_primary = pd
            log_msg += f"hit **{target.name}** ({pd})"
        elif self.weapon_id == "staff_of_good_vibes":
            dmg = int(base_dmg * 0.5)
            target.take_damage(dmg)
            heal = int(base_dmg * 0.4)
            for p in [p for p in instance.allies if p.hp > 0]:
                p.register_heal(heal)
            instance.record_healing(
                self.name,
                heal * len(instance.allies),
                source=getattr(self, "weapon_id", None),
            )
            final_primary = dmg
            log_msg += f"hit **{target.name}** ({dmg}) | ❤️ Team (+{heal})"
        else:
            mult = (
                1.2
                if (self.weapon_id == "spinsickle" and self.combo_count >= 6)
                else 1.0
            )
            actual_dmg = int(base_dmg * mult)
            target.take_damage(actual_dmg)
            final_primary = actual_dmg
            log_msg += f"hit **{target.name}** ({actual_dmg})"

        instance.record_damage(
            self.name,
            final_primary,
            target.is_boss,
            source=getattr(self, "weapon_id", None),
        )
        instance.logs.append(log_msg)


class RiftPlayer(RiftEntity):
    def __init__(self, bot, user_id, recommended_gp, name=None):
        u_data = database.get_user_data(user_id)
        lvl, _, _ = utils.get_level_info(u_data["xp"])
        base_hp, player_gp = utils.get_max_hp(user_id, lvl), utils.get_total_gp(user_id)
        super().__init__(u_data["current_title"] or "Hunter", base_hp, player_gp)
        self.bot, self.user_id, self.owner_id = bot, user_id, user_id

        if name:
            self.name = name
        else:
            user_obj = bot.get_user(user_id)
            self.name = (
                user_obj.display_name
                if user_obj
                else u_data["current_title"] or "Hunter"
            )

        self.emblem, self.level, self.action_queue = (
            utils.get_emblem(lvl),
            lvl,
            None,
        )
        self.dash_cd, self.combo_count, self.hits_taken = 0, 0, 0

        self.stat_mults = {
            "dmg": 1.0,
            "heal": 1.0,
            "crit": 0.0,
            "pet_dmg": 1.0,
            "hp": 1.0,
        }
        self.cdr_mult = 1.0
        self.dash_cd_max = 6.0
        self.regen_per_turn = 0
        self.extra_projectiles = 0
        self.combo_accel = 1

        ratio = recommended_gp / max(1, player_gp)
        if ratio < 1.0:
            self.defense_mult = max(0.3, ratio)
        else:
            self.defense_mult = min(2.0, ratio**1.5)

        self._load_loadout(user_id)

        self.max_hp = int(self.max_hp * self.stat_mults["hp"])
        self.hp = self.max_hp

        deficit = recommended_gp - player_gp
        if deficit > 0:
            self.dmg_mult = max(0.25, 1.0 - (deficit / (recommended_gp * 1.5)))
        else:

            self.dmg_mult = min(5.0, 1.0 + (abs(deficit) / 800.0))

    def _load_loadout(self, uid):
        kit = database.get_active_kit(uid)

        self.weapon_id, self.passives, self.gadgets, self.modules = (
            "monster_slugger",
            {},
            [None, None, None],
            [],
        )

        if kit:
            if kit["weapon_id"]:
                w = database.get_item_instance(kit["weapon_id"])
                if w:
                    self.weapon_id = w["item_id"]

            for i in range(3):
                inst_id = kit[f"gadget_{i+1}_id"]
                if inst_id:
                    g = database.get_item_instance(inst_id)
                    if g:
                        item_def = game_data.get_item(g["item_id"])
                        lvl = utils.get_effective_level(g["level"], self.level)
                        self.gadgets[i] = {
                            "id": g["item_id"],
                            "name": item_def["name"],
                            "cd": 0,
                            "max_cd": 15,
                            "lvl": lvl,
                        }
                        if g["item_id"] in [
                            "really_cool_sticker",
                            "very_mean_pendant",
                            "bunch_of_dice",
                            "overcharged_amulet",
                        ]:
                            self.passives[g["item_id"]] = lvl

            for i in range(3):
                inst_id = kit[f"passive_{i+1}_id"]
                if inst_id:
                    p = database.get_item_instance(inst_id)
                    if p:
                        self.passives[p["item_id"]] = utils.get_effective_level(
                            p["level"], self.level
                        )

            for i in range(3):
                inst_id = kit[f"ring_{i+1}_id"]
                if inst_id:
                    r = database.get_item_instance(inst_id)
                    if r:
                        rid = r["item_id"]
                        lvl = r["level"]
                        val1, val2 = scaling.get_ring_stats(rid, lvl)

                        if "insane" in rid:
                            if "cooldown" in rid:
                                self.cdr_mult *= 1.0 - (val1 / 100.0)
                            if "dash" in rid:
                                self.dash_cd_max = val1
                            if "self_healing" in rid:
                                self.regen_per_turn += val1
                            if "weapon_damage" in rid:
                                self.stat_mults["dmg"] += val1 / 100.0
                            if "damage_ring" in rid:
                                self.stat_mults["dmg"] += val1 / 100.0
                            if "projectile_ring" in rid:
                                self.extra_projectiles += int(val1)
                            if "weapon_combo" in rid:
                                self.combo_accel = 1 + int(val1 / 100.0)
                        else:
                            if val2 > 0:
                                self.max_hp += val2
                            if "damage" in rid:
                                self.stat_mults["dmg"] += val1 / 100.0
                            if "health" in rid:
                                self.max_hp += val1
                            if "healing" in rid:
                                self.stat_mults["heal"] += val1 / 100.0
                            if "crit" in rid:
                                self.stat_mults["crit"] += val1
                            if "pet" in rid:
                                self.stat_mults["pet_dmg"] += val1 / 100.0
                            if "time_ring" in rid:
                                self.cdr_mult *= 1.0 - (val1 / 100.0)

            if kit["elite_module_id"]:
                m = database.get_item_instance(kit["elite_module_id"])
                if m:
                    mid, mlvl = m["item_id"], m["level"]
                    self.modules.append({"id": mid, "lvl": mlvl})
                    if mid == "elite_dash_module":
                        self.dash_cd_max *= max(0.5, (1.0 - (0.1 * mlvl)))
                    elif mid == "healing_ride":
                        self.regen_per_turn += 50 * mlvl

    def get_weapon_emoji(self):
        return utils.get_emoji(self.bot, self.weapon_id, self.user_id)

    def tick(self, instance):
        self.tick_status()
        self.is_dashing = False

        if self.regen_per_turn > 0:
            self.register_heal(self.regen_per_turn * TICK_RATE)

        if self.stunned or self.hp <= 0:
            self.action_queue = None
            return
        if self.dash_cd > 0:
            self.dash_cd -= TICK_RATE
        for g in self.gadgets:
            if g and g["cd"] > 0:
                g["cd"] -= TICK_RATE

        self._process_passive_ticks(instance)

        if self.action_queue == "DASH" and self.dash_cd <= 0:
            self.is_dashing, self.dash_cd = True, self.dash_cd_max
            instance.logs.append(f"{config.DASH_EMOJI} **{self.name}** Dashed!")
        elif self.action_queue == "ADVANCE" and self.user_id == instance.leader_id:
            instance.advance_zone_manual()
        elif self.action_queue == "ATTACK":
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                self._perform_attack(sorted(targets, key=lambda x: x.hp)[0], instance)
        elif str(self.action_queue).startswith("GADGET_"):
            idx = int(self.action_queue.split("_")[1])
            if (
                idx < len(self.gadgets)
                and self.gadgets[idx]
                and self.gadgets[idx]["cd"] <= 0
            ):
                self._use_gadget(self.gadgets[idx], instance)
        self.action_queue = None

    def _process_passive_ticks(self, instance):
        if "smelly_socks" in self.passives:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                dmg = 30 + (self.passives["smelly_socks"] * 10)
                if self.stat_mults["dmg"] > 1.0:
                    dmg = int(dmg * self.stat_mults["dmg"])
                dmg = int(dmg * self.dmg_mult)
                random.choice(targets).take_damage(dmg)

        if "auto_zapper" in self.passives:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                dmg = scaling.get_passive_value(
                    "auto_zapper", self.passives["auto_zapper"]
                )
                dmg = int(dmg * self.dmg_mult)
                t = random.choice(targets)
                t.take_damage(dmg)

        if "unstable_lazer" in self.passives and random.random() < 0.20:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                dmg = scaling.get_passive_value(
                    "unstable_lazer", self.passives["unstable_lazer"]
                )
                dmg = int(dmg * self.dmg_mult)
                t = random.choice(targets)
                t.take_damage(dmg)
                if instance.turn_count % 3 == 0:
                    instance.logs.append(f"☄️ **Lazer** hit {t.name}!")

        if "unstable_beam" in self.passives and random.random() < 0.05:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                dmg = scaling.get_passive_value(
                    "unstable_beam", self.passives["unstable_beam"]
                )
                dmg = int(dmg * self.dmg_mult)
                t = random.choice(targets)
                t.take_damage(dmg)
                instance.logs.append(f"🌟 **MEGA BEAM** hit {t.name}!")

        if "randb_mixtape" in self.passives and instance.turn_count % 5 == 0:
            amt = 120 + (self.passives["randb_mixtape"] * 25)
            if "healing_charm" in self.passives:
                amt = int(amt * 1.5)
            amt = int(amt * self.stat_mults["heal"])
            for ally in [a for a in instance.allies if a.hp > 0]:
                ally.register_heal(amt)
            instance.logs.append(
                f"{utils.get_emoji(self.bot, 'randb_mixtape')} **{self.name}'s Mixtape** vibe: ❤️ Team (+{amt})"
            )

    def _use_gadget(self, gadget, instance):
        base_cds = {
            "splash_heal": 16,
            "smart_fireworks": 20,
            "monster_taser": 6,
            "vitamin_shot": 10,
            "life_jacket": 12,
            "boom_box": 10,
            "revitalizing_mist": 8,
            "pepper_spray": 14,
            "snow_globe": 30,
            "multi_zapper": 18,
            "super_loud_whistle": 8,
            "explosive_6_pack": 15,
        }
        base_val = base_cds.get(gadget["id"], 15)
        gadget["cd"] = max(1.0, base_val * self.cdr_mult)
        icon = utils.get_emoji(self.bot, gadget["id"], self.user_id)

        if gadget["id"] in ["explosive_6_pack", "snow_globe", "splash_heal"]:
            self.apply_status("AIRBORNE", 4.0, icon, instance=instance)
            self.is_dashing = True
        elif gadget["id"] == "life_jacket":
            self.apply_status("SHIELDED", 6.0, icon, instance=instance)
            self.is_dashing = True

        if "gadget_battery" in self.passives:
            t = random.choice([m for m in instance.mobs if m.hp > 0])
            if t:
                dmg = int(100 * self.dmg_mult)
                t.take_damage(dmg)
                instance.logs.append(f"⚡ **Battery Zap** ({t.name})")

        if "unstable_lightning" in self.passives and random.random() < (
            0.10 + self.passives["unstable_lightning"] * 0.02
        ):
            dmg = 100 + (self.passives["unstable_lightning"] * 20)
            dmg = int(dmg * self.dmg_mult)
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                t.take_damage(dmg)
                instance.logs.append(
                    f"{utils.get_emoji(self.bot, 'unstable_lightning')} **Unstable Lightning** chain on **{t.name}** ({dmg})"
                )

        if gadget["id"] == "portable_portal":
            pass
        elif gadget["id"] == "splash_heal":
            amt = int((350 + (gadget["lvl"] * 45)) * self.stat_mults["heal"])
            for p in [a for a in instance.allies if a.hp > 0]:
                p.register_heal(amt)
            instance.logs.append(
                f"{icon} **{self.name}** used **{gadget['name']}**: ❤️ Team (+{amt})"
            )
            instance.record_healing(
                self.user_id, amt * len(instance.allies), source=gadget["id"]
            )
        elif gadget["id"] == "explosive_6_pack":
            for m in instance.mobs:
                if m.hp > 0:
                    dmg = int((400 + (gadget["lvl"] * 50)) * self.stat_mults["dmg"])
                    dmg = int(dmg * self.dmg_mult)
                    m.take_damage(dmg, instance=instance)
                    instance.record_damage(
                        self.user_id, dmg, m.is_boss, source=gadget["id"]
                    )
            instance.logs.append(f"{icon} **{self.name}** used **6-Pack**: AOE Blast!")
        elif gadget["id"] == "vitamin_shot":
            amt = int((300 + (gadget["lvl"] * 30)) * self.stat_mults["heal"])
            self.register_heal(amt)
            self.apply_status("HASTE", 5.0, icon, instance=instance)
        elif gadget["id"] == "revitalizing_mist":
            lowest = min([a for a in instance.allies if a.hp > 0], key=lambda x: x.hp)
            amt = int((800 + (gadget["lvl"] * 100)) * self.stat_mults["heal"])
            lowest.register_heal(amt)
            instance.logs.append(
                f"{icon} **{self.name}** mists **{lowest.name}**: ❤️ (+{amt})"
            )
            instance.record_healing(self.user_id, amt, source=gadget["id"])
        elif gadget["id"] == "boom_box":
            for m in instance.mobs:
                if m.hp > 0:
                    dmg = int(200 * self.dmg_mult)
                    m.take_damage(dmg, instance=instance)
                    m.apply_status("STUN", 2.0, "💫", instance=instance)
            instance.logs.append(f"{icon} **{self.name}** used **Boom Box**: Stun AOE!")
        elif gadget["id"] == "monster_taser":
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                dmg = int((500 + (gadget["lvl"] * 50)) * self.stat_mults["dmg"])
                dmg = int(dmg * self.dmg_mult)
                t.take_damage(dmg, stun=True, instance=instance)
                instance.record_damage(
                    self.user_id, dmg, t.is_boss, source=gadget["id"]
                )
                instance.logs.append(
                    f"{icon} **{self.name}** used **{gadget['name']}** ({dmg})"
                )
        elif gadget["id"] == "smart_fireworks":
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:

                hit_targets = random.sample(targets, min(3, len(targets)))
                dmg = int((220 + (gadget["lvl"] * 25)) * self.stat_mults["dmg"])
                dmg = int(dmg * self.dmg_mult)
                for t in hit_targets:
                    t.take_damage(dmg)
                    instance.record_damage(
                        self.user_id, dmg, t.is_boss, source=gadget["id"]
                    )
                instance.logs.append(
                    f"{icon} **{self.name}** used **Fireworks**: Hit {len(hit_targets)} targets ({dmg} ea)"
                )
        elif gadget["id"] == "snow_globe":
            for m in instance.mobs:
                if m.hp > 0:
                    m.apply_status("SLOW", 8.0, "❄️", instance=instance)
            instance.logs.append(
                f"{icon} **{self.name}** used **Snow Globe**: Slow AOE!"
            )
        else:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                dmg = int((350 + (gadget["lvl"] * 40)) * self.stat_mults["dmg"])
                dmg = int(dmg * self.dmg_mult)
                t.take_damage(dmg)
                instance.record_damage(
                    self.user_id, dmg, t.is_boss, source=gadget["id"]
                )
                instance.logs.append(
                    f"{icon} **{self.name}** used **{gadget['name']}** ({dmg})"
                )

    def _perform_attack(self, target, instance):
        self.combo_count += self.combo_accel

        base_dmg = int(
            (250 + (self.level * 25)) * (1.5 if self.has_status("POWER") else 1.0)
        )
        base_dmg = int(base_dmg * self.stat_mults["dmg"])
        base_dmg = int(base_dmg * self.dmg_mult)

        log_msg = f"{self.get_weapon_emoji()} **{self.name}** "
        bonus_proj = self.extra_projectiles

        if self.weapon_id == "techno_fists":
            bounces = 10 if self.combo_count % 10 == 0 else 2
            other_mobs = [m for m in instance.mobs if m.hp > 0 and m != target]
            if other_mobs:
                hit_mobs = random.sample(other_mobs, min(bounces, len(other_mobs)))
                for m in hit_mobs:
                    m.take_damage(int(base_dmg * 0.5))
            target.take_damage(base_dmg)
            log_msg += f"hit **{target.name}** ({base_dmg})"
        elif self.weapon_id == "staff_of_good_vibes":
            dmg = int(base_dmg * 0.4)
            target.take_damage(dmg)
            heal = 50 + (self.level * 6)
            if self.combo_count % 10 == 0:
                heal *= 6
            if "healing_charm" in self.passives:
                heal = int(heal * 1.5)
            heal = int(heal * self.stat_mults["heal"])
            for p in [p for p in instance.allies if p.hp > 0]:
                p.register_heal(heal)
            instance.record_healing(
                self.user_id,
                heal * len(instance.allies),
                source=self.weapon_id,
            )
            log_msg += f"hit **{target.name}** ({dmg}) | ❤️ Team (+{heal})"
        elif self.weapon_id == "medicne_ball" and self.combo_count % 3 == 0:
            target.take_damage(base_dmg)
            heal = int(self.max_hp * 0.05 * self.stat_mults["heal"])
            if "healing_charm" in self.passives:
                heal = int(heal * 1.5)
            for p in [p for p in instance.allies if p.hp > 0]:
                p.register_heal(heal)
            instance.record_healing(
                self.user_id,
                heal * len(instance.allies),
                source=self.weapon_id,
            )
            log_msg += f"hit **{target.name}** ({base_dmg}) | ❤️ Team (+{heal})"
        elif self.weapon_id == "toothpick_and_shield" and self.hits_taken >= 15:
            self.hits_taken = 0
            for m in instance.mobs:
                if m.hp > 0:
                    m.take_damage(int(base_dmg * 3.0), stun=True, instance=instance)
            log_msg += "COUNTER SLAM! (Stun AOE)"
        elif self.weapon_id == "cpu_bomb" and self.combo_count % 8 == 0:
            target.take_damage(int(base_dmg * 2.5), stun=True, instance=instance)
            log_msg += f"MEGA BOMB on **{target.name}** ({int(base_dmg * 2.5)})"
        elif self.weapon_id == "portable_portal" and self.combo_count % 5 == 0:
            target.take_damage(base_dmg)
            if self.gadgets:
                g = self.gadgets[-1]
                if g:
                    g["cd"] = 0
                    log_msg += f"hit **{target.name}** & **Reset {g['name']}!**"
        elif self.weapon_id == "hornbow":
            if self.combo_count % 3 == 0:
                targets = random.sample(
                    [m for m in instance.mobs if m.hp > 0],
                    min(5, len([m for m in instance.mobs if m.hp > 0])),
                )
                for t in targets:
                    t.take_damage(base_dmg)
                log_msg += "PIERCING SHOT (5 targets)"
            elif bonus_proj > 0:
                targets = random.sample(
                    [m for m in instance.mobs if m.hp > 0],
                    min(
                        1 + bonus_proj,
                        len([m for m in instance.mobs if m.hp > 0]),
                    ),
                )
                for t in targets:
                    t.take_damage(base_dmg)
                log_msg += f"MULTI-SHOT ({len(targets)} targets)"
            else:
                target.take_damage(base_dmg)
                log_msg += f"hit **{target.name}** ({base_dmg})"
        elif self.weapon_id == "poison_bow" and self.combo_count % 5 == 0:
            target.take_damage(base_dmg)
            target.apply_status("POISON", 10.0, "🧪", instance=instance)
            log_msg += f"POISON arrow on **{target.name}**"
        elif self.weapon_id == "speedshot" and self.combo_count >= 10:
            actual = int(base_dmg * 1.5)
            target.take_damage(actual)
            log_msg += f"SPEED-SHOT **{target.name}** ({actual})"
        elif self.weapon_id == "spinsickle" and self.combo_count % 6 == 0:
            for m in [m for m in instance.mobs if m.hp > 0]:
                m.take_damage(int(base_dmg * 1.5))
            log_msg += "performed **SPIN ATTACK** AOE"
        elif self.weapon_id == "squid_blades":
            actual_dmg = int(base_dmg * 1.2)
            target.take_damage(actual_dmg)
            if self.combo_count >= 8:
                self.apply_status("INVISIBLE", 4.0, "👻", instance=instance)
                log_msg += f"hit **{target.name}** and vanished! (Invisible)"
                self.combo_count = 0
            else:
                log_msg += f"rapid-stabbed **{target.name}** ({actual_dmg})"
        else:
            mult = (
                1.8
                if (self.weapon_id == "monster_slugger" and self.combo_count % 4 == 0)
                else 1.0
            )
            final_dmg = int(base_dmg * mult * (1 + (self.gp / 2000)))
            target.take_damage(final_dmg)
            log_msg += f"hit **{target.name}** ({final_dmg})"

        if "vampire_teeth" in self.passives:
            h = int(base_dmg * 0.05)
            if "healing_charm" in self.passives:
                h = int(h * 1.5)
            self.register_heal(h)
            log_msg += f" | ❤️ self (+{h})"

        if (
            self.stat_mults["crit"] > 0
            and random.random() * 100 < self.stat_mults["crit"]
        ):
            log_msg += " (CRIT!)"

        instance.record_damage(
            self.user_id,
            base_dmg,
            target.is_boss,
            source=getattr(self, "weapon_id", None),
        )
        instance.logs.append(log_msg)

    def take_damage(self, amount, stun=False, instance=None):
        dodge_chance = 0
        if "pocket_airbag" in self.passives:
            dodge_chance += scaling.get_passive_value(
                "pocket_airbag", self.passives["pocket_airbag"]
            )
        if "bunch_of_dice" in self.passives:
            dodge_chance += scaling.get_passive_value(
                "bunch_of_dice", self.passives["bunch_of_dice"]
            )

        if dodge_chance > 0 and random.random() * 100 < dodge_chance:
            if instance:
                instance.logs.append(f"💨 **{self.name}** Dodged!")
            return 0

        if "chicken_o_matic" in self.passives:
            if random.random() * 100 < scaling.get_passive_value(
                "chicken_o_matic", self.passives["chicken_o_matic"]
            ):
                if instance:
                    instance.logs.append(
                        f"🐔 **Chicken-O-Matic** tanked the hit for **{self.name}**!"
                    )
                return 0

        if (
            self.is_dashing
            or self.has_status("SHIELDED")
            or self.has_status("DODGE")
            or self.has_status("INVISIBLE")
            or self.has_status("AIRBORNE")
        ):
            return
        self.hits_taken += 1

        if "cactus_charm" in self.passives and instance:
            ref_pct = (
                scaling.get_passive_value("cactus_charm", self.passives["cactus_charm"])
                / 100.0
            )
            ref_dmg = int(amount * ref_pct)
            alive_mobs = [m for m in instance.mobs if m.hp > 0]
            if alive_mobs:
                t = random.choice(alive_mobs)
                t.take_damage(ref_dmg)

        reduced_dmg = int(amount * self.defense_mult)

        if self.hits_taken_this_tick > 0:
            reduced_dmg = int(reduced_dmg * (0.85**self.hits_taken_this_tick))

        self.hits_taken_this_tick += 1

        self.hp -= int(reduced_dmg * self.dmg_mult)
        if self.hp <= 0:
            self.hp = 0
            self.death_time = time.time()

            if self.user_id:
                pedia.track_death(self.user_id, "Rift Monster")
        elif stun:
            self.stun_duration, self.stunned = 4.0, True


class RiftMob(RiftEntity):
    def __init__(self, bot, name, level, is_boss=False):

        base_hp = (8000 if is_boss else 800) * (1 + (level / 20.0))
        super().__init__(name, int(base_hp), 0)
        self.is_boss, self.level, self.state, self.bot = (
            is_boss,
            level,
            "IDLE",
            bot,
        )
        self.icon, self.loot_awarded, self.ability_cd = (
            self._resolve_icon(name),
            False,
            0,
        )

    def _resolve_icon(self, name):
        if name in config.MOBS:
            return config.MOBS[name]
        if name == "Berserker":
            return "<:beserker:1452460270093078549>"
        clean = name.lower().replace(" ", "_")
        if clean.startswith("royal_"):
            return "<:royal_knight:1452460324799381517>"
        if "mama" in clean:
            return "<:mama_boomer:1452460283132907692>"
        emap = self.bot.emoji_map
        if clean in emap:
            return emap[clean]
        for k, v in emap.items():
            if k.endswith(clean):
                return v
        return "👹"

    def tick(self, instance, allies):
        if self.hp <= 0:
            return None
        self.tick_status()
        if self.stunned:
            return None

        if self.has_status("SLOW") and random.random() < 0.50:
            return None

        if self.ability_cd > 0:
            self.ability_cd -= 1
        base_dmg = 250 if not self.is_boss else 800

        dmg_mult = 1.0
        if instance.difficulty == "Hard":
            dmg_mult = 1.5
        elif instance.difficulty == "Nightmare":
            dmg_mult = 3.0
        base_dmg = int(base_dmg * dmg_mult)

        alive_retaliation = [
            a for a in allies if a.hp > 0 and not a.has_status("INVISIBLE")
        ]
        if not alive_retaliation:
            return None
        target = random.choice(
            [a for a in alive_retaliation if (isinstance(a, RiftSummon) and a.taunt)]
            or alive_retaliation
        )
        if target:
            target.take_damage(base_dmg)
            if hasattr(target, "user_id"):
                instance.record_tank(target.user_id, base_dmg)
            instance.logs.append(
                f"{self.icon} **{self.name}** hit **{target.name}** ({base_dmg})"
            )
        return None


class RiftCombatView(View):
    def __init__(self, instance):
        super().__init__(timeout=None)
        self.instance = instance

        can_advance = self.instance.rift_key != "rift_van_defense"
        self.add_item(
            CombatButton(
                "ATTACK",
                "Attack",
                config.EMPTY_WEAPON,
                discord.ButtonStyle.primary,
                0,
            )
        )
        self.add_item(
            CombatButton(
                "DASH",
                "Dash (6s)",
                config.DASH_EMOJI,
                discord.ButtonStyle.success,
                0,
            )
        )
        self.add_item(OpenGadgetsButton())
        if can_advance:
            self.add_item(
                CombatButton(
                    "ADVANCE",
                    "Advance",
                    config.MAP_EMOJI,
                    discord.ButtonStyle.danger,
                    0,
                )
            )


class CombatButton(Button):
    def __init__(self, action, label, emoji, style, row):
        super().__init__(
            label=label, style=style, emoji=utils.safe_emoji(emoji), row=row
        )
        self.action = action

    async def callback(self, interaction):
        player = next(
            (
                p
                for p in self.view.instance.players
                if isinstance(p, RiftPlayer) and p.user_id == interaction.user.id
            ),
            None,
        )
        if player:
            if player.hp <= 0:
                rem = int(RESPAWN_TIME - (time.time() - player.death_time))
                return await interaction.response.send_message(
                    f"Enemies got you!\nReturning in **{max(0, rem)}** seconds!",
                    ephemeral=True,
                )
            if player.action_queue:
                return await interaction.response.send_message(
                    "❌ Action already queued!", ephemeral=True
                )

            player.action_queue = self.action
            q_emoji = (
                player.get_weapon_emoji() if self.action == "ATTACK" else self.emoji
            )
            await interaction.response.send_message(
                f"{q_emoji} **{self.label}** Queued!", ephemeral=True
            )
            await asyncio.sleep(1.0)
            await interaction.delete_original_response()
        else:
            await interaction.response.send_message(
                "You are not in control!", ephemeral=True
            )


class OpenGadgetsButton(Button):
    def __init__(self):
        super().__init__(
            label="Gadgets / Build",
            style=discord.ButtonStyle.secondary,
            emoji=utils.safe_emoji(config.EMPTY_GADGET),
        )

    async def callback(self, interaction):
        player = next(
            (
                p
                for p in self.view.instance.players
                if isinstance(p, RiftPlayer) and p.user_id == interaction.user.id
            ),
            None,
        )
        if player:
            if player.hp <= 0:
                rem = int(RESPAWN_TIME - (time.time() - player.death_time))
                return await interaction.response.send_message(
                    f"Enemies got you!\nReturning in **{max(0, rem)}** seconds!",
                    ephemeral=True,
                )
            view = RiftGadgetView(self.view.instance, player, self.view.instance.bot)
            embed = self.view.instance.bot.get_cog("Loadout").generate_kit_embed(
                player.user_id, player.name
            )
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )


class RiftGadgetView(View):
    def __init__(self, instance, player, bot):
        super().__init__(timeout=60)
        self.instance, self.player, self.bot = instance, player, bot
        has_gadgets = False
        for i, g in enumerate(player.gadgets):
            if g:
                self.add_item(SpecificGadgetButton(i, g, bot))
                has_gadgets = True
        if not has_gadgets:
            self.add_item(
                Button(
                    label="No Gadgets Equipped!",
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                )
            )


class SpecificGadgetButton(Button):
    def __init__(self, index, gadget_data, bot):
        icon = utils.get_emoji(bot, gadget_data["id"])
        super().__init__(
            label=gadget_data["name"],
            style=discord.ButtonStyle.secondary,
            emoji=utils.safe_emoji(icon),
            disabled=(gadget_data["cd"] > 0),
        )
        self.index, self.icon_str = index, icon

    async def callback(self, interaction):
        if self.view.player.hp <= 0:
            return
        if self.view.player.action_queue:
            return await interaction.response.send_message(
                "❌ Action already queued!", ephemeral=True
            )
        self.view.player.action_queue = f"GADGET_{self.index}"
        await interaction.response.edit_message(
            content=f"{self.icon_str} **{self.label}** Queued!",
            embed=None,
            view=None,
        )
        await asyncio.sleep(1.0)
        await interaction.delete_original_response()


class RiftResultsView(View):
    def __init__(self, instance, success):
        super().__init__(timeout=None)
        self.instance, self.success = instance, success

    def get_embed(self):
        title = (
            f"{config.RIFTS_EMOJI} RIFT CLEARED: {self.instance.rift_def['name']}"
            if self.success
            else "💀 RIFT FAILED"
        )
        color = 0xF1C40F if self.success else 0xE74C3C
        embed = discord.Embed(title=title, color=color)
        m, s = divmod(self.instance.turn_count * TICK_RATE, 60)
        if self.success:
            embed.description = f"⏱️ **Clear Time:** {int(m)}m {int(s)}s (Stability: {self.instance.stability}%)"
        else:
            embed.description = f"⏱️ The rift has collapsed after {int(m)}m {int(s)}s."
        stats = self.instance.player_stats
        players = self.instance.players
        best_boss = max(players, key=lambda p: stats[p.owner_id].dmg_boss)
        if stats[best_boss.owner_id].dmg_boss > 0:
            embed.add_field(
                name="Boss Damage",
                value=f"{best_boss.get_weapon_emoji()} **{best_boss.name}** ({stats[best_boss.owner_id].dmg_boss:,})",
                inline=True,
            )
        best_mob = max(players, key=lambda p: stats[p.owner_id].dmg_mobs)
        if stats[best_mob.owner_id].dmg_mobs > 0:
            embed.add_field(
                name="Non-Boss Damage",
                value=f"{best_mob.get_weapon_emoji()} **{best_mob.name}** ({stats[best_mob.owner_id].dmg_mobs:,})",
                inline=True,
            )
        best_tank = max(players, key=lambda p: stats[p.owner_id].dmg_tanked)
        if stats[best_tank.owner_id].dmg_tanked > 0:
            embed.add_field(
                name="Damage Tanked",
                value=f"{best_tank.emblem} **{best_tank.name}** ({stats[best_tank.owner_id].dmg_tanked:,})",
                inline=True,
            )
        best_healer = max(players, key=lambda p: stats[p.owner_id].healing)
        if stats[best_healer.owner_id].healing > 0:
            embed.add_field(
                name="Total Healing",
                value=f"❤️ **{best_healer.name}** ({stats[best_healer.owner_id].healing:,})",
                inline=True,
            )
        return embed

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.instance._distribute_loot(partial=not self.success)
        view = RiftLootView(self.instance)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class RiftLootView(View):
    def __init__(self, instance):
        super().__init__(timeout=None)
        self.instance = instance

        if self.instance.banked_loot["cores"] > 0:

            btn = discord.ui.Button(
                label="Open Cores",
                style=discord.ButtonStyle.secondary,
                emoji=utils.safe_emoji(config.CHAOS_CORE_EMOJI),
            )
            btn.callback = self.open_cores
            self.add_item(btn)

    def get_embed(self):
        embed = discord.Embed(title="📦 Rift Rewards", color=0x9B59B6)
        loot = self.instance.banked_loot
        val = f"{config.XP_EMOJI} {loot['xp']:,} XP\n{config.CHAOS_SHARD_EMOJI} {loot['shards']} Shards\n{config.CHAOS_CORE_EMOJI} {loot['cores']} Cores"
        for p in self.instance.players:
            if isinstance(p, RiftPlayer):
                embed.add_field(name=f"{p.name}", value=val, inline=True)
        return embed

    async def open_cores(self, interaction: discord.Interaction):
        inv_cog = self.instance.bot.get_cog("Inventory")
        if inv_cog:
            await inv_cog.open_cmd.callback(inv_cog, interaction)

    @discord.ui.button(label="Return Home", style=discord.ButtonStyle.success)
    async def return_lobby(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        from mo_co.cogs.teams import LobbyView, ACTIVE_LOBBIES

        thread_id = self.instance.channel.id
        if thread_id in ACTIVE_LOBBIES:
            lobby = ACTIVE_LOBBIES[thread_id]
            if lobby.get("is_solo"):
                del ACTIVE_LOBBIES[thread_id]
                await interaction.message.delete()
                return
            for m in lobby["members"]:
                lobby["ready"][m] = False
            await interaction.response.send_message(
                embed=LobbyView(self.instance.bot, thread_id).get_embed(),
                view=LobbyView(self.instance.bot, thread_id),
            )
            await interaction.message.delete()
        else:
            await interaction.message.delete()

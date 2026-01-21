import discord
from discord.ui import View, Button, Select
import asyncio
import time
import random
import json
from mo_co import config, database, utils, game_data
from mo_co.rift_engine import RiftPlayer, RiftBot, RiftEntity, TICK_RATE

AOE_WEAPONS = {
    "monster_slugger",
    "staff_of_good_vibes",
    "toothpick_and_shield",
    "cpu_bomb",
    "medicne_ball",
    "spinsickle",
    "buzz_kill",
    "hornbow",
    "singularity",
    "poison_bow",
}
MULTI_HIT_WEAPONS = {"techno_fists"}
AOE_GADGETS = {
    "smart_fireworks",
    "boom_box",
    "pepper_spray",
    "snow_globe",
    "explosive_6_pack",
    "very_mean_pendant",
}
AURA_PASSIVES = {"smelly_socks"}
PASSIVE_AOE = {"explode_o_matic_trigger", "unstable_lazer"}

DOJO_TIME_LIMIT = 90
SOLO_MOB_HP_MULT = 0.3


class DojoInstance:
    def __init__(self, bot, user, dojo_key):
        self.bot, self.user_id, self.dojo_key = bot, user.id, dojo_key
        self.dojo_def = game_data.DOJOS.get(dojo_key)
        self.start_time, self.turn_count, self.active, self.message = (
            None,
            0,
            True,
            None,
        )
        self.grace_timer = 5

        self.difficulty = "Normal"

        self.player = DojoPlayer(bot, user.id, self.dojo_def["recommended_gp"])
        self.player.name = user.display_name
        self.player_stats = {
            "damage": 0,
            "healing": 0,
            "tanked": 0,
            "damage_sources": {},
            "heal_sources": {},
        }

        self.companions = []
        companion_names = self.dojo_def.get("companions", ["Luna"])

        comp_level = self.player.level
        if dojo_key == "dojo_helping_hands":
            comp_level = 70
        elif dojo_key == "dojo_taking_hits":
            comp_level = 100

        for c_name in companion_names:
            bot_entity = RiftBot(
                bot, c_name, comp_level, self.dojo_def["recommended_gp"]
            )
            if dojo_key == "dojo_taking_hits" and c_name == "Jax":
                bot_entity.attack_pwr_bonus = 5.0
            self.companions.append(bot_entity)

        self.allies = [self.player] + self.companions

        self.mobs = []

        self.title_emoji = config.DOJO_ICON
        self.target_focus = "Lowest HP"
        self.logs = [f"{config.DOJO_ICON} **Dojo Starting... Prepare yourself!**"]

    def _spawn_wave(self):
        new_mobs = []

        hp_mult = 1.0
        if self.difficulty == "Hard":
            hp_mult = 1.5
        elif self.difficulty == "Nightmare":
            hp_mult = 2.5

        for m_cfg in self.dojo_def["mobs"]:
            m = DojoMob(
                self.bot,
                m_cfg["id"],
                m_cfg["lvl"],
                is_swarm=m_cfg.get("is_swarm", False),
                count=m_cfg.get("count", 1),
                is_boss=m_cfg.get("is_boss", False),
            )
            m.max_hp = int(m.max_hp * hp_mult)
            m.hp = m.max_hp

            new_mobs.append(m)
        return new_mobs

    async def start_loop(self, interaction):
        self.mobs = self._spawn_wave()
        self.message = await interaction.edit_original_response(
            content=None, embed=self._build_embed(), view=DojoCombatView(self)
        )

        while self.active:
            if self.grace_timer > 0:
                await asyncio.sleep(1.0)
                self.grace_timer -= 1
                if self.grace_timer == 0:
                    self.start_time = time.time()
            else:
                await asyncio.sleep(TICK_RATE)
                await self._tick()

            if not self.active:
                break
            try:
                await self.message.edit(
                    embed=self._build_embed(), view=DojoCombatView(self)
                )
            except:
                self.active = False

    async def _tick(self):
        self.turn_count += 1
        elapsed = time.time() - self.start_time
        if elapsed >= DOJO_TIME_LIMIT:
            self.logs.append("⏰ **OUT OF TIME!**")
            self.active = False
            await self._end_game(False)
            return
        if self.player.hp <= 0:
            self.logs.append("💀 **DEFEATED!**")
            self.active = False
            await self._end_game(False)
            return

        if self.dojo_key == "dojo_helping_hands":
            alive_comps = [c for c in self.companions if c.hp > 0]
            if not alive_comps:
                self.logs.append("💀 **Companions fell! Boss Enraged!**")
                self.player.take_damage(999999)
                self.active = False
                await self._end_game(False)
                return

        if self.dojo_key == "dojo_taking_hits":
            alive_jax = [c for c in self.companions if c.name == "Jax" and c.hp > 0]
            if not alive_jax:
                self.logs.append("💀 **Jax fell! Mission Failed.**")
                self.active = False
                await self._end_game(False)
                return

        self.player.is_dashing = False

        for ally in self.allies:
            if ally.hp > 0:
                ally.tick(self)

        self.mobs = [m for m in self.mobs if m.hp > 0]
        if not self.mobs:
            self.logs.append("🏆 **VICTORY!**")
            self.active = False
            await self._end_game(True)
            return

        for mob in self.mobs:
            potential_targets = [a for a in self.allies if a.hp > 0]
            if not potential_targets:
                continue

            aggro_target = self.player

            if self.dojo_key == "dojo_helping_hands":
                companions_alive = [c for c in self.companions if c.hp > 0]
                if companions_alive and random.random() < 0.70:
                    aggro_target = random.choice(companions_alive)
            elif self.dojo_key == "dojo_taking_hits":
                aggro_target = self.player
            else:
                alive_comps = [c for c in self.companions if c.hp > 0]
                if alive_comps and random.random() < 0.3:
                    aggro_target = random.choice(alive_comps)

            mob.tick(self, [aggro_target])

    def calculate_swarm_damage(self, source_id, base_dmg, target):
        if not target.is_swarm:
            return base_dmg
        mult = 1.0
        if source_id in AOE_WEAPONS or source_id in AOE_GADGETS:
            mult = 4.0
        elif source_id in MULTI_HIT_WEAPONS:
            mult = 2.5
        elif source_id in AURA_PASSIVES:
            mult = 2.0
        elif source_id in PASSIVE_AOE:
            mult = 3.0
        return int(base_dmg * mult)

    def _build_embed(self):
        remaining_str = "--:--"
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            remaining = max(0, DOJO_TIME_LIMIT - elapsed)
            m, s = divmod(remaining, 60)
            remaining_str = f"{m}:{s:02d}"

        embed = discord.Embed(
            title=f"{self.title_emoji} {self.dojo_def['name']} ({self.difficulty})",
            color=0x9B59B6,
        )
        if self.grace_timer > 0:
            embed.description = (
                f"{config.LOADING_EMOJI} **PREPARING:** `{self.grace_timer}s`"
            )
        else:
            embed.description = f"⏱️ **Time Left:** `{remaining_str}`"

        m_list = []
        for m in self.mobs:
            s_tag = f" (x{m.unit_count})" if m.is_swarm else ""
            f_tag = " 🎯" if self.target_focus == m.name else ""
            m_list.append(f"{m.icon} **{m.name}{s_tag}**: {m.hp}/{m.max_hp} HP{f_tag}")
        embed.add_field(name="Enemies", value="\n".join(m_list), inline=False)

        a_list = []
        for a in self.allies:
            icon = (
                a.emblem
                if hasattr(a, "emblem")
                else config.BOT_EMOJIS.get(a.name, "👤")
            )
            a_list.append(
                f"{icon} **{a.name}**: {a.hp}/{a.max_hp} HP {a.get_status_str()}"
            )
        embed.add_field(name="Allies", value="\n".join(a_list), inline=False)

        if self.logs:
            embed.add_field(
                name="Combat Log",
                value="\n".join(self.logs[-5:]),
                inline=False,
            )
        return embed

    async def _end_game(self, success):
        clear_time = int(time.time() - self.start_time) if self.start_time else 0
        u_data = database.get_user_data(self.user_id)
        best_times = json.loads(u_data["dojo_best_times"] or "{}")
        old_best = best_times.get(self.dojo_key)
        claimed_projects = []
        if success:
            if old_best is None or clear_time < old_best:
                best_times[self.dojo_key] = clear_time
            completed = json.loads(u_data["completed_dojos"] or "[]")
            if self.dojo_key not in completed:
                completed.append(self.dojo_key)
            database.update_user_stats(
                self.user_id,
                {
                    "completed_dojos": json.dumps(completed),
                    "dojo_best_times": json.dumps(best_times),
                },
            )
            hunt_cog = self.bot.get_cog("Hunting")
            if hunt_cog:

                mod_str = f"Standard-{self.difficulty}"
                _, cleared_projs = hunt_cog.update_progression(
                    self.user_id,
                    None,
                    self.dojo_key,
                    mod_str,
                    "Normal",
                    rift_time=clear_time,
                )
                claimed_projects = cleared_projs
            database.update_user_stats(
                self.user_id,
                {
                    "xp": u_data["xp"] + 500,
                    "chaos_cores": u_data["chaos_cores"] + 1,
                },
            )
        view = DojoSummaryView(self, success, clear_time, old_best, claimed_projects)
        await self.message.edit(embed=view.get_embed(), view=view)

    def record_damage(self, uid, amt, is_boss, source=None):
        if uid == self.user_id:
            self.player_stats["damage"] += amt
            if source:
                self.player_stats["damage_sources"][source] = (
                    self.player_stats["damage_sources"].get(source, 0) + amt
                )

    def record_healing(self, uid, amt, source=None):
        if uid == self.user_id:
            self.player_stats["healing"] += amt
            if source:
                self.player_stats["heal_sources"][source] = (
                    self.player_stats["heal_sources"].get(source, 0) + amt
                )

    def record_tank(self, uid, amt):
        if uid == self.user_id:
            self.player_stats["tanked"] += amt


class DojoPlayer(RiftPlayer):
    def tick(self, instance):
        if instance.grace_timer > 0:
            self.tick_status()
            return

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

        if self.action_queue and "GADGET_" in str(self.action_queue):
            idx = int(self.action_queue.split("_")[1])
            if idx < len(self.gadgets) and self.gadgets[idx]:
                g_id = self.gadgets[idx]["id"]
                icon = utils.get_emoji(instance.bot, g_id, self.user_id)
                if g_id in ["explosive_6_pack", "snow_globe"]:
                    self.apply_status("AIRBORNE", 4.0, icon, instance=instance)
                    self.is_dashing = True
                elif g_id == "life_jacket":
                    self.apply_status("SHIELDED", 6.0, icon, instance=instance)
                    self.is_dashing = True

        self._process_passive_ticks(instance)

        if self.action_queue == "DASH" and self.dash_cd <= 0:
            self.is_dashing, self.dash_cd = True, self.dash_cd_max
            instance.logs.append(f"{config.DASH_EMOJI} **{self.name}** Dashed!")
        elif self.action_queue == "ATTACK":
            alive_mobs = [m for m in instance.mobs if m.hp > 0]
            if alive_mobs:
                target = None
                if instance.target_focus == "Lowest HP":
                    target = sorted(alive_mobs, key=lambda x: x.hp)[0]
                else:
                    target = next(
                        (m for m in alive_mobs if m.name == instance.target_focus),
                        alive_mobs[0],
                    )
                self._perform_attack(target, instance)
        elif str(self.action_queue).startswith("GADGET_"):
            idx = int(self.action_queue.split("_")[1])
            if (
                idx < len(self.gadgets)
                and self.gadgets[idx]
                and self.gadgets[idx]["cd"] <= 0
            ):
                self._use_gadget(self.gadgets[idx], instance)

        self.tick_status()
        self.action_queue = None

    def _process_passive_ticks(self, instance):
        if "smelly_socks" in self.passives:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                base = 20 + (self.passives["smelly_socks"] * 8)
                dmg = instance.calculate_swarm_damage("smelly_socks", base, t)
                if self.stat_mults["dmg"] > 1.0:
                    dmg = int(dmg * self.stat_mults["dmg"])
                t.take_damage(dmg)

        if "auto_zapper" in self.passives:
            targets = [m for m in instance.mobs if m.hp > 0]
            if targets:
                t = random.choice(targets)
                base = 10 + (self.passives["auto_zapper"] * 5)
                dmg = instance.calculate_swarm_damage("auto_zapper", base, t)
                t.take_damage(dmg)

        if "randb_mixtape" in self.passives and instance.turn_count % 5 == 0:
            amt = 120 + (self.passives["randb_mixtape"] * 25)
            if "healing_charm" in self.passives:
                amt = int(amt * 1.5)
            amt = int(amt * self.stat_mults["heal"])
            actual = self.register_heal(amt)
            instance.logs.append(
                f"{utils.get_emoji(instance.bot, 'randb_mixtape')} **Mixtape Vibe**: ❤️ (+{actual})"
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

        icon = utils.get_emoji(instance.bot, gadget["id"], self.user_id)

        if "gadget_battery" in self.passives:
            t = random.choice([m for m in instance.mobs if m.hp > 0])
            if t:
                dmg = instance.calculate_swarm_damage("gadget_battery", 100, t)
                t.take_damage(dmg)
                instance.logs.append(f"⚡ **Battery Zap** ({dmg})")

        if "unstable_lightning" in self.passives and random.random() < (
            0.10 + self.passives["unstable_lightning"] * 0.02
        ):
            t = random.choice([m for m in instance.mobs if m.hp > 0])
            if t:
                dmg = instance.calculate_swarm_damage("unstable_lightning", 150, t)
                t.take_damage(dmg)
                instance.logs.append(f"🔌 **Chain Lightning** ({dmg})")

        if gadget["id"] == "splash_heal":
            amt = int((350 + (gadget["lvl"] * 45)) * self.stat_mults["heal"])
            for a in instance.allies:
                a.register_heal(amt)
            instance.logs.append(
                f"{icon} **{self.name}** used **{gadget['name']}**: ❤️ Team (+{amt})"
            )
        elif gadget["id"] == "explosive_6_pack":
            for m in instance.mobs:
                if m.hp > 0:
                    dmg = 400 + (gadget["lvl"] * 40)
                    dmg = int(dmg * self.stat_mults["dmg"])
                    dmg = instance.calculate_swarm_damage(gadget["id"], dmg, m)
                    m.take_damage(dmg)
            instance.logs.append(
                f"{icon} **{self.name}** used **6-Pack**: 💥 **CLEAVED SWARM!**"
            )
        elif gadget["id"] == "boom_box":
            for m in instance.mobs:
                if m.hp > 0:
                    dmg = instance.calculate_swarm_damage(gadget["id"], 200, m)
                    m.take_damage(dmg, stun=True)
            instance.logs.append(
                f"{icon} **{self.name}** used **Boom Box**: 💫 Stun AOE!"
            )
        elif gadget["id"] == "snow_globe":
            for m in instance.mobs:
                if m.hp > 0:
                    m.apply_status("SLOW", 8.0, "❄️")
            instance.logs.append(
                f"{icon} **{self.name}** used **Snow Globe**: ❄️ Frozen AOE!"
            )
        else:
            t = random.choice([m for m in instance.mobs if m.hp > 0])
            raw_dmg = 350 + (gadget["lvl"] * 40)
            raw_dmg = int(raw_dmg * self.stat_mults["dmg"])

            dmg = instance.calculate_swarm_damage(gadget["id"], raw_dmg, t)
            t.take_damage(dmg)
            instance.logs.append(
                f"{icon} **{self.name}** used **{gadget['name']}** ({dmg})"
            )

    def _perform_attack(self, target, instance):
        self.combo_count += self.combo_accel

        base_dmg = int(
            (200 + (self.level * 15)) * (1.5 if self.has_status("POWER") else 1.0)
        )
        base_dmg = int(base_dmg * self.stat_mults["dmg"])

        if instance.dojo_key == "dojo_taking_hits":
            base_dmg = int(base_dmg * 0.1)

        w_icon = self.get_weapon_emoji()

        if self.weapon_id == "monster_slugger":
            is_combo = self.combo_count % 4 == 0
            mult = 1.5 if is_combo else 1.0
            dmg = instance.calculate_swarm_damage(
                self.weapon_id, int(base_dmg * mult), target
            )
            target.take_damage(dmg, stun=is_combo)
            verb = "CLEAVED" if target.is_swarm else "hit"
            instance.logs.append(
                f"{w_icon} **{self.name}** {verb} **{target.name}** ({dmg})"
            )

        elif self.weapon_id == "staff_of_good_vibes":
            dmg = instance.calculate_swarm_damage(
                self.weapon_id, int(base_dmg * 0.4), target
            )
            target.take_damage(dmg)
            heal = 50 + (self.level * 6)
            if self.combo_count % 10 == 0:
                heal *= 6
            heal = int(heal * self.stat_mults["heal"])
            for a in instance.allies:
                a.register_heal(heal)
            instance.logs.append(
                f"{w_icon} **{self.name}** hit **{target.name}** ({dmg}) | ❤️ Team (+{heal})"
            )

        elif self.weapon_id == "techno_fists":
            mult = 2.5 if target.is_swarm else 1.0
            if self.combo_count % 10 == 0:
                mult *= 2.0
            dmg = int(base_dmg * mult)
            target.take_damage(dmg)
            instance.logs.append(
                f"{w_icon} **{self.name}** hit **{target.name}** ({dmg})"
            )

        elif self.weapon_id == "hornbow":
            mult = 4.0 if target.is_swarm else 1.5
            dmg = int(base_dmg * mult)
            target.take_damage(dmg)
            instance.logs.append(
                f"{w_icon} **{self.name}** PIERCED **{target.name}** ({dmg})"
            )

        else:
            dmg = instance.calculate_swarm_damage(self.weapon_id, base_dmg, target)
            target.take_damage(dmg)
            instance.logs.append(
                f"{w_icon} **{self.name}** hit **{target.name}** ({dmg})"
            )

        if "vampire_teeth" in self.passives:
            h = int(base_dmg * (0.05 + (self.passives["vampire_teeth"] * 0.01)))
            actual = self.register_heal(h)
            if actual > 50:
                instance.logs.append(f"🦷 **Lifesteal**: ❤️ (+{actual})")


class DojoMob:
    def __init__(self, bot, mob_id, level, is_swarm=False, count=1, is_boss=False):
        from mo_co.rift_engine import RiftMob

        ref = RiftMob(bot, mob_id, level, is_boss)
        (
            self.name,
            self.icon,
            self.is_boss,
            self.is_swarm,
            self.unit_count,
            self.level,
        ) = (
            utils.format_monster_name(mob_id),
            ref.icon,
            is_boss,
            is_swarm,
            count,
            level,
        )
        self.unit_hp = int(ref.max_hp * SOLO_MOB_HP_MULT)
        self.max_hp = self.unit_hp * count
        (
            self.hp,
            self.status_effects,
            self.stunned,
            self.stun_duration,
            self.state,
        ) = (
            self.max_hp,
            [],
            False,
            0,
            "IDLE",
        )
        self.ability_cd = 0

    def take_damage(self, amount, stun=False, instance=None):
        self.hp = max(0, self.hp - amount)
        if self.is_swarm:
            self.unit_count = (self.hp // self.unit_hp) + (
                1 if self.hp % self.unit_hp > 0 else 0
            )
        if stun and not self.is_boss:
            self.stunned, self.stun_duration = True, 4.0

    def tick(self, instance, targets):
        if self.hp <= 0:
            return
        if self.stunned:
            self.stun_duration -= TICK_RATE
            if self.stun_duration <= 0:
                self.stunned = False
            return

        target = targets[0]
        if target.is_dashing:
            return

        if instance.dojo_key == "dojo_one_on_one" and self.name == "Berserker":
            if self.ability_cd <= 0:
                instance.logs.append(f"🌪️ **Berserker** spins furiously!")
                self.ability_cd = 8
                for a in instance.allies:
                    a.take_damage(600)
                return
            self.ability_cd -= TICK_RATE

        dmg = 200 + (self.level * 10)
        if self.is_boss:
            dmg *= 2
        if self.is_swarm:
            dmg = int(dmg * (0.3 + (self.unit_count * 0.05)))

        dmg_mult = 1.0
        if instance.difficulty == "Hard":
            dmg_mult = 1.5
        elif instance.difficulty == "Nightmare":
            dmg_mult = 3.0
        dmg = int(dmg * dmg_mult)

        target.take_damage(dmg)
        instance.record_tank(getattr(target, "user_id", None), dmg)
        instance.logs.append(
            f"{self.icon} **{self.name}** hit **{target.name}** ({dmg})"
        )

    def get_status_str(self):
        return "💫" if self.stunned else ""


class DojoSummaryView(View):
    def __init__(self, instance, success, clear_time, old_best, projects):
        super().__init__(timeout=None)
        (
            self.instance,
            self.success,
            self.clear_time,
            self.old_best,
            self.projects,
        ) = (
            instance,
            success,
            clear_time,
            old_best,
            projects,
        )

    def format_time(self, seconds):
        if seconds is None:
            return "--:--"
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    def get_embed(self):
        title, color = (
            f"{config.DOJO_ICON} {self.instance.dojo_def['name']}",
            (0x2ECC71 if self.success else 0xE74C3C),
        )
        embed = discord.Embed(title=title, color=color)
        if not self.success:
            embed.description = "### 💀 Dojo Failed\nBetter luck next time, Hunter!"
            return embed
        embed.description = f"### 🎉 Dojo Cleared!\n**Clear Time:** `{self.format_time(self.clear_time)}`"
        best_str = self.format_time(self.old_best)
        if self.old_best is None or self.clear_time < self.old_best:
            best_str = f"**{self.format_time(self.clear_time)}** (New Best!)"
        embed.add_field(
            name="Performance",
            value=f"⏱️ **Best Run:** {best_str}",
            inline=False,
        )
        rewards = [
            f"{config.XP_EMOJI} **500 XP**",
            f"{config.CHAOS_CORE_EMOJI} **1 Chaos Core**",
        ]
        embed.add_field(name="🎁 Rewards", value="\n".join(rewards), inline=True)
        if self.projects:
            lines = []
            for p_name, p_xp in self.projects:
                icon = (
                    config.MISSION_EMOJI if "Defeat" in p_name else config.PROJECT_EMOJI
                )
                token_str = (
                    f" | {config.MERCH_TOKEN_EMOJI} **25**"
                    if "Defeat" in p_name
                    else ""
                )
                lines.append(
                    f"{icon} **{p_name}**\n└ {config.XP_EMOJI} **{p_xp:,}**{token_str}"
                )
            embed.add_field(
                name="🎯 Projects Completed",
                value="\n".join(lines),
                inline=False,
            )
        return embed

    @discord.ui.button(label="Finish", style=discord.ButtonStyle.success)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class DojoCombatView(View):
    def __init__(self, instance):
        super().__init__(timeout=None)
        self.instance = instance
        self.add_item(DojoTargetSelect(instance))
        w_emoji = self.instance.player.get_weapon_emoji()
        is_p = self.instance.grace_timer > 0
        self.add_item(
            DojoActionButton(
                "ATTACK",
                "Attack",
                w_emoji,
                discord.ButtonStyle.primary,
                disabled=is_p,
            )
        )
        dash_label = (
            "Dash"
            if self.instance.player.dash_cd <= 0
            else f"{int(self.instance.player.dash_cd)}s"
        )
        self.add_item(
            DojoActionButton(
                "DASH",
                dash_label,
                config.DASH_EMOJI,
                discord.ButtonStyle.success,
                disabled=(is_p or self.instance.player.dash_cd > 0),
            )
        )
        self.add_item(
            DojoActionButton(
                "QUIT",
                "Return Home",
                config.MAP_EMOJI,
                discord.ButtonStyle.success,
            )
        )
        for i, g in enumerate(self.instance.player.gadgets):
            if g:
                self.add_item(DojoGadgetButton(i, g, self.instance.bot, disabled=is_p))


class DojoTargetSelect(Select):
    def __init__(self, instance):
        opts = [
            discord.SelectOption(
                label="🎯 Lowest HP (Auto)",
                value="Lowest HP",
                default=(instance.target_focus == "Lowest HP"),
            )
        ]
        for m in instance.mobs:
            if m.hp > 0:
                opts.append(
                    discord.SelectOption(
                        label=f"{m.name}{' (x'+str(m.unit_count)+')' if m.is_swarm else ''}",
                        value=m.name,
                        emoji=utils.safe_emoji(m.icon),
                        default=(instance.target_focus == m.name),
                    )
                )
        super().__init__(placeholder="Select Focus Target...", options=opts, row=0)

    async def callback(self, i):
        self.view.instance.target_focus = self.values[0]
        await i.response.send_message(
            f"🎯 Targeted: **{self.values[0]}**", ephemeral=True
        )


class DojoActionButton(Button):
    def __init__(self, action, label, emoji, style, disabled=False):
        super().__init__(
            label=label,
            style=style,
            emoji=utils.safe_emoji(emoji),
            row=1,
            disabled=disabled,
        )
        self.action = action

    async def callback(self, i):
        if i.user.id != self.view.instance.user_id:
            return
        if self.action == "QUIT":
            self.view.instance.active = False
            await i.message.delete()
            return
        player = self.view.instance.player
        if player.action_queue:
            return await i.response.send_message("❌ Already queued!", ephemeral=True)
        player.action_queue = self.action
        await i.response.defer()


class DojoGadgetButton(Button):
    def __init__(self, index, gadget, bot, disabled=False):
        icon = utils.get_emoji(bot, gadget["id"])
        super().__init__(
            label=gadget["name"],
            style=discord.ButtonStyle.secondary,
            emoji=utils.safe_emoji(icon),
            row=2,
        )
        self.index, self.disabled = index, (disabled or gadget["cd"] > 0)
        if gadget["cd"] > 0:
            self.label = f"{int(gadget['cd'])}s"

    async def callback(self, i):
        if i.user.id != self.view.instance.user_id:
            return
        if self.view.instance.player.action_queue:
            return await i.response.send_message("❌ Already queued!", ephemeral=True)
        self.view.instance.player.action_queue = f"GADGET_{self.index}"
        await i.response.defer()

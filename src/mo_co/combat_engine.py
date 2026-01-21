import random
import time
from mo_co import config, utils
from mo_co import game_data
from mo_co.game_data import scaling
from mo_co import database
from mo_co import pedia


class CombatEntity:
    def __init__(
        self,
        engine,
        name,
        is_player=False,
        owner=None,
        is_bot=False,
        source_id=None,
    ):
        self.engine = engine
        self.is_player = is_player
        self.is_bot = is_bot
        self.owner = owner
        self.user_id = None

        self.source_id = source_id if source_id else name

        if not is_player and not is_bot and not owner:
            self.name = utils.format_monster_name(name)
        else:
            self.name = name

        self.max_hp = 1000
        self.hp = 1000
        self.level = 1
        self.attack_pwr = 0
        self.luck = 0
        self.gp = 0

        self.is_swarm = False
        self.is_boss = False
        self.windup = False
        self.stunned = False
        self.taunt = False
        self.is_dashing = False
        self.combo_triggered = False

        self.weapon_id = None
        self.weapon_data = {}
        self.gadgets = []
        self.passives = {}
        self.rings = []
        self.modules = []
        self.emblem = "👤"

        self.combo_count = 0
        self.hits_taken_count = 0
        self.status_effects = []
        self.dash_cd = 0
        self.action_queue = None

        self.stat_mults = {
            "dmg": 1.0,
            "heal": 1.0,
            "hp": 1.0,
            "cd": 1.0,
            "weapon_crit": 0.0,
            "gadget_crit": 0.0,
            "passive_crit": 0.0,
            "heal_crit": 0.0,
            "pet_crit": 0.0,
            "pet_dmg": 1.0,
            "executioner": 1.0,
        }

        self.cdr_mult = 1.0
        self.modifier_cd_penalty = 1.0

        self.dash_cd_max = 6.0
        self.regen_per_turn = 0
        self.extra_projectiles = 0
        self.combo_accel = 1
        self.attack_speed_mult = 1.0

        self.total_dmg_dealt = 0
        self.dmg_boss = 0
        self.dmg_mobs = 0
        self.total_healing = 0
        self.healed_this_tick = 0
        self.total_tanked = 0
        self.damage_sources = {}
        self.heal_sources = {}
        self.xp_mult_bonus = 0.0
        self.loot_rolls_bonus = 0
        self.death_time = 0

        self.defense_mult = 1.0
        self.hits_taken_this_tick = 0

        self.icon = "❓"
        self._resolve_icon()

    def _resolve_icon(self):

        if self.source_id in config.BOT_EMOJIS:
            self.icon = config.BOT_EMOJIS[self.source_id]
            return
        if self.source_id in config.MOBS:
            self.icon = config.MOBS[self.source_id]
            return

        if self.name in config.BOT_EMOJIS:
            self.icon = config.BOT_EMOJIS[self.name]
            return
        if self.name in config.MOBS:
            self.icon = config.MOBS[self.name]
            return

        if hasattr(self.engine.bot, "emoji_map"):
            emap = self.engine.bot.emoji_map

            if self.source_id in emap:
                self.icon = emap[self.source_id]
                return

            d_key = f"d_{self.name}"
            if d_key in emap:
                self.icon = emap[d_key]
                return

            clean = self.name.lower().replace(" ", "_")
            if clean in emap:
                self.icon = emap[clean]
                return
            for k, v in emap.items():
                if k.endswith(clean) or clean in k:
                    self.icon = v
                    return
        self.icon = "👤" if self.is_player else "👹"

    def setup_stats(
        self,
        level,
        hp=None,
        weapon=None,
        gadgets=None,
        passives=None,
        rings=None,
    ):
        self.level = level
        if self.is_player and not self.is_bot:
            self.max_hp = utils.get_base_hp(level)
        else:
            self.max_hp = int(hp) if hp else utils.get_base_hp(level)

        if isinstance(weapon, dict):
            self.weapon_id = weapon.get("id")
            self.weapon_data = weapon
        else:
            self.weapon_id = weapon
            self.weapon_data = {
                "id": weapon,
                "modifier": "Standard",
                "level": level,
            }

        if self.is_player and not self.is_bot:
            item_lvl = self.weapon_data.get("level", 1)
            self.weapon_data["level"] = utils.get_effective_level(item_lvl, self.level)

        self.gadgets = []
        if gadgets:
            for g in gadgets:
                g_lvl = g.get("lvl", 1)
                if self.is_player and not self.is_bot:
                    g["lvl"] = utils.get_effective_level(g_lvl, self.level)
                self.gadgets.append(g)

        self.passives = passives if passives else {}
        self.rings = rings if rings else []
        self.modules = []

        if self.is_player and self.user_id:
            with database.get_connection() as conn:
                row = conn.execute(
                    "SELECT elite_module_id FROM gear_kits WHERE user_id=? AND slot_index = (SELECT active_kit_index FROM users WHERE user_id=?)",
                    (self.user_id, self.user_id),
                ).fetchone()
                if row and row[0]:
                    m_row = conn.execute(
                        "SELECT item_id, level FROM inventory WHERE instance_id=?",
                        (row[0],),
                    ).fetchone()
                    if m_row:
                        self.modules.append({"id": m_row[0], "lvl": m_row[1]})

        self._apply_modifier_stats(self.weapon_data.get("modifier", "Standard"))

        for g in self.gadgets:
            if g["id"] in [
                "really_cool_sticker",
                "very_mean_pendant",
                "bunch_of_dice",
                "overcharged_amulet",
            ]:
                self.passives[g["id"]] = g["lvl"]

        self._apply_rings()
        for mod in self.modules:
            mid, mlvl = mod["id"], mod["lvl"]
            if mid == "elite_dash_module":
                self.dash_cd_max *= max(0.5, (1.0 - (0.1 * mlvl)))
            elif mid == "healing_ride":
                self.regen_per_turn += 50 * mlvl

        if self.weapon_id == "medicne_ball":
            self.max_hp = int(self.max_hp * 1.3)
        if "healthy_snacks" in self.passives:
            self.max_hp += int(
                scaling.get_passive_value(
                    "healthy_snacks", self.passives["healthy_snacks"]
                )
            )
        self.max_hp = int(self.max_hp * self.stat_mults["hp"])

        if "bunch_of_dice" in self.passives:
            self.luck = scaling.get_passive_value(
                "bunch_of_dice", self.passives["bunch_of_dice"]
            )
        if "really_cool_sticker" in self.passives:
            self.attack_pwr += int(
                scaling.get_passive_value(
                    "really_cool_sticker", self.passives["really_cool_sticker"]
                )
            )
        if "explode_o_matic_trigger" in self.passives:
            self.loot_rolls_bonus += 1

        if self.is_player and not self.is_bot:
            start_hp = int(hp) if hp is not None else self.max_hp
            self.hp = min(start_hp, self.max_hp)
        else:
            self.hp = self.max_hp

        if self.is_player and not self.is_bot:
            u = database.get_user_data(self.user_id)
            prestige = u["prestige_level"] if u else 0
            self.icon = utils.get_emblem(self.level, prestige=prestige)
            self.emblem = self.icon
        else:
            if self.icon == "❓":
                self._resolve_icon()
            self.emblem = self.icon

    def _apply_modifier_stats(self, mod):
        if mod == "Overcharged":
            self.stat_mults["dmg"] += 0.30
            self.modifier_cd_penalty += 0.20
        elif mod == "Megacharged":
            self.stat_mults["dmg"] += 0.60
            self.modifier_cd_penalty += 0.40
        elif mod == "Overcharged Chaos":
            self.stat_mults["dmg"] += 0.20
        elif mod == "Elite":
            self.stat_mults["dmg"] += 0.25
            self.stat_mults["heal"] += 0.25
            self.stat_mults["weapon_crit"] += 10
            self.stat_mults["gadget_crit"] += 10
            self.stat_mults["passive_crit"] += 10

    def _apply_rings(self):
        for r in self.rings:
            if not r:
                continue
            rid, lvl = r["id"], r["lvl"]
            val1, val2 = scaling.get_ring_stats(rid, lvl)

            if "executioner" in rid:
                self.stat_mults["executioner"] += val1 / 100.0

            if "insane" in rid:
                if "attack_speed" in rid:
                    self.attack_speed_mult += val1 / 100.0
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
                    if "precision" in rid:
                        self.stat_mults["weapon_crit"] += val1
                    elif "explosive" in rid:
                        self.stat_mults["gadget_crit"] += val1
                    elif "echo" in rid:
                        self.stat_mults["passive_crit"] += val1
                    elif "savage" in rid:
                        self.stat_mults["pet_crit"] += val1
                    else:
                        self.stat_mults["weapon_crit"] += val1
                        self.stat_mults["gadget_crit"] += val1
                        self.stat_mults["passive_crit"] += val1

                if "vitality" in rid:
                    self.stat_mults["heal_crit"] += val1
                if "pet" in rid:
                    self.stat_mults["pet_dmg"] += val1 / 100.0
                if "time_ring" in rid:
                    self.cdr_mult *= 1.0 - (val1 / 100.0)
                if "warriors_ring" in rid:
                    self.attack_speed_mult += val1 / 100.0

    def apply_modifier(self, modifier):
        if not hasattr(self, "modifier_icons"):
            self.modifier_icons = []
        if "Overcharged" in modifier:
            self.modifier_icons.append(config.OVERCHARGED_ICON)
            self.max_hp *= 2
            self.hp = self.max_hp
            self.attack_pwr *= 2
        elif "Megacharged" in modifier:
            self.modifier_icons.append(config.CHAOS_ALERT)
            self.max_hp *= 4
            self.hp = self.max_hp
            self.attack_pwr *= 4
        if "Chaos" in modifier:
            self.modifier_icons.append(config.CHAOS_CORE_EMOJI)
            self.attack_pwr = int(self.attack_pwr * 1.2)

    def tick(self, delta_time):
        if self.hp <= 0:
            return
        self.healed_this_tick = 0
        self.hits_taken_this_tick = 0
        self.combo_triggered = False

        if self.dash_cd > 0:
            self.dash_cd -= delta_time
        for g in self.gadgets:
            if g and g.get("cd", 0) > 0:
                g["cd"] -= delta_time

        self.is_dashing = self.dash_cd > (self.dash_cd_max * 0.66)
        self.stunned = False
        self.taunt = False

        active_status = []
        for s in self.status_effects:
            s["duration"] -= delta_time
            if s["type"] == "STUN":
                self.stunned = True
            elif s["type"] == "TAUNT":
                self.taunt = True
            elif s["type"] == "POISON":
                self.take_damage(50 * delta_time, source="Poison")
            elif s["type"] == "SPIN":
                targets = self.engine.get_enemies(self)
                dmg = (
                    scaling.get_weapon_damage(self.weapon_id, self.weapon_data["level"])
                    * 0.5
                    * delta_time
                )
                for t in targets:
                    self.engine.deal_damage(
                        self, t, int(dmg), "spinsickle_spin", silent=True
                    )
            if s["duration"] > 0:
                active_status.append(s)

        self.status_effects = active_status
        if self.regen_per_turn > 0:
            self.heal(self.regen_per_turn * delta_time, "regen_ring")

        for mod in self.modules:
            if mod["id"] == "speed_kill":
                self.passives["pocket_airbag"] = self.passives.get(
                    "pocket_airbag", 0
                ) + (5 * mod["lvl"])

        if self.stunned:
            self.windup = False
            return

        self._process_passive_ticks(delta_time)

        if self.is_player and not self.is_bot:
            self._player_logic(delta_time)
        else:
            self._ai_logic(delta_time)

    def _process_passive_ticks(self, delta_time):
        if "smelly_socks" in self.passives:
            dmg = int(
                scaling.get_passive_value("smelly_socks", self.passives["smelly_socks"])
                * (delta_time / 2.0)
            )
            if self.stat_mults["dmg"] > 1.0:
                dmg = int(dmg * self.stat_mults["dmg"])
            target = self.engine.get_target(self, aoe=True)
            if target:
                self.engine.deal_damage(self, target, dmg, "smelly_socks", silent=True)
                if self.engine.turn_count % 3 == 0:
                    icon = utils.get_emoji(self.engine.bot, "smelly_socks")
                    self.engine.log(
                        f"{icon} **Smelly Socks** stunk up {target.icon} **{target.name}** ({dmg})"
                    )

        if "very_mean_pendant" in self.passives:
            dmg_per_target = int(
                scaling.get_gadget_value(
                    "very_mean_pendant", self.passives["very_mean_pendant"]
                )
                * (delta_time / 2.0)
            )
            targets = self.engine.get_enemies(self)
            total_dealt = 0
            for t in targets:
                dealt = self.engine.deal_damage(
                    self, t, dmg_per_target, "very_mean_pendant", silent=True
                )
                total_dealt += dealt

            if total_dealt > 0:
                heal_amt = int(total_dealt * 0.20)
                actual_heal = self.heal(heal_amt, "very_mean_pendant")

                if self.engine.turn_count % 4 == 0:
                    icon = utils.get_emoji(self.engine.bot, "very_mean_pendant")
                    self.engine.log(
                        f"{icon} **Very Mean Pendant** hit all ({total_dealt}) | ❤️ Lifesteal (+{actual_heal})"
                    )

        if "auto_zapper" in self.passives:
            dmg = int(
                scaling.get_passive_value("auto_zapper", self.passives["auto_zapper"])
            )
            target = self.engine.get_target(self)
            if target:
                self.engine.deal_damage(self, target, dmg, "auto_zapper", silent=True)
                if self.engine.turn_count % 5 == 0:
                    icon = utils.get_emoji(self.engine.bot, "auto_zapper")
                    self.engine.log(
                        f"{icon} **Auto Zapper** zapped {target.icon} **{target.name}** ({dmg})"
                    )

        if "randb_mixtape" in self.passives:
            if self.engine.turn_count % 4 == 0:
                amt = 30 + (self.passives["randb_mixtape"] * 10)
                self.heal(amt, "randb_mixtape")
                icon = utils.get_emoji(self.engine.bot, "randb_mixtape")
                self.engine.log(f"{icon} **R&B Mixtape** healed ❤️ (+{amt})")

    def _player_logic(self, delta_time):
        if self.engine.mode == "sim":
            for g in self.gadgets:
                if g and g.get("cd", 0) <= 0:
                    self.use_gadget(g)
            target = self.engine.get_target(self)
            if target:
                self._perform_attack(target)
            return
        if not self.action_queue:
            return
        if self.action_queue == "ATTACK":
            target = self.engine.get_target(self)
            if target:
                self._perform_attack(target)
        elif self.action_queue == "DASH":
            if self.dash_cd <= 0:
                self.dash_cd = self.dash_cd_max
                self.is_dashing = True
                self.engine.log(f"{config.DASH_EMOJI} **{self.name}** Dashed!")
        elif str(self.action_queue).startswith("GADGET_"):
            idx = int(self.action_queue.split("_")[1])
            if idx < len(self.gadgets) and self.gadgets[idx]:
                self.use_gadget(self.gadgets[idx])
        self.action_queue = None

    def _ai_logic(self, delta_time):
        target = self.engine.get_target(self)
        if not target:
            return
        if self.owner:
            if self.name == "Sheldon":
                return
            if self.name == "Bloom":
                self.engine.heal_team(
                    self.owner,
                    scaling.get_gadget_value("feel_better_bloom", self.level),
                    "Bloom",
                )
                return
            dmg = self.attack_pwr * (
                self.owner.stat_mults["pet_dmg"]
                if hasattr(self.owner, "stat_mults")
                else 1.0
            )
            if self.name == "Wolf":
                self.engine.deal_damage(self, target, dmg, "wolf_stick")
            elif self.name == "Bee":
                self.engine.deal_damage(self, target, dmg, "buzz_kill")
            else:
                self.engine.deal_damage(self, target, dmg, "summon_attack")
            return
        if self.is_bot:
            for g in self.gadgets:
                if g and g.get("cd", 0) <= 0 and random.random() < 0.4:
                    self.use_gadget(g)
                    return
            self._perform_attack(target)
            return
        if not self.windup:
            if random.random() < 0.50:
                self.windup = True
                if self.is_boss or self.level > 10 or self.engine.mode == "sim":
                    self.engine.log(f"{self.icon} **{self.name}** is winding up!")
                return
        self.windup = False
        dmg = self.attack_pwr
        if self.engine.gamemode == "rift":
            dmg = int(dmg * 0.5)
        elif self.engine.gamemode == "dojo":
            dmg = int(dmg * 0.4)
        if self.is_boss and random.random() < 0.2:
            dmg = int(dmg * 1.5)
            self.engine.log(f"{self.icon} **{self.name}** released a Heavy Attack!")
        self.engine.deal_damage(self, target, dmg, "monster_hit")
        self.engine.log(
            f"{self.icon} **{self.name}** hit {target.icon} **{target.name}** ({dmg})"
        )

    def use_gadget(self, g):
        if g.get("cd", 0) > 0:
            return
        if g["id"] in [
            "really_cool_sticker",
            "very_mean_pendant",
            "bunch_of_dice",
            "overcharged_amulet",
        ]:
            return

        base_cd = scaling.get_cooldown(g["id"])
        mod_penalty = self.modifier_cd_penalty
        g["cd"] = max(1.0, base_cd * self.cdr_mult * mod_penalty)
        gid = g["id"]
        lvl = g["lvl"]
        val = scaling.get_gadget_value(gid, lvl)

        if gid not in [
            "splash_heal",
            "revitalizing_mist",
            "vitamin_shot",
            "life_jacket",
        ]:
            val = int(val * self.stat_mults["dmg"])

        icon = utils.get_emoji(self.engine.bot, gid)
        i_def = game_data.get_item(gid)

        if gid in ["splash_heal", "revitalizing_mist"]:
            val = int(val * self.stat_mults["heal"])
            self.engine.heal_team(self, val, gid)
            self.engine.log(
                f"{icon} **{self.name}** used **{i_def['name']}**! (+{val} ❤️)"
            )
        elif gid == "vitamin_shot":
            val = int(val * self.stat_mults["heal"])
            self.heal(val, gid)
            self.apply_status("HASTE", 5.0, source_id=gid)
            self.engine.log(f"{icon} **{self.name}** boosted up! (+{val} ❤️)")
        elif gid in [
            "smart_fireworks",
            "spicy_dagger",
            "explosive_6_pack",
            "multi_zapper",
            "pepper_spray",
        ]:
            t = self.engine.get_target(self)
            if t:
                if gid in ["explosive_6_pack", "multi_zapper"]:
                    for sub_t in [t] + self.engine.get_neighbors(t):
                        self.engine.deal_damage(self, sub_t, val, gid)
                    self.engine.log(f"{icon} **{self.name}** blasted the area!")
                else:
                    self.engine.deal_damage(self, t, val, gid)
                    self.engine.log(f"{icon} **{self.name}** used **{i_def['name']}**!")
        elif gid == "monster_taser":
            t = self.engine.get_target(self)
            if t:
                self.engine.deal_damage(self, t, val, gid)
                t.apply_status("STUN", 2.0, source_id=gid)
                self.engine.log(f"{icon} **{self.name}** tased {t.icon} **{t.name}**!")
        elif gid == "boom_box":
            t = self.engine.get_target(self)
            if t:
                self.engine.deal_damage(self, t, val, gid)
                t.apply_status("STUN", 1.5, source_id=gid)
                self.engine.log(f"{icon} **{self.name}** blasted sick beats!")
        elif gid == "snow_globe":
            for t in self.engine.get_enemies(self):
                t.apply_status("SLOW", 8.0, source_id=gid)
            self.engine.log(f"{icon} **Snow Globe** slowed enemies!")
        elif gid == "life_jacket":
            self.apply_status("SHIELD", 6.0, source_id=gid)
            self.engine.log(f"{icon} **Life Jacket** deployed!")
        elif gid == "super_loud_whistle":
            self.apply_status("TAUNT", 8.0, source_id=gid)
            self.engine.log(f"{icon} **{self.name}** whistled!")
        elif gid == "sheldon":
            self.engine.spawn_summon(self, "Sheldon", lvl, taunt=True)
        elif gid == "pew3000":
            self.engine.spawn_summon(self, "Turret", lvl)
        elif gid == "feel_better_bloom":
            self.engine.spawn_summon(self, "Bloom", lvl)

        if "gadget_battery" in self.passives:
            dmg = scaling.get_passive_value(
                "gadget_battery", self.passives["gadget_battery"]
            )
            t = self.engine.get_target(self)
            if t:
                self.engine.deal_damage(self, t, dmg, "gadget_battery")
                batt_icon = utils.get_emoji(self.engine.bot, "gadget_battery")
                self.engine.log(f"{batt_icon} **Battery Zap!**")

        if "unstable_lightning" in self.passives:
            if random.random() * 100 < scaling.get_passive_value(
                "unstable_lightning", self.passives["unstable_lightning"]
            ):
                t = self.engine.get_target(self)
                if t:
                    dmg = 150 + (self.level * 10)
                    self.engine.deal_damage(self, t, dmg, "unstable_lightning")
                    lightning_icon = utils.get_emoji(
                        self.engine.bot, "unstable_lightning"
                    )
                    self.engine.log(f"{lightning_icon} **Unstable Lightning** struck!")

    def _perform_attack(self, target):
        self.combo_count += self.combo_accel
        base_dmg = (
            scaling.get_weapon_damage(self.weapon_id, self.weapon_data["level"])
            + self.attack_pwr
        )
        base_dmg = int(base_dmg * self.stat_mults["dmg"])

        mult = 1.0
        is_combo = False
        combo_tag = "COMBO!"
        heal_log = ""
        bonus_proj = self.extra_projectiles

        if self.weapon_id == "monster_slugger" and self.combo_count % 4 == 0:
            mult = 1.5
            is_combo = True
            combo_tag = "CLEAVE!"
            for e in self.engine.get_enemies(self):
                if not e.is_boss:
                    e.apply_status("SLOW", 5.0)
        elif self.weapon_id == "techno_fists":
            if self.combo_count % 10 == 0:
                mult = 2.0
                is_combo = True
                combo_tag = "MEGA BALL!"
                for e in self.engine.get_enemies(self):
                    if not e.is_boss:
                        e.apply_status("STUN", 2.0)
            elif bonus_proj > 0:
                others = self.engine.get_enemies(self)
                hits = 0
                while hits < bonus_proj and others:
                    t = random.choice(others)
                    self.engine.deal_damage(self, t, base_dmg, "techno_fists_extra")
                    hits += 1
        elif self.weapon_id == "wolf_stick" and self.combo_count % 6 == 0:
            self.engine.spawn_summon(self, "Wolf", self.level)
            is_combo = True
            combo_tag = "SUMMONED WOLF!"
        elif self.weapon_id == "buzz_kill" and self.combo_count % 3 == 0:
            self.engine.spawn_summon(self, "Bee", self.level)
            is_combo = True
            combo_tag = "SUMMONED BEE!"
        elif self.weapon_id == "staff_of_good_vibes":
            mult = 0.5
            heal_val = 50 + (self.level * 5)
            if self.combo_count % 10 == 0:
                mult = 3.0
                heal_val *= 3
                is_combo = True
                combo_tag = "360 HEAL!"
            heal_val = int(heal_val * self.stat_mults["heal"])
            self.engine.heal_team(self, heal_val, "staff_of_good_vibes")
            heal_log = f" (+{heal_val} ❤️)"
        elif self.weapon_id == "medicne_ball" and self.combo_count % 3 == 0:
            heal_amt = int(self.max_hp * 0.05 * self.stat_mults["heal"])
            self.engine.heal_team(self, heal_amt, "medicne_ball")
            is_combo = True
            combo_tag = f"AOE HEAL!"
            heal_log = f" (+{heal_amt} ❤️)"
        elif self.weapon_id == "hornbow":
            if self.combo_count % 3 == 0:
                mult = 1.5
                is_combo = True
                combo_tag = "MEGASHOT!"
            if bonus_proj > 0:
                neighbors = self.engine.get_neighbors(target)
                for n in neighbors[:bonus_proj]:
                    self.engine.deal_damage(self, n, base_dmg, "hornbow_extra")
        elif self.weapon_id == "squid_blades" and self.combo_count >= 8:
            mult = 4.0
            self.combo_count = 0
            is_combo = True
            combo_tag = "AMBUSH!"
            for e in self.engine.get_enemies(self):
                if not e.is_boss:
                    e.apply_status("STUN", 2.0)
        elif self.weapon_id == "cpu_bomb" and self.combo_count % 8 == 0:
            mult = 2.5
            is_combo = True
            combo_tag = "MEGA BOMB!"
            for e in self.engine.get_enemies(self):
                if not e.is_boss:
                    e.apply_status("STUN", 2.0)
        elif self.weapon_id == "singularity" and self.combo_count % 6 == 0:
            mult = 1.2
            is_combo = True
            combo_tag = "TIME WARP!"
            for g in self.gadgets:
                if g:
                    g["cd"] = max(0, g.get("cd", 0) - 1.5)
        elif self.weapon_id == "toothpick_and_shield" and self.hits_taken_count >= 15:
            mult = 3.0
            is_combo = True
            combo_tag = "SHIELD SLAM!"
            self.hits_taken_count = 0
            for e in self.engine.get_enemies(self):
                if not e.is_boss:
                    e.apply_status("STUN", 2.0)
        elif self.weapon_id == "portable_portal":
            if self.combo_count % 5 == 0:
                is_combo = True
                combo_tag = "FREE GADGET!"
                if self.gadgets:
                    g_target = self.gadgets[-1]
                    g_target["cd"] = 0
                    self.use_gadget(g_target)
        elif self.weapon_id == "speedshot" and self.combo_count % 10 == 0:
            is_combo = True
            combo_tag = "RAPID FIRE!"
            t = self.engine.get_target(self)
            if t:
                self.engine.deal_damage(self, t, int(base_dmg * 0.5), "speedshot_rapid")
                self.engine.deal_damage(self, t, int(base_dmg * 0.5), "speedshot_rapid")
        elif self.weapon_id == "poison_bow" and self.combo_count % 5 == 0:
            is_combo = True
            combo_tag = "POISON VOLLEY!"
            t = self.engine.get_target(self)
            if t:
                t.apply_status("POISON", 8.0, icon="🧪")
                if not t.is_boss:
                    t.apply_status("SLOW", 5.0, icon="❄️")
        elif self.weapon_id == "spinsickle" and self.combo_count % 6 == 0:
            is_combo = True
            combo_tag = "SPIN MODE!"
            self.apply_status("SPIN", 5.0, source_id="spinsickle")

        final_dmg = int(base_dmg * mult)
        extra_log = ""
        mod = self.weapon_data.get("modifier", "Standard")

        if "Chaos" in mod:
            rng_mult = (
                random.uniform(0.75, 2.0)
                if mod == "Overcharged Chaos"
                else random.uniform(0.5, 4.0)
            )
            final_dmg = int(final_dmg * rng_mult)
            extra_log += f" {config.CHAOS_CRACK_EMOJI} x{rng_mult:.1f}"

        if "Toxic" in mod:
            duration = 10.0 if self.weapon_id == "poison_bow" else 5.0
            target.apply_status("POISON", duration, "🧪")
            extra_log += f" {utils.get_emoji(self.engine.bot, 'poison_bow')}"

        w_icon = utils.get_emoji(self.engine.bot, self.weapon_id, self.user_id)
        if is_combo:
            self.engine.log(
                f"{w_icon} **{self.name}** **{combo_tag}** ({final_dmg}){extra_log}{heal_log}"
            )
            self.combo_triggered = True
        else:
            self.engine.log(
                f"{w_icon} **{self.name}** hit {target.icon} **{target.name}** ({final_dmg}){extra_log}{heal_log}"
            )

        actual_dealt = self.engine.deal_damage(self, target, final_dmg, self.weapon_id)

        if "unstable_lazer" in self.passives and random.random() < 0.20:
            dmg = scaling.get_passive_value(
                "unstable_lazer", self.passives["unstable_lazer"]
            )
            self.engine.deal_damage(self, target, dmg, "unstable_lazer")
            self.xp_mult_bonus += 0.1
            lazer_icon = utils.get_emoji(self.engine.bot, "unstable_lazer")
            self.engine.log(
                f"{lazer_icon} **Lazer** hit {target.icon} **{target.name}** ({dmg})"
            )

        if "unstable_beam" in self.passives and random.random() < 0.05:
            dmg = scaling.get_passive_value(
                "unstable_beam", self.passives["unstable_beam"]
            )
            self.engine.deal_damage(self, target, dmg, "unstable_beam")
            beam_icon = utils.get_emoji(self.engine.bot, "unstable_beam")
            self.engine.log(
                f"{beam_icon} **MEGA BEAM** hit {target.icon} **{target.name}** ({dmg})"
            )

        if (
            self.stat_mults["weapon_crit"] > 0
            and random.random() * 100 < self.stat_mults["weapon_crit"]
        ):

            icon = utils.get_emoji(self.engine.bot, "precision_ring")
            self.engine.log(f"{icon} **CRITICAL HIT!** ({int(final_dmg * 3)})")

        if "vampire_teeth" in self.passives:
            pct = (
                scaling.get_passive_value(
                    "vampire_teeth", self.passives["vampire_teeth"]
                )
                / 100.0
            )
            h = self.heal(actual_dealt * pct, "vampire_teeth")
            if h > 0:
                v_icon = utils.get_emoji(self.engine.bot, "vampire_teeth")
                self.engine.log(f"{v_icon} **Lifesteal**: ❤️ (+{h})")

    def heal(self, amount, source):
        is_crit = False
        if (
            self.stat_mults["heal_crit"] > 0
            and random.random() * 100 < self.stat_mults["heal_crit"]
        ):
            amount *= 3.0
            is_crit = True

        tick_cap = int(self.max_hp * 0.45)
        remaining_budget = max(0, tick_cap - self.healed_this_tick)

        if "healing_charm" in self.passives:
            amount *= (
                1.0
                + scaling.get_passive_value(
                    "healing_charm", self.passives["healing_charm"]
                )
                / 100.0
            )

        amount *= self.stat_mults["heal"]
        can_heal_amt = max(0, self.max_hp - self.hp)
        actual = int(min(amount, remaining_budget, can_heal_amt))
        actual = max(0, actual)

        self.hp += actual
        self.total_healing += actual
        self.healed_this_tick += actual
        self.heal_sources[source] = self.heal_sources.get(source, 0) + actual

        if is_crit and actual > 0:
            v_icon = utils.get_emoji(self.engine.bot, "vitality_ring")
            self.engine.log(f"{v_icon} **CRITICAL HEAL!** ❤️ (+{actual})")

        return actual

    def take_damage(self, amount, source="Unknown"):
        if (
            self.is_dashing
            or self.has_status("SHIELD")
            or self.has_status("AIRBORNE")
            or self.has_status("INVISIBLE")
        ):
            return 0
        if self.is_player:
            cap = self.max_hp * 0.35
            if amount > cap:
                amount = cap

        dodge_chance = 0
        if "pocket_airbag" in self.passives:
            dodge_chance += scaling.get_passive_value(
                "pocket_airbag", self.passives["pocket_airbag"]
            )
        if "bunch_of_dice" in self.passives:
            dodge_chance += scaling.get_passive_value(
                "bunch_of_dice", self.passives["bunch_of_dice"]
            )
        if self.has_status("SPIN"):
            dodge_chance += 25

        if self.user_id:
            with database.get_connection() as conn:
                row = conn.execute(
                    "SELECT ride_id FROM gear_kits WHERE user_id=? AND slot_index = (SELECT active_kit_index FROM users WHERE user_id=?)",
                    (self.user_id, self.user_id),
                ).fetchone()
                if row and row[0]:
                    dodge_chance += 10

        if random.random() * 100 < dodge_chance:
            icon_id = (
                "pocket_airbag" if "pocket_airbag" in self.passives else "bunch_of_dice"
            )
            icon = utils.get_emoji(self.engine.bot, icon_id)
            self.engine.log(f"{icon} **{self.name}** dodged!")
            return 0

        if "chicken_o_matic" in self.passives:
            if random.random() * 100 < scaling.get_passive_value(
                "chicken_o_matic", self.passives["chicken_o_matic"]
            ):
                chick_icon = utils.get_emoji(self.engine.bot, "chicken_o_matic")
                self.engine.log(f"{chick_icon} **Chicken** blocked for {self.name}!")
                return 0

        if self.weapon_id == "toothpick_and_shield":
            amount *= 0.7

        reduced_dmg = int(amount * self.defense_mult)

        if self.hits_taken_this_tick > 0:
            reduced_dmg = int(reduced_dmg * (0.85**self.hits_taken_this_tick))

        self.hits_taken_this_tick += 1

        self.hp -= reduced_dmg
        self.hits_taken_count += 1
        self.total_tanked += reduced_dmg

        if self.hp <= 0 and self.user_id:
            pedia.track_death(self.user_id, source)
        return reduced_dmg

    def has_status(self, s_type):
        return any(s["type"] == s_type for s in self.status_effects)

    def apply_status(self, s_type, duration, source_id=None, icon=None):
        icon_str = icon
        if not icon_str:
            icon_str = (
                utils.get_emoji(self.engine.bot, source_id) if source_id else "✨"
            )

        for s in self.status_effects:
            if s["type"] == s_type:
                s["duration"] = max(s["duration"], duration)
                return
        self.status_effects.append(
            {"type": s_type, "duration": duration, "icon": icon_str}
        )


class CombatEngine:
    def __init__(self, bot, gamemode="hunt", mode="sim"):
        self.bot = bot
        self.gamemode = gamemode
        self.mode = mode
        self.team_a = []
        self.team_b = []
        self.logs = []
        self.turn_count = 0
        self.max_turns = 100

    def add_entity(self, entity, team="A"):
        if team == "A":
            self.team_a.append(entity)
        else:
            self.team_b.append(entity)

    def tick(self, delta_time=2.0):
        self.turn_count += 1

        for e in self.team_a + self.team_b:
            e.hits_taken_this_tick = 0

        current_a = list(self.team_a)
        current_b = list(self.team_b)
        for e in current_a:
            e.tick(delta_time)
        self.team_b = [e for e in self.team_b if e.hp > 0]
        for e in current_b:
            if e.hp > 0:
                e.tick(delta_time)
        self.team_a = [e for e in self.team_a if e.hp > 0]

    def simulate_battle(self):
        while (
            len(self.team_a) > 0
            and len(self.team_b) > 0
            and self.turn_count < self.max_turns
        ):
            self.tick()
        return self

    def spawn_summon(self, owner, s_name, level, taunt=False):
        stats = scaling.get_summon_stats(s_name.lower(), level)
        hp, atk = stats
        summon = CombatEntity(self, s_name, is_player=False, owner=owner)
        summon.max_hp = hp
        summon.hp = hp
        summon.attack_pwr = int(atk * owner.stat_mults["pet_dmg"])
        summon.stat_mults["weapon_crit"] = owner.stat_mults["pet_crit"]
        summon.taunt = taunt
        icon = "🐾"
        if s_name == "Wolf":
            icon = utils.get_emoji(self.bot, "wolf_stick")
        elif s_name == "Bee":
            icon = utils.get_emoji(self.bot, "buzz_kill")
        elif s_name == "Turret":
            icon = utils.get_emoji(self.bot, "pew3000")
        elif s_name == "Sheldon":
            icon = utils.get_emoji(self.bot, "sheldon")
        summon.icon = icon
        self.add_entity(summon, "A")
        self.log(f"{icon} **{s_name}** arrived to help!")

    def get_target(self, actor, aoe=False, reverse=False):
        if reverse:
            allies = self.team_a if actor in self.team_a else self.team_b
            return random.choice(allies) if allies else None
        enemies = self.team_b if actor in self.team_a else self.team_a
        if not enemies:
            return None
        taunters = [e for e in enemies if e.taunt]
        if taunters:
            return taunters[0]
        if actor.name == "Turret":
            return min(enemies, key=lambda x: x.hp)
        return random.choice(enemies)

    def get_neighbors(self, target):
        team = self.team_b if target in self.team_b else self.team_a
        return [e for e in team if e != target][:2]

    def get_enemies(self, actor):
        if actor in self.team_a:
            return self.team_b
        return self.team_a

    def heal_team(self, healer, amount, source):
        team = self.team_a if healer in self.team_a else self.team_b
        for member in team:
            member.heal(amount, source)

    def deal_damage(self, attacker, defender, amount, source, silent=False):
        target = defender
        if not defender.taunt:
            enemies = self.get_enemies(attacker)
            taunters = [e for e in enemies if e.taunt]
            if taunters:
                target = taunters[0]
                if not silent and (self.mode == "sim" or self.gamemode == "hunt"):
                    self.log(f"{target.icon} **{target.name}** intercepted the hit!")

        item_def = game_data.get_item(source)
        stype = item_def["type"] if item_def else "unknown"
        crit_chance = 0
        if stype == "weapon":
            crit_chance = attacker.stat_mults["weapon_crit"]
        elif stype == "gadget":
            crit_chance = attacker.stat_mults["gadget_crit"]
        elif stype == "passive":
            crit_chance = attacker.stat_mults["passive_crit"]
        elif attacker.owner:
            crit_chance = attacker.stat_mults["weapon_crit"]

        is_crit = False
        if crit_chance > 0 and random.random() * 100 < crit_chance:
            amount *= 3.0
            is_crit = True

        if target.hp / max(1, target.max_hp) < 0.2:
            amount *= attacker.stat_mults["executioner"]

        actual = target.take_damage(amount, source)

        if actual > 0:
            attacker.total_dmg_dealt += actual
            if target.is_boss:
                attacker.dmg_boss += actual
            else:
                attacker.dmg_mobs += actual
            attacker.damage_sources[source] = (
                attacker.damage_sources.get(source, 0) + actual
            )
            if "cactus_charm" in target.passives:
                ref_pct = (
                    scaling.get_passive_value(
                        "cactus_charm", target.passives["cactus_charm"]
                    )
                    / 100.0
                )
                ref_dmg = int(actual * ref_pct)
                attacker.take_damage(ref_dmg, source="Cactus Charm")
                if not silent and self.turn_count % 3 == 0:
                    icon = utils.get_emoji(self.bot, "cactus_charm")
                    self.log(
                        f"{icon} **Cactus Charm** reflected **{ref_dmg}** to {attacker.name}!"
                    )

        if is_crit and actual > 0 and not silent:
            rid = (
                "precision_ring"
                if stype == "weapon"
                else ("explosive_ring" if stype == "gadget" else "echo_ring")
            )
            icon = utils.get_emoji(self.bot, rid)
            self.log(f"{icon} **CRITICAL HIT!** ({actual})")

        if target.hp <= 0 and not getattr(target, "_death_logged", False):
            target._death_logged = True
            if target.owner:
                self.log(f"💀 {target.icon} **{target.name}** was defeated!")
            killer_id = attacker.user_id
            if not killer_id and attacker.owner:
                killer_id = attacker.owner.user_id
            if killer_id:
                icons = getattr(target, "modifier_icons", [])
                oc = config.OVERCHARGED_ICON in icons
                mega = config.CHAOS_ALERT in icons
                chaos = config.CHAOS_CORE_EMOJI in icons

                pedia.track_kill(killer_id, target.source_id, oc, chaos, mega)
        return actual

    def log(self, msg):
        self.logs.append(msg)

    def is_game_over(self):
        team_a_alive = any(e.hp > 0 for e in self.team_a if (e.is_player or e.is_bot))
        team_b_alive = any(e.hp > 0 for e in self.team_b)
        return not team_a_alive or not team_b_alive

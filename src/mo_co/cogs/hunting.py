import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import json
import asyncio
import time
from datetime import datetime, timedelta
from mo_co import config, database, game_data, utils
from mo_co.combat_engine import CombatEngine, CombatEntity
from mo_co.game_data import scaling
from mo_co.game_data.missions import MISSIONS
from mo_co.mission_engine import MissionEngine
from mo_co.cogs.missions import PhoneDashboardView
import typing
from mo_co import pedia
from mo_co.world_engine import WORLD_MGR, NPC_CONFIG
from mo_co.game_data.projects import PROJECTS


def _is_relevant(target_type, target, world_id, world_type, mob_pool):

    if target_type in [
        "hunt_any",
        "hunt_type",
        "loot_xp",
        "reach_level",
        "open_core",
        "collect_item",
        "collect_smart_rings",
        "reach_elite_level",
        "deal_damage_with",
        "heal_with",
        "hunt_shared_boss",
        "fight_with_npc",
    ]:
        return True

    if target_type == "hunt_world":
        return str(target) == str(world_id)
    if target_type == "hunt_world_type":
        return target == world_type

    if target_type == "hunt_mob":
        return target in mob_pool
    if target_type == "hunt_megacharged_boss":
        return target in mob_pool

    return False


class Hunting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not self.npc_loop.is_running():
            self.npc_loop.start()

    def cog_unload(self):
        self.npc_loop.cancel()

    @tasks.loop(seconds=1.0)
    async def npc_loop(self):
        await WORLD_MGR.npc_spawner_loop()

    async def world_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        user = database.get_user_data(interaction.user.id)
        if not user:
            return []
        player_lvl, _, _ = utils.get_level_info(user["xp"])
        all_available = game_data.WORLDS + getattr(self.bot, "active_elites", [])
        options = []
        for w in all_available:
            if player_lvl >= w["unlock_lvl"]:
                rgp = config.WORLD_RGP.get(w["id"], 50)
                label = f"{w['name']} (RGP: {rgp:,})"
                if current.lower() in label.lower():
                    options.append(app_commands.Choice(name=label, value=w["id"]))
        return options[:25]

    @staticmethod
    def get_monster_icon(is_overcharged=False, is_megacharged=False, is_chaos=False):
        if is_megacharged or is_chaos:
            return config.CHAOS_ALERT
        if is_overcharged:
            return config.OVERCHARGED_ICON
        return ""

    @staticmethod
    def format_modifier_display(modifier: str, mob_name: str):
        icons = []
        name_prefix = []

        if "Overcharged" in modifier:
            icons.append(config.OVERCHARGED_ICON)
            name_prefix.append("OVERCHARGED")

        if "Megacharged" in modifier:
            icons.append(config.CHAOS_ALERT)
            name_prefix.append("MEGACHARGED")

        if "Chaos" in modifier:
            icons.append(config.CHAOS_ALERT)
            name_prefix.append("CHAOS")

        icon_str = " ".join(icons)
        name_str = " ".join(name_prefix + [mob_name])

        return icon_str, name_str

    def update_progression(
        self,
        user_id,
        monster_id,
        world_id,
        modifier,
        monster_type,
        rift_time=None,
        damage_sources=None,
        heal_sources=None,
        loot_xp=0,
        jobs_completed=0,
        npc_ally=None,
        is_shared_boss=False,
    ):
        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        raw_ms = u_dict.get("mission_state")
        m_state = json.loads(raw_ms) if raw_ms else {}
        completed_missions = m_state.get("completed", [])
        active_missions = m_state.get("active", [])

        save_needed = False
        triggered_missions = set()

        jobs_unlocked = "chaos" in completed_missions or "chaos" in active_missions
        if jobs_unlocked:
            jobs = json.loads(u_data["active_jobs"] or "[]")
            jobs_changed = False
            for job in jobs:
                if job.get("completed", False):
                    continue
                if "claimed" not in job:
                    job["claimed"] = False
                inc = False
                t_type = job["target_type"]
                target = job["target"]
                if t_type == "hunt_any":
                    inc = True
                elif t_type == "hunt_world" and target == world_id:
                    inc = True
                elif t_type == "hunt_mob" and monster_id and target == monster_id:
                    inc = True
                elif t_type == "hunt_type":
                    if target == "Overcharged" and (
                        "Overcharged" in modifier or "Megacharged" in modifier
                    ):
                        inc = True
                    elif (
                        target == "Boss"
                        and monster_id
                        and (
                            "boss" in str(monster_id).lower()
                            or str(monster_id).startswith("chaos_")
                            or monster_id in ["Draymor", "Overlord", "Big Papa"]
                        )
                    ):
                        inc = True
                if inc:
                    job["progress"] += 1
                    jobs_changed = True
                    if job["progress"] >= job["count"]:
                        job["completed"] = True
            if jobs_changed:
                database.update_user_stats(user_id, {"active_jobs": json.dumps(jobs)})

        projects_unlocked = (
            "paidovertime" in completed_missions or "paidovertime" in active_missions
        )
        is_elite_user = bool(u_dict.get("is_elite"))
        if projects_unlocked:
            try:
                proj_data = json.loads(u_data.get("project_progress", "{}"))
                proj_changed = False
                w_def = game_data.get_world(world_id)
                w_type = w_def.get("type") if w_def else "unknown"
                for pid, p_def in PROJECTS.items():
                    if p_def.get("is_elite") and not is_elite_user:
                        continue
                    entry = proj_data.get(pid, {"prog": 0, "claimed": False})
                    if isinstance(entry, int):
                        entry = {"prog": entry, "claimed": False}
                    if entry.get("claimed", False):
                        continue

                    tt = p_def["target_type"]
                    tgt = p_def["target"]
                    inc_amt = 0
                    if tt == "hunt_any":
                        inc_amt = 1
                    elif tt == "hunt_world" and tgt == world_id:
                        inc_amt = 1
                    elif tt == "hunt_world_type" and tgt == w_type:
                        inc_amt = 1
                    elif tt == "hunt_mob" and tgt == monster_id:
                        inc_amt = 1
                    elif tt == "hunt_type":
                        if tgt == "Chaos" and "Chaos" in modifier:
                            inc_amt = 1
                        elif tgt == "Overcharged" and (
                            "Overcharged" in modifier or "Megacharged" in modifier
                        ):
                            inc_amt = 1
                        elif tgt == "Boss" and (
                            "boss" in str(monster_id).lower()
                            or str(monster_id).startswith("chaos_")
                        ):
                            inc_amt = 1
                    elif tt == "loot_xp":
                        inc_amt = loot_xp
                    elif (
                        tt == "deal_damage_with"
                        and damage_sources
                        and tgt in damage_sources
                    ):
                        inc_amt = damage_sources[tgt]
                    elif tt == "heal_with" and heal_sources and tgt in heal_sources:
                        inc_amt = heal_sources[tgt]
                    elif tt == "hunt_shared_boss" and is_shared_boss:
                        inc_amt = 1
                    elif tt == "fight_with_npc" and npc_ally and tgt == npc_ally:
                        inc_amt = 1

                    if inc_amt > 0:
                        entry["prog"] += inc_amt
                        proj_data[pid] = entry
                        proj_changed = True
                if proj_changed:
                    database.update_user_stats(
                        user_id, {"project_progress": json.dumps(proj_data)}
                    )
            except:
                pass

        try:
            targets = m_state.get("active", [])
            for m_id in targets:
                mission_def = MISSIONS.get(m_id)
                if not mission_def:
                    continue
                m_data = m_state["states"].get(m_id)
                if not m_data:
                    continue
                step = mission_def["steps"][m_data["step"]]
                inc_mission = False

                if step["type"] == "objective_hunt":
                    if step["target"] == "any":
                        if not step.get("world_id") or step["world_id"] == world_id:
                            inc_mission = True
                    elif step["target"] == monster_id:
                        if not step.get("world_id") or step["world_id"] == world_id:
                            inc_mission = True

                elif step["type"] == "objective_rift_boss":
                    if rift_time is not None and step["target"] == monster_id:
                        inc_mission = True

                if inc_mission:
                    if m_data["prog"] < step["count"]:
                        m_data["prog"] += 1
                        save_needed = True
                        triggered_missions.add(m_id)

                elif step["type"] == "objective_checklist":
                    if isinstance(m_data.get("prog"), int):
                        m_data["prog"] = [0] * len(step["targets"])
                        save_needed = True

                    for idx, target_def in enumerate(step["targets"]):
                        t_id = target_def["id"]
                        req = target_def["count"]
                        t_world = target_def.get("world_id")
                        if t_world and t_world != world_id:
                            continue

                        if idx < len(m_data["prog"]) and m_data["prog"][idx] < req:
                            match = False
                            if t_id == "Boss" and (
                                "boss" in str(monster_id).lower()
                                or str(monster_id).startswith("chaos_")
                                or str(monster_id)
                                in [
                                    "Draymor",
                                    "Overlord",
                                    "Big Papa",
                                    "Berserker",
                                ]
                            ):
                                match = True
                            elif t_id == monster_id:
                                match = True
                            elif t_id == "any":
                                match = True

                            if match:
                                m_data["prog"][idx] += 1
                                save_needed = True
                                triggered_missions.add(m_id)

            if save_needed:
                database.update_user_stats(
                    user_id, {"mission_state": json.dumps(m_state)}
                )

                thread_id = u_dict.get("mission_thread_id")
                if thread_id:
                    for mid in triggered_missions:
                        engine = MissionEngine(
                            self.bot,
                            user_id,
                            thread_id,
                            specific_mission_id=mid,
                        )
                        asyncio.create_task(engine.update_live_message(mid))
                        asyncio.create_task(engine.progress())

        except Exception as e:
            print(f"Mission Update Error: {e}")
        return 0, []

    async def check_new_player_redirect(self, interaction):
        u_data = database.get_user_data(interaction.user.id)
        if not u_data:
            return False
        try:
            m_state = json.loads(u_data["mission_state"])
            active_id = m_state.get("active")
            if isinstance(active_id, list):
                active_id = active_id[0] if active_id else None
            if active_id == "welcome2moco" and "welcome2moco" not in m_state.get(
                "completed", []
            ):
                m_def = MISSIONS.get("welcome2moco")
                step = m_def["steps"][m_state["states"]["welcome2moco"]["step"]]
                if step["type"] == "objective_hunt":
                    return False
                embed = discord.Embed(
                    title="⛔ Access Locked",
                    description="Finish your onboarding with Luna before accessing this feature!",
                    color=0xE74C3C,
                )
                view = PhoneDashboardView(self.bot, interaction.user.id, m_state)
                if interaction.response.is_done():
                    await interaction.followup.send(
                        embed=embed, view=view, ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        embed=embed, view=view, ephemeral=True
                    )
                return True
        except:
            pass
        return False

    @app_commands.command(name="hunt", description="Start a hunting session")
    @app_commands.autocomplete(world_id=world_autocomplete)
    async def hunt(self, interaction: discord.Interaction, world_id: str = None):
        user_id = interaction.user.id
        database.register_user(user_id)
        if await self.check_new_player_redirect(interaction):
            return

        utils.check_daily_reset(user_id)
        if self.bot.get_cog("Jobs"):
            self.bot.get_cog("Jobs").check_refresh(user_id)

        user = database.get_user_data(user_id)
        player_lvl, _, _ = utils.get_level_info(user["xp"])
        player_gp = utils.get_total_gp(user_id)

        if not world_id:
            try:
                m_state = json.loads(user["mission_state"] or "{}")
                actives = m_state.get("active", [])
                target_world = None
                for mid in actives:
                    if mid in m_state.get("completed", []):
                        continue
                    m_def = MISSIONS.get(mid)
                    step = m_def["steps"][m_state["states"][mid]["step"]]
                    if step["type"] == "objective_hunt" and step.get("world_id"):
                        target_world = step["world_id"]
                        break
                if target_world:
                    world_id = target_world
            except:
                pass

        if world_id:
            world_data = game_data.get_world(world_id)
            if not world_data or player_lvl < world_data["unlock_lvl"]:
                available = [
                    w for w in game_data.WORLDS if player_lvl >= w["unlock_lvl"]
                ]
                world_data = available[-1] if available else game_data.WORLDS[0]
        else:
            available = [w for w in game_data.WORLDS if player_lvl >= w["unlock_lvl"]]
            world_data = available[0]
            for w in available:
                if player_gp >= config.WORLD_RGP.get(w["id"], 15) * 0.8:
                    world_data = w

        max_hp = utils.get_max_hp(user_id, player_lvl)
        if user["current_hp"] <= 0:
            database.update_user_stats(user_id, {"current_hp": max_hp})

        events = database.get_active_system_events()
        active_boosts = [
            e
            for e in events
            if e["target_guild_id"] == 0 or e["target_guild_id"] == interaction.guild_id
        ]
        pedia.track_world_visit(user_id, world_data["id"])

        view = HuntSessionView(
            self.bot, interaction.user, world_data, player_lvl, active_boosts
        )
        await interaction.response.send_message(
            embed=view.create_embed("Press Start to begin hunting"), view=view
        )

    def _spawn_monster(
        self,
        world_id,
        world_type,
        unlock_lvl,
        luck=0,
        user_id=None,
        active_players=1,
    ):
        crate_chance = 0.05 + (luck / 200.0)
        if random.random() < crate_chance:
            if user_id:
                pedia.track_crate(user_id, world_id)
            return "mo.co Crate", unlock_lvl, False
        pool = game_data.get_monsters_for_world(world_id, world_type)

        if user_id:
            u = database.get_user_data(user_id)
            try:
                m_state = json.loads(u["mission_state"])
                for mid in m_state.get("active", []):
                    m_def = MISSIONS.get(mid)
                    step = m_def["steps"][m_state["states"][mid]["step"]]

                    target_mobs = []
                    if step["type"] == "objective_hunt":
                        target_mobs = [step["target"]]
                    elif step["type"] == "objective_checklist":
                        target_mobs = [t["id"] for t in step["targets"]]

                    eligible_targets = [m for m in target_mobs if m in pool]
                    if eligible_targets and random.random() < 0.50:
                        chosen = random.choice(eligible_targets)
                        is_boss = "boss" in chosen.lower() or chosen in [
                            "Overlord",
                            "Bug Lord",
                            "Smasher",
                            "Big Papa",
                            "Draymor",
                        ]
                        return (
                            chosen,
                            unlock_lvl + (6 if not is_boss else 12),
                            is_boss,
                        )
            except:
                pass

        bosses = [
            m
            for m in pool
            if "boss" in m
            or "Guardian" in m
            or m in ["Overlord", "Bug Lord", "Smasher", "Big Papa", "Draymor"]
        ]
        mobs = [m for m in pool if m not in bosses]
        if not mobs and not bosses:
            return "Minion", unlock_lvl, False
        boss_weight = 1 + (active_players * 2)
        weights = [10] * len(mobs) + [boss_weight] * len(bosses)
        monster_id = random.choices(mobs + bosses, weights=weights, k=1)[0]
        is_boss = (monster_id in bosses) or (monster_id.startswith("chaos_"))
        lvl = unlock_lvl + (12 if is_boss else 6)
        return monster_id, lvl, is_boss

    def _roll_modifier(self, world_id, is_boss, user_id):
        world_def = game_data.get_world(world_id)
        is_past_forest = world_def.get("unlock_lvl", 1) > 6

        if not is_past_forest:
            return "Standard"

        passives = utils.get_active_passives(user_id)
        amulet_lvl = passives.get("overcharged_amulet", 0)
        amulet_bonus = amulet_lvl / 100.0

        active_event = getattr(self.bot, "active_world_events", {}).get(world_id)
        event_oc_bonus = 0.15 if active_event == "overcharged" else 0.0
        event_mc_bonus = 0.05 if active_event == "overcharged" else 0.0

        mc_chance = (0.005 + amulet_bonus + event_mc_bonus) if is_boss else 0.0

        base_oc = 0.05 if is_boss else 0.025
        oc_chance = base_oc + amulet_bonus + event_oc_bonus

        roll = random.random()
        if roll < mc_chance:
            return "Megacharged"
        elif roll < (mc_chance + oc_chance):
            return "Overcharged"

        if active_event == "chaos" and random.random() < 0.30:
            return random.choice(["Chaos", "Overcharged Chaos"])

        return "Standard"

    def _calculate_xp(
        self,
        u_data,
        monster_id,
        monster_lvl,
        player_lvl,
        multiplier,
        is_boss,
        world_id,
        modifier,
    ):
        if "Crate" in monster_id:
            return 0, 0, 0

        base_xp_val = (monster_lvl * 10) + (monster_lvl**1.25)
        if is_boss:
            base_xp_val *= 4.0

        mod_multiplier = 1.0
        if modifier == "Overcharged":
            mod_multiplier = 4.0
        elif modifier == "Megacharged":
            mod_multiplier = 12.0

        active_world_events = getattr(self.bot, "active_world_events", {})
        if active_world_events.get(world_id) == "double_xp":
            base_xp_val *= 2.0

        diff = monster_lvl - player_lvl
        scale = 1.0
        if diff > 0:
            scale = 1.0 + min(0.40, diff * 0.12)
        elif diff < -10:
            scale = 0.20

        user_id = u_data["user_id"]

        player_gp = utils.get_total_gp(u_data["user_id"])
        world_rgp = config.WORLD_RGP.get(world_id, 50)

        gp_ratio = player_gp / max(1, world_rgp)

        if gp_ratio > 5.0:
            scale *= 0.10
        elif gp_ratio > 3.0:
            scale *= 0.50

        core_xp = int(base_xp_val * scale * multiplier)
        bonus_xp = int(core_xp * (mod_multiplier - 1.0))

        bank_available = u_data["daily_xp_total"]
        fuel_available = u_data["daily_xp_boosted"]

        xp_consumed_from_cap = min(core_xp, bank_available)

        if xp_consumed_from_cap <= 0:
            return 0, 0, 0

        xp_to_boost = 0
        if player_lvl >= 10:
            xp_to_boost = min(xp_consumed_from_cap, fuel_available)

        boosted_portion_value = xp_to_boost * config.XP_BOOST_MULT
        unboosted_portion_value = xp_consumed_from_cap - xp_to_boost

        final_xp = int(boosted_portion_value + unboosted_portion_value + bonus_xp)

        return final_xp, int(xp_consumed_from_cap), int(xp_to_boost)

    def _generate_loot(
        self,
        u_data,
        monster_id,
        is_boss,
        loot_mult,
        player_lvl,
        monster_lvl,
        is_jackpot=False,
        world_id=None,
    ):
        if "Crate" in monster_id:
            return 0, 0
        if u_data["daily_xp_total"] <= 0:
            return (0, 1) if is_boss else (0, 0)
        level_diff = player_lvl - monster_lvl
        if level_diff >= 15:
            return 0, 0
        elif level_diff >= 8:
            loot_mult *= 0.5

        if world_id:
            player_gp = utils.get_total_gp(u_data["user_id"])
            world_rgp = config.WORLD_RGP.get(world_id, 50)
            gp_ratio = player_gp / max(1, world_rgp)
            if gp_ratio > 5.0:
                loot_mult *= 0.1
            elif gp_ratio > 3.0:
                loot_mult *= 0.5

        if is_jackpot:
            loot_mult *= 4.0
        shards = 0
        if player_lvl >= 12:
            base = (
                random.choices([2, 3, 4, 5, 6], weights=[10, 30, 30, 20, 10], k=1)[0]
                if is_boss
                else random.choices([0, 1, 2, 3], weights=[60, 30, 9, 1], k=1)[0]
            )
            shards = int(base * loot_mult)
        core_chance = 0.02 + min(0.08, player_lvl * 0.001)
        if is_boss:
            core_chance = 0.65
        cores = 0
        rolls = int(loot_mult)
        remainder = loot_mult - rolls
        for _ in range(rolls):
            if random.random() < core_chance:
                cores += 1
        if random.random() < (core_chance * remainder):
            cores += 1
        return shards, cores


class HuntSessionView(discord.ui.View):

    def __init__(self, bot, user, world, start_lvl, active_boosts=[]):
        super().__init__(timeout=600)
        self.bot, self.user, self.world, self.start_lvl, self.active_boosts = (
            bot,
            user,
            world,
            start_lvl,
            active_boosts,
        )
        self.user_id = user.id
        self.selected_target = "standard"
        self.last_activity, self.is_processing, self.started = (
            "Press Start to begin hunting!",
            False,
            False,
        )
        (
            self.session_xp,
            self.session_shards,
            self.session_cores,
            self.session_tokens,
            self.full_logs,
            self.log_page,
            self.log_window,
            self.lives,
            self.respawn_ts,
        ) = (0, 0, 0, 0, [], 0, 8, 3, None)
        self.children[0].label = "Start"
        self.add_item(HuntLoadoutButton())
        u_data = database.get_user_data(user.id)
        u_dict = dict(u_data)
        lvl, _, _ = utils.get_level_info(u_dict["xp"])
        is_elite = bool(u_dict.get("is_elite", 0))
        prestige = u_dict.get("prestige_level", 0)
        emblem = utils.get_emblem(lvl, is_elite, prestige)

        kit_data = {
            "weapon": {
                "id": "monster_slugger",
                "modifier": "Standard",
                "level": lvl,
            },
            "gadgets": [],
            "passives": {},
        }

        with database.get_connection() as conn:
            row = conn.execute(
                "SELECT active_kit_index FROM users WHERE user_id=?",
                (user.id,),
            ).fetchone()
            idx = row["active_kit_index"] if row else 1
            kit = conn.execute(
                "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
                (user.id, idx),
            ).fetchone()

            if kit:
                if kit["weapon_id"]:
                    w = database.get_item_instance(kit["weapon_id"])
                    if w:
                        kit_data["weapon"] = {
                            "id": w["item_id"],
                            "modifier": w["modifier"],
                            "level": w["level"],
                        }
                for i in range(1, 4):
                    gid = kit[f"gadget_{i}_id"]
                    if gid:
                        g = database.get_item_instance(gid)
                        if g:
                            kit_data["gadgets"].append(
                                {
                                    "id": g["item_id"],
                                    "lvl": g["level"],
                                    "cd": 0,
                                }
                            )
                for i in range(1, 4):
                    pid = kit[f"passive_{i}_id"]
                    if pid:
                        p = database.get_item_instance(pid)
                        if p:
                            kit_data["passives"][p["item_id"]] = p["level"]

        WORLD_MGR.check_in(
            world["id"], user.id, user.display_name, lvl, emblem, kit_data
        )

    async def on_timeout(self):
        WORLD_MGR.check_out(self.world["id"], self.user_id)
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    async def handle_respawn(self, interaction):
        if not self.respawn_ts:
            return
        self.children[0].disabled, self.children[0].label = (
            True,
            "Respawning...",
        )
        try:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=self.create_embed(),
                view=self,
            )
        except:
            await interaction.response.edit_message(
                embed=self.create_embed(), view=self
            )
        while True:
            remaining = (self.respawn_ts - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            await asyncio.sleep(min(remaining, 1.0))
        u_data = database.get_user_data(self.user_id)
        pl, _, _ = utils.get_level_info(u_data["xp"] + self.session_xp)
        max_hp = utils.get_max_hp(self.user_id, pl)
        database.update_user_stats(self.user_id, {"current_hp": max_hp})
        self.respawn_ts, self.last_activity, self.is_processing = (
            None,
            "❤️ **Revived!** Ready to hunt.",
            False,
        )

        self.update_action_button()

        try:
            await interaction.message.edit(embed=self.create_embed(), view=self)
        except:
            pass

    def update_action_button(self):
        ws = WORLD_MGR.get_world(self.world["id"])
        ws.check_boss_timeout()

        button = None
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.label in [
                "Start",
                "Hunt Again",
                "Attack Threat",
                "Hunting...",
                "Respawning...",
            ]:
                button = child
                break

        if not button:
            return

        if self.respawn_ts and datetime.now() < self.respawn_ts:
            button.disabled = True
            button.label = "Respawning..."
            button.style = discord.ButtonStyle.secondary
            return

        if ws.boss and self.selected_target == "boss":
            button.label = "Attack Threat"
            button.style = discord.ButtonStyle.danger
            button.emoji = utils.safe_emoji(config.CHAOS_ALERT)
        else:
            button.label = "Start" if not self.started else "Hunt Again"
            button.style = (
                discord.ButtonStyle.success
                if not self.started
                else discord.ButtonStyle.primary
            )
            button.emoji = utils.safe_emoji(config.ELITE_EMOJI)

        button.disabled = False

    def create_embed(self, status_msg=None):
        if status_msg:
            self.last_activity = status_msg
        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)
        player_lvl, lvl_cost, current_xp = utils.get_level_info(u_dict["xp"])
        if player_lvl >= 50:
            elite_lvl, elite_cost, elite_curr = utils.get_elite_level_info(
                u_dict["elite_xp"]
            )
            lvl_display_str = f"Elite {elite_lvl}"
            prog_str = f"{config.ELITE_EMOJI} **{lvl_display_str}**: {elite_curr:,}/{elite_cost:,}"
        else:
            prog_str = (
                f"{config.XP_EMOJI} Lvl {player_lvl}: {current_xp:,}/{lvl_cost:,}"
            )
        max_hp = utils.get_max_hp(self.user_id, player_lvl)
        player_gp = utils.get_total_gp(self.user_id)
        rgp = config.WORLD_RGP.get(self.world["id"], 50)
        icon = config.WORLD_ICONS.get(self.world["type"], "🗺️")
        color = 0x3498DB if player_gp >= rgp else 0xE74C3C
        if (
            self.lives < 3
            and u_data["current_hp"] <= 0
            and self.lives > 0
            and self.respawn_ts
        ):
            self.last_activity = f":skull: **Enemies got you!**\nReturning in <t:{int(self.respawn_ts.timestamp())}:R>"
            color = 0x2B2D31
        embed = discord.Embed(title=f"{icon} {self.world['name']}", color=color)
        embed.set_author(
            name=self.user.display_name, icon_url=self.user.display_avatar.url
        )

        active_world_events = getattr(self.bot, "active_world_events", {})
        world_evt = active_world_events.get(self.world["id"])
        if world_evt:
            evt_map = {
                "double_xp": f"{config.DOUBLE_XP_EMOJI} **Double XP Alert**",
                "overcharged": f"{config.OVERCHARGED_ICON} **Overcharged Alert**",
                "chaos": f"{config.CHAOS_ALERT} **Chaos Alert**",
            }
            embed.add_field(
                name="Active Event",
                value=evt_map.get(world_evt, "Special Event"),
                inline=False,
            )

        ws = WORLD_MGR.get_world(self.world["id"])
        boss_despawned = ws.check_boss_timeout()
        if boss_despawned:
            self.last_activity = "💨 **The Shared Boss has fled!**"
            self.selected_target = "standard"

        raw_ms = u_dict.get("mission_state")
        m_state = json.loads(raw_ms) if raw_ms else {}

        active_list = m_state.get("active", [])
        if isinstance(active_list, str):
            active_list = [active_list]

        if active_list:
            first_m = active_list[0]
            if "states" in m_state and first_m in m_state["states"]:
                if m_state["states"][first_m]["step"] == 0:
                    embed.description = f"📱 **INCOMING MESSAGE:** *Luna is trying to reach you! Check `/missions`!*\n\n"
            elif "step" in m_state and m_state["step"] == 0:
                embed.description = f"📱 **INCOMING MESSAGE:** *Luna is trying to reach you! Check `/missions`!*\n\n"

        objectives = []
        completed_ms = m_state.get("completed", [])
        active_ms = m_state.get("active", [])

        for mid in active_ms:
            m_def = MISSIONS.get(mid)
            if not m_def:
                continue
            m_data = m_state["states"].get(mid, {})
            step_idx = m_data.get("step", 0)
            if step_idx < len(m_def["steps"]):
                step = m_def["steps"][step_idx]
                stype = step["type"]

                if stype in [
                    "objective_rift_boss",
                    "objective_dojo",
                    "objective_versus",
                ]:
                    continue

                mob_pool = game_data.get_monsters_for_world(
                    self.world["id"], self.world["type"]
                )
                if stype == "objective_hunt":
                    if step["target"] != "any" and step["target"] not in mob_pool:
                        if (
                            not step.get("world_id")
                            or step["world_id"] != self.world["id"]
                        ):
                            continue

                if stype == "objective_checklist":
                    lines = [f"{config.MISSION_EMOJI} **{m_def['name']}**"]
                    prog_list = m_data.get("prog", [])
                    if isinstance(prog_list, int):
                        prog_list = [0] * len(step["targets"])
                    for i, t in enumerate(step["targets"]):
                        curr = prog_list[i] if i < len(prog_list) else 0
                        req = t["count"]
                        check_icon = "✅" if curr >= req else "⬜"
                        lines.append(f"- {check_icon} {t['desc']} ({curr}/{req})")
                    objectives.append("\n".join(lines))
                elif "objective" in stype:
                    prog = m_data.get("prog", 0)
                    limit = step.get("count", 1)
                    desc = step.get("desc", "Mission in progress...")
                    objectives.append(
                        f"{config.MISSION_EMOJI} **{desc}** ({prog}/{limit})"
                    )

        mob_pool = game_data.get_monsters_for_world(
            self.world["id"], self.world["type"]
        )
        jobs_unlocked = "chaos" in completed_ms or "chaos" in active_ms
        if jobs_unlocked:
            jobs = json.loads(u_dict.get("active_jobs", "[]"))
            for job in jobs:
                if job.get("completed", False) or job.get("claimed", False):
                    continue
                if _is_relevant(
                    job["target_type"],
                    job["target"],
                    self.world["id"],
                    self.world["type"],
                    mob_pool,
                ):
                    objectives.append(
                        f"<:dailyjob:1452418984984186890> **{job['desc']}** ({job['progress']}/{job['count']})"
                    )

        projs_unlocked = "paidovertime" in completed_ms or "paidovertime" in active_ms
        if projs_unlocked:
            proj_data = json.loads(u_dict.get("project_progress", "{}"))
            grouped = {}
            for pid, pdata in PROJECTS.items():
                group = pdata.get("group", pid)
                if group not in grouped:
                    grouped[group] = []
                grouped[group].append((pid, pdata))

            for group, items in grouped.items():
                items.sort(key=lambda x: x[1].get("tier", 1))
                active_proj = None
                for pid, pdata in items:
                    entry = proj_data.get(pid, {"prog": 0, "claimed": False})
                    if isinstance(entry, int):
                        entry = {"prog": entry, "claimed": False}
                    if not entry.get("claimed", False):
                        active_proj = (pid, pdata, entry.get("prog", 0))
                        break

                if active_proj:
                    pid, pdata, prog = active_proj
                    if _is_relevant(
                        pdata["target_type"],
                        pdata["target"],
                        self.world["id"],
                        self.world["type"],
                        mob_pool,
                    ):
                        objectives.append(
                            f"<:project:1452418974410084515> **{pdata['desc']}** ({prog}/{pdata['count']})"
                        )

        if objectives:
            display_list = objectives[:5]
            final_text = "\n".join(display_list)
            if len(objectives) > 5:
                final_text += f"\n*...and {len(objectives) - 5} more*"
            embed.add_field(name="Active Objectives", value=final_text, inline=False)

        u_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        u_is_elite = bool(u_dict.get("is_elite"))
        u_prestige = u_dict.get("prestige_level", 0)
        u_emblem = utils.get_emblem(u_lvl, u_is_elite, u_prestige)

        hunter_lines = [f"{u_emblem} **{self.user.display_name}** (Lvl {u_lvl})"]

        nearby = ws.get_nearby_allies(exlcude_id=self.user_id, count=3)

        for h in nearby:
            if h["type"] == "player":
                emblem = h["emblem"]
                hunter_lines.append(f"{emblem} **{h['name']}** (Lvl {h['lvl']})")
            elif h["type"] == "ghost":
                emblem = h["emblem"]
                hunter_lines.append(f"{emblem} *{h['name']}* (Echo)")
            elif h["type"] == "bot":
                emblem = h["emblem"]
                hunter_lines.append(f"{emblem} {h['name']} (Lvl {h['lvl']})")
            elif h["type"] == "npc":
                hunter_lines.append(
                    f"{h['emoji']} **{h['name']}**\n❤️ {h['hp']:,} / {h['max_hp']:,} HP | ⏳ **{h.get('timer', 0)}s**"
                )
        embed.add_field(
            name="Nearby Hunters", value="\n".join(hunter_lines), inline=False
        )

        existing_select = next(
            (x for x in self.children if isinstance(x, TargetSelect)), None
        )
        if existing_select:
            self.remove_item(existing_select)

        if ws.boss and ws.boss["hp"] > 0:
            boss_pct = int((ws.boss["hp"] / ws.boss["max_hp"]) * 10)
            boss_bar = "🟥" * boss_pct + "⬛" * (10 - boss_pct)
            timer_str = f"Ends <t:{ws.boss['expiry']}:R>"
            embed.add_field(
                name=f"⚠️ {config.CHAOS_ALERT} {ws.boss['name'].upper()} DETECTED",
                value=f"`{boss_bar}` {ws.boss['hp']:,}/{ws.boss['max_hp']:,}\n⏱️ {timer_str}",
                inline=False,
            )
            self.add_item(TargetSelect(self.selected_target))

        self.update_action_button()

        if self.last_activity:
            embed.description = (embed.description or "") + f"### {self.last_activity}"

        if self.full_logs and self.started:
            total = len(self.full_logs)
            end_idx = total - (self.log_page * self.log_window)
            start_idx = max(0, end_idx - self.log_window)
            chunk = self.full_logs[start_idx:end_idx] if end_idx > 0 else []
            embed.description = (
                (embed.description or "")
                + f"\n\n__**Combat History**__\n"
                + "\n".join(chunk)
            )

        gp_status = f"{config.GEAR_POWER_EMOJI} **Gear Power:** {player_gp:,}/{rgp:,}"
        embed.add_field(
            name="Status",
            value=f"❤️ **HP:** {int(u_data['current_hp'])} / {max_hp} ({self.lives}/3)\n{gp_status}",
            inline=False,
        )

        xp_icon, xp_label, is_boosted, xp_curr, xp_cap = utils.get_xp_display_info(
            u_dict
        )
        display_prog = f"{prog_str}\n{xp_icon} **{xp_label}:** {xp_curr:,}/{xp_cap:,}"
        embed.add_field(name="Session Stats", value=display_prog, inline=True)

        loot_display = f"{config.XP_EMOJI} **{self.session_xp:,}** XP\n{config.CHAOS_CORE_EMOJI} {self.session_cores}"
        if player_lvl >= 12:
            loot_display += f"\n{config.CHAOS_SHARD_EMOJI} {self.session_shards}"
        embed.add_field(name="Session Loot", value=loot_display, inline=True)
        return embed

    @discord.ui.button(
        label="Start",
        style=discord.ButtonStyle.success,
        emoji=discord.PartialEmoji.from_str(config.ELITE_EMOJI),
        row=1,
    )
    async def hunt_action(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id or self.is_processing:
            return
        self.is_processing = True
        ws = WORLD_MGR.get_world(self.world["id"])
        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)

        lvl, _, _ = utils.get_level_info(u_dict["xp"])
        is_elite = bool(u_dict.get("is_elite"))
        prestige = u_dict.get("prestige_level", 0)
        emblem = utils.get_emblem(lvl, is_elite, prestige)
        passives = utils.get_active_passives(self.user_id)
        luck_val = (
            scaling.get_passive_value("bunch_of_dice", passives.get("bunch_of_dice", 0))
            if "bunch_of_dice" in passives
            else 0
        )

        kit_data = {
            "weapon": {
                "id": "monster_slugger",
                "modifier": "Standard",
                "level": lvl,
            },
            "gadgets": [],
            "passives": {},
        }
        with database.get_connection() as conn:
            row = conn.execute(
                "SELECT active_kit_index FROM users WHERE user_id=?",
                (self.user_id,),
            ).fetchone()
            idx = row["active_kit_index"] if row else 1
            kit = conn.execute(
                "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
                (self.user_id, idx),
            ).fetchone()
            if kit:
                if kit["weapon_id"]:
                    w = database.get_item_instance(kit["weapon_id"])
                    if w:
                        kit_data["weapon"] = {
                            "id": w["item_id"],
                            "modifier": w["modifier"],
                            "level": w["level"],
                        }
                for i in range(1, 4):
                    gid = kit[f"gadget_{i}_id"]
                    if gid:
                        g = database.get_item_instance(gid)
                        if g:
                            kit_data["gadgets"].append(
                                {
                                    "id": g["item_id"],
                                    "lvl": g["level"],
                                    "cd": 0,
                                }
                            )
                for i in range(1, 4):
                    pid = kit[f"passive_{i}_id"]
                    if pid:
                        p = database.get_item_instance(pid)
                        if p:
                            kit_data["passives"][p["item_id"]] = p["level"]

        WORLD_MGR.check_in(
            self.world["id"],
            self.user_id,
            self.user.display_name,
            lvl,
            emblem,
            kit_data,
        )

        npc_status = ws.tick_npc()
        if npc_status == "DEPARTED" and ws.npc:
            database.update_user_stats(
                self.user_id, {"chaos_cores": u_dict["chaos_cores"] + 2}
            )
            self.session_cores += 2
            self.full_logs.append(f"🎁 **{ws.npc['name']}** left a gift! (+2 Cores)")
            ws.npc = None
        elif npc_status == "DIED":
            self.full_logs.append(
                f"💀 **{ws.npc['name']}** retreated! (Mission Failed)"
            )
            ws.npc = None

        if self.respawn_ts:
            if datetime.now() < self.respawn_ts:
                self.is_processing = False
                rem = int((self.respawn_ts - datetime.now()).total_seconds())
                return await interaction.response.send_message(
                    f"Wait {rem} seconds!", ephemeral=True
                )
            else:
                pl, _, _ = utils.get_level_info(u_dict["xp"] + self.session_xp)
                max_hp = utils.get_max_hp(self.user_id, pl)
                database.update_user_stats(self.user_id, {"current_hp": max_hp})
                self.respawn_ts = None

        button.disabled, button.label = True, "Hunting..."
        await interaction.response.edit_message(view=self)
        utils.check_daily_reset(self.user_id)
        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)

        if not self.started:
            self.started = True
        pedia.track_world_hunt(self.user_id, self.world["id"])
        player_lvl, _, _ = utils.get_level_info(u_dict["xp"] + self.session_xp)
        player_gp = utils.get_total_gp(self.user_id)

        max_hp = utils.get_max_hp(self.user_id, player_lvl)

        if ws.boss and ws.boss["hp"] > 0 and self.selected_target == "boss":
            engine = CombatEngine(self.bot, gamemode="hunt", mode="sim")
            player = CombatEntity(engine, self.user.display_name, is_player=True)
            player.user_id, player.icon = self.user_id, emblem

            weapon_data = {
                "id": "monster_slugger",
                "modifier": "Standard",
                "level": 1,
            }
            gadgets = []
            with database.get_connection() as conn:
                u = conn.execute(
                    "SELECT active_kit_index FROM users WHERE user_id=?",
                    (self.user_id,),
                ).fetchone()
                idx = u["active_kit_index"] if u else 1
                kit = conn.execute(
                    "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
                    (self.user_id, idx),
                ).fetchone()
                if kit:
                    if kit["weapon_id"]:
                        w = database.get_item_instance(kit["weapon_id"])
                        if w:
                            weapon_data = {
                                "id": w["item_id"],
                                "modifier": w["modifier"],
                                "level": w["level"],
                            }
                    for i in range(1, 4):
                        inst_id = kit[f"gadget_{i}_id"]
                        if inst_id:
                            g = database.get_item_instance(inst_id)
                            if g:
                                gadgets.append(
                                    {
                                        "id": g["item_id"],
                                        "lvl": g["level"],
                                        "cd": 0,
                                    }
                                )

            player.setup_stats(
                player_lvl,
                hp=u_dict["current_hp"],
                weapon=weapon_data,
                gadgets=gadgets,
                passives=passives,
            )
            engine.add_entity(player, "A")

            boss_lvl = ws.boss.get("level", player_lvl + 10)
            boss_entity = CombatEntity(
                engine,
                ws.boss["name"],
                is_player=False,
                source_id=ws.boss["name"],
            )
            boss_entity.setup_stats(boss_lvl, hp=ws.boss["hp"])

            if "Overcharged" in ws.boss["name"]:
                boss_entity.icon = config.OVERCHARGED_ICON
            elif "Megacharged" in ws.boss["name"] or "Chaos" in ws.boss["name"]:
                boss_entity.icon = config.CHAOS_ALERT
            else:
                boss_entity.icon = config.MOBS.get(ws.boss["name"], "👹")

            boss_entity.attack_pwr = int(boss_lvl * 15 * 1.5)
            engine.add_entity(boss_entity, "B")

            for _ in range(5):
                engine.tick()
                if player.hp <= 0:
                    break

            dmg_dealt, hp_loss = (
                player.total_dmg_dealt,
                player.max_hp - player.hp,
            )
            is_dead = ws.damage_boss(dmg_dealt, self.user_id)
            new_hp = max(0, int(u_dict["current_hp"] - hp_loss))
            database.update_user_stats(self.user_id, {"current_hp": new_hp})

            self.last_activity = (
                f"💥 **Skirmish with {ws.boss['name']}!** (-{dmg_dealt:,} Boss HP)"
            )
            self.full_logs = engine.logs + [self.last_activity]
            self.bot.get_cog("Hunting").update_progression(
                self.user_id,
                monster_id=ws.boss["name"],
                world_id=self.world["id"],
                modifier="Shared",
                monster_type="Boss",
                damage_sources=player.damage_sources,
                heal_sources=player.heal_sources,
                is_shared_boss=True,
            )

            if is_dead:
                tier = ws.boss.get("tier", "T2")

                xp_base = 15000
                shards = 15
                mvp_cores = 2
                mvp_tokens = 25
                mvp_gold = 2
                last_hit_xp = 5000

                if tier == "T1":
                    (
                        xp_base,
                        shards,
                        mvp_cores,
                        mvp_tokens,
                        mvp_gold,
                        last_hit_xp,
                    ) = (
                        5000,
                        5,
                        1,
                        10,
                        0,
                        2500,
                    )
                elif tier == "T3":
                    (
                        xp_base,
                        shards,
                        mvp_cores,
                        mvp_tokens,
                        mvp_gold,
                        last_hit_xp,
                    ) = (
                        40000,
                        30,
                        3,
                        50,
                        10,
                        10000,
                    )
                elif tier == "T4":
                    (
                        xp_base,
                        shards,
                        mvp_cores,
                        mvp_tokens,
                        mvp_gold,
                        last_hit_xp,
                    ) = (
                        100000,
                        60,
                        5,
                        100,
                        25,
                        25000,
                    )

                total_hp = ws.boss["max_hp"]
                for uid, dmg in ws.boss["participants"].items():
                    if dmg < (total_hp * 0.01):
                        continue
                    u_rec = database.get_user_data(uid)
                    if u_rec:
                        database.update_user_stats(
                            uid,
                            {
                                "xp": u_rec["xp"] + xp_base,
                                "chaos_shards": u_rec["chaos_shards"] + shards,
                            },
                        )

                sorted_p = sorted(
                    ws.boss["participants"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
                mvp_id = sorted_p[0][0]
                mvp_rec = database.get_user_data(mvp_id)
                if mvp_rec:
                    database.update_user_stats(
                        mvp_id,
                        {
                            "chaos_cores": mvp_rec["chaos_cores"] + mvp_cores,
                            "merch_tokens": mvp_rec["merch_tokens"] + mvp_tokens,
                            "mo_gold": mvp_rec["mo_gold"] + mvp_gold,
                        },
                    )

                if self.user_id in ws.boss["participants"]:
                    self.session_xp += xp_base
                    self.session_shards += shards

                if self.user_id == mvp_id:
                    self.session_cores += mvp_cores

                if self.user_id == interaction.user.id:
                    self.session_xp += last_hit_xp
                    u_now = database.get_user_data(self.user_id)
                    database.update_user_stats(
                        self.user_id, {"xp": u_now["xp"] + last_hit_xp}
                    )

                self.full_logs.append(
                    f"🏆 **{ws.boss['name']} DEFEATED!** Participation loot granted."
                )
                ws.boss = None
            else:
                xp_gain = 500
                utils.add_user_xp(self.user_id, xp_gain)
                self.session_xp += xp_gain

            if new_hp <= 0:
                self.lives -= 1
                if self.lives > 0:
                    self.respawn_ts, self.last_activity = (
                        datetime.now() + timedelta(seconds=10),
                        f":skull: **Knocked Out!**\nWaiting for revive...",
                    )
                    button.disabled, button.label, button.style = (
                        True,
                        "Respawning...",
                        discord.ButtonStyle.secondary,
                    )
                    boss_display_name = ws.boss["name"] if (ws and ws.boss) else "Boss"
                    self.full_logs = engine.logs + [
                        f"💀 **{boss_display_name}** defeated you!",
                        self.last_activity,
                    ]
                    asyncio.create_task(self.handle_respawn(interaction))
                else:
                    self.last_activity = "💀 **Hunt Failed! Portal Collapsed.**"
                    self.full_logs = engine.logs + [self.last_activity]
                    button.disabled, button.label = True, "Game Over"
                    for child in self.children:
                        if (
                            isinstance(child, discord.ui.Button)
                            and child.label == "Return Home"
                        ):
                            child.style = discord.ButtonStyle.primary
                    self.is_processing = False
            else:
                self.is_processing, button.disabled = False, False

            return await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=self.create_embed(),
                view=self,
            )

        weapon_data = {
            "id": "monster_slugger",
            "modifier": "Standard",
            "level": 1,
        }
        gadgets = []
        if kit_data.get("weapon"):
            weapon_data = kit_data["weapon"]
        if kit_data.get("gadgets"):
            gadgets = kit_data["gadgets"]

        cog = self.bot.get_cog("Hunting")
        active_count = len(ws.hunters) + len(ws.ghosts) + len(ws.bots)
        monster_id, monster_lvl, is_boss = cog._spawn_monster(
            self.world["id"],
            self.world["type"],
            self.world["unlock_lvl"],
            luck=luck_val,
            user_id=self.user_id,
            active_players=active_count,
        )
        modifier = cog._roll_modifier(self.world["id"], is_boss, self.user_id)

        xp_lvl = monster_lvl
        if modifier == "Overcharged":
            xp_lvl += 10
        elif modifier == "Megacharged":
            xp_lvl += 25

        rgp = config.WORLD_RGP.get(self.world["id"], 50)
        base_icon = config.MOBS.get(monster_id, utils.get_emoji(self.bot, monster_id))
        mod_icons, display_name = cog.format_modifier_display(modifier, monster_id)
        m_icon = f"{mod_icons} {base_icon}".strip()

        if (
            ws.boss is None
            and self.world["unlock_lvl"] >= 12
            and random.random() < (0.05 + active_count * 0.02)
        ):
            clean_name = utils.format_monster_name(monster_id)
            if is_boss:
                hp, dur, tier = 150000, 300, "T2"
                if "Megacharged" in modifier:
                    if "Chaos" in modifier:
                        hp, dur, tier = 500000, 900, "T4"
                    else:
                        hp, dur, tier = 300000, 600, "T3"
                elif "Chaos" in modifier and "Overcharged" in modifier:
                    hp, dur, tier = 200000, 300, "T3"
                elif "Chaos" in modifier:
                    hp, dur, tier = 75000, 300, "T2"
                else:
                    hp, dur, tier = 15000, 120, "T1"
                ws.spawn_boss(
                    f"{modifier} {clean_name}", hp, monster_lvl + 10, dur, tier
                )
                self.last_activity, self.is_processing = (
                    f"⚠️ **{modifier} {clean_name.upper()} SPAWNED!**",
                    False,
                )
                self.update_action_button()
                return await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    embed=self.create_embed(),
                    view=self,
                )

        if "mo.co Crate" in monster_id:
            database.update_user_stats(
                self.user_id, {"merch_tokens": u_dict["merch_tokens"] + 10}
            )
            self.session_tokens += 10
            self.last_activity = (
                f"{config.MOCO_CRATE_EMOJI} **mo.co Crate Found! +10 Tokens**"
            )
            self.full_logs.append(self.last_activity)
            self.is_processing = False
            button.disabled, button.label = False, "Hunt Again"
            return await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=self.create_embed(),
                view=self,
            )

        engine = CombatEngine(self.bot, gamemode="hunt", mode="sim")
        player = CombatEntity(engine, self.user.display_name, is_player=True)
        player.user_id, player.icon = self.user_id, emblem
        player.setup_stats(
            player_lvl,
            hp=u_dict["current_hp"],
            weapon=weapon_data,
            gadgets=gadgets,
            passives=passives,
        )

        if player_lvl < 5:
            player.max_hp *= 10
            player.hp, player.attack_pwr = player.max_hp, max(
                100, player.attack_pwr * 5
            )

        engine.add_entity(player, "A")

        allies = ws.get_nearby_allies(exlcude_id=self.user_id)
        npc_ally_name = None
        for ally in allies:
            if ally["type"] in ["player", "ghost", "bot"]:
                clone = CombatEntity(engine, ally["name"], is_player=True, is_bot=True)
                clone.icon = ally.get("emblem", "👤")

                w_data = {
                    "id": "monster_slugger",
                    "modifier": "Standard",
                    "level": ally["lvl"],
                }
                g_data = []
                p_data = {}

                if "kit" in ally:
                    k = ally["kit"]
                    if k.get("weapon"):
                        w_data = k["weapon"]
                    if k.get("gadgets"):
                        g_data = k["gadgets"]
                    if k.get("passives"):
                        p_data = k["passives"]

                clone.setup_stats(
                    ally["lvl"], weapon=w_data, gadgets=g_data, passives=p_data
                )
                engine.add_entity(clone, "A")

            elif ally["type"] == "npc":
                npc_ally_name = ally["name"]
                if random.random() < 0.2:
                    ws.damage_npc(random.randint(100, 500))
                npc = CombatEntity(
                    engine, f"{ally['name']}", is_player=True, is_bot=True
                )
                npc.icon = NPC_CONFIG[ally["name"]]["emoji"]
                npc.setup_stats(
                    50,
                    hp=ally["hp"],
                    weapon={"id": ally["weapon"], "level": 50},
                )
                engine.add_entity(npc, "A")

        mob = CombatEntity(engine, display_name, is_player=False, source_id=monster_id)
        mob.icon = m_icon
        mob.icon, starting_hp = m_icon, int(u_dict["current_hp"])
        combat_atk_mult, combat_hp_mult = 1.0, 1.0
        mob.apply_modifier(modifier)

        if "Megacharged" in modifier or "Chaos" in modifier:
            if "Megacharged" in modifier:
                combat_atk_mult, combat_hp_mult = 2.5, 1.8
            else:
                combat_atk_mult = 1.2
        elif "Overcharged" in modifier:
            combat_atk_mult, combat_hp_mult = 1.5, 1.3

        gp_deficit, atk_mult = rgp - player_gp, combat_atk_mult
        if gp_deficit > 0:
            atk_mult *= 1.0 + (gp_deficit / rgp) * 4
            if player_lvl >= 5:
                player.attack_pwr = int(player.attack_pwr * (rgp / (rgp + gp_deficit)))
        else:
            atk_mult *= max(0.5, 1.0 - (abs(gp_deficit) / (rgp * 2.0)))

        m_hp = int(
            (1200 + (xp_lvl * 150) + (xp_lvl**2) * 4)
            * combat_hp_mult
            * (1.0 + len(allies) * 0.3)
        )
        if is_boss:
            m_hp *= 2.5
            atk_mult *= 1.5
        mob.setup_stats(xp_lvl, hp=m_hp)
        mob.attack_pwr = int(xp_lvl * 8 * atk_mult)
        engine.add_entity(mob, "B")
        engine.simulate_battle()

        real_current_hp = player.hp if player_lvl >= 5 else int(player.hp / 10)
        net_hp = real_current_hp - starting_hp
        hp_line = f"❤️ **{'+' if net_hp>=0 else ''}{net_hp}**"

        if real_current_hp <= 0:
            self.lives -= 1
            database.update_user_stats(self.user_id, {"current_hp": 0})
            cog.update_progression(
                self.user_id,
                monster_id,
                self.world["id"],
                modifier,
                "Boss" if is_boss else "Normal",
                damage_sources=player.damage_sources,
                heal_sources=player.heal_sources,
                npc_ally=npc_ally_name,
            )
            if self.lives > 0:
                self.respawn_ts, self.last_activity = (
                    datetime.now() + timedelta(seconds=10),
                    f":skull: **Knocked Out!**\nWaiting for revive...",
                )
                button.disabled, button.label, button.style = (
                    True,
                    "Respawning...",
                    discord.ButtonStyle.secondary,
                )
                self.full_logs = engine.logs + [
                    f"💀 **{mob.name}** defeated you!",
                    self.last_activity,
                ]
                asyncio.create_task(self.handle_respawn(interaction))
            else:
                self.last_activity = "💀 **Hunt Failed! Portal Collapsed.**"
                self.full_logs = engine.logs + [self.last_activity]
                button.disabled, button.label = True, "Game Over"
                for child in self.children:
                    if (
                        isinstance(child, discord.ui.Button)
                        and child.label == "Return Home"
                    ):
                        child.style = discord.ButtonStyle.primary
                self.is_processing = False
            self.log_page = 0
            if not any(isinstance(x, LogUpButton) for x in self.children):
                self.add_item(LogUpButton())
                self.add_item(LogDownButton())
            return await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=self.create_embed(),
                view=self,
            )

        xp_multiplier = 1.0 + player.xp_mult_bonus
        loot_mod_mult = 1.0
        if "Overcharged" in modifier:
            loot_mod_mult = 2.0
        elif "Megacharged" in modifier:
            loot_mod_mult = 4.0
        for e in self.active_boosts:
            if e["event_type"] == "xp_boost":
                xp_multiplier *= e["multiplier"]

        is_jackpot = random.random() * 100 < luck_val
        if is_jackpot:
            xp_multiplier *= 4.0

        xp_gain, bank_consumed, fuel_consumed = cog._calculate_xp(
            u_dict,
            monster_id,
            xp_lvl,
            player_lvl,
            xp_multiplier,
            is_boss,
            self.world["id"],
            modifier,
        )

        shards, cores = cog._generate_loot(
            u_dict,
            monster_id,
            is_boss,
            loot_mod_mult,
            player_lvl,
            xp_lvl,
            is_jackpot=is_jackpot,
            world_id=self.world["id"],
        )

        if fuel_consumed > 0:
            shards, cores = int(shards * 1.5), int(cores * 1.5)

        utils.add_user_xp(self.user_id, xp_gain)
        self.session_xp += xp_gain
        self.session_shards += shards
        self.session_cores += cores

        final_hp = min(int(max(0, real_current_hp)), max_hp)

        database.update_user_stats(
            self.user_id,
            {
                "chaos_shards": u_dict["chaos_shards"] + shards,
                "chaos_cores": u_dict["chaos_cores"] + cores,
                "current_hp": final_hp,
                "daily_xp_total": max(0, u_dict["daily_xp_total"] - bank_consumed),
                "daily_xp_boosted": max(0, u_dict["daily_xp_boosted"] - fuel_consumed),
            },
        )
        cog.update_progression(
            self.user_id,
            monster_id,
            self.world["id"],
            modifier,
            "Boss" if is_boss else "Normal",
            loot_xp=xp_gain,
            damage_sources=player.damage_sources,
            heal_sources=player.heal_sources,
            npc_ally=npc_ally_name,
        )

        header_msg = (
            f"{m_icon} **Lvl {xp_lvl} {mob.name}**\n"
            f"+{xp_gain:,} {config.XP_BOOST_3X_EMOJI if fuel_consumed > 0 else config.XP_EMOJI}"
        )
        if is_jackpot:
            header_msg = f"{config.BUNCH_OF_DICE_EMOJI} **JACKPOT (x4)** {header_msg}"
        loot_bits = []
        if shards > 0:
            loot_bits.append(f"{config.CHAOS_SHARD_EMOJI} +{shards}")
        if cores > 0:
            loot_bits.append(f"{config.CHAOS_CORE_EMOJI} +{cores}")
        if loot_bits:
            header_msg += " | " + " ".join(loot_bits)
        self.last_activity, self.full_logs = header_msg, engine.logs + [
            header_msg,
            hp_line,
        ]
        self.log_page, self.is_processing = 0, False
        button.disabled, button.label = False, "Hunt Again"
        if not any(isinstance(x, LogUpButton) for x in self.children):
            self.add_item(LogUpButton())
            self.add_item(LogDownButton())
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=self.create_embed(),
            view=self,
        )

    @discord.ui.button(
        label="Return Home",
        style=discord.ButtonStyle.secondary,
        emoji=discord.PartialEmoji.from_str(config.MAP_EMOJI),
        row=2,
    )
    async def return_home(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id or self.is_processing:
            return
        self.is_processing = True
        WORLD_MGR.check_out(self.world["id"], self.user_id)
        u_data = database.get_user_data(self.user_id)
        player_lvl, _, _ = utils.get_level_info(u_data["xp"])
        if self.lives > 0:
            database.update_user_stats(
                self.user_id,
                {
                    "current_hp": utils.get_max_hp(self.user_id, player_lvl),
                    "weapon_combo_count": 0,
                },
            )
            actual_shards = self.session_shards if player_lvl >= 12 else 0
            summary = HuntSummaryView(
                self.bot,
                self.user,
                self.session_xp,
                actual_shards,
                self.session_cores,
                player_lvl,
                self.start_lvl,
                [],
                self.session_tokens,
                world_id=self.world["id"],
            )
            await interaction.response.edit_message(
                embed=summary.get_embed(), view=summary
            )
        else:
            database.update_user_stats(self.user_id, {"current_hp": 100})
            embed = discord.Embed(
                title="💀 Hunt Failed",
                description="You collapsed and were emergency teleported home.\n**All session loot was lost.**",
                color=0xE74C3C,
            )
            await interaction.response.edit_message(embed=embed, view=None)


class TargetSelect(discord.ui.Select):
    def __init__(self, current_target="standard"):
        options = [
            discord.SelectOption(
                label="Standard Hunt",
                value="standard",
                description="Hunt regular monsters",
                emoji=utils.safe_emoji(config.ELITE_EMOJI),
                default=(current_target == "standard"),
            ),
            discord.SelectOption(
                label="Attack Boss",
                value="boss",
                description="Attack the shared threat",
                emoji=utils.safe_emoji(config.CHAOS_ALERT),
                default=(current_target == "boss"),
            ),
        ]
        super().__init__(placeholder="Select Target...", row=0, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_target = self.values[0]
        self.view.update_action_button()
        await interaction.response.edit_message(
            embed=self.view.create_embed(), view=self.view
        )


class HuntLoadoutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Loadout", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=interaction.client.get_cog("Loadout").generate_kit_embed(
                interaction.user.id, interaction.user.display_name
            ),
            ephemeral=True,
        )


class LogUpButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬇️ Old Logs", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction):
        self.view.log_page += 1
        await interaction.response.edit_message(
            embed=self.view.create_embed(), view=self.view
        )


class LogDownButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="⬆️ New Logs", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction):
        if self.view.log_page > 0:
            self.view.log_page -= 1
            await interaction.response.edit_message(
                embed=self.view.create_embed(), view=self.view
            )
        else:
            await interaction.response.defer()


class LootRevealView(discord.ui.View):
    def __init__(
        self,
        bot,
        user,
        pending,
        player_lvl,
        start_lvl,
        is_elite=False,
        world_idx=0,
    ):
        super().__init__(timeout=300)
        self.bot, self.user, self.user_id = bot, user, user.id
        (
            self.pending,
            self.player_lvl,
            self.start_lvl,
            self.is_elite,
            self.world_idx,
        ) = (
            pending,
            player_lvl,
            start_lvl,
            is_elite,
            world_idx,
        )
        self.index = 0
        self.add_item(OpenCoreButton())

    async def finish(self, interaction):
        await interaction.message.delete()
        u = database.get_user_data(self.user_id)
        u_dict = dict(u)
        end_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        if end_lvl > self.start_lvl:
            for lvl in range(self.start_lvl + 1, end_lvl + 1):
                utils.apply_level_reward(self.user_id, lvl)
            await interaction.channel.send(
                embed=utils.create_level_up_embed(self.user, end_lvl),
                view=utils.LevelUpView(self.bot, self.user_id, end_lvl),
            )

        try:
            m_state = json.loads(u_dict.get("mission_state", "{}"))
            active_list = m_state.get("active", [])
            for mid in active_list:
                m_def = MISSIONS.get(mid)
                if not m_def:
                    continue
                m_data = m_state["states"].get(mid, {})
                step = m_def["steps"][m_data.get("step", 0)]

                if step["type"] == "objective_level":
                    req_lvl = step["count"]
                    if end_lvl >= req_lvl:
                        thread_id = u_dict.get("mission_thread_id")
                        if thread_id:
                            engine = MissionEngine(
                                self.bot,
                                self.user_id,
                                thread_id,
                                specific_mission_id=mid,
                            )
                            asyncio.create_task(engine.progress())
        except Exception as e:
            print(f"Level up trigger error: {e}")


class OpenCoreButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Open Chaos Core",
            style=discord.ButtonStyle.primary,
            emoji=discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
        )

    async def callback(self, interaction):
        view = self.view
        if interaction.user.id != view.user_id:
            return
        view.index += 1
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{config.CHAOS_CRACK_EMOJI} **CRACK!**",
                color=0xF1C40F,
            ),
            view=None,
        )
        await asyncio.sleep(0.8)
        inventory = database.get_user_inventory(view.user_id)
        item_types = ["weapon", "gadget", "passive"]
        if view.is_elite:
            item_types.append("smart_ring")
        pool = [
            k
            for k, v in game_data.ALL_ITEMS.items()
            if v["type"] in item_types
            and k != "bunch_of_dice"
            and not v.get("shop_exclusive", False)
        ]
        if random.random() < 0.30 or not inventory:
            key = random.choice(pool if pool else ["monster_slugger"])
            mod = random.choices(
                config.HUNT_MODS,
                weights=(
                    config.HUNT_WEIGHTS
                    if view.world_idx >= 7
                    else [90, 8, 2, 0, 0, 0, 0]
                ),
                k=1,
            )[0]
            item_def, lvl = game_data.get_item(key), 1
            if item_def["type"] != "smart_ring":
                lvl = min(50, max(1, view.player_lvl - random.randint(0, 2)))
            database.add_item_to_inventory(view.user_id, key, mod, lvl)
            pedia.track_gear(view.user_id, key, mod, source="core")
            pedia.track_archive(
                view.user_id, "Core", key, item_def.get("rarity", "Common")
            )
            embed = discord.Embed(
                title=f"NEW {'' if mod=='Standard' else mod+' '}{item_def['name'].upper()}",
                color=0x9B59B6,
                description=f"{utils.get_emoji(view.bot, key)} *A new item manifests from Chaos!*",
            )
            embed.add_field(name="LEVEL", value=f"**{lvl}**", inline=True)
            embed.add_field(
                name="POWER",
                value=f"{config.GEAR_POWER_EMOJI} **{utils.get_item_gp(key, lvl):,}**",
                inline=True,
            )
            embed.add_field(
                name="STATS",
                value=utils.get_item_stats(key, lvl)[0],
                inline=False,
            )
        else:
            target = random.choice(inventory)
            item_id, old_lvl = target["item_id"], target["level"]
            boost = random.choices(
                [1, 2, 3, 4, 5, 6, 7], weights=[7, 6, 5, 4, 3, 2, 1], k=1
            )[0]
            item_def = game_data.get_item(item_id)
            max_cap = view.player_lvl
            if item_def["type"] == "smart_ring":
                u_data = database.get_user_data(view.user_id)
                e_lvl, _, _ = utils.get_elite_level_info(u_data["elite_xp"])
                max_cap = e_lvl
            boost = min(boost, max_cap - old_lvl) if old_lvl < max_cap else 0
            if boost > 0:
                database.upgrade_item_level(target["instance_id"], max_cap, boost)
            new_lvl = old_lvl + boost
            pedia.track_upgrade(view.user_id, item_id, new_lvl)
            pedia.track_archive(view.user_id, "Core", item_id, "Upgrade")
            embed = discord.Embed(
                title=item_def["name"].upper(),
                color=0x9B59B6,
                description=f"{utils.get_emoji(view.bot, item_id)} *Chaos energy surges!*",
            )
            embed.add_field(
                name="LEVEL",
                value=f"**{old_lvl}** ➔ **{new_lvl}** `+{boost}`",
                inline=True,
            )
            embed.add_field(
                name="POWER",
                value=f"{config.GEAR_POWER_EMOJI} **{utils.get_item_gp(item_id, old_lvl):,}** ➔ **{utils.get_item_gp(item_id, new_lvl):,}**",
                inline=True,
            )
            embed.add_field(
                name="STATS",
                value=utils.get_stat_diff(item_id, old_lvl, new_lvl),
                inline=False,
            )
        view.clear_items()
        if view.index >= len(view.pending):
            btn = discord.ui.Button(label="Finish", style=discord.ButtonStyle.success)
            btn.callback = view.finish
            view.add_item(btn)
        else:
            view.add_item(OpenCoreButton())
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=view
        )


class HuntSummaryView(discord.ui.View):
    def __init__(
        self,
        bot,
        user,
        xp,
        shards,
        cores,
        current_lvl,
        start_lvl,
        claimed_projects=None,
        tokens=0,
        world_id=None,
    ):
        super().__init__(timeout=180)
        (
            self.bot,
            self.user,
            self.xp,
            self.shards,
            self.cores,
            self.tokens,
            self.current_lvl,
            self.start_lvl,
            self.claimed_projects,
            self.claimed_cores,
            self.world_id,
        ) = (
            bot,
            user,
            xp,
            shards,
            cores,
            tokens,
            current_lvl,
            start_lvl,
            claimed_projects or [],
            False,
            world_id,
        )
        self.user_id = user.id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.cores > 0 and not self.claimed_cores:
            btn = discord.ui.Button(
                label=f"Open Cores ({self.cores})",
                style=discord.ButtonStyle.success,
                emoji=discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
            )
            btn.callback = self.open_cores_callback
            self.add_item(btn)
        done_btn = discord.ui.Button(
            label="Done",
            style=discord.ButtonStyle.secondary,
            custom_id="done_btn",
            disabled=(self.cores > 0 and not self.claimed_cores),
        )
        done_btn.callback = self.done_callback
        self.add_item(done_btn)

    def get_embed(self):
        embed = discord.Embed(
            title="🏠 Home Sweet Home",
            color=0x2ECC71,
            description=(
                f"**Hunt Complete!**\n{config.XP_EMOJI} +{self.xp:,} XP\n"
                + (
                    f"{config.CHAOS_SHARD_EMOJI} +{self.shards} Shards\n"
                    if self.shards > 0
                    else ""
                )
                + (
                    f"{config.CHAOS_CORE_EMOJI} +{self.cores} Cores\n"
                    if self.cores > 0
                    else ""
                )
                + (
                    f"{config.MERCH_TOKEN_EMOJI} +{self.tokens} Tokens"
                    if self.tokens > 0
                    else ""
                )
            ),
        )

        objectives = []
        u_dict = dict(database.get_user_data(self.user_id))
        ms = json.loads(u_dict.get("mission_state", "{}"))
        completed_ms = ms.get("completed", [])
        active_ms = ms.get("active", [])

        mob_pool = []
        world_type = None
        if self.world_id:
            w_def = game_data.get_world(self.world_id)
            if w_def:
                world_type = w_def["type"]
                mob_pool = game_data.get_monsters_for_world(self.world_id, world_type)

        for mid in active_ms:
            m_def = MISSIONS.get(mid)
            if not m_def:
                continue
            m_data = ms["states"].get(mid, {})
            step_idx = m_data.get("step", 0)
            if step_idx < len(m_def["steps"]):
                step = m_def["steps"][step_idx]
                stype = step["type"]

                if stype in [
                    "objective_rift_boss",
                    "objective_dojo",
                    "objective_versus",
                ]:
                    continue

                if stype == "objective_hunt":
                    if step["target"] != "any" and step["target"] not in mob_pool:
                        if (
                            not step.get("world_id")
                            or step["world_id"] != self.world_id
                        ):
                            continue

                if stype == "objective_checklist":
                    lines = [f"{config.MISSION_EMOJI} **{m_def['name']}**"]
                    prog_list = m_data.get("prog", [])
                    if isinstance(prog_list, int):
                        prog_list = [0] * len(step["targets"])
                    for i, t in enumerate(step["targets"]):
                        curr = prog_list[i] if i < len(prog_list) else 0
                        req = t["count"]
                        check_icon = "✅" if curr >= req else "⬜"
                        lines.append(f"- {check_icon} {t['desc']} ({curr}/{req})")
                    objectives.append("\n".join(lines))
                elif "objective" in stype:
                    prog = m_data.get("prog", 0)
                    limit = step.get("count", 1)
                    desc = step.get("desc", "Mission in progress...")
                    objectives.append(
                        f"{config.MISSION_EMOJI} **{desc}** ({prog}/{limit})"
                    )

        jobs_unlocked = "chaos" in completed_ms or "chaos" in active_ms
        projs_unlocked = "paidovertime" in completed_ms or "paidovertime" in active_ms

        if jobs_unlocked:
            jobs = json.loads(u_dict.get("active_jobs", "[]"))
            for job in jobs:
                if job.get("completed", False) or job.get("claimed", False):
                    continue
                if _is_relevant(
                    job["target_type"],
                    job["target"],
                    self.world_id,
                    world_type,
                    mob_pool,
                ):
                    objectives.append(
                        f"<:dailyjob:1452418984984186890> **{job['desc']}** ({job['progress']}/{job['count']})"
                    )

        if projs_unlocked:
            proj_data = json.loads(u_dict.get("project_progress", "{}"))
            grouped = {}
            for pid, pdata in PROJECTS.items():
                group = pdata.get("group", pid)
                if group not in grouped:
                    grouped[group] = []
                grouped[group].append((pid, pdata))

            for group, items in grouped.items():
                items.sort(key=lambda x: x[1].get("tier", 1))
                active_proj = None
                for pid, pdata in items:
                    entry = proj_data.get(pid, {"prog": 0, "claimed": False})
                    if isinstance(entry, int):
                        entry = {"prog": entry, "claimed": False}
                    if not entry.get("claimed", False):
                        active_proj = (pid, pdata, entry.get("prog", 0))
                        break

                if active_proj:
                    pid, pdata, prog = active_proj
                    if _is_relevant(
                        pdata["target_type"],
                        pdata["target"],
                        self.world_id,
                        world_type,
                        mob_pool,
                    ):
                        objectives.append(
                            f"<:project:1452418974410084515> **{pdata['desc']}** ({prog}/{pdata['count']})"
                        )

        if objectives:
            display_list = objectives[:5]
            final_text = "\n".join(display_list)
            if len(objectives) > 5:
                final_text += f"\n*...and {len(objectives) - 5} more*"
            embed.add_field(name="Active Objectives", value=final_text, inline=False)

        return embed

    async def open_cores_callback(self, interaction):
        self.claimed_cores = True
        u_data = database.get_user_data(self.user_id)
        database.update_user_stats(
            self.user_id, {"chaos_cores": u_data["chaos_cores"] - self.cores}
        )
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{config.CHAOS_CORE_EMOJI} Opening {self.cores} Cores...",
                color=0x9B59B6,
            ),
            view=LootRevealView(
                self.bot,
                self.user,
                [
                    {"type": "new" if random.random() < 0.3 else "upgrade"}
                    for _ in range(self.cores)
                ],
                self.current_lvl,
                self.start_lvl,
                bool(u_data["is_elite"]),
                0,
            ),
        )

    async def done_callback(self, interaction):
        if interaction.user.id != self.user_id:
            return
        u_dict = dict(database.get_user_data(self.user_id))
        end_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        try:
            await interaction.message.delete()
        except:
            pass
        if end_lvl > self.start_lvl:
            for lvl in range(self.start_lvl + 1, end_lvl + 1):
                utils.apply_level_reward(self.user_id, lvl)
            await interaction.channel.send(
                embed=utils.create_level_up_embed(self.user, end_lvl),
                view=utils.LevelUpView(self.bot, self.user_id, end_lvl),
            )

        try:
            m_state = json.loads(u_dict.get("mission_state", "{}"))
            active_list = m_state.get("active", [])
            for mid in active_list:
                m_def = MISSIONS.get(mid)
                if not m_def:
                    continue
                m_data = m_state["states"].get(mid, {})
                step = m_def["steps"][m_data.get("step", 0)]

                if step["type"] == "objective_level":
                    req_lvl = step["count"]
                    if end_lvl >= req_lvl:
                        thread_id = u_dict.get("mission_thread_id")
                        if thread_id:
                            engine = MissionEngine(
                                self.bot,
                                self.user_id,
                                thread_id,
                                specific_mission_id=mid,
                            )
                            asyncio.create_task(engine.progress())
        except Exception as e:
            print(f"Level up trigger error: {e}")


async def setup(bot):
    await bot.add_cog(Hunting(bot))

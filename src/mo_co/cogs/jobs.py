import discord
from discord import app_commands
from discord.ext import commands
import json
import random
from datetime import datetime, timedelta
from discord.ui import View, Button, Select, Modal, TextInput
from mo_co.mission_engine import MissionEngine
from mo_co.game_data.missions import MISSIONS
from mo_co import database, config, game_data, utils
import asyncio


class Jobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_job_icon(self, job):
        t_type = job["target_type"]
        if t_type == "hunt_mob":
            return utils.get_emoji(self.bot, job["target"])
        elif t_type == "hunt_type" and job["target"] == "Overcharged":
            return config.OVERCHARGED_ICON
        else:
            return config.DAILY_JOB_EMOJI

    def generate_jobs(self, user_id, count=3):
        u_data = database.get_user_data(user_id)
        if not u_data:
            return []
        u_dict = dict(u_data)
        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        unlocked_worlds = [w for w in game_data.WORLDS if player_lvl >= w["unlock_lvl"]]
        if not unlocked_worlds:
            return []

        new_jobs = []
        for _ in range(count):
            tpl = random.choice(game_data.JOB_TEMPLATES)
            job = {
                "desc": tpl["desc"],
                "target_type": tpl["target_type"],
                "target": tpl["target"],
                "count": tpl["count"],
                "progress": 0,
                "completed": False,
                "claimed": False,
            }

            if "{world_id}" in str(job["target"]):
                w = random.choice(unlocked_worlds)
                job["target"] = w["id"]
                job["desc"] = job["desc"].replace("{world_name}", w["name"])

            if "{mob_id}" in str(job["target"]):
                w = random.choice(unlocked_worlds)
                pool = game_data.get_monsters_for_world(w["id"], w["type"])

                if pool:
                    mob = random.choice(pool)
                    job["target"] = mob
                    job["desc"] = job["desc"].replace(
                        "{mob_name}", utils.format_monster_name(mob)
                    )

                    if "boss" in mob.lower():
                        job["count"] = 1

                else:
                    job["target_type"] = "hunt_any"
                    job["desc"] = "Hunt Monsters"

            new_jobs.append(job)
        return new_jobs

    def check_refresh(self, user_id):
        u_data = database.get_user_data(user_id)
        if not u_data:
            return
        u_dict = dict(u_data)

        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        if player_lvl < 9:
            return

        current_jobs = json.loads(u_dict["active_jobs"])

        repaired = False
        for job in current_jobs:
            if "boss" in str(job.get("target", "")).lower() and job.get("count", 0) > 1:
                job["count"] = 1

                if job["progress"] >= 1:
                    job["completed"] = True
                repaired = True

        if repaired:
            database.update_user_stats(
                user_id, {"active_jobs": json.dumps(current_jobs)}
            )

        last_spawn_str = u_dict["last_job_spawn"]
        last = (
            datetime.now() - timedelta(hours=12)
            if not last_spawn_str
            else datetime.fromisoformat(last_spawn_str)
        )
        now = datetime.now()
        diff = now - last
        intervals_passed = int(diff.total_seconds() // (4 * 3600))

        if not current_jobs and intervals_passed < 1:
            intervals_passed = 1
            to_add = 4
        else:
            if len(current_jobs) >= 8:
                current_jobs = [j for j in current_jobs if not j.get("claimed", False)]

            slots_open = 10 - len(current_jobs)
            to_add = min(intervals_passed, slots_open)

        if to_add > 0:
            new_generated = self.generate_jobs(user_id, to_add)
            current_jobs.extend(new_generated)

            new_timestamp = (last + timedelta(hours=intervals_passed * 4)).isoformat()
            if not last_spawn_str:
                new_timestamp = datetime.now().isoformat()

            database.update_user_stats(
                user_id,
                {
                    "active_jobs": json.dumps(current_jobs),
                    "last_job_spawn": new_timestamp,
                },
            )
        elif intervals_passed > 0:
            database.update_user_stats(
                user_id,
                {
                    "last_job_spawn": (
                        last + timedelta(hours=intervals_passed * 4)
                    ).isoformat()
                },
            )

    def get_jobs_embed(self, user_id):

        self.check_refresh(user_id)

        u_data = dict(database.get_user_data(user_id))
        jobs = json.loads(u_data["active_jobs"])
        last_spawn = u_data.get("last_job_spawn")
        last = datetime.fromisoformat(last_spawn) if last_spawn else datetime.now()
        next_refresh = int((last + timedelta(hours=4)).timestamp())

        embed = discord.Embed(
            title=f"{config.DAILY_JOB_EMOJI} Daily Jobs", color=0xE67E22
        )
        desc_lines = []
        active_jobs = [j for j in jobs if not j.get("claimed", False)]

        if not active_jobs:
            desc_lines.append("No active jobs. Check back soon!")

        for job in active_jobs:
            status_icon = "🟩" if job.get("completed") else "🟦"
            icon = self.get_job_icon(job)
            pct = min(1.0, job["progress"] / job["count"])
            filled = int(pct * 8)
            bar = "🟦" * filled + "⬛" * (8 - filled)
            claim_txt = " **[READY]**" if job.get("completed") else ""
            desc_lines.append(
                f"{icon} **{job['desc']}** {status_icon}{claim_txt}\n`{bar}` {job['progress']}/{job['count']}\n"
            )

        embed.description = "\n".join(desc_lines)
        bonus = u_data["job_completion_count"]
        bonus_str = f"{bonus}/3" if bonus < 3 else "READY!"
        embed.add_field(
            name="Bonus Rewards",
            value=f"Next Job <t:{next_refresh}:R>\nBonus Kit: {config.CHAOS_CORE_EMOJI} **{bonus_str}**",
            inline=False,
        )
        return embed

    def get_projects_embed(
        self, user_id, page=0, search_query=None, sort_method="Default Sort"
    ):
        u_data = dict(database.get_user_data(user_id))
        prog_data = json.loads(u_data["project_progress"])
        player_lvl, _, _ = utils.get_level_info(u_data["xp"])

        def _compute(pid, pdata):
            t_type = pdata["target_type"]
            entry = prog_data.get(pid, {"prog": 0, "claimed": False})
            if isinstance(entry, int):
                entry = {"prog": entry, "claimed": False}
            current, claimed = entry.get("prog", 0), entry.get("claimed", False)
            if t_type == "reach_level":
                current = player_lvl
            elif t_type == "open_core":
                inv = database.get_user_inventory(user_id)
                current = sum(1 for i in inv if i["level"] > 1) if inv else 0
            elif t_type == "collect_item":
                inv = database.get_user_inventory(user_id)
                current = len(set(i["item_id"] for i in inv)) if inv else 0
            return current, claimed

        final_list = []
        grouped = {}
        for pid, pdata in game_data.PROJECTS.items():
            group = pdata.get("group", pid)
            if group not in grouped:
                grouped[group] = []
            grouped[group].append((pid, pdata))

        for group, items in grouped.items():
            items.sort(key=lambda x: x[1].get("tier", 1))
            active_proj = None
            for pid, pdata in items:
                current, claimed = _compute(pid, pdata)
                if not claimed:
                    active_proj = (
                        pid,
                        pdata,
                        current,
                        pdata["count"],
                        claimed,
                    )
                    break
            if not active_proj:
                last_pid, last_pdata = items[-1]
                last_cur, last_clm = _compute(last_pid, last_pdata)
                active_proj = (
                    last_pid,
                    last_pdata,
                    last_cur,
                    last_pdata["count"],
                    last_clm,
                )

            if active_proj:
                if search_query and search_query not in active_proj[1]["desc"].lower():
                    continue
                final_list.append(active_proj)

        if sort_method == "Sort by Completion":
            final_list.sort(key=lambda x: (x[4], -(x[2] / x[3] if x[3] > 0 else 0)))
        elif sort_method == "Sort by XP Reward":
            final_list.sort(key=lambda x: (x[4], -x[1].get("reward_xp", 0)))
        else:
            final_list.sort(key=lambda x: (x[4], x[1]["group"]))

        embed = discord.Embed(title=f"{config.PROJECT_EMOJI} Projects", color=0x3498DB)
        if search_query:
            embed.description = f"Filter: **{search_query}**"

        per_page = 5
        start = page * per_page
        chunk = final_list[start : start + per_page]

        if not chunk:
            embed.description = "No available projects."
        for pid, pdata, current, target, claimed in chunk:
            pct = min(1.0, current / target) if target > 0 else 0
            bar = "🟦" * int(pct * 10) + "⬛" * (10 - int(pct * 10))
            reward = pdata.get("reward_xp", 1000)
            status = " ✅" if claimed else (" **[READY]**" if current >= target else "")

            t_type = pdata.get("target_type")
            raw_icon = pdata.get("icon")
            icon = config.PROJECT_EMOJI

            if t_type in ["dojo_clear", "dojo_time"]:
                icon = config.DOJO_ICON
            elif t_type == "rift_time":
                icon = config.RIFTS_EMOJI
            elif raw_icon:
                if raw_icon.startswith("<") or len(raw_icon) < 4:
                    icon = raw_icon
                elif raw_icon in config.MOBS:
                    icon = config.MOBS[raw_icon]
                else:
                    e = utils.get_emoji(self.bot, raw_icon)
                    if e and not e.startswith("📦"):
                        icon = e
                    elif raw_icon == "Overcharged":
                        icon = config.OVERCHARGED_ICON
                    elif raw_icon == "Chaos":
                        icon = config.CHAOS_CORE_EMOJI

            embed.add_field(
                name="\u200b",
                value=f"{icon} **{pdata['desc']}**{status}\n`{bar}` {current}/{target} | {reward:,} {config.XP_EMOJI}",
                inline=False,
            )

        max_p = max(1, (len(final_list) - 1) // per_page + 1)
        embed.set_footer(text=f"Page {page+1}/{max_p} | Total: {len(final_list)}")
        return embed, final_list


class TabButton(Button):
    def __init__(self, label, tab_id, style, emoji, disabled=False):
        super().__init__(
            label=label, style=style, emoji=emoji, row=0, disabled=disabled
        )
        self.tab_id = tab_id

    async def callback(self, i):

        if self.tab_id == "projects":
            u_data = dict(database.get_user_data(self.view.user_id))
            m_state = json.loads(u_data.get("mission_state", "{}"))

            is_unlocked = "paidovertime" in m_state.get(
                "completed", []
            ) or "paidovertime" in m_state.get("active", [])

            if not is_unlocked:
                return await i.response.send_message(
                    "❌ Projects are locked! Start the 'Paid Overtime' mission first.",
                    ephemeral=True,
                )

        self.view.tab, self.view.page = self.tab_id, 0
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ReturnToMissionBtn(Button):
    def __init__(self):
        super().__init__(
            label="Back to Phone",
            style=discord.ButtonStyle.secondary,
            emoji="📱",
            row=0,
        )

    async def callback(self, i):
        from mo_co.cogs.missions import PhoneDashboardView

        u_dict = dict(database.get_user_data(self.view.user_id))
        m_state = json.loads(u_dict["mission_state"])
        await i.response.edit_message(
            embed=PhoneDashboardView(
                self.view.bot, self.view.user_id, m_state
            ).get_embed(),
            view=PhoneDashboardView(self.view.bot, self.view.user_id, m_state),
        )


class ProjectSortSelect(Select):
    def __init__(self, current):
        opts = [
            discord.SelectOption(
                label="Default Sort",
                emoji="📋",
                default=(current == "Default Sort"),
            ),
            discord.SelectOption(
                label="Sort by Completion",
                emoji="✅",
                default=(current == "Sort by Completion"),
            ),
            discord.SelectOption(
                label="Sort by XP Reward",
                emoji=utils.safe_emoji(config.XP_EMOJI),
                default=(current == "Sort by XP Reward"),
            ),
        ]
        super().__init__(placeholder="Sort Projects...", options=opts, row=1)

    async def callback(self, i):
        self.view.sort_method = self.values[0]
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class SearchBtn(Button):
    def __init__(self, label):
        super().__init__(
            label=label, style=discord.ButtonStyle.secondary, emoji="🔍", row=0
        )

    async def callback(self, i):
        if self.view.search_query:
            self.view.search_query = None
            self.view.update_components()
            await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        else:
            await i.response.send_modal(SearchModal(self.view))


class SearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Projects")
        self.view = view
        self.q = TextInput(label="Term")
        self.add_item(self.q)

    async def on_submit(self, i):
        self.view.search_query = self.q.value.lower()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ClaimAllBtn(Button):
    def __init__(self):
        super().__init__(
            label="Claim All Ready",
            style=discord.ButtonStyle.success,
            emoji="📥",
            row=4,
        )

    async def callback(self, i):
        u = dict(database.get_user_data(self.view.user_id))
        prog = json.loads(u["project_progress"])
        total_xp = 0
        _, all_p = self.view.bot.get_cog("Jobs").get_projects_embed(
            self.view.user_id, 0, self.view.search_query
        )

        mission_updates_needed = False

        for pid, pdata, cur, tgt, clm in all_p:
            if cur >= tgt and not clm:
                entry = prog.get(pid, {"prog": tgt})
                entry["claimed"] = True
                prog[pid] = entry
                total_xp += pdata.get("reward_xp", 1000)

                mission_updates_needed = True

        database.update_user_stats(
            self.view.user_id,
            {"project_progress": json.dumps(prog), "xp": u["xp"] + total_xp},
        )

        if mission_updates_needed:
            await self.check_mission_progress(self.view.user_id)

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await i.followup.send(f"📥 **Claimed all!** +{total_xp:,} XP", ephemeral=True)

    async def check_mission_progress(self, user_id):

        try:
            u = dict(database.get_user_data(user_id))
            m_state = json.loads(u.get("mission_state", "{}"))
            active_list = m_state.get("active", [])
            for m_id in active_list:
                m_def = MISSIONS.get(m_id)
                if not m_def:
                    continue
                m_data = m_state["states"].get(m_id)
                step = m_def["steps"][m_data["step"]]
                if step["type"] == "objective_project":
                    m_data["prog"] += 1
                    database.update_user_stats(
                        user_id, {"mission_state": json.dumps(m_state)}
                    )
                    thread_id = u.get("mission_thread_id")
                    if thread_id:
                        engine = MissionEngine(
                            self.view.bot,
                            user_id,
                            thread_id,
                            specific_mission_id=m_id,
                        )
                        asyncio.create_task(engine.progress())
        except:
            pass


class ClaimJobBtn(Button):
    def __init__(self, idx, label):
        super().__init__(
            label=f"Claim Job",
            style=discord.ButtonStyle.success,
            emoji="✅",
            row=2,
        )
        self.idx = idx

    async def callback(self, i):
        u = dict(database.get_user_data(self.view.user_id))
        jobs = json.loads(u["active_jobs"])
        job = jobs[self.idx]
        job["claimed"] = True

        database.update_user_stats(
            self.view.user_id,
            {
                "active_jobs": json.dumps(jobs),
                "xp": u["xp"] + 5000,
                "job_completion_count": u["job_completion_count"] + 1,
            },
        )

        try:
            m_state = json.loads(u.get("mission_state", "{}"))
            active_list = m_state.get("active", [])

            for m_id in active_list:
                m_def = MISSIONS.get(m_id)
                if not m_def:
                    continue

                m_data = m_state["states"].get(m_id)
                step = m_def["steps"][m_data["step"]]

                if step["type"] == "objective_job":

                    m_data["prog"] += 1
                    database.update_user_stats(
                        self.view.user_id,
                        {"mission_state": json.dumps(m_state)},
                    )

                    thread_id = u.get("mission_thread_id")
                    if thread_id:
                        engine = MissionEngine(
                            self.view.bot,
                            self.view.user_id,
                            thread_id,
                            specific_mission_id=m_id,
                        )
                        asyncio.create_task(engine.progress())
        except Exception as e:
            print(f"Error updating job mission: {e}")

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ClaimProjectBtn(Button):
    def __init__(self, pid, label):
        super().__init__(
            label=f"Claim Project",
            style=discord.ButtonStyle.success,
            emoji="📜",
            row=2,
        )
        self.pid = pid

    async def callback(self, i):
        u = dict(database.get_user_data(self.view.user_id))
        prog = json.loads(u["project_progress"])
        entry = prog.get(self.pid, {"prog": 0})
        if isinstance(entry, int):
            entry = {"prog": entry}
        entry["claimed"] = True
        prog[self.pid] = entry

        pdata = game_data.PROJECTS[self.pid]
        xp = pdata.get("reward_xp", 1000)
        tokens = pdata.get("reward_tokens", 0)

        updates = {"project_progress": json.dumps(prog), "xp": u["xp"] + xp}
        if tokens > 0:
            updates["merch_tokens"] = u.get("merch_tokens", 0) + tokens

        database.update_user_stats(self.view.user_id, updates)

        try:
            m_state = json.loads(u.get("mission_state", "{}"))
            active_list = m_state.get("active", [])
            for m_id in active_list:
                m_def = MISSIONS.get(m_id)
                if not m_def:
                    continue
                m_data = m_state["states"].get(m_id)
                step = m_def["steps"][m_data["step"]]

                if step["type"] == "objective_project":
                    m_data["prog"] += 1
                    database.update_user_stats(
                        self.view.user_id,
                        {"mission_state": json.dumps(m_state)},
                    )
                    thread_id = u.get("mission_thread_id")
                    if thread_id:
                        engine = MissionEngine(
                            self.view.bot,
                            self.view.user_id,
                            thread_id,
                            specific_mission_id=m_id,
                        )
                        asyncio.create_task(engine.progress())
        except Exception as e:
            print(f"Error updating project mission: {e}")

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)

        desc = f"✅ **Project Claimed!**\n\n{config.XP_EMOJI} **+{xp:,} XP**"
        if tokens > 0:
            desc += f"\n{config.MERCH_TOKEN_EMOJI} **+{tokens} Tokens**"

        embed = discord.Embed(description=desc, color=0x2ECC71)
        await i.followup.send(embed=embed, ephemeral=True)


class OpenBonusKitBtn(Button):
    def __init__(self):
        super().__init__(
            label="Claim Bonus Kit",
            style=discord.ButtonStyle.success,
            emoji=utils.safe_emoji(config.CHAOS_CORE_EMOJI),
            row=2,
        )

    async def callback(self, i):
        u = dict(database.get_user_data(self.view.user_id))
        database.update_user_stats(
            self.view.user_id,
            {"job_completion_count": 0, "chaos_kits": u["chaos_kits"] + 1},
        )
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ProjPrevBtn(Button):
    def __init__(self, enabled):
        super().__init__(
            label="<",
            style=discord.ButtonStyle.secondary,
            row=3,
            disabled=not enabled,
        )

    async def callback(self, i):
        self.view.page -= 1
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ProjNextBtn(Button):
    def __init__(self, enabled):
        super().__init__(
            label=">",
            style=discord.ButtonStyle.secondary,
            row=3,
            disabled=not enabled,
        )

    async def callback(self, i):
        self.view.page += 1
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class JobsDashboardView(View):
    def __init__(self, bot, user_id, tab="daily"):
        super().__init__(timeout=300)
        self.bot, self.user_id, self.tab = bot, user_id, tab
        self.page, self.search_query, self.sort_method = (
            0,
            None,
            "Default Sort",
        )
        self.project_list = []
        self.update_components()

    def update_components(self):
        self.clear_items()

        u_data = database.get_user_data(self.user_id)
        if not u_data:
            return
        u_dict = dict(u_data)
        m_state = json.loads(u_dict.get("mission_state", "{}"))

        projs_unlocked = "paidovertime" in m_state.get(
            "completed", []
        ) or "paidovertime" in m_state.get("active", [])

        self.add_item(
            TabButton(
                "Daily Jobs",
                "daily",
                (
                    discord.ButtonStyle.primary
                    if self.tab == "daily"
                    else discord.ButtonStyle.secondary
                ),
                utils.safe_emoji(config.DAILY_JOB_EMOJI),
            )
        )
        self.add_item(
            TabButton(
                "Projects",
                "projects",
                (
                    discord.ButtonStyle.primary
                    if self.tab == "projects"
                    else discord.ButtonStyle.secondary
                ),
                utils.safe_emoji(config.PROJECT_EMOJI),
                disabled=not projs_unlocked,
            )
        )
        self.add_item(ReturnToMissionBtn())
        if self.tab == "projects":
            self.add_item(SearchBtn("Clear" if self.search_query else "Search"))

        if self.tab == "daily":
            jobs = json.loads(u_dict["active_jobs"])
            for idx, job in enumerate(jobs):
                if job.get("completed") and not job.get("claimed"):
                    self.add_item(ClaimJobBtn(idx, job["desc"]))
            if u_dict["job_completion_count"] >= 3:
                self.add_item(OpenBonusKitBtn())
        else:
            self.add_item(ProjectSortSelect(self.sort_method))
            _, self.project_list = self.bot.get_cog("Jobs").get_projects_embed(
                self.user_id, self.page, self.search_query, self.sort_method
            )

            ready_count = sum(1 for p in self.project_list if p[2] >= p[3] and not p[4])
            if ready_count >= 2:
                self.add_item(ClaimAllBtn())

            for pid, pdata, cur, tgt, clm in self.project_list[
                self.page * 5 : (self.page + 1) * 5
            ]:
                if cur >= tgt and not clm:
                    self.add_item(ClaimProjectBtn(pid, pdata["desc"]))

            max_pages = (len(self.project_list) - 1) // 5 + 1
            if max_pages > 1:
                self.add_item(ProjPrevBtn(self.page > 0))
                self.add_item(ProjNextBtn(self.page < max_pages - 1))

    def get_embed(self):
        if self.tab == "daily":
            return self.bot.get_cog("Jobs").get_jobs_embed(self.user_id)
        embed, _ = self.bot.get_cog("Jobs").get_projects_embed(
            self.user_id, self.page, self.search_query, self.sort_method
        )
        return embed


async def setup(bot):
    await bot.add_cog(Jobs(bot))

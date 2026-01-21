import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from mo_co import database, config, utils, game_data
import json
import math
import random
from datetime import datetime, timedelta
import mo_co.pedia as pedia


class Elite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="elite", description="Enroll or access the Elite Hunter Program"
    )
    async def elite(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        u_data = dict(database.get_user_data(interaction.user.id))

        level, _, _ = utils.get_level_info(u_data["xp"])
        is_enrolled = bool(u_data.get("is_elite", 0))

        if level < 50:
            return await interaction.response.send_message(
                f"Almost there... Level Up to join the Elite Hunter Program! ({level}/50)",
                ephemeral=True,
            )

        if not is_enrolled:
            embed = discord.Embed(
                title=f"{config.ELITE_EMOJI} Elite Hunter Program",
                description="Congrats on reaching **Level 50**! Enroll now to access Elite Projects, the Elite Shop, and Prestige.",
                color=0xF1C40F,
            )
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/1452381420130537606.png"
            )

            embed.add_field(
                name="Enroll to unlock",
                value="-------------------------",
                inline=False,
            )

            embed.add_field(
                name=f"{config.ELITE_HUNTER_ICON} Elite Gear (Permanent)",
                value="Visit the Elite Shop for some exclusive Elite Gear",
                inline=False,
            )

            mod_icon = "<:healing_ride:1452309445366382745>"
            embed.add_field(
                name=f"{mod_icon} Elite Modules (Permanent)",
                value="Permanently boost your power with our Elite Modules",
                inline=False,
            )

            embed.add_field(
                name=f"{config.ELITE_EMOJI} Elite Levels (Temporary)",
                value="Earn XP to increase your Elite Level and get better Smart Rings",
                inline=False,
            )

            embed.add_field(
                name=f"{config.EMPTY_RING} Smart Rings (Temporary)",
                value="Gain temporary but god-like powers!",
                inline=False,
            )

            embed.add_field(
                name=f"{config.PROJECT_EMOJI} Elite Projects (Temporary)",
                value="Elite Tokens come from Elite Projects. Use them in the Elite Shop before the Chapter Ends!",
                inline=False,
            )

            prestige_icon = "<:prestigemax_gold:1452825647545323643>"
            embed.add_field(
                name=f"{prestige_icon} Prestige",
                value="Climb to Elite Level 100 to unlock prestige, resetting your level back to **Level 1** while permanently upgrading your Emblem!",
                inline=False,
            )

            embed.set_footer(
                text="NOTE: Elite Hunter Levels and Smart Rings are temporary and removed in the next update, BUT, you get to keep everything bought from the Elite Shop including the elite modules"
            )

            view = EliteEnrollmentView(self.bot, interaction.user.id)
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )
        else:
            view = EliteDashboardView(self.bot, interaction.user.id)
            await interaction.response.send_message(
                embed=view.get_embed(), view=view, ephemeral=True
            )


class EliteEnrollmentView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="Enroll", style=discord.ButtonStyle.success)
    async def enroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return

        database.update_user_stats(self.user_id, {"is_elite": 1, "elite_xp": 0})

        await interaction.response.edit_message(
            content="✅ **Enrolled!**...", embed=None, view=None
        )

        view = EliteDashboardView(self.bot, self.user_id)
        await interaction.followup.send(
            embed=view.get_embed(), view=view, ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return

        await interaction.response.edit_message(
            content="❌ Enrollment Cancelled.", embeds=[], view=None
        )


class EliteDashboardView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.u_data = dict(database.get_user_data(user_id))
        self.elite_lvl, _, _ = utils.get_elite_level_info(
            self.u_data.get("elite_xp", 0)
        )
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        self.add_item(EliteProjectsButton())
        self.add_item(EliteShopButton())
        self.add_item(EliteLeaderboardButton())

        disabled = self.elite_lvl < 100
        label = "Prestige" if not disabled else "Prestige (Lvl 100)"
        self.add_item(PrestigeButton(disabled, label))

    def get_embed(self):
        u = self.u_data
        e_lvl, e_cost, e_curr = utils.get_elite_level_info(u.get("elite_xp", 0))
        tokens = u.get("elite_tokens", 0)

        inv = database.get_user_inventory(self.user_id)
        smart_rings = set()
        total_rings = 0
        for k, v in game_data.ALL_ITEMS.items():
            if v["type"] == "smart_ring":
                total_rings += 1
                for item in inv:
                    if item["item_id"] == k:
                        smart_rings.add(k)
                        break

        embed = discord.Embed(
            title=f"{config.ELITE_EMBLEM} Elite Level {e_lvl} - Elite Hunter Program 1",
            color=0x9B59B6,
        )

        pct = int((e_curr / e_cost) * 10) if e_cost > 0 else 10
        bar = "🟪" * pct + "⬛" * (10 - pct)

        embed.add_field(
            name="Balance",
            value=f"{config.ELITE_TOKEN_EMOJI} **{tokens:,}**",
            inline=True,
        )
        embed.add_field(
            name="Ring Collection",
            value=f"{config.EMPTY_RING} **{len(smart_rings)}/{total_rings}**",
            inline=True,
        )
        embed.add_field(
            name="Elite XP",
            value=f"`{bar}` {e_curr:,}/{e_cost:,}",
            inline=False,
        )

        if self.elite_lvl >= 100:
            embed.add_field(
                name="✨ Prestige Available",
                value="You have reached the pinnacle. Reset to ascend.",
                inline=False,
            )

        return embed


class EliteProjectsButton(Button):
    def __init__(self):
        super().__init__(
            label="Elite Projects",
            style=discord.ButtonStyle.primary,
            emoji=discord.PartialEmoji.from_str(config.PROJECT_EMOJI),
        )

    async def callback(self, i):
        await i.response.send_message(
            embed=EliteProjectsView(self.view.bot, self.view.user_id).get_embed(),
            view=EliteProjectsView(self.view.bot, self.view.user_id),
            ephemeral=True,
        )


class EliteShopButton(Button):
    def __init__(self):
        super().__init__(
            label="Elite Shop",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str(config.ELITE_EMOJI),
        )

    async def callback(self, i):
        await i.response.send_message(
            embed=EliteShopView(self.view.bot, self.view.user_id).get_embed(),
            view=EliteShopView(self.view.bot, self.view.user_id),
            ephemeral=True,
        )


class EliteLeaderboardButton(Button):
    def __init__(self):
        super().__init__(
            label="Elite Leaderboard",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str(config.XP_EMOJI),
        )

    async def callback(self, i):
        await i.response.defer(ephemeral=True)
        view = EliteLeaderboardView(self.view.bot, self.view.user_id)
        await view.resolve_visible_names()
        await i.followup.send(embed=view.get_embed(), view=view, ephemeral=True)


class PrestigeButton(Button):
    def __init__(self, disabled, label):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.danger,
            emoji=discord.PartialEmoji.from_str(
                "<:prestigemax_gold:1452825647545323643>"
            ),
            disabled=disabled,
        )

    async def callback(self, i):
        view = PrestigeWarningView(self.view.bot, i.user.id)
        await i.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)


class PrestigeWarningView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

    def get_embed(self):
        embed = discord.Embed(title="⚠️ PRESTIGE ASCENSION WARNING", color=0xFF0000)
        embed.description = (
            "You are about to Prestige. This is a **Soft Reset**.\n\n"
            "**WHAT YOU LOSE:**\n"
            "❌ **Level & XP:** Reset to Level 1.\n"
            "❌ **Elite Status:** Reset. You must climb back to Level 50.\n"
            "❌ **World Access:** High-level worlds will be re-locked.\n\n"
            "**WHAT YOU KEEP:**\n"
            "✅ **All Inventory:** Weapons, Gadgets, Passives, Rings.\n"
            "✅ **All Currencies:** Gold, Tokens, Cores, Kits, Shards.\n"
            "✅ **All Cosmetics:** Skins, Titles.\n"
            "✅ **Collection:** mo.copedia progress.\n"
            "✅ **Elite Modules:** Permanent power.\n\n"
            "**REWARDS:**\n"
            "✨ **New Emblem Tier** (Bronze/Silver/Gold upgraded).\n"
            "✨ **Permanent +10% XP Boost**.\n\n"
            "**Note:** High-level gear will be **Synced Down** to your current level until you level up again."
        )
        return embed

    @discord.ui.button(label="CONFIRM ASCENSION", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return

        u = database.get_user_data(self.user.id)
        current_prestige = u["prestige_level"]

        database.update_user_stats(
            self.user_id,
            {
                "xp": 0,
                "elite_xp": 0,
                "is_elite": 0,
                "prestige_level": current_prestige + 1,
                "current_hp": utils.get_base_hp(1),
            },
        )

        new_emblem = utils.get_emblem(1, is_elite=False, prestige=current_prestige + 1)

        embed = discord.Embed(title="✨ ASCENSION COMPLETE ✨", color=0xF1C40F)
        embed.description = f"**Welcome back to the beginning, Hunter.**\n\nYour Prestige Level is now **{current_prestige + 1}**.\nYour Emblem has been upgraded: {new_emblem}\n\n*The monsters are waiting.*"

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Ascension Cancelled.", embed=None, view=None
        )


class EliteProjectsView(View):
    def __init__(self, bot, user_id, tab="priority"):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.tab = tab
        self.page = 0
        self.project_list = []
        self.search_query = None
        self.hard_cleared_count = 0
        self.total_hard_rifts = 0
        self.nightmare_unlocked = False

        self.refresh_projects()
        self.update_components()

    def refresh_projects(self):
        u = dict(database.get_user_data(self.user_id))
        prog = json.loads(u.get("project_progress", "{}"))
        completed_rifts = json.loads(u.get("completed_rifts", "[]"))

        hard_projects = [
            k
            for k, v in game_data.PROJECTS.items()
            if v.get("target_type") == "clear_rift_hard"
        ]
        self.total_hard_rifts = len(hard_projects)
        self.hard_cleared_count = 0

        for pid in hard_projects:
            entry = prog.get(pid, {"prog": 0})
            if isinstance(entry, int):
                entry = {"prog": entry}
            if entry.get("claimed") or entry.get("prog", 0) >= 1:
                self.hard_cleared_count += 1

        self.nightmare_unlocked = self.hard_cleared_count >= self.total_hard_rifts

        grouped = {}
        for pid, pdata in game_data.PROJECTS.items():
            if not pdata.get("is_elite"):
                continue

            is_priority = pdata.get("group", "").startswith(
                "elite_priority"
            ) or "speed" in pdata.get("group", "")
            if self.tab == "priority" and not is_priority:
                continue
            if self.tab == "general" and is_priority:
                continue

            if (
                self.search_query
                and self.search_query.lower() not in pdata["desc"].lower()
            ):
                continue

            rift_id_ctx = None
            if "rift" in pdata.get("target_type", ""):
                tgt = pdata.get("target", "")
                rift_id_ctx = tgt.split(":")[0] if ":" in tgt else tgt

            if rift_id_ctx and rift_id_ctx in game_data.RIFTS:
                if rift_id_ctx not in completed_rifts:
                    continue

            if (
                "nightmare" in pdata.get("target_type", "")
                and not self.nightmare_unlocked
            ):
                continue

            group = pdata.get("group", pid)
            if group not in grouped:
                grouped[group] = []
            grouped[group].append((pid, pdata))

        final_list = []
        for group, items in grouped.items():
            items.sort(key=lambda x: x[1].get("tier", 1))
            active = None
            for pid, pdata in items:
                entry = prog.get(pid, {"prog": 0, "claimed": False})
                if isinstance(entry, int):
                    entry = {"prog": entry, "claimed": False}

                if pdata["target_type"] == "reach_elite_level":
                    entry["prog"] = utils.get_elite_level_info(u.get("elite_xp", 0))[0]
                elif pdata["target_type"] == "collect_smart_rings":
                    inv = database.get_user_inventory(self.user_id)
                    entry["prog"] = sum(
                        1
                        for i in inv
                        if game_data.get_item(i["item_id"])["type"] == "smart_ring"
                    )

                if not entry.get("claimed"):
                    active = (pid, pdata, entry["prog"], pdata["count"], False)
                    break

            if not active:
                last_pid, last_data = items[-1]
                active = (
                    last_pid,
                    last_data,
                    last_data["count"],
                    last_data["count"],
                    True,
                )

            final_list.append(active)

        final_list.sort(key=lambda x: (x[4], -(1 if x[2] >= x[3] else 0), x[1]["desc"]))
        self.project_list = final_list

    def get_embed(self):
        embed = discord.Embed(
            title=f"{config.PROJECT_EMOJI} Elite Projects", color=0x9B59B6
        )
        u = dict(database.get_user_data(self.user_id))
        tokens = u.get("elite_tokens", 0)

        embed.set_footer(text=f"Elite Tokens: {tokens:,}")

        if self.tab == "priority":
            nm_status = (
                "🔓 UNLOCKED"
                if self.nightmare_unlocked
                else f"🔒 LOCKED ({self.hard_cleared_count}/{self.total_hard_rifts} Hard Clears)"
            )
            embed.description = f"**Nightmare Status:** {nm_status}\n*Complete all Hard Rifts to unlock Nightmare difficulty and projects.*\n\n"

        if self.search_query:
            embed.description = (
                embed.description or ""
            ) + f"🔍 Filtering: **{self.search_query}**\n\n"

        per_page = 5
        start = self.page * per_page
        chunk = self.project_list[start : start + per_page]

        if not chunk:
            embed.add_field(
                name="Empty",
                value="No projects found in this category.",
                inline=False,
            )

        for pid, pdata, cur, tgt, clm in chunk:
            pct = min(1.0, cur / tgt) if tgt > 0 else 0
            bar = "🟪" * int(pct * 10) + "⬛" * (10 - int(pct * 10))

            status = "✅" if clm else ("**[READY]**" if cur >= tgt else "")
            reward_txt = f"{pdata.get('reward_tokens', 0)} {config.ELITE_TOKEN_EMOJI}"
            if pdata.get("reward_xp"):
                reward_txt += f" | {pdata['reward_xp']:,} XP"

            icon = config.PROJECT_EMOJI
            raw = pdata.get("icon")
            if raw:
                e = utils.get_emoji(self.bot, raw)
                if e and not e.startswith("📦"):
                    icon = e

            embed.add_field(
                name="\u200b",
                value=f"{icon} **{pdata['desc']}** {status}\n`{bar}` {cur}/{tgt}\nReward: {reward_txt}",
                inline=False,
            )

        max_p = max(1, (len(self.project_list) - 1) // per_page + 1)
        embed.title += f" ({self.page+1}/{max_p})"
        return embed

    def update_components(self):
        self.clear_items()

        self.add_item(TabButton("Priority", "priority", self.tab == "priority"))
        self.add_item(TabButton("General", "general", self.tab == "general"))
        self.add_item(SearchButton(bool(self.search_query)))

        per_page = 5
        start = self.page * per_page
        chunk = self.project_list[start : start + per_page]

        for pid, pdata, cur, tgt, clm in chunk:
            if cur >= tgt and not clm:
                self.add_item(ClaimEliteProjectBtn(pid))

        max_pages = (len(self.project_list) - 1) // per_page + 1
        if max_pages > 1:
            self.add_item(NavButton("<", self.page > 0, -1, row=2))
            self.add_item(NavButton(">", self.page < max_pages - 1, 1, row=2))

        self.add_item(GoToShopButton())
        self.add_item(GoToLeaderboardButton())


class TabButton(Button):
    def __init__(self, label, tab, active):
        style = discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary
        emoji = "🔥" if tab == "priority" else "📜"
        super().__init__(label=label, style=style, emoji=emoji, row=0)
        self.tab = tab

    async def callback(self, i):
        self.view.tab = self.tab
        self.view.page = 0
        self.view.refresh_projects()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class SearchButton(Button):
    def __init__(self, active):
        style = discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary
        label = "Clear Search" if active else "Search"
        super().__init__(label=label, style=style, emoji="🔍", row=0)

    async def callback(self, i):
        if self.view.search_query:
            self.view.search_query = None
            self.view.refresh_projects()
            self.view.update_components()
            await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        else:
            await i.response.send_modal(SearchModal(self.view))


class SearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Projects")
        self.view = view
        self.q = TextInput(label="Query", placeholder="Boss name, rift name, etc.")
        self.add_item(self.q)

    async def on_submit(self, i):
        self.view.search_query = self.q.value
        self.view.page = 0
        self.view.refresh_projects()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class ClaimEliteProjectBtn(Button):
    def __init__(self, pid):
        super().__init__(
            label="Claim", style=discord.ButtonStyle.success, emoji="✅", row=1
        )
        self.pid = pid

    async def callback(self, i):
        u = dict(database.get_user_data(self.view.user_id))
        prog = json.loads(u.get("project_progress", "{}"))
        pdata = game_data.PROJECTS[self.pid]

        entry = prog.get(self.pid, {"prog": pdata["count"]})
        if isinstance(entry, int):
            entry = {"prog": entry}
        entry["claimed"] = True
        prog[self.pid] = entry

        xp = pdata.get("reward_xp", 0)
        tokens = pdata.get("reward_tokens", 0)

        database.update_user_stats(
            self.view.user_id,
            {
                "project_progress": json.dumps(prog),
                "elite_xp": u.get("elite_xp", 0) + xp,
                "elite_tokens": u.get("elite_tokens", 0) + tokens,
            },
        )

        self.view.refresh_projects()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class NavButton(Button):
    def __init__(self, label, enabled, delta, row):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            disabled=not enabled,
            row=row,
        )
        self.delta = delta

    async def callback(self, i):
        self.view.page += self.delta
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class GoToShopButton(Button):
    def __init__(self):
        super().__init__(
            label="Elite Shop",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str(config.ELITE_EMOJI),
            row=3,
        )

    async def callback(self, i):
        await i.response.edit_message(
            embed=EliteShopView(self.view.bot, self.view.user_id).get_embed(),
            view=EliteShopView(self.view.bot, self.view.user_id),
        )


class GoToLeaderboardButton(Button):
    def __init__(self):
        super().__init__(
            label="Leaderboard",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str(config.XP_EMOJI),
            row=3,
        )

    async def callback(self, i):
        await i.response.defer(ephemeral=True)
        view = EliteLeaderboardView(self.view.bot, self.view.user_id)
        await view.resolve_visible_names()
        await i.followup.send(embed=view.get_embed(), view=view, ephemeral=True)


class EliteShopView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_id = user_id
        self.u_data = dict(database.get_user_data(user_id))
        self.elite_lvl, _, _ = utils.get_elite_level_info(
            self.u_data.get("elite_xp", 0)
        )

        all_item_keys = list(game_data.ALL_ITEMS.keys())
        rot_item_id, rot_refresh_ts = database.get_elite_rotation(all_item_keys)
        self.rot_item_id = rot_item_id
        self.rot_refresh_ts = rot_refresh_ts

        self.shop_items = [
            {
                "id": "elite_dash_module",
                "price": 500,
                "name": "Elite Dash Module",
                "type": "elite_module",
                "desc": "Reduces dash cooldown.",
            },
            {
                "id": "speed_kill",
                "price": 300,
                "name": "Speed Kill",
                "type": "elite_module",
                "desc": "Speed boost on kill.",
            },
            {
                "id": "healing_ride",
                "price": 400,
                "name": "Healing Ride",
                "type": "elite_module",
                "desc": "Heal while riding.",
            },
            {
                "id": "overcharged_amulet",
                "price": 400,
                "name": "Overcharged Amulet",
                "type": "passive",
                "desc": "Find Overcharged monsters.",
            },
            {
                "id": "chaos_enhancer",
                "price": 400,
                "name": "Chaos Enhancer",
                "type": "consumable_mod",
                "desc": "Randomly mod a gear piece.",
            },
            {
                "id": "random_smart_ring",
                "price": 150,
                "name": "Random Smart Ring",
                "type": "consumable_ring",
                "desc": "Grant a random ring.",
            },
            {
                "id": "rotating_slot",
                "price": 500,
                "name": "Elite Rotation",
                "type": "rotating",
                "desc": "Guaranteed [Elite] Item.",
            },
            {
                "id": "xp_booster",
                "price": 100,
                "name": "Elite XP Booster",
                "type": "consumable_xp",
                "desc": "+10,000 Boosted XP Fuel.",
            },
            {
                "id": "chaos_core_pack",
                "price": 50,
                "name": "Chaos Core",
                "type": "consumable_core",
                "desc": "Bulk buy cores.",
            },
            {
                "id": "mogold_pack",
                "price": 100,
                "name": "10 mo.gold",
                "type": "consumable_gold",
                "desc": "Pull merch in /shop.",
            },
            {
                "id": "elite_conquerer_title",
                "price": 1000,
                "name": "Title: Elite Conquerer",
                "type": "title",
                "desc": "The Mark of a True Elite.",
            },
        ]

        self.update_components()

    def get_embed(self):
        tokens = self.u_data.get("elite_tokens", 0)
        embed = discord.Embed(
            title=f"{config.ELITE_HUNTER_ICON} Elite Shop", color=0x3498DB
        )
        embed.description = f"**Balance:** {config.ELITE_TOKEN_EMOJI} **{tokens:,}**"

        refresh_ts = int(datetime.fromisoformat(self.rot_refresh_ts).timestamp())
        rot_item_def = game_data.get_item(self.rot_item_id)

        inv = database.get_user_inventory(self.user_id)
        owned_levels = {i["item_id"]: i["level"] for i in inv}
        owned_titles = json.loads(self.u_data.get("owned_titles", "[]"))

        for item in self.shop_items:
            price = item["price"]

            if item["type"] == "rotating":
                if rot_item_def["type"] == "title":
                    icon = "👑"
                    name = f"Title: {rot_item_def['name']}"
                    desc = f"Refreshes <t:{refresh_ts}:R>"
                    status_str = (
                        "✅ Owned" if rot_item_def["name"] in owned_titles else ""
                    )
                else:
                    icon = utils.get_emoji(self.bot, self.rot_item_id)
                    name = f"[Elite] {rot_item_def['name']}"
                    desc = f"Refreshes <t:{refresh_ts}:R>"
                    status_str = ""
            elif item["type"] == "consumable_xp":
                icon = config.XP_BOOST_3X_EMOJI
                name = item["name"]
                desc = item["desc"]
                status_str = ""
            elif item["type"] == "consumable_core":
                icon = config.CHAOS_CORE_EMOJI
                name = item["name"]
                desc = item["desc"]
                status_str = ""
            elif item["type"] == "consumable_gold":
                icon = config.MOGOLD_EMOJI
                name = item["name"]
                desc = item["desc"]
                status_str = ""
            elif item["type"] == "consumable_ring":
                icon = config.EMPTY_RING
                name = item["name"]
                desc = item["desc"]
                status_str = ""
            elif item["type"] == "title":
                icon = "👑"
                name = item["name"]
                desc = item["desc"]
                status_str = "✅ Owned" if "Elite Conquerer" in owned_titles else ""
            else:
                icon = utils.get_emoji(self.bot, item["id"])
                if item["id"] == "chaos_enhancer":
                    icon = config.CHAOS_CORE_EMOJI
                elif item["id"] == "overcharged_amulet":
                    icon = config.OVERCHARGED_ICON
                name = item["name"]
                desc = item["desc"]
                status_str = ""

                if (
                    item["type"] in ["elite_module", "passive"]
                    and item["id"] in owned_levels
                ):
                    lvl = owned_levels[item["id"]]
                    if item["type"] == "elite_module":
                        status_str = "✅ Maxed" if lvl >= 6 else f"Owned (Lvl {lvl})"
                    elif item["id"] == "overcharged_amulet":
                        status_str = "✅ Maxed" if lvl >= 50 else f"Owned (Lvl {lvl})"

            embed.add_field(
                name=f"{icon} {name}",
                value=f"{config.ELITE_TOKEN_EMOJI} **{price}**\n*{desc}*\n{status_str}",
                inline=True,
            )
        return embed

    def update_components(self):
        self.clear_items()
        inv = database.get_user_inventory(self.user_id)
        owned_levels = {i["item_id"]: i["level"] for i in inv}
        owned_titles = json.loads(self.u_data.get("owned_titles", "[]"))
        tokens = self.u_data.get("elite_tokens", 0)

        self.add_item(BackButton())

        for item in self.shop_items:
            price = item["price"]
            btn_label = f"Buy {item['name'].split(':')[0]}"
            disabled = False
            style = discord.ButtonStyle.secondary

            if item["type"] == "rotating":
                rot_def = game_data.get_item(self.rot_item_id)
                if rot_def["type"] == "title":
                    if rot_def["name"] in owned_titles:
                        btn_label = "Owned"
                        disabled = True
                    else:
                        btn_label = "Buy Title"
                        style = discord.ButtonStyle.primary
                else:
                    btn_label = "Buy Rotation"
                    style = discord.ButtonStyle.primary
            elif item["type"] == "consumable_xp":
                btn_label = "Buy Boost"
                style = discord.ButtonStyle.success
            elif item["type"] == "consumable_core":
                btn_label = "Buy Cores"
                style = discord.ButtonStyle.primary
            elif item["type"] == "consumable_gold":
                btn_label = "Buy Gold"
                style = discord.ButtonStyle.primary
            elif item["type"] == "consumable_ring":
                btn_label = "Buy Ring"
                style = discord.ButtonStyle.primary

            elif item["type"] == "title" and "Elite Conquerer" in owned_titles:
                btn_label = "Owned"
                disabled = True

            elif (
                item["type"] in ["elite_module", "passive"]
                and item["id"] in owned_levels
            ):
                lvl = owned_levels[item["id"]]
                if item["type"] == "elite_module":
                    if lvl >= 6:
                        btn_label = "Maxed"
                        disabled = True
                    else:
                        req_elite = lvl * 20
                        if self.elite_lvl < req_elite:
                            btn_label = f"Need Elite {req_elite}"
                            disabled = True
                            style = discord.ButtonStyle.danger
                        else:
                            btn_label = f"Upgrade (Lvl {lvl+1})"
                            style = discord.ButtonStyle.success
                elif item["id"] == "overcharged_amulet":
                    if lvl >= 50:
                        btn_label = "Maxed"
                        disabled = True
                    else:
                        price = 100
                        btn_label = f"Upgrade (Lvl {lvl+1})"
                        style = discord.ButtonStyle.success

            if tokens < price and not disabled and item["type"] != "consumable_core":
                disabled = True
                style = discord.ButtonStyle.danger

            btn = Button(
                label=btn_label,
                style=style,
                disabled=disabled,
                custom_id=f"buy_{item['id']}",
            )
            btn.callback = self.create_buy_callback(item, price)
            self.add_item(btn)

    def create_buy_callback(self, item, cost):
        async def cb(i: discord.Interaction):
            if i.user.id != self.user_id:
                return

            if item["type"] == "consumable_mod":
                await i.response.send_message(
                    "Select item to enhance:",
                    view=EnhancerSelectView(self.bot, self.user_id, cost),
                    ephemeral=True,
                )
                return

            if item["type"] == "consumable_core":
                await i.response.send_modal(
                    BulkBuyModal(
                        self.bot,
                        self.user_id,
                        cost,
                        "chaos_cores",
                        "Chaos Core",
                    )
                )
                return

            u = dict(database.get_user_data(self.user_id))
            if u.get("elite_tokens", 0) < cost:
                return await i.response.send_message(
                    "Not enough tokens!", ephemeral=True
                )

            database.update_user_stats(
                self.user_id, {"elite_tokens": u["elite_tokens"] - cost}
            )
            msg = ""

            if item["type"] == "rotating":
                current_rot, _ = database.get_elite_rotation(
                    list(game_data.ALL_ITEMS.keys())
                )
                rot_def = game_data.get_item(current_rot)

                if rot_def["type"] == "title":
                    t = json.loads(u.get("owned_titles", "[]"))
                    if rot_def["name"] not in t:
                        t.append(rot_def["name"])
                        database.update_user_stats(
                            self.user_id, {"owned_titles": json.dumps(t)}
                        )
                    msg = f"✅ Purchased Title: **{rot_def['name']}**!"
                else:
                    e_lvl, _, _ = utils.get_elite_level_info(u["elite_xp"])
                    target_lvl = max(1, e_lvl)
                    database.add_item_to_inventory(
                        self.user_id, current_rot, "Elite", target_lvl
                    )
                    pedia.track_gear(self.user_id, current_rot, "Elite", source="shop")
                    msg = f"✅ Purchased **[Elite] {rot_def['name']}**!"

            elif item["type"] == "consumable_ring":
                pool = [
                    k
                    for k, v in game_data.ALL_ITEMS.items()
                    if v["type"] == "smart_ring"
                ]
                if pool:
                    rid = random.choice(pool)
                    database.add_item_to_inventory(self.user.id, rid, "Standard", 1)
                    msg = f"💍 Acquired **{game_data.get_item(rid)['name']}**!"
            elif item["type"] in ["elite_module", "passive"]:
                inv = database.get_user_inventory(self.user.id)
                target = next((r for r in inv if r["item_id"] == item["id"]), None)
                if target:
                    database.upgrade_item_level(target["instance_id"], 999, 1)
                    msg = f"🆙 Upgraded **{item['name']}**!"
                else:
                    database.add_item_to_inventory(
                        self.user.id, item["id"], "Standard", 1
                    )
                    msg = f"✅ Acquired **{item['name']}**!"
            elif item["type"] == "consumable_xp":
                database.update_user_stats(
                    self.user.id,
                    {"daily_xp_boosted": u["daily_xp_boosted"] + 10000},
                )
                msg = "✅ **XP Booster Activated!**"
            elif item["type"] == "consumable_gold":
                database.update_user_stats(self.user.id, {"mo_gold": u["mo_gold"] + 10})
                msg = "✅ **Acquired 10 mo.gold!**"
            elif item["type"] == "title":
                t = json.loads(u.get("owned_titles", "[]"))
                if "Elite Conquerer" not in t:
                    t.append("Elite Conquerer")
                    database.update_user_stats(
                        self.user.id, {"owned_titles": json.dumps(t)}
                    )
                    msg = "👑 Acquired Title: **Elite Conquerer**!"

            self.u_data = dict(database.get_user_data(self.user_id))
            self.update_components()
            await i.response.edit_message(embed=self.get_embed(), view=self)
            await i.followup.send(msg, ephemeral=True)

        return cb


class BulkBuyModal(Modal):
    def __init__(self, bot, user_id, unit_price, db_col, name):
        super().__init__(title=f"Buy {name}s")
        self.bot, self.user_id, self.unit_price, self.db_col, self.name = (
            bot,
            user_id,
            unit_price,
            db_col,
            name,
        )
        self.qty = TextInput(
            label=f"Quantity ({unit_price} tokens each)",
            placeholder="1",
            required=True,
        )
        self.add_item(self.qty)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.qty.value)
        except:
            return await interaction.response.send_message(
                "Invalid quantity.", ephemeral=True
            )
        if qty <= 0:
            return await interaction.response.send_message(
                "Invalid quantity.", ephemeral=True
            )
        total_cost = qty * self.unit_price
        u = dict(database.get_user_data(self.user.id))
        if u.get("elite_tokens", 0) < total_cost:
            return await interaction.response.send_message(
                f"Not enough tokens! Need {total_cost}.", ephemeral=True
            )
        database.update_user_stats(
            self.user_id,
            {
                "elite_tokens": u["elite_tokens"] - total_cost,
                self.db_col: u[self.db_col] + qty,
            },
        )
        await interaction.response.send_message(
            f"✅ Purchased **{qty}x {self.name}** for {total_cost} Tokens!",
            ephemeral=True,
        )


class BackButton(Button):
    def __init__(self):
        super().__init__(
            label="Back to Main Page",
            style=discord.ButtonStyle.secondary,
            row=4,
        )

    async def callback(self, i):
        view = EliteDashboardView(self.view.bot, self.view.user_id)
        await i.response.edit_message(embed=view.get_embed(), view=view)


class EnhancerSelectView(View):
    def __init__(self, bot, user_id, cost):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.cost = cost
        inv = database.get_user_inventory(user_id)
        eligible = [
            i
            for i in inv
            if game_data.get_item(i["item_id"])["type"] in ["weapon", "gadget"]
        ]
        eligible.sort(key=lambda x: x["level"], reverse=True)
        if not eligible:
            self.add_item(Button(label="No eligible gear found.", disabled=True))
        else:
            self.add_item(EnhancerSelect(eligible[:25], cost))


class EnhancerSelect(Select):
    def __init__(self, items, cost):
        self.cost = cost
        options = []
        for i in items:
            d = game_data.get_item(i["item_id"])
            mod_str = f"[{i['modifier']}]" if i["modifier"] != "Standard" else ""
            options.append(
                discord.SelectOption(
                    label=f"Lvl {i['level']} {mod_str} {d['name']}",
                    value=str(i["instance_id"]),
                )
            )
        super().__init__(placeholder="Choose item to enhance...", options=options)

    async def callback(self, i):
        u = dict(database.get_user_data(i.user.id))
        if u.get("elite_tokens", 0) < self.cost:
            return await i.response.send_message("Not enough tokens!", ephemeral=True)
        inst_id = int(self.values[0])
        item = database.get_item_instance(inst_id)
        if not item:
            return
        database.update_user_stats(
            i.user.id, {"elite_tokens": u["elite_tokens"] - self.cost}
        )
        mods = config.HUNT_MODS
        weights = config.HUNT_WEIGHTS
        new_mod = random.choices(mods, weights=weights, k=1)[0]
        with database.get_connection() as conn:
            conn.execute(
                "UPDATE inventory SET modifier = ? WHERE instance_id = ?",
                (new_mod, inst_id),
            )
            conn.commit()
        d = game_data.get_item(item["item_id"])
        await i.response.edit_message(
            content=f"✨ **Enhanced!**\n**{d['name']}** is now **[{new_mod}]**!",
            view=None,
        )


class EliteLeaderboardView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_id = user_id
        self.data = []
        self._load_data()

    def _load_data(self):
        with database.get_connection() as conn:
            self.data = conn.execute(
                "SELECT user_id, elite_tokens, elite_xp, xp FROM users WHERE is_elite = 1 ORDER BY elite_tokens DESC LIMIT 10"
            ).fetchall()

    async def resolve_visible_names(self):
        self.names = {}
        for row in self.data:
            uid = row["user_id"]
            u = self.bot.get_user(uid)
            if not u:
                try:
                    u = await self.bot.fetch_user(uid)
                except:
                    pass
            self.names[uid] = u.display_name if u else "Unknown Hunter"

    def get_embed(self):
        embed = discord.Embed(
            title=f"{config.ELITE_TOKEN_EMOJI} Elite Leaderboard",
            color=0xF1C40F,
        )
        if not self.data:
            embed.description = "No Elite Hunters yet."
            return embed
        lines = []
        for idx, row in enumerate(self.data):
            name = self.names.get(row["user_id"], "Unknown")
            e_lvl, _, _ = utils.get_elite_level_info(row["elite_xp"])
            lines.append(
                f"`#{idx+1}` **{name}**\n{config.ELITE_TOKEN_EMOJI} {row['elite_tokens']:,} | Elite Lvl {e_lvl}"
            )
        embed.description = "\n\n".join(lines)
        return embed


async def setup(bot):
    await bot.add_cog(Elite(bot))

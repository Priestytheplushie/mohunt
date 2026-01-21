import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import json
import typing
import asyncio
from datetime import datetime, timedelta, timezone
from mo_co import database, config, game_data, utils
from mo_co.game_data.missions import MISSIONS


class Portal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="portal", description="Open the World Portal")
    async def portal(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)
        try:
            m_state = json.loads(u_data["mission_state"])
            active_id = m_state.get("active")
            if active_id == "welcome2moco" and "welcome2moco" not in m_state.get(
                "completed", []
            ):
                embed = discord.Embed(
                    title="⛔ Access Locked",
                    description="Finish your onboarding first!",
                    color=0xE74C3C,
                )
                from mo_co.cogs.missions import PhoneDashboardView

                view = PhoneDashboardView(
                    self.bot,
                    interaction.user.id,
                    m_state,
                    u_data["mission_thread_id"],
                )
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                return
        except:
            pass

        utils.check_daily_reset(interaction.user.id)
        u_dict = dict(u_data)
        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        view = PortalView(self.bot, interaction.user, player_lvl, mode="worlds")
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=False
        )

    async def rift_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        user = database.get_user_data(interaction.user.id)
        if not user:
            return []
        player_lvl, _, _ = utils.get_level_info(user["xp"])
        options = []
        for rset in game_data.RIFT_SETS:
            if player_lvl >= rset["unlock_lvl"]:
                for rift_key in rset["rifts"]:
                    r_def = game_data.RIFTS.get(rift_key)
                    if not r_def:
                        continue
                    label = f"Rift: {r_def['name']}"
                    if current.lower() in label.lower():
                        options.append(app_commands.Choice(name=label, value=rift_key))
        return options[:25]

    @app_commands.command(name="rift", description="Quickly enter a Rift")
    @app_commands.autocomplete(name=rift_autocomplete)
    async def rift(self, interaction: discord.Interaction, name: str):
        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)

        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])

        r_def = game_data.RIFTS.get(name)
        if not r_def:
            return await interaction.response.send_message(
                "❌ Unknown Rift.", ephemeral=True
            )

        unlocked = False
        for rset in game_data.RIFT_SETS:
            if name in rset["rifts"] and player_lvl >= rset["unlock_lvl"]:
                unlocked = True
                break

        if not unlocked:
            return await interaction.response.send_message(
                "🔒 **Rift Locked!** Level up to unlock.", ephemeral=True
            )

        req = r_def.get("req_rift")
        comp = json.loads(u_dict.get("completed_rifts", "[]"))

        if req and req not in comp:
            req_name = game_data.RIFTS.get(req, {}).get("name", "Previous Rift")
            return await interaction.response.send_message(
                f"🔒 **Locked!** Complete **{req_name}** first.",
                ephemeral=True,
            )

        icon = utils.get_emoji(self.bot, r_def["icon"])
        embed = discord.Embed(
            title=f"{config.RIFTS_EMOJI} {r_def['name']}",
            description=f"**Boss:** {icon} {r_def['boss']}\n*{r_def['desc']}*",
            color=0x3498DB,
        )
        await interaction.response.send_message(
            embed=embed,
            view=RiftEntryChoiceView(
                self.bot, interaction.user, name, interaction, mode="Rift"
            ),
        )

    async def dojo_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        user = database.get_user_data(interaction.user.id)
        if not user:
            return []
        player_lvl, _, _ = utils.get_level_info(user["xp"])
        options = []
        for dset in game_data.DOJO_SETS:
            if player_lvl >= dset["unlock_lvl"]:
                for dojo_key in dset["dojos"]:
                    d_def = game_data.DOJOS.get(dojo_key)
                    if not d_def:
                        continue
                    label = f"Dojo: {d_def['name']}"
                    if current.lower() in label.lower():
                        options.append(app_commands.Choice(name=label, value=dojo_key))
        return options[:25]

    @app_commands.command(name="dojo", description="Quickly enter a Dojo")
    @app_commands.autocomplete(name=dojo_autocomplete)
    async def dojo(self, interaction: discord.Interaction, name: str):
        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)

        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])

        d_def = game_data.DOJOS.get(name)
        if not d_def:
            return await interaction.response.send_message(
                "❌ Unknown Dojo.", ephemeral=True
            )

        unlocked = False
        prev_req_met = True

        comp = json.loads(u_dict.get("completed_dojos", "[]"))

        for dset in game_data.DOJO_SETS:
            if name in dset["dojos"]:
                if player_lvl >= dset["unlock_lvl"]:
                    unlocked = True
                    idx = dset["dojos"].index(name)
                    if idx > 0:
                        prev_dojo = dset["dojos"][idx - 1]
                        if prev_dojo not in comp:
                            prev_req_met = False
                break

        if not unlocked:
            return await interaction.response.send_message(
                "🔒 **Dojo Locked!** Level up to unlock.", ephemeral=True
            )
        if not prev_req_met:
            return await interaction.response.send_message(
                "🔒 **Locked!** Complete the previous Dojo in this set first.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"{config.DOJO_ICON} {d_def['name']}",
            description=f"**Training Simulation**\nRecommended GP: {config.GEAR_POWER_EMOJI} {d_def['recommended_gp']:,}",
            color=0x9B59B6,
        )
        await interaction.response.send_message(
            embed=embed,
            view=RiftEntryChoiceView(
                self.bot, interaction.user, name, interaction, mode="Dojo"
            ),
        )


class PortalView(View):
    def __init__(self, bot, user, player_lvl, mode="worlds"):
        super().__init__(timeout=180)
        self.bot = bot
        self.user = user
        self.user_id = user.id
        self.player_lvl = player_lvl
        self.mode = mode
        self.update_components()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except:
            pass

    def get_embed(self):
        u_data = database.get_user_data(self.user.id)
        u_dict = dict(u_data)
        self.player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        user_gp = utils.get_total_gp(self.user.id)

        embed = discord.Embed(color=0x9B59B6)
        title_str = u_dict.get("current_title") or "Hunter"
        embed.set_author(
            name=f"{self.user.display_name} • {title_str}",
            icon_url=self.user.display_avatar.url,
        )
        embed.set_footer(text=f"Your Gear Power: {user_gp:,} | Lvl: {self.player_lvl}")

        if self.mode == "worlds":
            embed.title = f"{config.MAP_EMOJI} Worlds"
            active_events = getattr(self.bot, "active_world_events", {})
            embed.description = f"**Event Legend**\n{config.DOUBLE_XP_EMOJI} Double XP | {config.OVERCHARGED_ICON} Overcharged Alert | {config.CHAOS_ALERT} Chaos Alert\n"
            lines = []
            all_available = game_data.WORLDS + getattr(self.bot, "active_elites", [])
            for w in all_available:
                evt = active_events.get(w["id"])
                e_icon = ""
                if evt == "double_xp":
                    e_icon = config.DOUBLE_XP_EMOJI
                elif evt == "overcharged":
                    e_icon = config.OVERCHARGED_ICON
                elif evt == "chaos":
                    e_icon = config.CHAOS_ALERT

                w_icon = config.WORLD_ICONS.get(w["type"], "🗺️")
                rgp = config.WORLD_RGP.get(w["id"], 50)

                if self.player_lvl < w["unlock_lvl"]:
                    lines.append(f"🔒 **{w['name']}** (Lvl {w['unlock_lvl']})")
                else:
                    lines.append(
                        f"{w_icon} **{w['name']}** {e_icon} | {config.GEAR_POWER_EMOJI} {rgp:,}"
                    )
            embed.description += "\n" + "\n".join(lines)

        elif self.mode == "rifts":
            embed.title = f"{config.RIFTS_EMOJI} Rifts"
            embed.description = (
                f"**Your Gear Power:** {config.GEAR_POWER_EMOJI} {user_gp:,}\n\n"
            )
            comp = json.loads(u_dict.get("completed_rifts", "[]"))
            for rs in game_data.RIFT_SETS:
                is_set = self.player_lvl >= rs["unlock_lvl"]
                lines = [f"{config.RIFTS_EMOJI if is_set else '🔒'} **{rs['name']}**"]
                for rk in rs["rifts"]:
                    r = game_data.RIFTS.get(rk)
                    req = r.get("req_rift")
                    i = utils.get_emoji(self.bot, r.get("icon"))
                    if not is_set or (req and req not in comp):
                        lines.append(f" ┗ 🔒 **Locked**")
                    else:
                        lines.append(
                            f" ┗ {i} **{r['name']}** | {config.GEAR_POWER_EMOJI} {r.get('recommended_gp', 0):,}"
                        )
                embed.description += "\n".join(lines) + "\n\n"

        elif self.mode == "dojo":
            embed.title = f"{config.DOJO_ICON} Dojo"
            embed.description = (
                f"**Your Gear Power:** {config.GEAR_POWER_EMOJI} {user_gp:,}\n"
            )
            comp = json.loads(u_dict.get("completed_dojos", "[]"))
            best = json.loads(u_dict.get("dojo_best_times", "{}"))
            for ds in game_data.DOJO_SETS:
                embed.description += "\n"
                is_u = self.player_lvl >= ds["unlock_lvl"]
                header_icon = config.DOJO_ICON if is_u else "🔒"
                lines = [f"{header_icon} **{ds['name']}**"]
                prev = True
                for d_id in ds["dojos"]:
                    d = game_data.DOJOS.get(d_id)
                    boss_id = next(
                        (m["id"] for m in d["mobs"] if m.get("is_boss")),
                        d["mobs"][-1]["id"],
                    )
                    boss_icon = utils.get_emoji(self.bot, boss_id)
                    if not is_u or not prev:
                        lines.append(f" ┗ 🔒 **Locked**")
                    else:
                        bt = best.get(d_id)
                        time_str = f"Best: `{bt//60}:{bt%60:02d}`" if bt else "New!"
                        lines.append(
                            f" ┗ {boss_icon} **{d['name']}** | {time_str} | {config.GEAR_POWER_EMOJI} {d['recommended_gp']:,}"
                        )
                    prev = d_id in comp
                embed.description += "\n".join(lines) + "\n"

        elif self.mode == "versus":
            embed.title = f"{config.VERSUS_ICON} Versus"
            stars = u_dict.get("versus_stars", 0)
            belt = config.YELLOW_BELT
            if stars >= config.BELT_THRESHOLDS["Black"]:
                belt = config.BLACK_BELT
            elif stars >= config.BELT_THRESHOLDS["Brown"]:
                belt = config.BROWN_BELT
            elif stars >= config.BELT_THRESHOLDS["Purple"]:
                belt = config.PURPLE_BELT
            elif stars >= config.BELT_THRESHOLDS["Blue"]:
                belt = config.BLUE_BELT
            embed.description = f"**Lone Ranger**\nCollect points by farming mobs or hunting your opponent!\n\n**Your Rank:** {belt} ({stars} Stars)\n\n*Click below to join the Queue.*"

        return embed

    def update_components(self):
        self.clear_items()
        if self.mode == "worlds":
            self.add_item(WorldSelect(self.bot, self.player_lvl))
        elif self.mode == "rifts":
            self.add_item(RiftSelect(self.bot, self.player_lvl, self.user.id))
        elif self.mode == "dojo":
            self.add_item(DojoSelect(self.bot, self.player_lvl, self.user.id))
        elif self.mode == "versus":
            self.add_item(RankedQueueButton())
            self.add_item(BeltsButton(config.BLACK_BELT))

        u_dict = dict(database.get_user_data(self.user.id))
        fuel = u_dict.get("daily_xp_boosted", 0)
        bank = u_dict.get("daily_xp_total", 0)

        if self.player_lvl < 10:
            label, emoji, style = (
                "Normal XP (Locked)",
                config.NO_XP_EMOJI,
                discord.ButtonStyle.secondary,
            )
        elif fuel > 0:
            label, emoji, style = (
                "Boosted Battle XP",
                config.XP_BOOST_3X_EMOJI,
                discord.ButtonStyle.primary,
            )
        elif bank > 0:
            label, emoji, style = (
                "Normal Battle XP",
                config.XP_EMOJI,
                discord.ButtonStyle.secondary,
            )
        else:
            label, emoji, style = (
                "No Battle XP",
                config.NO_XP_EMOJI,
                discord.ButtonStyle.danger,
            )

        self.add_item(
            XPStatusButton(self.user.id, label, emoji, style, self.player_lvl)
        )

        self.add_item(
            NavButton("Worlds", "worlds", config.MAP_EMOJI, self.mode == "worlds")
        )
        self.add_item(
            NavButton(
                "Rifts",
                "rifts",
                config.RIFTS_EMOJI,
                self.mode == "rifts",
                disabled=(self.player_lvl < 9),
            )
        )
        self.add_item(
            NavButton(
                "Dojo",
                "dojo",
                config.DOJO_ICON,
                self.mode == "dojo",
                disabled=(self.player_lvl < 14),
            )
        )
        self.add_item(
            NavButton(
                "Versus",
                "versus",
                config.VERSUS_ICON,
                self.mode == "versus",
                disabled=(self.player_lvl < 15),
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This portal isn't yours!", ephemeral=True
            )
            return False
        return True


class XPStatusButton(Button):
    def __init__(self, user_id, label, emoji, style, player_lvl):
        super().__init__(
            label=label,
            emoji=discord.PartialEmoji.from_str(emoji),
            style=style,
            row=1,
        )
        self.user_id = user_id
        self.player_lvl = player_lvl

    async def callback(self, interaction: discord.Interaction):
        utils.check_daily_reset(self.user_id)
        u_dict = dict(database.get_user_data(self.user_id))
        fuel, bank = u_dict["daily_xp_boosted"], u_dict["daily_xp_total"]

        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        reset_ts = int(midnight.timestamp())

        if self.player_lvl < 10:
            embed = discord.Embed(title="XP Boost Locked", color=0x95A5A6)
            embed.description = f"**Boosted XP unlocks at Hunter Level 10.**\nCurrently using Normal XP.\nNext Reset <t:{reset_ts}:R>"

        elif fuel > 0:
            embed = discord.Embed(title="Boosted Battle XP", color=0x9B59B6)
            embed.description = f"XP and Chaos Shard gains from battles are boosted by **3x**!\nNext Reset <t:{reset_ts}:R>"
            pct = fuel / config.XP_BOOST_BANK_CAP
            filled = max(1, round(pct * 10))
            bar = "🟦" * filled + "⬛" * (10 - filled)
            embed.add_field(
                name="Boosted XP Left",
                value=f"`{bar}`\n{fuel:,} / {config.XP_BOOST_BANK_CAP:,}",
                inline=False,
            )

        elif bank > 0:
            embed = discord.Embed(title="Normal Battle XP", color=0x3498DB)
            embed.description = (
                f"XP gains are normal (1x).\nNext Reset <t:{reset_ts}:R>"
            )
            pct = bank / config.XP_BANK_CAP
            filled = max(1, round(pct * 10))
            bar = "🟦" * filled + "⬛" * (10 - filled)
            embed.add_field(
                name="Normal XP Bank",
                value=f"`{bar}`\n{bank:,} / {config.XP_BANK_CAP:,}",
                inline=False,
            )

        else:
            embed = discord.Embed(title="No Battle XP", color=0x95A5A6)
            embed.description = f"You can no longer gain XP or chaos shards from battles.\nNext Reset <t:{reset_ts}:R>"

        await interaction.response.send_message(embed=embed, ephemeral=True)


class NavButton(Button):
    def __init__(self, label, mode_id, emoji, is_active, disabled=False):
        super().__init__(
            label=label,
            style=(
                discord.ButtonStyle.primary
                if is_active
                else discord.ButtonStyle.secondary
            ),
            emoji=utils.safe_emoji(emoji),
            disabled=disabled,
            row=2,
        )
        self.mode_id = mode_id

    async def callback(self, interaction: discord.Interaction):
        self.view.mode = self.mode_id
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class BeltsButton(Button):
    def __init__(self, belt_emoji):
        super().__init__(
            label="View Belts",
            style=discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str(belt_emoji),
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        from mo_co.cogs.hunting import BeltsView

        await interaction.response.send_message(
            embed=BeltsView(interaction.user.id).get_embed(), ephemeral=True
        )


class RankedQueueButton(Button):
    def __init__(self):
        super().__init__(
            label="Battle", style=discord.ButtonStyle.success, emoji="⚔️", row=0
        )

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Versus")
        if cog:
            await cog.join_queue(interaction)
        else:
            await interaction.response.send_message("Versus offline.", ephemeral=True)


class WorldSelect(Select):
    def __init__(self, bot, player_lvl):
        opts = []
        for w in game_data.WORLDS + getattr(bot, "active_elites", []):
            if player_lvl >= w["unlock_lvl"]:
                icon = utils.safe_emoji(config.WORLD_ICONS.get(w["type"], "🗺️"))
                opts.append(
                    discord.SelectOption(label=w["name"], value=w["id"], emoji=icon)
                )
        super().__init__(placeholder="Travel to World...", options=opts[:25], row=0)

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Hunting")
        await cog.hunt.callback(cog, interaction, self.values[0])


class RiftSelect(Select):
    def __init__(self, bot, player_lvl, user_id):
        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        comp = json.loads(u_dict.get("completed_rifts", "[]"))
        opts = []
        for rs in game_data.RIFT_SETS:
            if player_lvl >= rs["unlock_lvl"]:
                for rk in rs["rifts"]:
                    r = game_data.RIFTS.get(rk)
                    if not r.get("req_rift") or r["req_rift"] in comp:
                        icon = utils.safe_emoji(utils.get_emoji(bot, r.get("icon")))
                        opts.append(
                            discord.SelectOption(
                                label=r["name"],
                                value=rk,
                                description=f"Boss: {r['boss']}",
                                emoji=icon,
                            )
                        )
        super().__init__(placeholder="Select a Rift...", options=opts[:25], row=0)

    async def callback(self, interaction: discord.Interaction):
        r = game_data.RIFTS.get(self.values[0])
        icon = utils.get_emoji(self.view.bot, r["icon"])
        embed = discord.Embed(
            title=f"{config.RIFTS_EMOJI} {r['name']}",
            description=f"**Boss:** {icon} {r['boss']}\n*{r['desc']}*",
            color=0x3498DB,
        )
        await interaction.response.edit_message(
            embed=embed,
            view=RiftEntryChoiceView(
                self.view.bot,
                interaction.user,
                self.values[0],
                interaction.message,
                mode="Rift",
            ),
        )


class DojoSelect(Select):
    def __init__(self, bot, player_lvl, user_id):
        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        comp = json.loads(u_dict.get("completed_dojos", "[]"))
        best = json.loads(u_dict.get("dojo_best_times", "{}"))
        opts = []
        for ds in game_data.DOJO_SETS:
            if player_lvl >= ds["unlock_lvl"]:
                prev = True
                for d_id in ds["dojos"]:
                    if prev:
                        d = game_data.DOJOS.get(d_id)
                        bt = best.get(d_id)
                        time_str = f"Best: {bt//60}:{bt%60:02d}" if bt else "New!"
                        boss_id = next(
                            (m["id"] for m in d["mobs"] if m.get("is_boss")),
                            d["mobs"][-1]["id"],
                        )
                        icon = utils.safe_emoji(utils.get_emoji(bot, boss_id))
                        opts.append(
                            discord.SelectOption(
                                label=d["name"],
                                value=d_id,
                                description=time_str,
                                emoji=icon,
                            )
                        )
                    prev = d_id in comp
        super().__init__(placeholder="Enter Dojo...", options=opts[:25], row=0)

    async def callback(self, interaction: discord.Interaction):
        d = game_data.DOJOS.get(self.values[0])
        embed = discord.Embed(
            title=f"{config.DOJO_ICON} {d['name']}",
            description=f"**Training Simulation**\nRecommended GP: {config.GEAR_POWER_EMOJI} {d['recommended_gp']:,}",
            color=0x9B59B6,
        )
        await interaction.response.edit_message(
            embed=embed,
            view=RiftEntryChoiceView(
                self.view.bot,
                interaction.user,
                self.values[0],
                interaction.message,
                mode="Dojo",
            ),
        )


class RiftEntryChoiceView(discord.ui.View):
    def __init__(self, bot, user, key, parent_msg, mode="Rift"):
        super().__init__(timeout=60)
        self.bot, self.user, self.key, self.parent_msg, self.mode = (
            bot,
            user,
            key,
            parent_msg,
            mode,
        )
        self.difficulty = "Normal"
        u_data = database.get_user_data(user.id)
        is_elite = bool(u_data["is_elite"]) if u_data else False
        self.add_item(DifficultySelect(is_elite))

    @discord.ui.button(
        label="Play", style=discord.ButtonStyle.primary, emoji="▶️", row=1
    )
    async def play(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mode == "Dojo":
            from mo_co.dojo_engine import DojoInstance

            instance = DojoInstance(self.bot, interaction.user, self.key)
            instance.difficulty = self.difficulty
            await instance.start_loop(interaction)
        else:
            from mo_co.cogs.teams import MatchmakingView, ACTIVE_LOBBIES

            u_data = dict(database.get_user_data(self.user.id))
            lvl, _, _ = utils.get_level_info(u_data["xp"])
            gp = utils.get_total_gp(self.user.id)

            ACTIVE_LOBBIES[interaction.channel.id] = {
                "leader": self.user.id,
                "members": [self.user.id],
                "member_info": {
                    self.user.id: {
                        "name": self.user.display_name,
                        "lvl": lvl,
                        "gp": gp,
                        "emblem": utils.get_emblem(lvl),
                    }
                },
                "ready": {self.user.id: True},
                "rift": self.key,
                "difficulty": self.difficulty,
                "guild_id": interaction.guild_id,
                "lfg_channel_id": interaction.channel_id,
                "lfg_message_id": 0,
                "message": "Solo Run",
                "thread_id": interaction.channel.id,
                "matchmaking": True,
                "is_solo": True,
                "game_started": False,
            }
            mm = MatchmakingView(self.bot, interaction.channel.id)
            if isinstance(self.parent_msg, discord.Message):
                await interaction.response.edit_message(
                    content=None, embed=mm.get_embed(), view=mm
                )
            else:
                await interaction.response.edit_message(
                    content=None, embed=mm.get_embed(), view=mm
                )

            asyncio.create_task(mm.start_counter(interaction))

    @discord.ui.button(
        label="Team Up", style=discord.ButtonStyle.success, emoji="👥", row=1
    )
    async def team(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mode == "Dojo":
            return await interaction.response.send_message(
                "Dojos are solo only!", ephemeral=True
            )
        cog = self.bot.get_cog("Teams")
        if cog:
            await cog.team.callback(cog, interaction, self.key)

        if isinstance(self.parent_msg, discord.Message):
            await self.parent_msg.delete()
        else:
            await interaction.delete_original_response()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(self.parent_msg, discord.Message):
            await self.parent_msg.delete()
        else:
            await interaction.delete_original_response()


class DifficultySelect(Select):
    def __init__(self, is_elite=False):
        options = [
            discord.SelectOption(
                label="Normal",
                value="Normal",
                description="Standard difficulty",
                default=True,
            )
        ]
        if is_elite:
            options.append(
                discord.SelectOption(
                    label="Hard",
                    value="Hard",
                    description="Increased Enemy Stats",
                    emoji="🔥",
                )
            )
            options.append(
                discord.SelectOption(
                    label="Nightmare",
                    value="Nightmare",
                    description="Extreme Stats + Reduced Stability",
                    emoji="💀",
                )
            )
        super().__init__(placeholder="Select Difficulty...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        self.view.difficulty = self.values[0]
        await interaction.response.defer()


class BeltsView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.u_data = database.get_user_data(user_id)

    def get_embed(self):
        u_dict = dict(self.u_data)
        stars = u_dict.get("versus_stars", 0)
        embed = discord.Embed(title=f"{config.BLACK_BELT} Lone Ranger", color=0xF1C40F)
        embed.description = f"Earn stars based on your rank in each match. Progress through the Belts to earn XP and an exclsuive Title. Your Belt will reset once the new Season starts, so don't miss out!\n\n🥇 1st: **+10 ⭐**\n🥈 2nd: **-5 ⭐**\n\n"

        def render_row(name, threshold, icon):
            status = "✅" if stars >= threshold else f"{stars}/{threshold}"
            return f"{icon} **{name} Belt**\n`{status}` Requirement: {threshold} ⭐"

        embed.add_field(
            name="\u200b",
            value=render_row(
                "Yellow",
                config.BELT_THRESHOLDS["Yellow"],
                config.BELT_EMOJIS["Yellow"],
            ),
            inline=True,
        )
        embed.add_field(
            name="\u200b",
            value=render_row(
                "Blue",
                config.BELT_THRESHOLDS["Blue"],
                config.BELT_EMOJIS["Blue"],
            ),
            inline=True,
        )
        embed.add_field(
            name="\u200b",
            value=render_row(
                "Purple",
                config.BELT_THRESHOLDS["Purple"],
                config.BELT_EMOJIS["Purple"],
            ),
            inline=True,
        )
        embed.add_field(
            name="\u200b",
            value=render_row(
                "Brown",
                config.BELT_THRESHOLDS["Brown"],
                config.BELT_EMOJIS["Brown"],
            ),
            inline=True,
        )
        embed.add_field(
            name="\u200b",
            value=render_row(
                "Black",
                config.BELT_THRESHOLDS["Black"],
                config.BELT_EMOJIS["Black"],
            ),
            inline=True,
        )
        return embed


async def setup(bot):
    await bot.add_cog(Portal(bot))

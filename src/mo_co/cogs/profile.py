import discord
from discord import app_commands
from discord.ext import commands
from mo_co import database, utils, config, game_data
import json
import math
import asyncio
from discord.ui import View, Button, Select, Modal, TextInput


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="View Profile", callback=self.context_profile
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def _generate_profile_embed(self, target: discord.User):
        row = database.get_user_data(target.id)
        if not row:
            return None
        user_data = dict(row)

        is_masked = False
        if user_data.get("account_state") != "LEGIT":
            snap = database.get_snapshot(target.id)
            if snap:
                user_data = snap["user"]
                is_masked = True
            else:
                pass

        level, xp_needed, xp_curr = utils.get_level_info(user_data["xp"])
        is_elite = bool(user_data.get("is_elite", 0))
        elite_level = 0

        if is_elite and level >= 50:
            elite_level, elite_cost, elite_prog = utils.get_elite_level_info(
                user_data["elite_xp"]
            )

        hp = utils.get_max_hp(target.id, level)
        gp = utils.get_total_gp(target.id)

        if is_masked:
            gp_str = "???"
        else:
            gp_str = f"{gp:,}"

        if is_elite and elite_level > 0:
            display_level = f"Elite {elite_level}"
            emblem = config.ELITE_EMBLEM
            xp_needed = elite_cost
            xp_curr = elite_prog
        else:
            display_level = f"{level}"
            emblem = utils.get_emblem(level)

        header_text = f"{target.display_name}"
        if user_data["current_title"]:
            header_text += f" • {user_data['current_title']}"

        embed = discord.Embed(color=0xE67E22)
        embed.set_author(name=header_text, icon_url=target.display_avatar.url)

        embed.add_field(
            name="Level", value=f"{emblem} **{display_level}**", inline=True
        )
        embed.add_field(name="HP", value=f"❤️ **{hp}**", inline=True)
        embed.add_field(
            name="Gear Power",
            value=f"{config.GEAR_POWER_EMOJI} **{gp_str}**",
            inline=True,
        )

        pct = int((xp_curr / max(1, xp_needed)) * 10)
        bar = "🟦" * pct + "⬜" * (10 - pct)

        bank_base = user_data["daily_xp_total"]
        bank_boost = user_data["daily_xp_boosted"]

        xp_status = ""
        if level < 10:
            xp_status = (
                f"{config.XP_EMOJI} **Normal XP:** {bank_base:,}/{config.XP_BANK_CAP:,}"
            )
        elif bank_boost > 0:
            xp_status = f"{config.XP_BOOST_3X_EMOJI} **Boosted:** {bank_boost:,}/{config.XP_BOOST_BANK_CAP:,}"
        elif bank_base > 0:
            xp_status = (
                f"{config.XP_EMOJI} **Normal XP:** {bank_base:,}/{config.XP_BANK_CAP:,}"
            )
        else:
            xp_status = f"{config.NO_XP_EMOJI} **No Battle XP**"

        embed.add_field(
            name="Level Progress",
            value=f"`{bar}` {xp_curr:,}/{xp_needed:,}\n{xp_status}",
            inline=False,
        )

        if is_elite and elite_level > 0:
            ring_icon = utils.get_emoji(self.bot, "empty_ring")
            embed.add_field(
                name="Elite Status",
                value=f"{ring_icon} Smart Ring Cap: **Lvl {elite_level}**",
                inline=True,
            )
        else:
            next_lvl = level + 1
            reward_info = next(
                (item for item in config.LEVEL_DATA if item["lvl"] == next_lvl), None
            )
            if reward_info:
                r_type = reward_info["reward"]
                r_text = "Unknown Reward"
                if r_type == "kit":
                    r_text = f"{config.CHAOS_CORE_EMOJI} Chaos Kit"
                elif r_type.startswith("world:"):
                    r_text = f"{config.MAP_EMOJI} **New World**: {r_type.split(':')[1]}"
                elif r_type.startswith("rift:"):
                    r_text = (
                        f"{config.RIFTS_EMOJI} **New Rift Set**: {r_type.split(':')[1]}"
                    )
                elif r_type.startswith("dojo:"):
                    r_text = (
                        f"{config.DOJO_ICON} **New Dojo Set**: {r_type.split(':')[1]}"
                    )
                elif r_type.startswith("elite:"):
                    r_text = f"{config.ELITE_EMOJI} {r_type.split(':')[1]}"
                embed.add_field(name="Next Reward", value=r_text, inline=True)

        currency_str = (
            f"{config.MOGOLD_EMOJI} **{user_data['mo_gold']:,}** | "
            f"{config.CHAOS_SHARD_EMOJI} **{user_data['chaos_shards']:,}** | "
            f"{config.MERCH_TOKEN_EMOJI} **{user_data['merch_tokens']:,}**\n"
            f"{config.CHAOS_CORE_EMOJI} **{user_data['chaos_cores']}** Cores | "
            f"{config.CHAOS_CORE_EMOJI} **{user_data['chaos_kits']}** Kits"
        )
        embed.add_field(name="Currencies", value=currency_str, inline=False)

        if is_masked:
            embed.add_field(
                name="Active Kit",
                value="*Data unavailable due to Temporal Displacement.*",
                inline=False,
            )
        else:
            with database.get_connection() as conn:
                u = conn.execute(
                    "SELECT active_kit_index FROM users WHERE user_id=?", (target.id,)
                ).fetchone()
                idx = u["active_kit_index"] if u else 1
                kit = conn.execute(
                    "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
                    (target.id, idx),
                ).fetchone()

            def get_item_display(inst_id, empty_key):
                if not inst_id:
                    return utils.get_emoji(self.bot, empty_key)
                with database.get_connection() as conn:
                    row = conn.execute(
                        "SELECT item_id, level FROM inventory WHERE instance_id=?",
                        (inst_id,),
                    ).fetchone()
                if row:
                    return f"{utils.get_emoji(self.bot, row['item_id'], target.id)} Lvl {row['level']}"
                return utils.get_emoji(self.bot, empty_key)

            if kit:
                gadget_list = [
                    get_item_display(kit[f"gadget_{i}_id"], "empty_gadget")
                    for i in range(1, 4)
                ]
                gadgets = " | ".join(gadget_list)
                passive_list = [
                    get_item_display(kit[f"passive_{i}_id"], "empty_passive")
                    for i in range(1, 4)
                ]
                passives = " | ".join(passive_list)
                ring_list = [
                    get_item_display(kit[f"ring_{i}_id"], "empty_ring")
                    for i in range(1, 4)
                ]
                rings = " | ".join(ring_list)

                kit_desc = (
                    f"**Weapon:** {get_item_display(kit['weapon_id'], 'empty_weapon')}\n"
                    f"**Gadgets:** {gadgets}\n"
                    f"**Passives:** {passives}\n"
                    f"**Module:** {get_item_display(kit['elite_module_id'], 'empty_module')}\n"
                    f"**Rings:** {rings}"
                )
                embed.add_field(
                    name=f"Active Kit: {kit['name']}", value=kit_desc, inline=False
                )

        return embed

    async def context_profile(
        self, interaction: discord.Interaction, user: discord.User
    ):
        await interaction.response.defer()
        database.register_user(user.id, user.display_name)
        embed = await self._generate_profile_embed(user)
        if not embed:
            return await interaction.followup.send(
                "This hunter hasn't started their journey yet!", ephemeral=True
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="profile", description="View player card")
    async def profile(
        self, interaction: discord.Interaction, target: discord.User = None
    ):
        await interaction.response.defer()
        target = target or interaction.user
        database.register_user(target.id, target.display_name)

        embed = await self._generate_profile_embed(target)
        if not embed:
            return await interaction.followup.send(
                "User hasn't started playing yet.", ephemeral=True
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="delete", description="Permanently delete your account data"
    )
    async def delete_account(self, interaction: discord.Interaction):
        user_data = database.get_user_data(interaction.user.id)
        if not user_data:
            return await interaction.response.send_message(
                "You don't have an account to delete.", ephemeral=True
            )

        user_dict = dict(user_data)
        lvl, _, _ = utils.get_level_info(user_dict["xp"])
        gp = utils.get_total_gp(interaction.user.id)
        inventory = database.get_user_inventory(interaction.user.id)

        embed = discord.Embed(
            title="⚠️ PERMANENT ACCOUNT DELETION",
            description=(
                "You are about to permanently delete your **mo.hunt** account data. "
                "This action **cannot be undone**. All progress, items, and currency will be wiped."
            ),
            color=0xFF0000,
        )
        embed.add_field(
            name="What you are losing:",
            value=(
                f"• **Level:** {lvl}\n"
                f"• **Gear Power:** {gp:,}\n"
                f"• **Inventory Size:** {len(inventory)} items\n"
                f"• **Mo.Gold:** {user_dict['mo_gold']:,}\n"
                f"• **Merch Tokens:** {user_dict['merch_tokens']:,}"
            ),
            inline=False,
        )
        embed.set_footer(text="To confirm, click the button below and type 'CONFIRM'.")

        view = AccountDeletionView(interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Global Hunter Rankings")
    async def leaderboard(self, interaction: discord.Interaction):

        await interaction.response.defer()
        view = LeaderboardView(self.bot, interaction.user.id)

        await interaction.followup.send(embed=view.get_embed(), view=view)

    @app_commands.command(name="title", description="Equip a Title")
    async def equip_title(self, interaction: discord.Interaction, title: str):
        row = database.get_user_data(interaction.user.id)
        if not row:
            return await interaction.response.send_message(
                "You haven't started playing yet!", ephemeral=True
            )
        u = dict(row)
        owned = json.loads(u["owned_titles"])
        if title not in owned and title != "Hunter":
            return await interaction.response.send_message(
                "You don't own this title.", ephemeral=True
            )
        database.update_user_stats(interaction.user.id, {"current_title": title})
        await interaction.response.send_message(
            f"✅ Title set to **{title}**", ephemeral=True
        )

    @equip_title.autocomplete("title")
    async def title_ac(self, interaction: discord.Interaction, current: str):
        row = database.get_user_data(interaction.user.id)
        if not row:
            return []
        u = dict(row)
        owned = json.loads(u["owned_titles"])
        if "Hunter" not in owned:
            owned.insert(0, "Hunter")
        return [
            app_commands.Choice(name=t, value=t)
            for t in owned
            if current.lower() in t.lower()
        ][:25]


class AccountDeletionView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(
        label="Permanently Delete Everything",
        style=discord.ButtonStyle.danger,
        emoji="🗑️",
    )
    async def delete_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return
        await interaction.response.send_modal(DeletionModal(self.user_id))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_btn(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="Deletion cancelled. Your data is safe.", embed=None, view=None
        )


class DeletionModal(Modal):
    def __init__(self, user_id):
        super().__init__(title="Verify Deletion")
        self.user_id = user_id
        self.verify = TextInput(
            label="Type 'CONFIRM' to delete your account",
            placeholder="CONFIRM",
            min_length=7,
            max_length=7,
            required=True,
        )
        self.add_item(self.verify)

    async def on_submit(self, interaction: discord.Interaction):
        if self.verify.value.upper() != "CONFIRM":
            return await interaction.response.send_message(
                "Verification failed. Incorrect text entered.", ephemeral=True
            )

        u_data = database.get_user_data(self.user_id)
        if u_data:
            u_dict = dict(u_data)
            tid = u_dict.get("mission_thread_id")
            if tid and tid != 0:
                try:
                    thread = await interaction.client.fetch_channel(tid)
                    await thread.delete()
                except:
                    pass

        database.delete_user_account(self.user_id)
        await interaction.response.edit_message(
            content="🗑️ **Account Deleted.** Your data and active mission connection have been wiped. Farewell, Hunter.",
            embed=None,
            view=None,
        )


class LeaderboardView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.offset = 0
        self.window_size = 10
        self.scroll_step = 5
        self.category = "Level"
        self.search_results = None
        self.all_data = []
        self._refresh_db_data()
        self.update_components()

    def _refresh_db_data(self):

        raw_data = database.get_leaderboard_data(limit=100)

        processed = []
        for u in raw_data:
            uid = u["user_id"]
            xp = u["xp"]
            elite_xp = u["elite_xp"]
            is_elite = bool(u["is_elite"])
            lvl, _, _ = utils.get_level_info(xp)

            if is_elite and lvl >= 50:
                e_lvl, _, _ = utils.get_elite_level_info(elite_xp)
                sort_metric = xp + elite_xp
                emblem = config.ELITE_EMBLEM
                lvl_disp = f"Elite {e_lvl}"
            else:
                sort_metric = xp
                emblem = utils.get_emblem(lvl)
                lvl_disp = f"{lvl}"

            gp = utils.get_total_gp(uid)

            name = u["display_name"] or f"Hunter#{str(uid)[-4:]}"

            processed.append(
                {
                    "id": uid,
                    "name": name,
                    "xp": sort_metric,
                    "lvl": lvl_disp,
                    "gp": gp,
                    "emblem": emblem,
                }
            )
        self.all_data = processed
        self._apply_sort()

    def _apply_sort(self):
        if self.category == "Level":
            self.all_data.sort(key=lambda x: x["xp"], reverse=True)
        else:
            self.all_data.sort(key=lambda x: x["gp"], reverse=True)

    def get_embed(self):
        title = (
            f"{config.XP_EMOJI} Global Rankings"
            if self.category == "Level"
            else f"{config.GEAR_POWER_EMOJI} Power Rankings"
        )
        embed = discord.Embed(title=title, color=0xF1C40F)
        data = self.search_results if self.search_results is not None else self.all_data
        chunk = data[self.offset : self.offset + self.window_size]
        if not chunk:
            embed.description = "*No hunters found in this range.*"
            return embed
        lines = []
        for idx, item in enumerate(chunk):
            rank = self.offset + idx + 1
            final_name = (
                f"**{item['name']}**" if item["id"] == self.user_id else item["name"]
            )
            lines.append(
                f"`#{rank:02}` {item['emblem']} {final_name} | {config.GEAR_POWER_EMOJI} `{item['gp']:,}` | Lvl `{item['lvl']}`"
            )
        embed.description = "\n".join(lines)
        total_count = len(data)
        my_rank = next(
            (i + 1 for i, r in enumerate(self.all_data) if r["id"] == self.user_id), "?"
        )
        progress = (
            int((self.offset / max(1, total_count - self.window_size)) * 10)
            if total_count > self.window_size
            else 10
        )
        bar = "▬" * progress + "🔘" + "▬" * (10 - progress)
        embed.set_footer(
            text=f"Your Rank: #{my_rank} | Viewing {self.offset+1}-{min(self.offset+self.window_size, total_count)} of {total_count}\n{bar}"
        )
        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(LeaderboardTypeSelect(self.category))
        data = self.search_results if self.search_results is not None else self.all_data
        total_len = len(data)
        can_up = self.offset > 0
        can_down = (self.offset + self.window_size) < total_len
        self.add_item(
            Button(
                label="Scroll Up",
                style=discord.ButtonStyle.primary,
                emoji="⬆️",
                disabled=not can_up,
                custom_id="lb_up",
                row=1,
            )
        )
        self.add_item(
            Button(
                label="Scroll Down",
                style=discord.ButtonStyle.primary,
                emoji="⬇️",
                disabled=not can_down,
                custom_id="lb_down",
                row=1,
            )
        )
        self.add_item(
            Button(
                label="Search",
                style=discord.ButtonStyle.secondary,
                emoji="🔍",
                custom_id="lb_search",
                row=2,
            )
        )
        self.add_item(
            Button(
                label="Reset",
                style=discord.ButtonStyle.danger,
                emoji="🔄",
                custom_id="lb_reset",
                row=2,
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            return False
        cid = interaction.data.get("custom_id")
        if cid == "lb_search":
            await interaction.response.send_modal(LeaderboardSearchModal(self))
            return True
        if not interaction.response.is_done():
            await interaction.response.defer()
        data = self.search_results if self.search_results is not None else self.all_data
        if cid == "lb_up":
            self.offset = max(0, self.offset - self.scroll_step)
        elif cid == "lb_down":
            self.offset = min(
                len(data) - self.window_size, self.offset + self.scroll_step
            )
            if self.offset < 0:
                self.offset = 0
        elif cid == "lb_reset":
            self.search_results, self.offset = None, 0
            self._refresh_db_data()

        self.update_components()
        await interaction.edit_original_response(embed=self.get_embed(), view=self)
        return True


class LeaderboardTypeSelect(Select):
    def __init__(self, current):
        options = [
            discord.SelectOption(
                label="Sort by Level",
                value="Level",
                emoji=config.XP_EMOJI,
                default=(current == "Level"),
            ),
            discord.SelectOption(
                label="Sort by Gear Power",
                value="Gear Power",
                emoji=config.GEAR_POWER_EMOJI,
                default=(current == "Gear Power"),
            ),
        ]
        super().__init__(
            placeholder="Choose ranking category...", options=options, row=0
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.category = self.values[0]
        self.view.offset = 0
        self.view._apply_sort()
        if not interaction.response.is_done():
            await interaction.response.defer()
        self.view.update_components()
        await interaction.edit_original_response(
            embed=self.view.get_embed(), view=self.view
        )


class LeaderboardSearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Leaderboard")
        self.view = view
        self.query = TextInput(
            label="Hunter Name", placeholder="Search for a hunter..."
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        q = self.query.value.lower()
        if not interaction.response.is_done():
            await interaction.response.defer()
        results = [row for row in self.view.all_data if q in row["name"].lower()]
        self.view.search_results, self.view.offset = results, 0
        self.view.update_components()
        await interaction.edit_original_response(
            embed=self.view.get_embed(), view=self.view
        )


async def setup(bot):
    await bot.add_cog(Profile(bot))

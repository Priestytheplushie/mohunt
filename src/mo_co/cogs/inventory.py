import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from mo_co import database, game_data, utils, config
from mo_co.cogs.hunting import LootRevealView
from mo_co.mission_engine import MissionEngine
from mo_co.game_data import scaling
import json
import random
import asyncio
from mo_co import pedia

MODIFIER_DESCRIPTIONS = {
    "Standard": "No special bonuses.",
    "Overcharged": "+30% Damage, +20% Cooldown Duration.",
    "Megacharged": "+60% Damage, +40% Cooldown Duration.",
    "Chaos": "Attacks roll a random multiplier (0.5x to 4.0x).",
    "Toxic": "Applies Poison (50 dmg/s) on every hit.",
    "Overcharged Chaos": "+20% Base Damage. Attacks roll random multiplier (0.75x to 2.0x). No cooldown penalty.",
    "Elite": "+25% Damage/Heal, +10% Crit Chance.",
}


class SearchModal(Modal):
    def __init__(self, view):
        super().__init__(title="Search Inventory")
        self.view = view
        self.query = TextInput(
            label="Search Query",
            placeholder="Enter item name or modifier...",
            required=True,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.search_query = self.query.value
        self.view.page = 0
        self.view.refresh_data()
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventory", description="Advanced Gear Management")
    async def inventory(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        view = AdvancedInventoryView(self.bot, interaction.user.id)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )

    @app_commands.command(name="inspect", description="View detailed info")
    @app_commands.describe(
        item_name="Name to inspect",
        level="Preview Level (Default: Your Level)",
        modifier="Preview Modifier",
    )
    @app_commands.autocomplete(
        item_name=utils.item_autocomplete, modifier=utils.modifier_autocomplete
    )
    async def inspect(
        self,
        interaction: discord.Interaction,
        item_name: str,
        level: int = None,
        modifier: str = "Standard",
    ):
        item = next(
            (
                v
                for k, v in game_data.ALL_ITEMS.items()
                if v["name"].lower() == item_name.lower()
            ),
            game_data.get_item(item_name),
        )
        if not item:
            return await interaction.response.send_message(
                f"❌ Not found: `{item_name}`", ephemeral=True
            )

        if item["type"] == "title":
            embed = discord.Embed(title=f"👑 {item['name']}", color=0xF1C40F)
            embed.description = item.get("description", "No description available.")
            embed.add_field(
                name="Rarity", value=item.get("rarity", "Common"), inline=True
            )
            embed.add_field(name="Type", value="Title", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        u_data = database.get_user_data(interaction.user.id)
        if level is None:
            if u_data:
                u_dict = dict(u_data)
                level, _, _ = utils.get_level_info(u_dict["xp"])
            else:
                level = 1
        level = max(1, min(50, level))

        stats_desc, raw_val = utils.get_item_stats(item["id"], level)

        if modifier == "Overcharged":
            if isinstance(raw_val, (int, float)) and raw_val > 0:
                boosted = int(raw_val * 1.3)
                stats_desc = (
                    stats_desc.replace(str(raw_val), f"**{boosted}**") + " *(+30%)*"
                )
        elif modifier == "Megacharged":
            if isinstance(raw_val, (int, float)) and raw_val > 0:
                boosted = int(raw_val * 1.6)
                stats_desc = (
                    stats_desc.replace(str(raw_val), f"**{boosted}**") + " *(+60%)*"
                )
        elif modifier == "Overcharged Chaos":
            if isinstance(raw_val, (int, float)) and raw_val > 0:
                boosted = int(raw_val * 1.2)
                stats_desc = (
                    stats_desc.replace(str(raw_val), f"**{boosted}**") + " *(+20%)*"
                )

        embed = discord.Embed(
            title=f"{utils.get_emoji(self.bot, item['id'])} {item['name']}",
            color=0x95A5A6,
        )
        if item.get("quote"):
            embed.description = f"*\"{item['quote']}\"*"

        static_desc = item.get("description") or item.get("effect")
        if static_desc and static_desc != "No info.":
            embed.add_field(name="Effect Description", value=static_desc, inline=False)

        if item["type"] != "ride":
            embed.add_field(
                name="Stats (Preview)",
                value=f"Lvl {level} | {stats_desc}",
                inline=False,
            )

        if item["type"] == "weapon":
            embed.add_field(
                name="Attack",
                value=item.get("main_attack", "Attack"),
                inline=True,
            )
            embed.add_field(
                name="Combo",
                value=item.get("combo_attack", "Combo"),
                inline=True,
            )

        mod_desc = MODIFIER_DESCRIPTIONS.get(modifier, "Unknown modifier.")
        embed.add_field(name=f"Modifier: {modifier}", value=mod_desc, inline=False)

        embed.add_field(
            name="Type",
            value=item["type"].replace("_", " ").title(),
            inline=True,
        )
        embed.add_field(name="Rarity", value=item.get("rarity", "Common"), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="open", description="3D Printer: Open Cores and Use Kits"
    )
    async def open_cmd(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        view = OpenDashboard(self.bot, interaction.user.id)
        embed = discord.Embed(
            title="🖨️ 3D Printer",
            description="Manage your Chaos Cores and Kits here.",
            color=0x9B59B6,
        )
        embed.add_field(
            name="Chaos Cores",
            value=f"{config.CHAOS_CORE_EMOJI} **{view.cores}**\n*Open to find new gear!*",
            inline=True,
        )
        embed.add_field(
            name="Chaos Kits",
            value=f"{config.CHAOS_CORE_EMOJI} **{view.kits}**\n*Use to upgrade gear!*",
            inline=True,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def prompt_kit_usage(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        player_lvl, _, _ = utils.get_level_info(u_dict["xp"])

        items = database.get_user_inventory(user_id)
        upgradeable_items = []
        for r in items:
            if r["level"] >= player_lvl:
                continue
            i_def = game_data.get_item(r["item_id"])
            if not i_def or i_def["type"] == "ride":
                continue
            upgradeable_items.append(r)

        if not upgradeable_items:
            msg = "No items to upgrade! (Kit saved)"
            if interaction.response.is_done():
                return await interaction.followup.send(msg, ephemeral=True)
            return await interaction.response.send_message(msg, ephemeral=True)

        candidates = random.sample(upgradeable_items, min(len(upgradeable_items), 6))
        opts = []
        embed = discord.Embed(
            title=f"{config.CHAOS_CORE_EMOJI} Select Item to Upgrade",
            description="Select an item to channel the Chaos Kit into. Underleveled gear receives larger boosts!",
            color=0x9B59B6,
        )

        for r in candidates:
            d = game_data.get_item(r["item_id"])
            boost_amount = random.choices(
                [1, 2, 3, 4, 5, 6, 7], weights=[5, 10, 20, 30, 20, 10, 5], k=1
            )[0]
            current_lvl = r["level"]
            new_lvl = min(50, min(player_lvl, current_lvl + boost_amount))
            actual_boost = new_lvl - current_lvl

            if actual_boost == 0 and current_lvl < player_lvl:
                actual_boost = 1
                new_lvl = current_lvl + 1

            old_gp = utils.get_item_gp(r["item_id"], current_lvl)
            new_gp = utils.get_item_gp(r["item_id"], new_lvl)

            lbl_old, _ = utils.get_item_stats(r["item_id"], current_lvl)
            lbl_new, _ = utils.get_item_stats(r["item_id"], new_lvl)
            stat_preview = f"{lbl_old} ➔ {lbl_new}"

            icon = utils.get_emoji(self.bot, d["id"])
            mod_prefix = f"[{r['modifier']}] " if r["modifier"] != "Standard" else ""

            embed.add_field(
                name=f"{icon} {mod_prefix}{d['name']}",
                value=f"**Lvl {current_lvl} ➔ {new_lvl}** (+{actual_boost})\nGP: {old_gp:,} ➔ {new_gp:,}\n*{stat_preview}*",
                inline=True,
            )
            opts.append(
                discord.SelectOption(
                    label=f"{mod_prefix}{d['name']}",
                    description=f"Lvl +{actual_boost} | GP +{new_gp-old_gp}",
                    value=f"{r['instance_id']}:{actual_boost}",
                    emoji=utils.safe_emoji(icon),
                )
            )

        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed,
                view=ChaosKitView(self.bot, user_id, opts),
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=ChaosKitView(self.bot, user_id, opts),
                ephemeral=True,
            )


class AdvancedInventoryView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.page = 0
        self.selected_filters = []
        self.sort_method = "Level (High > Low)"
        self.search_query = None
        self.show_advanced = False
        self.items_per_page = 5
        self.filtered_items = []
        self.refresh_data()
        self.update_components()

    def refresh_data(self):
        raw_inv = database.get_user_inventory(self.user_id)
        selected_types = [
            x.split("_", 1)[1] for x in self.selected_filters if x.startswith("type_")
        ]
        selected_mods = [
            x.split("_", 1)[1] for x in self.selected_filters if x.startswith("mod_")
        ]
        processed = []
        for row in raw_inv:
            d = game_data.get_item(row["item_id"])
            if not d:
                continue
            processed.append(
                {
                    "inst": row["instance_id"],
                    "id": row["item_id"],
                    "name": d["name"],
                    "type": d["type"],
                    "lvl": row["level"],
                    "mod": row["modifier"],
                    "rarity": d.get("rarity", "Common"),
                    "gp": utils.get_item_gp(row["item_id"], row["level"]),
                    "acquired": row["acquired_at"],
                    "quote": d.get("quote", ""),
                    "locked": row["locked"],
                }
            )

        filtered = []
        for item in processed:
            if selected_types and item["type"] not in selected_types:
                continue
            if selected_mods and not any(m in item["mod"] for m in selected_mods):
                continue
            if self.search_query:
                q = self.search_query.lower()
                if q not in item["name"].lower() and q not in item["mod"].lower():
                    continue
            filtered.append(item)

        if self.sort_method == "Level (High > Low)":
            filtered.sort(key=lambda x: (x["lvl"], x["gp"]), reverse=True)
        elif self.sort_method == "Level (Low > High)":
            filtered.sort(key=lambda x: (x["lvl"], x["gp"]))
        elif self.sort_method == "Newest":
            filtered.sort(key=lambda x: x["acquired"], reverse=True)
        elif self.sort_method == "Rarity":
            r_map = {"Legendary": 4, "Epic": 3, "Rare": 2, "Common": 1}
            filtered.sort(key=lambda x: r_map.get(x["rarity"], 0), reverse=True)

        self.filtered_items = filtered
        max_pages = max(1, (len(self.filtered_items) - 1) // self.items_per_page + 1)
        if self.page >= max_pages:
            self.page = 0

    def get_embed(self):
        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)
        total_gp = utils.get_total_gp(self.user_id)
        level, _, _ = utils.get_level_info(u_dict["xp"])
        emblem = utils.get_emblem(level)
        embed = discord.Embed(
            title=f"{emblem} {u_dict['current_title'] or 'Hunter'}'s Wardrobe",
            color=0x2C3E50,
        )
        embed.set_footer(
            text=f"Items: {len(self.filtered_items)} | GP: {total_gp:,} | Gold: {u_dict['mo_gold']:,}"
        )

        start = self.page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.filtered_items[start:end]

        if not chunk:
            embed.description = "*No items found matching criteria.*"
        else:
            for item in chunk:
                icon = utils.get_emoji(self.bot, item["id"], self.user_id)
                mod_str = f"**[{item['mod']}]** " if item["mod"] != "Standard" else ""
                lock_icon = "🔒 " if item["locked"] else ""

                if item["type"] == "ride":
                    stats_str = f"*{item['rarity']}*"
                else:
                    stats_str = f"`Lvl {item['lvl']}` | {config.GEAR_POWER_EMOJI} `{item['gp']:,}` | *{item['rarity']}*"

                skin_id = utils.get_equipped_skin(self.user_id, item["id"])
                if skin_id:
                    stats_str += f"\n🎨 **{game_data.get_item(skin_id)['name']}**"

                if self.show_advanced and item["type"] != "ride":
                    stat_label, stat_val = utils.get_item_stats(item["id"], item["lvl"])
                    next_label, next_val = utils.get_item_stats(
                        item["id"], item["lvl"] + 1
                    )

                    if isinstance(stat_val, tuple):
                        stat_val = stat_val[0]
                    if isinstance(next_val, tuple):
                        next_val = next_val[0]

                    diff = round(next_val - stat_val, 2)
                    diff_str = f" (+{diff})" if diff > 0 else ""
                    stats_str += f"\n**Effect:** {stat_label}\n**Next Lvl:** {next_label}{diff_str}"

                embed.add_field(
                    name=f"{lock_icon}{icon} {mod_str}**{item['name']}**",
                    value=stats_str,
                    inline=False,
                )

        info = []
        if self.selected_filters:
            pretty_filters = [
                f.split("_", 1)[1].replace("_", " ").title()
                for f in self.selected_filters
            ]
            info.append(
                f"Filters: {', '.join(pretty_filters)}"
                if len(pretty_filters) <= 3
                else f"Filters: {len(pretty_filters)} active"
            )
        if self.search_query:
            info.append(f"Search: **{self.search_query}**")
        info.append(f"Sort: {self.sort_method}")
        embed.description = (
            " • ".join(info)
            + f"\nPage {self.page + 1} / {max(1, (len(self.filtered_items)-1)//self.items_per_page + 1)}"
        )
        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(FilterSelect(self.bot, self.selected_filters))
        self.add_item(SortSelect(self.sort_method))
        self.add_item(AdvancedButton(self.show_advanced))
        self.add_item(SearchButton())
        if self.search_query or self.selected_filters:
            self.add_item(ResetButton())

        max_pages = max(1, (len(self.filtered_items) - 1) // self.items_per_page + 1)
        self.add_item(
            Button(
                label="◀",
                style=discord.ButtonStyle.primary,
                row=3,
                disabled=(self.page == 0),
                custom_id="inv_prev",
            )
        )
        self.add_item(
            Button(
                label=f"{self.page + 1}/{max_pages}",
                style=discord.ButtonStyle.secondary,
                row=3,
                disabled=True,
            )
        )
        self.add_item(
            Button(
                label="▶",
                style=discord.ButtonStyle.primary,
                row=3,
                disabled=(self.page >= max_pages - 1),
                custom_id="inv_next",
            )
        )

        self.add_item(CosmeticsButton())
        self.add_item(FusionButton())
        self.add_item(
            InspectModeButton(
                self.filtered_items[
                    self.page
                    * self.items_per_page : (self.page + 1)
                    * self.items_per_page
                ]
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            return False
        if interaction.data.get("custom_id") == "inv_prev":
            self.page -= 1
            self.update_components()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        elif interaction.data.get("custom_id") == "inv_next":
            self.page += 1
            self.update_components()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        return True


class FilterSelect(Select):
    def __init__(self, bot, current_selection):
        def get_pe(emoji_str):
            return (
                discord.PartialEmoji.from_str(emoji_str)
                if emoji_str and emoji_str.startswith("<")
                else None
            )

        options = [
            discord.SelectOption(
                label="Weapons",
                value="type_weapon",
                emoji=get_pe(utils.get_emoji(bot, "empty_weapon")),
            ),
            discord.SelectOption(
                label="Gadgets",
                value="type_gadget",
                emoji=get_pe(utils.get_emoji(bot, "empty_gadget")),
            ),
            discord.SelectOption(
                label="Passives",
                value="type_passive",
                emoji=get_pe(utils.get_emoji(bot, "empty_passive")),
            ),
            discord.SelectOption(
                label="Rides",
                value="type_ride",
                emoji=get_pe(config.EMPTY_RIDE),
            ),
            discord.SelectOption(label="Standard", value="mod_Standard"),
            discord.SelectOption(
                label="Overcharged",
                value="mod_Overcharged",
                emoji=get_pe(config.OVERCHARGED_ICON),
            ),
            discord.SelectOption(
                label="Megacharged",
                value="mod_Megacharged",
                emoji=get_pe(config.CHAOS_ALERT),
            ),
        ]
        for o in options:
            if o.value in current_selection:
                o.default = True
        super().__init__(
            placeholder="Filter...",
            options=options,
            row=0,
            min_values=0,
            max_values=len(options),
        )

    async def callback(self, i):
        self.view.selected_filters = self.values
        self.view.page = 0
        self.view.refresh_data()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class SortSelect(Select):
    def __init__(self, current):
        sort_opts = [
            "Level (High > Low)",
            "Level (Low > High)",
            "Newest",
            "Rarity",
        ]
        options = []
        for o in sort_opts:
            is_default = o == current
            options.append(discord.SelectOption(label=o, default=is_default))
        super().__init__(placeholder="Sort Order", options=options, row=1)

    async def callback(self, i):
        self.view.sort_method = self.values[0]
        self.view.page = 0
        self.view.refresh_data()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class AdvancedButton(Button):
    def __init__(self, state):
        super().__init__(
            label="Stats",
            style=(
                discord.ButtonStyle.success if state else discord.ButtonStyle.secondary
            ),
            emoji="🔬",
            row=2,
        )

    async def callback(self, i):
        self.view.show_advanced = not self.view.show_advanced
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class SearchButton(Button):
    def __init__(self):
        super().__init__(
            label="Search",
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            row=2,
        )

    async def callback(self, i):
        await i.response.send_modal(SearchModal(self.view))


class ResetButton(Button):
    def __init__(self):
        super().__init__(
            label="Reset", style=discord.ButtonStyle.danger, emoji="❌", row=2
        )

    async def callback(self, i):
        self.view.selected_filters = []
        self.view.search_query = None
        self.view.page = 0
        self.view.refresh_data()
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class CosmeticsButton(Button):
    def __init__(self):
        super().__init__(
            label="Skins", style=discord.ButtonStyle.primary, emoji="🎨", row=4
        )

    async def callback(self, i):
        await i.response.send_message(
            "Select item to skin:",
            view=BaseItemSelectView(self.view.bot, self.view.user_id),
            ephemeral=True,
        )


class BaseItemSelectView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

        inv = database.get_user_inventory(user_id)
        eligible_items = []
        for r in inv:
            d = game_data.get_item(r["item_id"])
            if d["type"] in ["weapon", "gadget"]:
                eligible_items.append(r)

        if not eligible_items:
            self.add_item(
                Button(label="No items available for skinning!", disabled=True)
            )
        else:
            self.add_item(BaseItemSelect(eligible_items[:25], bot))


class BaseItemSelect(Select):
    def __init__(self, items, bot):
        options = []
        for r in items:
            d = game_data.get_item(r["item_id"])
            icon = utils.get_emoji(bot, r["item_id"])
            options.append(
                discord.SelectOption(
                    label=f"{d['name']} (Lvl {r['level']})",
                    value=str(r["instance_id"]),
                    emoji=utils.safe_emoji(icon),
                )
            )
        super().__init__(placeholder="Select item to customize...", options=options)

    async def callback(self, interaction: discord.Interaction):
        inst_id = int(self.values[0])
        item_row = database.get_item_instance(inst_id)
        if not item_row:
            return

        item_id = item_row["item_id"]
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)
        owned_skins = json.loads(u_dict["owned_skins"])

        compatible_skins = []
        for skin_id in owned_skins:
            s_def = game_data.get_item(skin_id)
            if s_def and s_def.get("base_item") == item_id:
                compatible_skins.append(skin_id)

        await interaction.response.edit_message(
            content=f"Select skin for **{game_data.get_item(item_id)['name']}**:",
            embed=None,
            view=SkinSelectView(
                self.view.bot, interaction.user.id, item_id, compatible_skins
            ),
        )


class SkinSelectView(View):
    def __init__(self, bot, user_id, base_id, skins):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.base_id = base_id
        self.add_item(SkinSelect(skins, bot))
        self.add_item(RemoveSkinButton(base_id))


class SkinSelect(Select):
    def __init__(self, skins, bot):
        options = []
        for s in skins:
            d = game_data.get_item(s)
            icon = utils.get_emoji(bot, s)
            options.append(
                discord.SelectOption(
                    label=d["name"], value=s, emoji=utils.safe_emoji(icon)
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No skins owned for this item!", value="none"
                )
            )

        super().__init__(placeholder="Choose a skin...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return
        skin_id = self.values[0]

        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)
        equipped = json.loads(u_dict["equipped_skins"])
        equipped[self.view.base_id] = skin_id

        database.update_user_stats(
            interaction.user.id, {"equipped_skins": json.dumps(equipped)}
        )
        pedia.track_skin(interaction.user.id, skin_id)

        skin_name = game_data.get_item(skin_id)["name"]
        await interaction.response.edit_message(
            content=f"✅ Equipped **{skin_name}**!", view=None
        )


class RemoveSkinButton(Button):
    def __init__(self, base_id):
        super().__init__(label="Remove Skin", style=discord.ButtonStyle.danger)
        self.base_id = base_id

    async def callback(self, interaction: discord.Interaction):
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)
        equipped = json.loads(u_dict["equipped_skins"])
        if self.base_id in equipped:
            del equipped[self.base_id]
            database.update_user_stats(
                interaction.user.id, {"equipped_skins": json.dumps(equipped)}
            )
            await interaction.response.edit_message(
                content="✅ Skin removed. Item reset to default appearance.",
                view=None,
            )
        else:
            await interaction.response.send_message(
                "No skin is equipped on this item.", ephemeral=True
            )


class FusionButton(Button):
    def __init__(self):
        emoji = discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI)
        super().__init__(
            label="Fusion",
            style=discord.ButtonStyle.danger,
            emoji=emoji,
            row=4,
        )

    async def callback(self, interaction):
        u_data = database.get_user_data(self.view.user_id)
        u_dict = dict(u_data)
        f_count = u_dict["daily_fusions"]
        if f_count >= 20:
            return await interaction.response.send_message(
                "⚠️ **Fusion Limit Reached (20/20)!**\nWait for daily reset to fuse more items.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=f"{config.CHAOS_CORE_EMOJI} Chaos Fusion",
            description=(
                f"Daily Capacity: **{20-f_count}/20** items remaining.\n\n"
                "**Mechanics:**\n"
                "• Earn **Chaos Rolls** based on Level: `1 + (Lvl/20)`.\n"
                "• ✨ **Resonant Sacrifice:** Duplicates grant **Double Rolls**!\n"
                "• **Gambling Pool:** Cores, Kits, Shards, Tokens, Nothing.\n"
                "• Shards require **Hunter Level 12**.\n\n"
                "**Warning:** Destroyed items are gone forever!"
            ),
            color=0xE74C3C,
        )
        embed.set_footer(text="Equipped/Locked items are hidden.")
        await interaction.response.send_message(
            embed=embed,
            view=FusionSelectView(self.view.bot, self.view.user_id),
            ephemeral=True,
        )


class FusionSelectView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

        inv = database.get_user_inventory(user_id)
        kits = database.get_all_kits(user_id)
        equipped_ids = set()
        slots = [
            "weapon_id",
            "gadget_1_id",
            "gadget_2_id",
            "gadget_3_id",
            "passive_1_id",
            "passive_2_id",
            "passive_3_id",
            "elite_module_id",
            "ring_1_id",
            "ring_2_id",
            "ring_3_id",
            "ride_id",
        ]
        for kit in kits:
            for s in slots:
                if kit[s]:
                    equipped_ids.add(kit[s])

        eligible = []
        for r in inv:
            d = game_data.get_item(r["item_id"])
            if d["type"] == "ride":
                continue
            if not r["locked"] and r["instance_id"] not in equipped_ids:
                is_duplicate = sum(1 for x in inv if x["item_id"] == r["item_id"]) > 1
                eligible.append({"type": "gear", "data": r, "resonant": is_duplicate})

        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        owned_skins = json.loads(u_dict["owned_skins"])
        for skin_id in owned_skins:
            eligible.append({"type": "skin", "data": skin_id, "resonant": True})

        eligible.sort(
            key=lambda x: (x["data"]["level"] if x["type"] == "gear" else 0),
            reverse=True,
        )
        if not eligible:
            self.add_item(Button(label="No eligible items found!", disabled=True))
            self.add_item(FusionInitialCancelButton())
        else:
            self.add_item(FusionSelect(eligible[:25], bot))
            self.add_item(FusionInitialCancelButton())


class FusionInitialCancelButton(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="Fusion menu closed.", embed=None, view=None
        )


class FusionSelect(Select):
    def __init__(self, items, bot):
        self.data_map = {}
        options = []
        for idx, item in enumerate(items):
            key = str(idx)
            self.data_map[key] = item
            if item["type"] == "gear":
                i = item["data"]
                d = game_data.get_item(i["item_id"])
                rolls = utils.calculate_fusion_rolls(i)
                if item["resonant"]:
                    rolls *= 2
                mod = f"[{i['modifier']}] " if i["modifier"] != "Standard" else ""
                resonant_tag = " ✨" if item["resonant"] else ""
                icon_str = utils.get_emoji(bot, i["item_id"])
                options.append(
                    discord.SelectOption(
                        label=f"Lvl {i['level']} {mod}{d['name']}{resonant_tag}",
                        value=key,
                        description=f"Yields {rolls} Rolls",
                        emoji=utils.safe_emoji(icon_str),
                    )
                )
            else:
                skin_id = item["data"]
                d = game_data.get_item(skin_id)
                options.append(
                    discord.SelectOption(
                        label=f"Skin: {d['name']} ✨",
                        value=key,
                        description="Yields 10 Rolls",
                        emoji="🎨",
                    )
                )
        super().__init__(
            placeholder="Select up to 20 items to fuse...",
            min_values=1,
            max_values=min(len(options), 20),
            options=options,
            row=0,
        )

    async def callback(self, interaction):
        u_data = database.get_user_data(self.view.user_id)
        u_dict = dict(u_data)
        limit_rem = 20 - u_dict["daily_fusions"]
        if len(self.values) > limit_rem:
            return await interaction.response.send_message(
                f"❌ You can only fuse {limit_rem} more items today!",
                ephemeral=True,
            )

        total_rolls = 0
        selected_items = []
        for key in self.values:
            item = self.data_map[key]
            selected_items.append(item)
            if item["type"] == "gear":
                base = utils.calculate_fusion_rolls(item["data"])
                total_rolls += base * 2 if item["resonant"] else base
            else:
                total_rolls += 10

        desc = f"Sacrificing **{len(selected_items)} items**.\n**Chaos Rolls: {total_rolls}** 🎲\n\n**Probabilities per Roll:**\n"
        desc += f"{config.CHAOS_CORE_EMOJI} **Core:** 30% | {config.CHAOS_CORE_EMOJI} **Kit:** 15%\n"
        desc += f"{config.CHAOS_SHARD_EMOJI} **Shards:** 20% | {config.MERCH_TOKEN_EMOJI} **Tokens:** 10%\n"
        desc += "💨 **Nothing:** 25%\n"

        embed = discord.Embed(
            title="⚠️ Confirm Fusion", description=desc, color=0xE74C3C
        )
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=FusionConfirmView(
                self.view.bot, self.view.user_id, selected_items, total_rolls
            ),
        )


class FusionConfirmView(View):
    def __init__(self, bot, user_id, items, rolls):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.items = items
        self.rolls = rolls

    @discord.ui.button(label="Confirm Fusion", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        button.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{config.CHAOS_CRACK_EMOJI} **FUSING...**",
                color=0xF1C40F,
            ),
            view=None,
        )
        await asyncio.sleep(2)

        for item in self.items:
            if item["type"] == "gear":
                database.delete_inventory_item(item["data"]["instance_id"])
            else:
                database.remove_user_skin(self.user_id, item["data"])

        rewards = utils.generate_fusion_rewards(self.rolls, self.user_id)
        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)

        database.update_user_stats(
            self.user_id,
            {
                "chaos_cores": u_dict["chaos_cores"] + rewards["cores"],
                "chaos_kits": u_dict["chaos_kits"] + rewards["kits"],
                "chaos_shards": u_dict["chaos_shards"] + rewards["shards"],
                "merch_tokens": u_dict["merch_tokens"] + rewards["tokens"],
                "daily_fusions": u_dict["daily_fusions"] + len(self.items),
            },
        )

        embed_pub = discord.Embed(title="♻️ Fusion Complete!", color=0x2ECC71)
        res = []
        if rewards["cores"]:
            res.append(f"{config.CHAOS_CORE_EMOJI} **{rewards['cores']}** Cores")
        if rewards["kits"]:
            res.append(f"{config.CHAOS_CORE_EMOJI} **{rewards['kits']}** Kits")
        if rewards["shards"]:
            res.append(f"{config.CHAOS_SHARD_EMOJI} **{rewards['shards']}** Shards")
        if rewards["tokens"]:
            res.append(f"{config.MERCH_TOKEN_EMOJI} **{rewards['tokens']}** Tokens")

        embed_pub.description = (
            f"**{interaction.user.name}** sacrificed {len(self.items)} items for {self.rolls} rolls.\n\n"
            + ("\n".join(res) if res else "*The Chaos yielded nothing.*")
        )

        await interaction.channel.send(embed=embed_pub)
        try:
            await interaction.delete_original_response()
        except:
            pass


class InspectModeButton(Button):
    def __init__(self, current_page_items):
        super().__init__(
            label="Inspect",
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            row=4,
        )
        self.items = current_page_items

    async def callback(self, interaction):
        if not self.items:
            return await interaction.response.send_message(
                "No items visible.", ephemeral=True
            )
        await interaction.response.send_message(
            "Select item to inspect:",
            view=InspectSelectView(self.view.bot, self.items),
            ephemeral=True,
        )


class InspectSelectView(View):
    def __init__(self, bot, items):
        super().__init__(timeout=60)
        self.bot = bot
        self.add_item(InspectSelect(items, bot))


class InspectSelect(Select):
    def __init__(self, items, bot):
        options = []
        for i in items:
            d = game_data.get_item(i["id"])
            mod = f"[{i['mod']}] " if i["mod"] != "Standard" else ""
            options.append(
                discord.SelectOption(
                    label=f"Lvl {i['lvl']} {mod}{d['name']}",
                    value=str(i["inst"]),
                    emoji=utils.safe_emoji(utils.get_emoji(bot, i["id"])),
                )
            )
        super().__init__(placeholder="Choose item...", options=options)

    async def callback(self, interaction):
        iid = int(self.values[0])
        view = DetailedInspectView(self.view.bot, interaction.user.id, iid)
        await interaction.response.edit_message(
            embed=view.get_embed(), view=view, content=None
        )


class DetailedInspectView(View):
    def __init__(self, bot, user_id, instance_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id
        self.instance_id = instance_id
        self.item_row = None
        self.update_view()

    def update_view(self):
        self.item_row = database.get_item_instance(self.instance_id)
        self.clear_items()
        if not self.item_row:
            self.add_item(Button(label="Item Gone", disabled=True))
        else:
            self.add_item(LockToggleButton(bool(self.item_row["locked"])))
            self.add_item(CloseButton())

    def get_embed(self):
        if not self.item_row:
            return discord.Embed(title="Item not found", color=0xE74C3C)

        i = self.item_row
        d = game_data.get_item(i["item_id"])
        colors = {
            "Common": 0x95A5A6,
            "Rare": 0x3498DB,
            "Epic": 0x9B59B6,
            "Legendary": 0xF1C40F,
        }
        icon = utils.get_emoji(self.bot, i["item_id"], self.user_id)
        mod = f"[{i['modifier']}] " if i["modifier"] != "Standard" else ""
        title = f"{'🔒 ' if i['locked'] else ''}{icon} {mod}{d['name']}"

        embed = discord.Embed(
            title=title, color=colors.get(d.get("rarity", "Common"), 0x95A5A6)
        )
        if d.get("quote"):
            embed.description = f"*\"{d['quote']}\"*"

        lvl = i["level"]
        gp = utils.get_item_gp(i["item_id"], lvl)

        if d["type"] == "ride":
            embed.add_field(name="Rarity", value=d.get("rarity", "Common"), inline=True)
        else:
            embed.add_field(name="Level", value=str(lvl), inline=True)
            embed.add_field(
                name="Power",
                value=f"{config.GEAR_POWER_EMOJI} {gp:,}",
                inline=True,
            )
            stats_desc, _ = utils.get_item_stats(i["item_id"], lvl)
            embed.add_field(name="📊 Stats", value=stats_desc, inline=False)

        mod_desc = MODIFIER_DESCRIPTIONS.get(i["modifier"], "Unknown modifier.")
        embed.add_field(name=f"Modifier: {i['modifier']}", value=mod_desc, inline=False)

        if d["type"] == "weapon":
            embed.add_field(
                name="Attack",
                value=d.get("main_attack", "Attack"),
                inline=False,
            )
            embed.add_field(
                name="Combo",
                value=d.get("combo_attack", "Combo"),
                inline=False,
            )

        embed.set_footer(text=f"ID: {i['instance_id']}")
        return embed


class LockToggleButton(Button):
    def __init__(self, is_locked):
        super().__init__(
            label="Unlock" if is_locked else "Lock",
            style=(
                discord.ButtonStyle.success
                if is_locked
                else discord.ButtonStyle.secondary
            ),
            emoji="🔓" if is_locked else "🔒",
        )
        self.is_locked = is_locked

    async def callback(self, interaction):
        database.toggle_item_lock(self.view.instance_id, not self.is_locked)
        self.is_locked = not self.is_locked
        self.view.update_view()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class CloseButton(Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.secondary)

    async def callback(self, i):
        await i.response.edit_message(content="[Closed]", embed=None, view=None)


class OpenDashboard(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_id = user_id
        u_data = database.get_user_data(user_id)
        u_dict = dict(u_data)
        self.cores, self.kits = u_dict["chaos_cores"], u_dict["chaos_kits"]
        self.player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        c_btn = Button(
            label=f"Open Cores ({self.cores})",
            style=discord.ButtonStyle.primary,
            emoji=discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
        )
        if self.cores > 0:
            c_btn.callback = self.open_cores_callback
        else:
            c_btn.disabled = True
        self.add_item(c_btn)

        k_btn = Button(
            label=f"Use Kits ({self.kits})",
            style=discord.ButtonStyle.success,
            emoji=discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
        )
        if self.kits > 0:
            k_btn.callback = self.use_kits_callback
        else:
            k_btn.disabled = True
        self.add_item(k_btn)

    async def open_cores_callback(self, interaction):

        await interaction.response.send_modal(
            CoreOpenModal(self.bot, self.user_id, self.cores, self.player_lvl)
        )

    async def use_kits_callback(self, interaction):

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.bot.get_cog("Inventory").prompt_kit_usage(interaction)


class CoreOpenModal(Modal):
    def __init__(self, bot, user_id, total, lvl):
        super().__init__(title="Open Chaos Cores")
        self.bot = bot
        self.user_id = user_id
        self.total = total
        self.lvl = lvl
        self.amount = TextInput(
            label=f"How many? (Max {total})", placeholder="1", required=True
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction):
        try:
            amt = int(self.amount.value)
        except:
            return await interaction.response.send_message(
                "Invalid number.", ephemeral=True
            )

        if amt <= 0:
            return await interaction.response.send_message(
                "Invalid amount.", ephemeral=True
            )

        u_data = database.get_user_data(self.user_id)
        u_dict = dict(u_data)
        if u_dict["chaos_cores"] < amt:
            return await interaction.response.send_message(
                f"❌ You only have {u_dict['chaos_cores']} cores left!",
                ephemeral=True,
            )

        database.update_user_stats(
            self.user_id, {"chaos_cores": u_dict["chaos_cores"] - amt}
        )
        is_elite = bool(u_dict.get("is_elite"))

        loot = [
            {"type": "new" if random.random() < 0.3 else "upgrade"} for _ in range(amt)
        ]

        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"{config.CHAOS_CORE_EMOJI} Opening {amt} Chaos Cores...",
                color=0x9B59B6,
            ),
            view=LootRevealView(
                self.bot,
                interaction.user,
                loot,
                self.lvl,
                self.lvl,
                is_elite,
                0,
            ),
            ephemeral=True,
        )


class ChaosKitView(View):
    def __init__(self, bot, user_id, options):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.add_item(ChaosKitSelect(options))


class ChaosKitSelect(Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Select item to upgrade...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return

        self.disabled = True
        await interaction.response.edit_message(view=self.view)

        p = self.values[0].split(":")
        iid, boost = int(p[0]), int(p[1])
        u_data = database.get_user_data(self.view.user_id)
        u_dict = dict(u_data)

        if u_dict["chaos_kits"] < 1:
            return await interaction.followup.send("No Kits!", ephemeral=True)

        old = database.get_item_instance(iid)
        new_lvl = old["level"] + boost
        database.update_user_stats(
            self.view.user_id, {"chaos_kits": u_dict["chaos_kits"] - 1}
        )

        with database.get_connection() as c:
            c.execute(
                "UPDATE inventory SET level = ? WHERE instance_id = ?",
                (new_lvl, iid),
            )
            c.commit()

        pedia.track_upgrade(self.view.user_id, old["item_id"], new_lvl)
        pedia.track_archive(self.view.user_id, "Kit", old["item_id"], "Upgrade")

        await interaction.followup.send(
            embed=discord.Embed(
                description=f"{config.CHAOS_CRACK_EMOJI} **CRACK!**",
                color=0xF1C40F,
            ),
            ephemeral=True,
        )
        await asyncio.sleep(0.8)

        stats_diff = utils.get_stat_diff(old["item_id"], old["level"], new_lvl)

        e = discord.Embed(
            title=game_data.get_item(old["item_id"])["name"].upper(),
            color=0x9B59B6,
            description=f"{utils.get_emoji(self.view.bot, old['item_id'])} *Channeling resonant energy...*",
        )
        e.add_field(
            name="LEVEL",
            value=f"**{old['level']}** ➔ **{new_lvl}** `+{boost}`",
            inline=True,
        )
        e.add_field(name="STATS", value=stats_diff, inline=False)

        await interaction.followup.send(embed=e, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Inventory(bot))

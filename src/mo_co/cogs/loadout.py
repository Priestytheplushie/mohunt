import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from mo_co import database, game_data, utils, config
import json


class Loadout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def generate_kit_embed(self, user_id, user_name):
        database.register_user(user_id)
        database.ensure_user_has_kit(user_id)

        user_data, active_kit, inv_map = database.get_full_user_context(user_id)

        if not active_kit:
            return discord.Embed(
                title="Error",
                description="No active kit found. Please create a new kit.",
                color=0xE74C3C,
            )

        total_gp = utils.get_total_gp(user_id, kit_cache=active_kit, inv_cache=inv_map)

        kit_name = active_kit["name"]
        embed = discord.Embed(
            title=f"{user_name}'s {kit_name}",
            description=f"{config.GEAR_POWER_EMOJI} **Gear Power:** {total_gp:,}",
            color=0xE67E22,
        )

        def render_slot(inst_id, skin_id, empty_key, label_fallback):
            if not inst_id or inst_id == 0:
                emoji = (
                    config.EMPTY_RIDE
                    if empty_key == "empty_ride"
                    else utils.get_emoji(self.bot, empty_key)
                )
                return f"{emoji} *{label_fallback}*"

            item = inv_map.get(inst_id)
            if not item:
                return "Unknown"

            item_id, mod, level = (
                item["item_id"],
                item["modifier"],
                item["level"],
            )
            item_def = game_data.get_item(item_id)
            gp = utils.get_item_gp(item_id, level)

            if skin_id:
                icon = utils.get_emoji(self.bot, skin_id)
            else:
                icon = utils.get_emoji(self.bot, item_id)

            mod_str = "" if mod == "Standard" else f"[{mod}] "

            skin_txt = ""
            if skin_id:
                s_def = game_data.get_item(skin_id)
                skin_txt = f" (🎨 {s_def['name']})"

            return f"{icon} **Lvl {level} {mod_str}{item_def['name']}**{skin_txt} ({config.GEAR_POWER_EMOJI} {gp:,})"

        embed.add_field(
            name=f"{utils.get_emoji(self.bot, 'empty_weapon')} Weapon",
            value=render_slot(
                active_kit["weapon_id"],
                active_kit["weapon_skin"],
                "empty_weapon",
                "No Weapon",
            ),
            inline=False,
        )

        gadget_lines = [
            render_slot(
                active_kit[f"gadget_{i}_id"],
                active_kit[f"gadget_{i}_skin"],
                "empty_gadget",
                "Empty",
            )
            for i in range(1, 4)
        ]
        embed.add_field(
            name=f"{utils.get_emoji(self.bot, 'empty_gadget')} Gadgets",
            value="\n".join(gadget_lines),
            inline=True,
        )

        passive_lines = [
            render_slot(active_kit[f"passive_{i}_id"], None, "empty_passive", "Empty")
            for i in range(1, 4)
        ]
        embed.add_field(
            name=f"{utils.get_emoji(self.bot, 'empty_passive')} Passives",
            value="\n".join(passive_lines),
            inline=True,
        )

        embed.add_field(
            name=f"{config.EMPTY_RIDE} Ride",
            value=render_slot(
                active_kit["ride_id"],
                active_kit["ride_skin"],
                "empty_ride",
                "No Ride",
            ),
            inline=True,
        )
        embed.add_field(
            name=f"{utils.get_emoji(self.bot, 'empty_module')} Module",
            value=render_slot(
                active_kit["elite_module_id"],
                None,
                "empty_module",
                "No Module",
            ),
            inline=True,
        )

        ring_lines = [
            render_slot(active_kit[f"ring_{i}_id"], None, "empty_ring", "Empty")
            for i in range(1, 4)
        ]
        embed.add_field(
            name=f"{utils.get_emoji(self.bot, 'empty_ring')} Rings",
            value="\n".join(ring_lines),
            inline=False,
        )

        return embed

    @app_commands.command(name="kit", description="View loadout")
    async def view_kit(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        database.register_user(interaction.user.id, interaction.user.display_name)
        database.ensure_user_has_kit(interaction.user.id)

        embed = self.generate_kit_embed(
            interaction.user.id, interaction.user.display_name
        )
        view = KitMainView(self.bot, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class KitMainView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=120)
        self.bot = bot
        self.user_id = user_id

        self.add_item(KitSelector(bot, user_id))

        self.add_item(EditLoadoutButton())
        self.add_item(SkinsButton())

        kits = database.get_all_kits(user_id)
        if len(kits) > 1:
            self.add_item(DeleteKitButton())


class KitSelector(discord.ui.Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        self.user_id = user_id

        kits = database.get_all_kits(user_id)
        u_data = database.get_user_data(user_id)
        active_idx = u_data["active_kit_index"]

        options = []
        seen_indices = set()

        for kit in kits:
            idx = kit["slot_index"]

            if idx in seen_indices:
                continue
            seen_indices.add(idx)

            name = kit["name"]

            w_id = kit["weapon_id"]
            if w_id:
                item = database.get_item_instance(w_id)

                if kit["weapon_skin"]:
                    icon_str = utils.get_emoji(bot, kit["weapon_skin"])
                else:
                    icon_str = utils.get_emoji(bot, item["item_id"]) if item else "📦"
            else:
                icon_str = "📦"

            emoji = (
                discord.PartialEmoji.from_str(icon_str)
                if icon_str.startswith("<")
                else discord.PartialEmoji(name=icon_str)
            )

            count = 0
            for k in kit.keys():
                if k.endswith("_id") and kit[k]:
                    count += 1

            desc = "Active Kit" if idx == active_idx else f"{count} Items Equipped"

            options.append(
                discord.SelectOption(
                    label=name,
                    value=f"kit_{idx}",
                    description=desc,
                    emoji=emoji,
                    default=(idx == active_idx),
                )
            )

        if len(kits) < 12:
            options.append(
                discord.SelectOption(
                    label="Create New Kit",
                    value="create",
                    description="Start fresh with an empty kit",
                    emoji="➕",
                )
            )

        if not options:
            options.append(discord.SelectOption(label="Error: No Kits", value="error"))

        super().__init__(
            placeholder="Select Gear Kit...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        val = self.values[0]

        if val == "create":
            success = database.create_new_kit(self.user_id)
            if not success:
                return await interaction.response.send_message(
                    "Max kits reached!", ephemeral=True
                )

            new_embed = self.view.bot.get_cog("Loadout").generate_kit_embed(
                self.user_id, interaction.user.name
            )
            new_view = KitMainView(self.view.bot, self.user_id)
            await interaction.response.edit_message(embed=new_embed, view=new_view)
        elif val == "error":
            await interaction.response.send_message(
                "Kit data error. Please report to admin.", ephemeral=True
            )
        else:
            idx = int(val.split("_")[1])
            database.update_user_stats(self.user_id, {"active_kit_index": idx})
            new_embed = self.view.bot.get_cog("Loadout").generate_kit_embed(
                self.user_id, interaction.user.name
            )
            new_view = KitMainView(self.view.bot, self.user_id)
            await interaction.response.edit_message(embed=new_embed, view=new_view)


class EditLoadoutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Edit Slots",
            style=discord.ButtonStyle.primary,
            emoji="🛠️",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        await interaction.response.edit_message(
            view=KitSlotSelectView(self.view.bot, self.view.user_id)
        )


class SkinsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Skins",
            style=discord.ButtonStyle.secondary,
            emoji="🎨",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        await interaction.response.edit_message(
            view=SkinSlotSelectView(self.view.bot, self.view.user_id)
        )


class DeleteKitButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Delete", style=discord.ButtonStyle.danger, emoji="🗑️", row=1
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.view.user_id:
            return

        active_kit = database.get_active_kit(self.view.user_id)
        modal = DeleteKitConfirmModal(
            self.view.bot,
            self.view.user_id,
            active_kit["slot_index"],
            active_kit["name"],
        )

        await interaction.response.send_modal(modal)


class DeleteKitConfirmModal(Modal):
    def __init__(self, bot, user_id, slot_index, kit_name):
        super().__init__(title=f"Delete {kit_name}?")
        self.bot = bot
        self.user_id = user_id
        self.slot_index = slot_index
        self.confirm = TextInput(
            label="Type 'DELETE' to confirm",
            placeholder="DELETE",
            min_length=6,
            max_length=6,
            required=True,
        )
        self.add_item(self.confirm)

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm.value.upper() != "DELETE":
            return await interaction.response.send_message(
                "Deletion cancelled.", ephemeral=True
            )

        success, msg = database.delete_gear_kit(self.user_id, self.slot_index)

        if success:
            embed = self.bot.get_cog("Loadout").generate_kit_embed(
                self.user_id, interaction.user.name
            )
            view = KitMainView(self.bot, self.user_id)
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)


class KitSlotSelectView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.add_item(SlotSelect(bot))
        self.add_item(BackButton(KitMainView))


class SlotSelect(discord.ui.Select):
    def __init__(self, bot):
        def pe(k):
            e = utils.get_emoji(bot, k)
            return discord.PartialEmoji.from_str(e) if e.startswith("<") else None

        options = [
            discord.SelectOption(
                label="Weapon", value="weapon", emoji=pe("empty_weapon")
            ),
            discord.SelectOption(
                label="Ride",
                value="ride",
                emoji=discord.PartialEmoji.from_str(config.EMPTY_RIDE),
            ),
            discord.SelectOption(
                label="Module", value="elite_module", emoji=pe("empty_module")
            ),
            discord.SelectOption(
                label="Gadget 1", value="gadget_1", emoji=pe("empty_gadget")
            ),
            discord.SelectOption(
                label="Gadget 2", value="gadget_2", emoji=pe("empty_gadget")
            ),
            discord.SelectOption(
                label="Gadget 3", value="gadget_3", emoji=pe("empty_gadget")
            ),
            discord.SelectOption(
                label="Passive 1", value="passive_1", emoji=pe("empty_passive")
            ),
            discord.SelectOption(
                label="Passive 2", value="passive_2", emoji=pe("empty_passive")
            ),
            discord.SelectOption(
                label="Passive 3", value="passive_3", emoji=pe("empty_passive")
            ),
            discord.SelectOption(
                label="Ring 1", value="ring_1", emoji=pe("empty_ring")
            ),
            discord.SelectOption(
                label="Ring 2", value="ring_2", emoji=pe("empty_ring")
            ),
            discord.SelectOption(
                label="Ring 3", value="ring_3", emoji=pe("empty_ring")
            ),
        ]
        super().__init__(placeholder="Select slot to equip...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        slot = self.values[0]
        if "weapon" in slot:
            t_filter = "weapon"
        elif "gadget" in slot:
            t_filter = "gadget"
        elif "passive" in slot:
            t_filter = "passive"
        elif "ring" in slot:
            t_filter = "smart_ring"
        elif "ride" in slot:
            t_filter = "ride"
        else:
            t_filter = "elite_module"

        inventory = database.get_user_inventory(interaction.user.id)
        compatible_items = sorted(
            [
                r
                for r in inventory
                if game_data.get_item(r["item_id"])["type"] == t_filter
            ],
            key=lambda x: x["level"],
            reverse=True,
        )
        if compatible_items:
            await interaction.response.edit_message(
                view=KitItemSelectView(
                    self.view.bot, self.view.user_id, slot, compatible_items
                )
            )
        else:
            await interaction.response.send_message(
                f"No items of type {t_filter} found!", ephemeral=True
            )


class KitItemSelectView(discord.ui.View):
    def __init__(self, bot, user_id, slot, items):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.slot = slot
        self.items = items
        self.page = 0
        self.items_per_page = 25
        self.update_components()

    def update_components(self):
        self.clear_items()
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        chunk = self.items[start:end]

        options = []
        for r in chunk:
            item_def = game_data.get_item(r["item_id"])
            mod_str = "" if r["modifier"] == "Standard" else f"[{r['modifier']}] "
            emoji_str = utils.get_emoji(self.bot, r["item_id"])
            emoji = (
                discord.PartialEmoji.from_str(emoji_str)
                if emoji_str.startswith("<")
                else None
            )
            label = f"Lvl {r['level']} {mod_str}{item_def['name']}"
            if len(label) > 100:
                label = label[:97] + "..."
            options.append(
                discord.SelectOption(
                    label=label, value=str(r["instance_id"]), emoji=emoji
                )
            )

        sel = discord.ui.Select(
            placeholder=f"Equip item (Page {self.page+1})",
            options=options,
            row=0,
        )
        sel.callback = self.item_callback
        self.add_item(sel)

        max_page = (len(self.items) - 1) // self.items_per_page
        if max_page > 0:
            if self.page > 0:
                prev_btn = Button(
                    label="Previous",
                    style=discord.ButtonStyle.secondary,
                    row=1,
                )
                prev_btn.callback = self.prev_page
                self.add_item(prev_btn)
            if self.page < max_page:
                next_btn = Button(
                    label="Next", style=discord.ButtonStyle.secondary, row=1
                )
                next_btn.callback = self.next_page
                self.add_item(next_btn)

        self.add_item(UnequipButton(self.slot))
        self.add_item(BackButton(KitSlotSelectView))

    async def prev_page(self, interaction):
        self.page -= 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction):
        self.page += 1
        self.update_components()
        await interaction.response.edit_message(view=self)

    async def item_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        iid = int(self.children[0].values[0])

        col_name = self.slot if self.slot.endswith("_id") else f"{self.slot}_id"
        database.update_active_kit(interaction.user.id, {col_name: iid})

        embed = self.bot.get_cog("Loadout").generate_kit_embed(
            interaction.user.id, interaction.user.name
        )
        await interaction.response.edit_message(
            embed=embed, view=KitMainView(self.bot, self.user_id)
        )


class UnequipButton(discord.ui.Button):
    def __init__(self, slot):
        super().__init__(label="Unequip Slot", style=discord.ButtonStyle.danger, row=2)
        self.slot = slot

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        col_name = self.slot if self.slot.endswith("_id") else f"{self.slot}_id"

        database.update_active_kit(interaction.user.id, {col_name: None})

        embed = self.view.bot.get_cog("Loadout").generate_kit_embed(
            interaction.user.id, interaction.user.name
        )
        await interaction.response.edit_message(
            embed=embed, view=KitMainView(self.view.bot, self.view.user_id)
        )


class BackButton(discord.ui.Button):
    def __init__(self, target_view_cls):
        super().__init__(
            label="Back",
            style=discord.ButtonStyle.secondary,
            emoji="🔙",
            row=2,
        )
        self.target_view_cls = target_view_cls

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        await interaction.response.edit_message(
            view=self.target_view_cls(self.view.bot, self.view.user_id)
        )


class SkinSlotSelectView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id

        kit = database.get_active_kit(user_id)

        options = []
        if kit:
            for key in [
                "weapon_id",
                "gadget_1_id",
                "gadget_2_id",
                "gadget_3_id",
                "ride_id",
            ]:
                inst_id = kit[key]
                if inst_id:
                    item = database.get_item_instance(inst_id)
                    if item:
                        d = game_data.get_item(item["item_id"])
                        label = f"{key.split('_')[0].title()}: {d['name']}"
                        emoji = utils.safe_emoji(utils.get_emoji(bot, item["item_id"]))

                        options.append(
                            discord.SelectOption(
                                label=label,
                                value=f"{key}|{item['item_id']}",
                                emoji=emoji,
                            )
                        )

        if not options:
            self.add_item(Button(label="No skinnable items equipped", disabled=True))
        else:
            self.add_item(SkinItemSelect(bot, user_id, options))

        self.add_item(BackButton(KitMainView))


class SkinItemSelect(Select):
    def __init__(self, bot, user_id, options):
        super().__init__(placeholder="Select item to skin...", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):

        parts = self.values[0].split("|")
        slot_col = parts[0]
        base_item_id = parts[1]

        skin_col = slot_col.replace("_id", "_skin")

        u = database.get_user_data(self.user_id)
        owned = json.loads(u["owned_skins"])
        compatible = [
            s for s in owned if game_data.get_item(s).get("base_item") == base_item_id
        ]

        if not compatible:
            return await interaction.response.send_message(
                "You don't own any skins for this item!", ephemeral=True
            )

        view = View()
        opts = []
        for skin_id in compatible:
            d = game_data.get_item(skin_id)
            opts.append(discord.SelectOption(label=d["name"], value=skin_id))

        async def skin_cb(i):
            sid = select.values[0]
            database.update_active_kit(self.user_id, {skin_col: sid})

            embed = self.bot.get_cog("Loadout").generate_kit_embed(
                self.user_id, i.user.display_name
            )
            await i.response.edit_message(
                embed=embed, view=KitMainView(self.bot, self.user_id)
            )

        select = Select(placeholder="Choose skin...", options=opts)
        select.callback = skin_cb
        view.add_item(select)

        async def remove_cb(i):
            database.update_active_kit(self.user_id, {skin_col: None})
            embed = self.bot.get_cog("Loadout").generate_kit_embed(
                self.user_id, i.user.display_name
            )
            await i.response.edit_message(
                embed=embed, view=KitMainView(self.bot, self.user_id)
            )

        rem_btn = Button(label="Remove Skin", style=discord.ButtonStyle.danger)
        rem_btn.callback = remove_cb
        view.add_item(rem_btn)

        await interaction.response.send_message(
            "Select Skin:", view=view, ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Loadout(bot))

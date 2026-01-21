import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from mo_co import database, game_data, config, utils
from datetime import datetime
import asyncio


MIN_TRADE_LEVEL = 12
TAX_RATE_TOKENS = 0.05
TAX_RATE_GOLD = 0.00


class Trading(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="trade", description="Trade an item for currency")
    @app_commands.describe(user="The buyer")
    async def trade(self, interaction: discord.Interaction, user: discord.User):

        if user.id == interaction.user.id:
            return await interaction.response.send_message(
                "❌ You cannot trade with yourself.", ephemeral=True
            )
        if user.bot:
            return await interaction.response.send_message(
                "❌ You cannot trade with bots.", ephemeral=True
            )

        database.register_user(interaction.user.id)
        database.register_user(user.id)

        u_seller = database.get_user_data(interaction.user.id)
        u_buyer = database.get_user_data(user.id)

        lvl_seller, _, _ = utils.get_level_info(u_seller["xp"])
        lvl_buyer, _, _ = utils.get_level_info(u_buyer["xp"])

        if lvl_seller < MIN_TRADE_LEVEL:
            return await interaction.response.send_message(
                f"🚫 **Trading Locked.** You must be Hunter Level {MIN_TRADE_LEVEL} to trade.",
                ephemeral=True,
            )
        if lvl_buyer < MIN_TRADE_LEVEL:
            return await interaction.response.send_message(
                f"🚫 **Trading Locked.** {user.name} must be Hunter Level {MIN_TRADE_LEVEL} to trade.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="🤝 Trade Setup",
            description=f"Selling to **{user.name}**.\nSelect an item category to view your sellable items.",
            color=0xF1C40F,
        )
        embed.set_footer(text="Only unlocked and unequipped items are shown.")

        view = TradeSetupView(self.bot, interaction.user, user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class TradeSetupView(View):
    def __init__(self, bot, seller, buyer):
        super().__init__(timeout=120)
        self.bot = bot
        self.seller = seller
        self.buyer = buyer

        categories = [
            ("Weapons", "weapon", "empty_weapon"),
            ("Gadgets", "gadget", "empty_gadget"),
            ("Passives", "passive", "empty_passive"),
            ("Modules", "elite_module", "empty_module"),
            ("Rings", "smart_ring", "empty_ring"),
        ]

        for label, type_key, emoji_key in categories:
            self.add_item(CategoryButton(label, type_key, emoji_key))


class CategoryButton(Button):
    def __init__(self, label, type_key, emoji_key):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=0)
        self.type_key = type_key
        self.emoji_key = emoji_key

    async def callback(self, interaction: discord.Interaction):

        u_data = database.get_user_data(interaction.user.id)
        is_elite = bool(u_data.get("is_elite", 0))

        if self.type_key in ["elite_module", "smart_ring"] and not is_elite:
            return await interaction.response.send_message(
                "🚫 **Elite Restricted.** You must be an Elite Hunter to trade Modules and Rings.",
                ephemeral=True,
            )

        self.emoji = utils.safe_emoji(utils.get_emoji(self.view.bot, self.emoji_key))

        inv = database.get_user_inventory(interaction.user.id)

        eligible = []
        for row in inv:
            if row["locked"]:
                continue

            d = game_data.get_item(row["item_id"])
            if d["type"] == self.type_key:

                if row["modifier"] == "Elite" and not is_elite:
                    continue
                eligible.append(row)

        if not eligible:
            return await interaction.response.send_message(
                f"No tradeable {self.label} found.", ephemeral=True
            )

        eligible.sort(key=lambda x: x["level"], reverse=True)
        top_25 = eligible[:25]

        view = ItemSelectionView(
            self.view.bot, self.view.seller, self.view.buyer, top_25
        )
        await interaction.response.edit_message(
            embed=None, content="Select the item to sell:", view=view
        )


class ItemSelectionView(View):
    def __init__(self, bot, seller, buyer, items):
        super().__init__(timeout=120)
        self.bot = bot
        self.seller = seller
        self.buyer = buyer
        self.add_item(ItemSelect(items, bot))


class ItemSelect(Select):
    def __init__(self, items, bot):
        options = []
        for r in items:
            d = game_data.get_item(r["item_id"])
            mod_str = f"[{r['modifier']}] " if r["modifier"] != "Standard" else ""
            label = f"Lvl {r['level']} {mod_str}{d['name']}"

            if len(label) > 100:
                label = label[:97] + "..."

            options.append(
                discord.SelectOption(
                    label=label,
                    value=str(r["instance_id"]),
                    emoji=utils.safe_emoji(utils.get_emoji(bot, r["item_id"])),
                )
            )

        super().__init__(placeholder="Choose item to sell...", options=options)

    async def callback(self, interaction: discord.Interaction):
        instance_id = int(self.values[0])
        await interaction.response.send_modal(
            TradePriceModal(
                self.view.bot, self.view.seller, self.view.buyer, instance_id
            )
        )


class TradePriceModal(Modal):
    def __init__(self, bot, seller, buyer, instance_id):
        super().__init__(title="Set Trade Price")
        self.bot = bot
        self.seller = seller
        self.buyer = buyer
        self.instance_id = instance_id

        self.amount = TextInput(
            label="Amount", placeholder="1000", min_length=1, max_length=9
        )
        self.currency = TextInput(
            label="Currency (gold/tokens)",
            placeholder="gold",
            min_length=3,
            max_length=6,
        )

        self.add_item(self.amount)
        self.add_item(self.currency)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.amount.value)
            if price <= 0:
                raise ValueError
        except:
            return await interaction.response.send_message(
                "❌ Invalid amount.", ephemeral=True
            )

        curr_input = self.currency.value.lower().strip()
        if "gold" in curr_input or "mo" in curr_input:
            currency_type = "mo_gold"
            currency_emoji = config.MOGOLD_EMOJI
            tax_rate = TAX_RATE_GOLD
        elif "token" in curr_input or "merch" in curr_input:
            currency_type = "merch_tokens"
            currency_emoji = config.MERCH_TOKEN_EMOJI
            tax_rate = TAX_RATE_TOKENS
        else:
            return await interaction.response.send_message(
                "❌ Invalid currency. Use 'gold' or 'tokens'.", ephemeral=True
            )

        item_row = database.get_item_instance(self.instance_id)
        if not item_row or item_row["user_id"] != self.seller.id:
            return await interaction.response.send_message(
                "❌ Item no longer valid.", ephemeral=True
            )

        d = game_data.get_item(item_row["item_id"])
        is_elite_item = (d["type"] in ["elite_module", "smart_ring"]) or (
            item_row["modifier"] == "Elite"
        )

        if is_elite_item:
            buyer_data = database.get_user_data(self.buyer.id)
            if not bool(buyer_data.get("is_elite", 0)):
                return await interaction.response.send_message(
                    f"🚫 **Trade Locked.** {self.buyer.name} is not an Elite Hunter and cannot receive Elite items.",
                    ephemeral=True,
                )

        embed = self.create_contract_embed(
            item_row, price, currency_type, currency_emoji, tax_rate
        )

        view = ActiveTradeView(
            self.bot,
            self.seller,
            self.buyer,
            item_row,
            price,
            currency_type,
            tax_rate,
        )

        await interaction.response.send_message(
            f"{self.buyer.mention}, you have a trade offer!",
            embed=embed,
            view=view,
        )

    def create_contract_embed(
        self, item_row, price, currency_type, currency_emoji, tax_rate
    ):
        d = game_data.get_item(item_row["item_id"])

        stats_text, _ = utils.get_item_stats(item_row["item_id"], item_row["level"])

        tax_amt = int(price * tax_rate)
        seller_receives = price - tax_amt

        embed = discord.Embed(title="🤝 Trade Offer", color=0x3498DB)
        embed.set_thumbnail(
            url=f"https://cdn.discordapp.com/emojis/{utils.get_emoji(self.bot, item_row['item_id']).split(':')[2].replace('>', '')}.png"
        )

        embed.add_field(name="Seller", value=self.seller.name, inline=True)
        embed.add_field(name="Buyer", value=self.buyer.name, inline=True)

        mod_str = (
            f"**[{item_row['modifier']}]** "
            if item_row["modifier"] != "Standard"
            else ""
        )
        item_name = f"{mod_str}{d['name']}"

        embed.add_field(
            name="Item Offered",
            value=f"{utils.get_emoji(self.bot, item_row['item_id'])} {item_name}",
            inline=False,
        )
        embed.add_field(
            name="Power Level",
            value=f"Lvl **{item_row['level']}** | {config.GEAR_POWER_EMOJI} **{utils.get_item_gp(item_row['item_id'], item_row['level']):,}**",
            inline=False,
        )
        embed.add_field(name="Stats", value=stats_text, inline=False)

        cost_str = f"{currency_emoji} **{price:,}**"
        if tax_amt > 0:
            cost_str += f"\n(Tax: {currency_emoji} {tax_amt:,} ➔ Seller gets {currency_emoji} {seller_receives:,})"

        embed.add_field(name="Cost", value=cost_str, inline=False)

        buyer_data = database.get_user_data(self.buyer.id)
        b_lvl, _, _ = utils.get_level_info(buyer_data["xp"])
        if b_lvl < item_row["level"]:
            embed.add_field(
                name="⚠️ Level Gap Warning",
                value=f"This item is **Level {item_row['level']}**. You are **Level {b_lvl}**.\nYou may not be able to equip/utilize its full power yet.",
                inline=False,
            )

        return embed


class ActiveTradeView(View):
    def __init__(self, bot, seller, buyer, item_row, price, currency_type, tax_rate):
        super().__init__(timeout=300)
        self.bot = bot
        self.seller = seller
        self.buyer = buyer
        self.item_row = item_row
        self.price = price
        self.currency_type = currency_type
        self.tax_rate = tax_rate
        self.instance_id = item_row["instance_id"]

    @discord.ui.button(
        label="Accept Offer", style=discord.ButtonStyle.success, emoji="✅"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.buyer.id:
            return await interaction.response.send_message(
                "This isn't your trade!", ephemeral=True
            )

        conn = database.get_connection()
        try:
            cur = conn.cursor()

            check_item = cur.execute(
                "SELECT user_id, locked FROM inventory WHERE instance_id=?",
                (self.instance_id,),
            ).fetchone()
            if not check_item:
                return await interaction.response.send_message(
                    "❌ Item no longer exists.", ephemeral=True
                )
            if check_item["user_id"] != self.seller.id:
                return await interaction.response.send_message(
                    "❌ Seller no longer owns this item.", ephemeral=True
                )
            if check_item["locked"]:
                return await interaction.response.send_message(
                    "❌ Item is locked and cannot be traded.", ephemeral=True
                )

            buyer_funds = cur.execute(
                f"SELECT {self.currency_type} FROM users WHERE user_id=?",
                (self.buyer.id,),
            ).fetchone()
            if not buyer_funds or buyer_funds[0] < self.price:
                return await interaction.response.send_message(
                    f"❌ You don't have enough {self.currency_type.replace('_', '.').title()}!",
                    ephemeral=True,
                )

            tax_amt = int(self.price * self.tax_rate)
            seller_amt = self.price - tax_amt

            cur.execute(
                f"UPDATE users SET {self.currency_type} = {self.currency_type} - ? WHERE user_id = ?",
                (self.price, self.buyer.id),
            )

            cur.execute(
                f"UPDATE users SET {self.currency_type} = {self.currency_type} + ? WHERE user_id = ?",
                (seller_amt, self.seller.id),
            )

            cur.execute(
                "UPDATE inventory SET user_id = ? WHERE instance_id = ?",
                (self.buyer.id, self.instance_id),
            )

            conn.commit()

            database.unequip_from_all_slots(self.seller.id, self.instance_id)

            for child in self.children:
                child.disabled = True

            currency_emoji = (
                config.MOGOLD_EMOJI
                if self.currency_type == "mo_gold"
                else config.MERCH_TOKEN_EMOJI
            )

            embed = discord.Embed(title="✅ Trade Complete", color=0x2ECC71)
            embed.description = f"**{self.buyer.name}** paid {currency_emoji} **{self.price:,}** for the item."
            if tax_amt > 0:
                embed.set_footer(text=f"Bureau Tax Collected: {tax_amt:,}")

            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            print(f"Trade Error: {e}")
            await interaction.response.send_message(
                "❌ Transaction failed due to a database error.",
                ephemeral=True,
            )
        finally:
            conn.close()

    @discord.ui.button(label="Inspect", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def inspect(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        item_def = game_data.get_item(self.item_row["item_id"])

        stats, raw_val = utils.get_item_stats(
            self.item_row["item_id"], self.item_row["level"]
        )

        embed = discord.Embed(
            title=f"🔍 Inspection: {item_def['name']}", color=0x95A5A6
        )
        embed.description = f"**Level:** {self.item_row['level']}\n**Modifier:** {self.item_row['modifier']}\n\n**Stats:**\n{stats}"
        if item_def.get("quote"):
            embed.set_footer(text=f"\"{item_def['quote']}\"")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.seller.id, self.buyer.id]:
            return await interaction.response.send_message(
                "You cannot cancel this trade.", ephemeral=True
            )

        await interaction.response.edit_message(
            content="❌ Trade Cancelled.", embed=None, view=None
        )


async def setup(bot):
    await bot.add_cog(Trading(bot))

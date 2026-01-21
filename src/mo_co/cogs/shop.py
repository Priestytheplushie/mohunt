import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import json
import random
import asyncio
from datetime import datetime, timedelta
from mo_co import database, config, game_data, utils


from mo_co.game_data.missions import MISSIONS
from mo_co import pedia


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_maintenance_loop.start()

    def cog_unload(self):
        self.shop_maintenance_loop.cancel()

    async def check_new_player_redirect(self, interaction):
        u_data = database.get_user_data(interaction.user.id)
        try:
            m_state = json.loads(u_data["mission_state"])
            active_id = m_state.get("active")

            if isinstance(active_id, list):
                active_id = active_id[0] if active_id else None

            if active_id == "welcome2moco" and "welcome2moco" not in m_state.get(
                "completed", []
            ):
                embed = discord.Embed(
                    title="⛔ Access Locked",
                    description="Finish your onboarding first!",
                    color=0xE74C3C,
                )
                from mo_co.cogs.missions import PhoneDashboardView

                view = PhoneDashboardView(self.bot, interaction.user.id, m_state)
                await interaction.response.send_message(
                    embed=embed, view=view, ephemeral=True
                )
                return True
        except:
            pass
        return False

    @app_commands.command(name="shop", description="Open Manny's mo.co Shop")
    async def shop(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)

        if await self.check_new_player_redirect(interaction):
            return

        self.check_shop_refresh()
        view = ShopView(self.bot, interaction.user)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )

    def check_shop_refresh(self):
        state = database.get_shop_state()
        last = datetime.fromisoformat(state["last_refresh_date"]).date()
        now = datetime.now().date()
        if now > last:
            new_seed = random.randint(1, 999999)
            database.update_shop_seed(new_seed, now.isoformat())

    @tasks.loop(minutes=10)
    async def shop_maintenance_loop(self):
        """Maintains the Deals tab by removing expired deals and filling empty slots."""
        database.prune_expired_deals()

        deals = database.get_active_deals()
        target_count = 4

        if len(deals) < target_count:
            needed = target_count - len(deals)
            for _ in range(needed):
                self.generate_random_deal()

    @shop_maintenance_loop.before_loop
    async def before_shop_loop(self):
        await self.bot.wait_until_ready()

    def generate_random_deal(self):

        roll = random.random()

        if roll < 0.20:
            self._create_bundle_deal()
        elif roll < 0.50:
            self._create_cosmetic_deal()
        elif roll < 0.80:
            self._create_gear_deal()
        else:
            self._create_ring_deal()

    def _create_bundle_deal(self):

        options = [
            ("chaos_cores", "Chaos Cores", 3, 200, "merch_tokens"),
            ("chaos_kits", "Chaos Kits", 2, 250, "merch_tokens"),
            ("chaos_shards", "Shard Pack", 50, 500, "mo_gold"),
        ]
        choice = random.choice(options)
        iid, name, qty, price, currency = choice
        duration = random.choice([4, 6, 8])
        expiry = (datetime.utcnow() + timedelta(hours=duration)).isoformat()

        discount = random.uniform(0.7, 0.9)
        final_price = int(price * discount)

        database.add_deal(
            "currency",
            iid,
            "gold" if currency == "mo_gold" else "tokens",
            final_price,
            f"{qty}x {name} ({int((1-discount)*100)}% OFF)",
            expiry,
        )

    def _create_cosmetic_deal(self):

        if random.random() < 0.7:
            skins = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "skin"]
            if not skins:
                return
            target = random.choice(skins)
            price = 150
            duration = 24
        else:
            titles = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "title"]
            if not titles:
                return
            target = random.choice(titles)
            price = 100
            duration = 24

        expiry = (datetime.utcnow() + timedelta(hours=duration)).isoformat()
        database.add_deal(
            game_data.get_item(target)["type"],
            target,
            "gold",
            price,
            "Direct Purchase",
            expiry,
        )

    def _create_gear_deal(self):

        pool = [
            k
            for k, v in game_data.ALL_ITEMS.items()
            if v["type"] in ["weapon", "gadget"]
        ]
        target = random.choice(pool)

        mod = random.choice(["Overcharged", "Megacharged", "Toxic", "Chaos"])
        duration = random.choice([12, 24])
        price = 800
        if mod == "Megacharged":
            price = 1500
        elif mod == "Overcharged":
            price = 1000

        expiry = (datetime.utcnow() + timedelta(hours=duration)).isoformat()
        database.add_deal(
            "item_mod",
            f"{target}:{mod}",
            "tokens",
            price,
            f"{mod} Special",
            expiry,
        )

    def _create_ring_deal(self):

        is_major = random.random() < 0.30
        prefix = "Major" if is_major else "Minor"

        pool = [
            k
            for k, v in game_data.ALL_ITEMS.items()
            if v["type"] == "smart_ring" and prefix in v["name"]
        ]

        if not pool:
            pool = [
                k
                for k, v in game_data.ALL_ITEMS.items()
                if v["type"] == "smart_ring" and "insane" not in k
            ]

        if not pool:
            return

        target = random.choice(pool)
        price = 1200 if is_major else 400
        duration = random.choice([8, 12])

        expiry = (datetime.utcnow() + timedelta(hours=duration)).isoformat()
        database.add_deal(
            "item", target, "tokens", price, f"{prefix} Ring Offer", expiry
        )


class ShopView(View):
    def __init__(self, bot, user):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.user_id = user.id
        self.tab = "deals"
        self.u_data = database.get_user_data(user.id)
        self.shop_state = database.get_shop_state()
        self.generate_daily_gear()
        self.update_components()

    def generate_daily_gear(self):
        random.seed(self.shop_state["daily_seed"])
        pl, _, _ = utils.get_level_info(self.u_data["xp"])
        discount_slots = random.sample(range(6), 2)
        discount_amounts = {
            discount_slots[0]: random.choice([0.10, 0.15, 0.20, 0.25]),
            discount_slots[1]: random.choice([0.10, 0.15, 0.20, 0.25]),
        }
        daily_items = []
        types = ["weapon", "gadget", "passive"]
        for i in range(6):
            t = random.choice(types)
            pool = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == t]
            if not pool:
                continue
            item_id = random.choice(pool)
            roll = random.random()
            rarity = "Common"
            mod = "Standard"
            cost = 125
            if roll < 0.60:
                pass
            elif roll < 0.90:
                rarity = "Rare"
                cost = 250
            else:
                rarity = "Epic"
                cost = 500
            if random.random() < 0.20:
                m_roll = random.random()
                if m_roll < 0.60:
                    mod = "Toxic"
                    cost += 50
                elif m_roll < 0.90:
                    mod = "Overcharged"
                    cost += 100
                else:
                    mod = "Megacharged"
                    cost += 200
            final_cost = cost
            discount_label = ""
            if i in discount_slots:
                pct = discount_amounts[i]
                final_cost = int(cost * (1 - pct))
                discount_label = f" ~~{cost}~~ ({int(pct*100)}% OFF)"
            daily_items.append(
                {
                    "id": item_id,
                    "mod": mod,
                    "cost": final_cost,
                    "slot": i,
                    "discount_label": discount_label,
                }
            )
        random.seed()
        self.daily_items_cache = daily_items

    def is_visible_deal(self, deal):
        """Checks if a deal should be visible to the current user."""
        if deal["item_type"] == "item":
            item = game_data.get_item(deal["item_id"])
            if item and item.get("type") == "smart_ring":

                try:
                    elite_xp = self.u_data["elite_xp"] or 0
                    elite_tokens = self.u_data["elite_tokens"] or 0
                    return (elite_xp > 0) or (elite_tokens > 0)
                except (IndexError, KeyError):
                    return False
        return True

    def get_embed(self):
        embed = discord.Embed(color=0xF1C40F)
        embed.set_author(
            name="Manny's mo.co Shop",
            icon_url="https://cdn.discordapp.com/emojis/1455320328518762686.png",
        )
        gold = self.u_data["mo_gold"]
        tokens = self.u_data["merch_tokens"]
        embed.description = f"{config.MOGOLD_EMOJI} **{gold:,}** | {config.MERCH_TOKEN_EMOJI} **{tokens:,}**\n\n"

        if self.tab == "deals":
            embed.title = f"{config.MOGOLD_EMOJI} Special Deals"
            deals = database.get_active_deals()
            if deals:
                for idx, d in enumerate(deals):
                    if not self.is_visible_deal(d):
                        continue

                    name = "Unknown"
                    if d["item_type"] == "currency":
                        name = d["item_id"].replace("_", " ").title()
                        if d["item_id"] == "chaos_shards":
                            name = "Chaos Shards"
                        elif d["item_id"] == "chaos_cores":
                            name = "Chaos Cores"
                        elif d["item_id"] == "chaos_kits":
                            name = "Chaos Kits"
                    elif (
                        d["item_type"] == "item"
                        or d["item_type"] == "skin"
                        or d["item_type"] == "title"
                    ):
                        name = game_data.get_item(d["item_id"])["name"]
                    elif d["item_type"] == "item_mod":
                        parts = d["item_id"].split(":")
                        i_name = game_data.get_item(parts[0])["name"]
                        name = f"{parts[1]} {i_name}"

                    price_icon = (
                        config.MOGOLD_EMOJI
                        if d["price_type"] == "gold"
                        else config.MERCH_TOKEN_EMOJI
                    )

                    ts = int(
                        datetime.fromisoformat(d["expiration_timestamp"]).timestamp()
                    )
                    exp_str = f" • Ends <t:{ts}:R>"

                    offer_desc = f"*{d['offer_name']}*" if d["offer_name"] else ""
                    val = f"{offer_desc}\n{price_icon} **{d['price_amount']}**{exp_str}"
                    embed.add_field(name=f"#{idx+1} {name}", value=val, inline=True)
            else:
                embed.description += "*Restocking... Check back soon!*"

            inv = database.get_user_inventory(self.user.id)
            dice = next((i for i in inv if i["item_id"] == "bunch_of_dice"), None)
            if not dice:
                embed.add_field(
                    name=f"{config.BUNCH_OF_DICE_EMOJI} Bunch of Dice (Passive)",
                    value=f"*Increases Luck! Check /inspect!*\n{config.MOGOLD_EMOJI} **100**",
                    inline=False,
                )
            else:
                lvl = dice["level"]
                if lvl < 50:
                    cost = int(100 * (1.15**lvl))
                    embed.add_field(
                        name=f"{config.BUNCH_OF_DICE_EMOJI} Upgrade Dice (Lvl {lvl} ➔ {lvl+1})",
                        value=f"*Better odds! Check /inventory stats.*\n{config.MOGOLD_EMOJI} **{cost:,}**",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name=f"{config.BUNCH_OF_DICE_EMOJI} Bunch of Dice (Maxed)",
                        value="**MAX LEVEL**",
                        inline=False,
                    )

        elif self.tab == "merch":
            embed.title = f"{config.MOGOLD_EMOJI} Merch Drops"
            end_ts = int(datetime(2026, 3, 1).timestamp())
            embed.description += f"**Classic Collection** (Ends <t:{end_ts}:D>)\n*Collect skins and titles! No duplicates.*"
            crate_id = config.MOGOLD_CRATE_EMOJI.split(":")[2].replace(">", "")
            embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{crate_id}.png")
            owned_skins = json.loads(self.u_data["owned_skins"])
            owned_titles = json.loads(self.u_data["owned_titles"])
            box_items = game_data.CLASSIC_COLLECTION_BOX
            collected = 0
            total = len(box_items)

            available_items = []
            total_weight = 0.0
            for item_id in box_items:
                is_owned = (
                    ("OG Crew" in owned_titles)
                    if item_id == "og_crew_title"
                    else (item_id in owned_skins)
                )
                if not is_owned:
                    weight = 30
                    if item_id == "og_crew_title":
                        weight = 10
                    else:
                        r = game_data.get_item(item_id).get("rarity", "Common")
                        if r == "Common":
                            weight = 60
                        elif r == "Epic":
                            weight = 10
                        elif r == "Legendary":
                            weight = 5
                    total_weight += weight
                    available_items.append((item_id, weight))
                else:
                    collected += 1

            skin_map = {
                "turbo_pills": config.TURBO_PILLS_EMOJI,
                "golden_boombox": config.GOLDEN_BOOMBOX_EMOJI,
                "golden_fireworks": config.GOLDEN_FIREWORKS_EMOJI,
                "golden_taser": config.GOLDEN_TASER_EMOJI,
                "classic_snow_globe": config.CLASSIC_SNOW_GLOBE_EMOJI,
                "classic_shelldon": config.CLASSIC_SHELLDON_EMOJI,
                "classic_really_cool_sticker": config.CLASSIC_STICKER_EMOJI,
                "classic_lifejacket": config.CLASSIC_LIFEJACKET_EMOJI,
                "og_crew_title": "👑",
            }
            lines = []
            for item_id in box_items:
                is_owned = (
                    ("OG Crew" in owned_titles)
                    if item_id == "og_crew_title"
                    else (item_id in owned_skins)
                )
                name = (
                    "OG Crew Title"
                    if item_id == "og_crew_title"
                    else game_data.get_item(item_id)["name"]
                )
                rarity = (
                    "Epic"
                    if item_id == "og_crew_title"
                    else game_data.get_item(item_id).get("rarity", "Common")
                )
                check = "✅" if is_owned else "⬜"
                if is_owned:
                    lines.append(f"{check} {skin_map.get(item_id, '🎁')} **{name}**")
                else:
                    weight = next((w for i, w in available_items if i == item_id), 0)
                    chance = (weight / total_weight * 100) if total_weight > 0 else 0
                    lines.append(
                        f"{check} {skin_map.get(item_id, '🎁')} **{name}** ({rarity}) - `{chance:.1f}%`"
                    )
            embed.add_field(
                name=f"Collection Progress ({collected}/{total})",
                value="\n".join(lines),
                inline=False,
            )
            if collected >= total:
                embed.add_field(
                    name="💧 Bonus Reward",
                    value=f"{config.WATER_BALLOON_EMOJI} Water Balloon Skin\n{'✅ Claimed' if 'water_balloon' in owned_skins else '**READY TO CLAIM**'}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Pull",
                    value=f"{config.MOGOLD_EMOJI} **50** per pull",
                    inline=False,
                )

        elif self.tab == "gear":
            embed.title = "⚙️ Daily Gear"
            now = datetime.utcnow()
            refresh_ts = int(
                datetime.combine(
                    now.date() + timedelta(days=1), datetime.min.time()
                ).timestamp()
            )
            embed.description += f"Refreshes daily. Scaled to your level.\n**Refreshes** <t:{refresh_ts}:R>"
            pl, _, _ = utils.get_level_info(self.u_data["xp"])
            daily_purchases = json.loads(self.u_data["daily_purchases"])

            for item in self.daily_items_cache:
                i_def = game_data.get_item(item["id"])
                icon = utils.get_emoji(self.bot, item["id"])
                mod_str = f"[{item['mod']}] " if item["mod"] != "Standard" else ""

                if item["slot"] in daily_purchases:
                    embed.add_field(
                        name=f"#{item['slot']+1} [SOLD OUT]",
                        value=f"~~{mod_str}{i_def['name']}~~",
                        inline=True,
                    )
                else:
                    embed.add_field(
                        name=f"#{item['slot']+1} {icon} {mod_str}{i_def['name']}",
                        value=f"Lvl {pl} | {config.MERCH_TOKEN_EMOJI} **{item['cost']}**{item['discount_label']}",
                        inline=True,
                    )

        elif self.tab == "chaos":
            embed.title, embed.description = (
                f"{config.CHAOS_CORE_EMOJI} Chaos Exchange",
                embed.description + "Trade Merch Tokens for Chaos resources.",
            )
            embed.add_field(
                name="Chaos Core",
                value=f"{config.MERCH_TOKEN_EMOJI} **100**",
                inline=True,
            )
            embed.add_field(
                name="Chaos Kit",
                value=f"{config.MERCH_TOKEN_EMOJI} **150**",
                inline=True,
            )
        return embed

    def update_components(self):
        self.clear_items()
        daily_purchases = json.loads(self.u_data["daily_purchases"])
        self.add_item(
            NavButton(
                "Deals",
                "deals",
                discord.PartialEmoji.from_str(config.MOGOLD_EMOJI),
                self.tab == "deals",
            )
        )
        self.add_item(
            NavButton(
                "Merch",
                "merch",
                discord.PartialEmoji.from_str(config.GOLDEN_BOOMBOX_EMOJI),
                self.tab == "merch",
            )
        )
        gear_str = utils.get_emoji(self.bot, "monster_slugger")
        gear_emoji = (
            discord.PartialEmoji.from_str(gear_str) if gear_str.startswith("<") else "⚙️"
        )
        self.add_item(NavButton("Gear", "gear", gear_emoji, self.tab == "gear"))
        self.add_item(
            NavButton(
                "Chaos",
                "chaos",
                discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                self.tab == "chaos",
            )
        )

        if self.tab == "deals":
            deals = database.get_active_deals()

            # Filter and track buttons to prevent overflow
            visible_deals = []
            for d in deals:
                if self.is_visible_deal(d):
                    visible_deals.append(d)

            button_count = 0
            for idx, d in enumerate(
                deals
            ):  # Use original index for consistency with embed
                if self.is_visible_deal(d):
                    # Calculate row: starting at row 2, each row holds 5 items.
                    target_row = 2 + (button_count // 5)
                    if (
                        target_row <= 3
                    ):  # Keep within valid Discord rows (0-4 used for nav/dice)
                        self.add_item(BuyDealButton(idx, d, row=target_row))
                        button_count += 1

            self.add_item(BuyDiceButton())

        elif self.tab == "merch":
            owned_skins = json.loads(self.u_data["owned_skins"])
            owned_titles = json.loads(self.u_data["owned_titles"])
            box = game_data.CLASSIC_COLLECTION_BOX
            collected = sum(
                1
                for i in box
                if (
                    i in owned_skins
                    or (i == "og_crew_title" and "OG Crew" in owned_titles)
                )
            )
            if collected < len(box):
                self.add_item(PullMerchButton())
            elif "water_balloon" not in owned_skins:
                self.add_item(ClaimBonusButton())
            else:
                self.add_item(
                    Button(
                        label="Completed",
                        disabled=True,
                        style=discord.ButtonStyle.success,
                    )
                )
        elif self.tab == "gear":
            for i, item in enumerate(self.daily_items_cache):
                row = 1 if i < 3 else 2
                is_sold = item["slot"] in daily_purchases
                self.add_item(BuyGearButton(self.bot, item, row, is_sold))
        elif self.tab == "chaos":
            self.add_item(BuyChaosButton("core", 100))
            self.add_item(BuyChaosButton("kit", 150))


class NavButton(Button):
    def __init__(self, label, tab, emoji, active):
        super().__init__(
            label=label,
            emoji=emoji,
            style=(
                discord.ButtonStyle.primary if active else discord.ButtonStyle.secondary
            ),
            row=0,
        )
        self.tab = tab

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        self.view.tab = self.tab
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class BuyDiceButton(Button):
    def __init__(self):
        super().__init__(
            label="Buy/Upgrade Dice",
            emoji=discord.PartialEmoji.from_str(config.BUNCH_OF_DICE_EMOJI),
            style=discord.ButtonStyle.success,
            row=1,
        )

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        inv = database.get_user_inventory(self.view.user.id)
        dice = next((i for i in inv if i["item_id"] == "bunch_of_dice"), None)
        u = database.get_user_data(self.view.user.id)
        lvl = 1
        cost = 100
        if dice:
            lvl = dice["level"]
            cost = int(100 * (1.15**lvl))
        if u["mo_gold"] < cost:
            return await interaction.response.send_message(
                "Not enough Gold!", ephemeral=True
            )
        database.update_user_stats(self.view.user.id, {"mo_gold": u["mo_gold"] - cost})
        if not dice:
            database.add_item_to_inventory(
                self.view.user.id, "bunch_of_dice", "Standard", 1
            )
            msg = "🎲 **Acquired Bunch of Dice!**"
        else:
            database.upgrade_item_level(dice["instance_id"], 999, 1)
            msg = f"🎲 **Upgraded Dice to Level {lvl+1}!**"
        self.view.u_data = database.get_user_data(self.view.user.id)
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(msg, ephemeral=True)


class PullMerchButton(Button):
    def __init__(self):
        super().__init__(
            label="Pull (50 Gold)", style=discord.ButtonStyle.primary, row=1
        )

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        u = database.get_user_data(self.view.user.id)
        if u["mo_gold"] < 50:
            return await interaction.response.send_message(
                "Not enough Gold!", ephemeral=True
            )
        await interaction.response.edit_message(
            embed=discord.Embed(
                description=f"{config.CHAOS_CRACK_EMOJI} **OPENING CRATE...**",
                color=0xF1C40F,
            ),
            view=None,
        )
        await asyncio.sleep(2)
        owned_skins = json.loads(u["owned_skins"])
        owned_titles = json.loads(u["owned_titles"])
        box = game_data.CLASSIC_COLLECTION_BOX
        available = [
            i
            for i in box
            if (i != "og_crew_title" and i not in owned_skins)
            or (i == "og_crew_title" and "OG Crew" not in owned_titles)
        ]
        if not available:
            return
        weights = [
            (
                10
                if i == "og_crew_title"
                else {"Common": 60, "Epic": 10, "Legendary": 5}.get(
                    game_data.get_item(i).get("rarity", "Common"), 30
                )
            )
            for i in available
        ]
        chosen = random.choices(available, weights=weights, k=1)[0]
        database.update_user_stats(self.view.user.id, {"mo_gold": u["mo_gold"] - 50})
        if chosen == "og_crew_title":
            owned_titles.append("OG Crew")
            database.update_user_stats(
                self.view.user_id, {"owned_titles": json.dumps(owned_titles)}
            )
            name = "Title: OG Crew"
        else:
            owned_skins.append(chosen)
            database.update_user_stats(
                self.view.user_id, {"owned_skins": json.dumps(owned_skins)}
            )
            name = game_data.get_item(chosen)["name"]
            pedia.track_skin(self.view.user.id, chosen)

        try:
            m_state = json.loads(u["mission_state"])
            if m_state.get("active"):

                active_list = m_state["active"]
                if isinstance(active_list, list):
                    active_list = active_list[0] if active_list else None

                if active_list:
                    m_def = MISSIONS.get(active_list)
                    m_data = m_state["states"].get(active_list, {})
                    step = m_def["steps"][m_data.get("step", 0)]
                    if step["type"] == "objective_buy_skin":
                        thread_id = u["mission_thread_id"]
                        if thread_id:
                            from mo_co.mission_engine import MissionEngine

                            engine = MissionEngine(
                                self.view.bot, self.view.user.id, thread_id
                            )
                            asyncio.create_task(engine.progress())
        except:
            pass

        self.view.u_data = database.get_user_data(self.view.user.id)
        self.view.update_components()
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=self.view.get_embed(),
            view=self.view,
        )
        await interaction.followup.send(f"🎉 **Pulled: {name}**!", ephemeral=True)


class ClaimBonusButton(Button):
    def __init__(self):
        super().__init__(
            label="Claim Bonus Skin", style=discord.ButtonStyle.success, row=1
        )

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        u = database.get_user_data(self.view.user.id)
        owned_skins = json.loads(u["owned_skins"])
        owned_skins.append("water_balloon")
        database.update_user_stats(
            self.view.user.id, {"owned_skins": json.dumps(owned_skins)}
        )
        self.view.u_data = database.get_user_data(self.view.user.id)
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(
            f"💧 **Bonus Acquired: Water Balloon!**", ephemeral=True
        )


class BuyGearButton(Button):
    def __init__(self, bot, item_data, row, is_sold):
        label = "SOLD OUT" if is_sold else f"#{item_data['slot']+1}"
        style = discord.ButtonStyle.danger if is_sold else discord.ButtonStyle.secondary
        super().__init__(
            label=label,
            emoji=utils.safe_emoji(utils.get_emoji(bot, item_data["id"])),
            style=style,
            row=row,
            disabled=is_sold,
        )
        self.item_data = item_data

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        u = database.get_user_data(self.view.user.id)
        if u["merch_tokens"] < self.item_data["cost"]:
            return await interaction.response.send_message(
                "Not enough Tokens!", ephemeral=True
            )
        pl, _, _ = utils.get_level_info(u["xp"])
        purchases = json.loads(u["daily_purchases"])
        purchases.append(self.item_data["slot"])
        database.update_user_stats(
            self.view.user.id,
            {
                "merch_tokens": u["merch_tokens"] - self.item_data["cost"],
                "daily_purchases": json.dumps(purchases),
            },
        )
        database.add_item_to_inventory(
            self.view.user.id, self.item_data["id"], self.item_data["mod"], pl
        )

        pedia.track_gear(
            self.view.user.id,
            self.item_data["id"],
            self.item_data["mod"],
            source="shop",
        )

        self.view.u_data = database.get_user_data(self.view.user.id)
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(
            f"✅ Bought **{self.item_data['id']}**!", ephemeral=True
        )


class BuyChaosButton(Button):
    def __init__(self, type_str, cost):
        super().__init__(
            label=f"Buy {type_str.title()} ({cost})",
            style=discord.ButtonStyle.primary,
            row=1,
        )
        self.type_str, self.cost = type_str, cost

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        u = database.get_user_data(self.view.user.id)
        if u["merch_tokens"] < self.cost:
            return await interaction.response.send_message(
                "Not enough Tokens!", ephemeral=True
            )
        upd = {"merch_tokens": u["merch_tokens"] - self.cost}
        if self.type_str == "core":
            upd["chaos_cores"] = u["chaos_cores"] + 1
        else:
            upd["chaos_kits"] = u["chaos_kits"] + 1
        database.update_user_stats(self.view.user.id, upd)
        self.view.u_data = database.get_user_data(self.view.user.id)
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(
            f"✅ Bought 1 {self.type_str.title()}!", ephemeral=True
        )


class BuyDealButton(Button):
    def __init__(self, idx, deal, row=2):
        super().__init__(
            label=f"Buy #{idx+1}", style=discord.ButtonStyle.success, row=row
        )
        self.deal = deal

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        u = database.get_user_data(self.view.user.id)
        cost, ptype = self.deal["price_amount"], self.deal["price_type"]
        bal = u["mo_gold"] if ptype == "gold" else u["merch_tokens"]
        if bal < cost:
            return await interaction.response.send_message(
                f"Not enough {ptype}!", ephemeral=True
            )

        database.update_user_stats(
            self.view.user.id,
            {("mo_gold" if ptype == "gold" else "merch_tokens"): bal - cost},
        )

        it, iid = self.deal["item_type"], self.deal["item_id"]
        msg = ""

        if it == "item":
            lvl = utils.get_level_info(u["xp"])[0]
            database.add_item_to_inventory(self.view.user.id, iid, "Standard", lvl)
            pedia.track_gear(self.view.user.id, iid, "Standard", source="shop")
            msg = f"**{game_data.get_item(iid)['name']}**"
        elif it == "item_mod":
            parts = iid.split(":")
            lvl = utils.get_level_info(u["xp"])[0]
            database.add_item_to_inventory(self.view.user.id, parts[0], parts[1], lvl)
            pedia.track_gear(self.view.user.id, parts[0], parts[1], source="shop")
            msg = f"**{parts[1]} {game_data.get_item(parts[0])['name']}**"
        elif it == "skin":
            o = json.loads(u["owned_skins"])
            o.append(iid) if iid not in o else None
            database.update_user_stats(
                self.view.user.id, {"owned_skins": json.dumps(o)}
            )
            pedia.track_skin(self.view.user.id, iid)
            msg = f"Skin: **{game_data.get_item(iid)['name']}**"
        elif it == "title":
            t = json.loads(u["owned_titles"])
            t_name = game_data.get_item(iid)["name"]
            if t_name not in t:
                t.append(t_name)
            database.update_user_stats(
                self.view.user.id, {"owned_titles": json.dumps(t)}
            )
            msg = f"Title: **{t_name}**"
        elif it == "currency":
            import re

            match = re.match(r"(\d+)x", self.deal["offer_name"])
            qty = int(match.group(1)) if match else 1

            current_val = u[iid]
            database.update_user_stats(self.view.user.id, {iid: current_val + qty})
            msg = f"**{qty}x {iid.replace('_', ' ').title()}**"

        self.view.u_data = database.get_user_data(self.view.user.id)
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(f"✅ Bought {msg}!", ephemeral=True)

    def create_buy_callback(self, item, cost):
        async def cb(i: discord.Interaction):
            if i.user.id != self.user_id:
                return

            u = database.get_user_data(i.user.id)
            if u["elite_tokens"] < cost:
                return await i.response.send_message(
                    "Not enough Tokens!", ephemeral=True
                )

            database.update_user_stats(
                i.user.id, {"elite_tokens": u["elite_tokens"] - cost}
            )
            msg = ""

            if item["type"] == "rotating":
                current_rot, _ = database.get_elite_rotation(
                    list(game_data.ALL_ITEMS.keys())
                )
                e_lvl, _, _ = utils.get_elite_level_info(u["elite_xp"])
                target_lvl = max(1, e_lvl)
                database.add_item_to_inventory(
                    self.user_id, current_rot, "Elite", target_lvl
                )
                pedia.track_gear(self.user_id, current_rot, "Elite", source="shop")
                msg = f"✅ Purchased **[Elite] {game_data.get_item(current_rot)['name']}**!"
            elif item["type"] == "consumable_ring":
                pool = [
                    k
                    for k, v in game_data.ALL_ITEMS.items()
                    if v["type"] == "smart_ring"
                ]
                if pool:
                    rid = random.choice(pool)
                    database.add_item_to_inventory(self.user.id, rid, "Standard", 1)
                    pedia.track_gear(self.user.id, rid, "Standard", source="shop")
                    msg = f"💍 Acquired **{game_data.get_item(rid)['name']}**!"
            elif item["type"] in ["elite_module", "passive"]:
                inv = database.get_user_inventory(self.user.id)
                target = next((r for r in inv if r["item_id"] == item["id"]), None)
                if target:
                    database.upgrade_item_level(target["instance_id"], 999, 1)
                    pedia.track_upgrade(self.user.id, item["id"], target["level"] + 1)
                    msg = f"🆙 Upgraded **{item['name']}**!"
                else:
                    database.add_item_to_inventory(
                        self.user.id, item["id"], "Standard", 1
                    )
                    pedia.track_gear(
                        self.user.id, item["id"], "Standard", source="shop"
                    )
                    msg = f"✅ Acquired **{item['name']}**!"
            elif item["type"] == "consumable_xp":
                database.update_user_stats(
                    self.user_id,
                    {"daily_xp_boosted": u["daily_xp_boosted"] + 10000},
                )
                msg = "✅ **XP Booster Activated!**"
            elif item["type"] == "consumable_gold":
                database.update_user_stats(self.user.id, {"mo_gold": u["mo_gold"] + 10})
                msg = "✅ **Acquired 10 mo.gold!**"

            await i.response.edit_message(embed=self.get_embed(), view=self)
            await i.followup.send(msg, ephemeral=True)

        return cb


async def setup(bot):
    await bot.add_cog(Shop(bot))

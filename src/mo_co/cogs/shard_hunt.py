import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
import datetime
import random
from mo_co import database, config, game_data, utils

TIERS_PER_PAGE = 5
MAIN_TIERS_MAX = 40
BONUS_CYCLE_LENGTH = 120


class ShardHunt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="shards", description="Open the Shard Hunt Pass")
    async def shards(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)

        level, _, _ = utils.get_level_info(u_data["xp"])
        if level < 12:
            return await interaction.response.send_message(
                "🚫 **Shard Hunt unlocks at Hunter Level 12!**", ephemeral=True
            )

        from mo_co import season_manager

        season_manager.init_season()
        season_manager.check_user_season_reset(interaction.user.id)

        view = ShardPassView(self.bot, interaction.user.id)
        await interaction.response.send_message(embed=view.get_embed(), view=view)


class ShardPassView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id

        u_data = database.get_user_data(user_id)
        self.claimed = u_data["season_tier_claimed"]

        if self.claimed >= MAIN_TIERS_MAX:
            self.mode = "bonus"
            self.page = 0
        else:
            self.mode = "main"
            self.page = self.claimed // TIERS_PER_PAGE

        self.season = database.get_active_season()
        self.premium_items = json.loads(self.season["premium_items"])
        self.free_items = json.loads(self.season["free_items"])

        self.update_components()

    def get_reward_info(self, tier):
        info = {
            "text": "---",
            "emoji": None,
            "type": "none",
            "is_premium": False,
            "item_id": None,
        }

        if self.season["type"] == "XP_Rush":
            info.update(
                {
                    "text": "2000 XP",
                    "emoji": discord.PartialEmoji.from_str(config.XP_EMOJI),
                    "type": "xp",
                }
            )
            return info

        is_chaos_season = self.season["type"] == "Chaos"

        if tier > MAIN_TIERS_MAX:
            b_cycle = (tier - MAIN_TIERS_MAX - 1) % 4
            if b_cycle == 0:
                if is_chaos_season:
                    info.update(
                        {
                            "text": "Chaos Core",
                            "emoji": discord.PartialEmoji.from_str(
                                config.CHAOS_CORE_EMOJI
                            ),
                            "type": "core",
                        }
                    )
                else:
                    info.update(
                        {
                            "text": "8 Mo.Gold",
                            "emoji": discord.PartialEmoji.from_str(config.MOGOLD_EMOJI),
                            "type": "gold",
                        }
                    )
            elif b_cycle == 1:
                if is_chaos_season:
                    info.update(
                        {
                            "text": "Chaos Kit",
                            "emoji": discord.PartialEmoji.from_str(
                                config.CHAOS_CORE_EMOJI
                            ),
                            "type": "kit",
                        }
                    )
                else:
                    info.update(
                        {
                            "text": "2000 XP",
                            "emoji": discord.PartialEmoji.from_str(config.XP_EMOJI),
                            "type": "xp",
                        }
                    )
            elif b_cycle == 2:

                info.update(
                    {
                        "text": "Chaos Grab Bag",
                        "emoji": discord.PartialEmoji.from_str(
                            config.CHAOS_CRACK_EMOJI
                        ),
                        "type": "random",
                    }
                )
            elif b_cycle == 3:
                info.update(
                    {
                        "text": "8 Merch Tokens",
                        "emoji": discord.PartialEmoji.from_str(
                            config.MERCH_TOKEN_EMOJI
                        ),
                        "type": "token",
                    }
                )
            return info

        cycle_idx = (tier - 1) % 9 + 1

        if cycle_idx == 1:
            item_idx = (tier - 1) // 9
            if item_idx < len(self.premium_items):
                iid = self.premium_items[item_idx]
                d = game_data.get_item(iid)
                e_str = utils.get_emoji(self.bot, iid)
                info.update(
                    {
                        "text": d["name"],
                        "emoji": discord.PartialEmoji.from_str(e_str),
                        "type": "item",
                        "item_id": iid,
                    }
                )
            else:
                info.update(
                    {
                        "text": "Chaos Grab Bag",
                        "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                        "type": "random",
                    }
                )
            info["is_premium"] = True

        elif cycle_idx == 5:
            item_idx = (tier - 1) // 9
            if item_idx < len(self.free_items):
                iid = self.free_items[item_idx]
                d = game_data.get_item(iid)
                e_str = utils.get_emoji(self.bot, iid)
                info.update(
                    {
                        "text": d["name"],
                        "emoji": discord.PartialEmoji.from_str(e_str),
                        "type": "item",
                        "item_id": iid,
                    }
                )
            else:
                info.update(
                    {
                        "text": "Chaos Grab Bag",
                        "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                        "type": "random",
                    }
                )

        elif cycle_idx in [2, 8]:
            if is_chaos_season:
                info.update(
                    {
                        "text": "Chaos Core",
                        "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                        "type": "core",
                    }
                )
            else:
                info.update(
                    {
                        "text": "2000 XP",
                        "emoji": discord.PartialEmoji.from_str(config.XP_EMOJI),
                        "type": "xp",
                    }
                )

        elif cycle_idx in [3, 9]:
            info.update(
                {
                    "text": "Chaos Kit",
                    "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                    "type": "kit",
                }
            )

        elif cycle_idx == 4:
            if is_chaos_season:
                info.update(
                    {
                        "text": "Chaos Core",
                        "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                        "type": "core",
                    }
                )
            else:
                info.update(
                    {
                        "text": "8 Mo.Gold",
                        "emoji": discord.PartialEmoji.from_str(config.MOGOLD_EMOJI),
                        "type": "gold",
                    }
                )

        elif cycle_idx == 7:
            if is_chaos_season:
                info.update(
                    {
                        "text": "Chaos Core",
                        "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                        "type": "core",
                    }
                )
            else:
                info.update(
                    {
                        "text": "8 Merch Tokens",
                        "emoji": discord.PartialEmoji.from_str(
                            config.MERCH_TOKEN_EMOJI
                        ),
                        "type": "token",
                    }
                )

        elif cycle_idx == 6:
            info.update(
                {
                    "text": "Chaos Core",
                    "emoji": discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI),
                    "type": "core",
                }
            )

        return info

    def get_embed(self):
        u_data = database.get_user_data(self.user_id)
        shards = u_data["chaos_shards"]
        claimed = u_data["season_tier_claimed"]
        has_pass = u_data["has_premium_pass"]

        embed = discord.Embed(color=0xF1C40F)
        end_ts = int(
            datetime.datetime.fromisoformat(self.season["end_date"]).timestamp()
        )

        icon_url = "https://cdn.discordapp.com/emojis/1452763522390954174.png"
        pass_txt = f"{config.SHARD_HUNT_EMOJI} FREE"
        if has_pass:
            pass_txt = "🌟 PREMIUM"

        embed.set_author(name=f"SHARD HUNT: {self.season['name']}", icon_url=icon_url)
        embed.description = f"**Ends:** <t:{end_ts}:R>\n**Pass:** {pass_txt}\n**Progress:** {config.CHAOS_SHARD_EMOJI} **{shards}** Shards"

        if self.mode == "bonus":
            next_tier = claimed + 1
            bonus_step = next_tier - MAIN_TIERS_MAX
            cycle_num = ((bonus_step - 1) % BONUS_CYCLE_LENGTH) + 1
            cost_total = (MAIN_TIERS_MAX * 5) + (bonus_step * 10)
            needed_for_next = cost_total - shards

            info = self.get_reward_info(next_tier)

            embed.title = "✨ Bonus Tiers"
            embed.add_field(
                name=f"NEXT REWARD ({cycle_num}/{BONUS_CYCLE_LENGTH})",
                value=f"{info['emoji']} **{info['text']}**",
                inline=False,
            )

            current_in_step = 10 - needed_for_next
            current_in_step = max(0, min(10, current_in_step))
            bar = "🟦" * current_in_step + "⬜" * (10 - current_in_step)
            embed.add_field(
                name="Step Progress",
                value=f"`{bar}` {current_in_step}/10\n*(10 Shards per tier)*",
                inline=False,
            )
            return embed

        embed.title = "🏆 Main Pass"
        start_tier = (self.page * TIERS_PER_PAGE) + 1
        end_tier = start_tier + TIERS_PER_PAGE - 1

        for t in range(start_tier, end_tier + 1):
            if t > MAIN_TIERS_MAX:
                break
            cost_total = t * 5
            info = self.get_reward_info(t)
            is_unlocked = shards >= cost_total

            status_icon = "⬛"
            if t <= claimed:
                if info["is_premium"] and not has_pass:
                    status_icon = "🔒"
                else:
                    status_icon = "✅"
            elif is_unlocked:
                status_icon = "🟦"

            prefix = "🌟 Prem: " if (info["is_premium"]) else ""
            name_txt = f"{prefix}{info['emoji']} **{info['text']}**"

            embed.add_field(
                name=f"{status_icon} Tier {t} ({cost_total} Shards)",
                value=name_txt,
                inline=False,
            )

        embed.set_footer(text=f"Page {self.page + 1}")
        return embed

    def get_next_claimable_tier(self):
        u_data = database.get_user_data(self.user_id)
        claimed = u_data["season_tier_claimed"]
        has_pass = u_data["has_premium_pass"]

        curr = claimed + 1
        while curr <= MAIN_TIERS_MAX:
            info = self.get_reward_info(curr)
            if info["is_premium"] and not has_pass:
                curr += 1
                continue
            return curr
        return curr

    def update_components(self):
        self.clear_items()
        u_data = database.get_user_data(self.user_id)
        shards = u_data["chaos_shards"]
        claimed = u_data["season_tier_claimed"]
        has_pass = u_data["has_premium_pass"]

        next_claimable = self.get_next_claimable_tier()

        if self.mode == "bonus":

            next_tier = claimed + 1
            cost = (MAIN_TIERS_MAX * 5) + ((next_tier - MAIN_TIERS_MAX) * 10)
            info = self.get_reward_info(next_tier)
            btn = Button(
                style=discord.ButtonStyle.primary,
                label=f"Claim {info['text']}",
                emoji=info["emoji"],
                row=0,
            )
            if shards >= cost:
                btn.disabled = False
                btn.callback = self.make_callback(next_tier)
            else:
                btn.style = discord.ButtonStyle.secondary
                btn.disabled = True
            self.add_item(btn)

            toggle = Button(
                label="View Main Pass",
                style=discord.ButtonStyle.secondary,
                emoji="🔄",
                row=1,
            )
            toggle.callback = self.toggle_mode
            self.add_item(toggle)

        else:

            start_tier = (self.page * TIERS_PER_PAGE) + 1
            for i in range(TIERS_PER_PAGE):
                t = start_tier + i
                if t > MAIN_TIERS_MAX:
                    break
                cost = t * 5
                info = self.get_reward_info(t)

                btn = Button(
                    style=discord.ButtonStyle.secondary,
                    label=f"Claim {t}",
                    custom_id=f"c_{t}",
                    row=0,
                )
                if info["emoji"]:
                    btn.emoji = info["emoji"]

                if t <= claimed:
                    if info["is_premium"] and not has_pass:
                        btn.style = discord.ButtonStyle.secondary
                        btn.emoji = "🔒"
                        btn.disabled = True
                    else:
                        btn.style = discord.ButtonStyle.success
                        btn.emoji = "✅"
                        btn.disabled = True
                        btn.label = ""
                else:
                    if t == next_claimable and shards >= cost:
                        btn.style = discord.ButtonStyle.primary
                        btn.disabled = False
                    else:
                        btn.disabled = True

                btn.callback = self.make_callback(t)
                self.add_item(btn)

            if self.page > 0:
                prev = Button(label="<", style=discord.ButtonStyle.secondary, row=1)
                prev.callback = self.prev_page
                self.add_item(prev)

            if (self.page + 1) * TIERS_PER_PAGE < MAIN_TIERS_MAX:
                nxt = Button(label=">", style=discord.ButtonStyle.secondary, row=1)
                nxt.callback = self.next_page
                self.add_item(nxt)

            if self.claimed >= MAIN_TIERS_MAX:
                to_bonus = Button(
                    label="View Bonus Tiers",
                    style=discord.ButtonStyle.secondary,
                    emoji="🔄",
                    row=1,
                )
                to_bonus.callback = self.toggle_mode
                self.add_item(to_bonus)

        if not has_pass and self.season["type"] != "XP_Rush":
            buy = Button(
                label=f"Buy Premium Pass ({config.PREMIUM_PASS_PRICE})",
                style=discord.ButtonStyle.danger,
                row=2,
                emoji=discord.PartialEmoji.from_str(config.MOGOLD_EMOJI),
            )
            buy.callback = self.buy_pass
            self.add_item(buy)

    async def toggle_mode(self, i):
        if i.user.id != self.user_id:
            return
        self.mode = "bonus" if self.mode == "main" else "main"
        self.update_components()
        await i.response.edit_message(embed=self.get_embed(), view=self)

    def make_callback(self, tier):
        async def cb(intx):
            if intx.user.id != self.user_id:
                return
            await self.claim_tier(intx, tier)

        return cb

    async def prev_page(self, i):
        if i.user.id != self.user_id:
            return
        self.page -= 1
        self.update_components()
        await i.response.edit_message(embed=self.get_embed(), view=self)

    async def next_page(self, i):
        if i.user.id != self.user_id:
            return
        self.page += 1
        self.update_components()
        await i.response.edit_message(embed=self.get_embed(), view=self)

    async def buy_pass(self, i):
        if i.user.id != self.user_id:
            return
        u = database.get_user_data(self.user_id)
        if u["mo_gold"] < config.PREMIUM_PASS_PRICE:
            return await i.response.send_message(
                f"Not enough mo.gold! {config.MOGOLD_EMOJI}", ephemeral=True
            )

        database.update_user_stats(
            self.user_id,
            {
                "mo_gold": u["mo_gold"] - config.PREMIUM_PASS_PRICE,
                "has_premium_pass": 1,
            },
        )

        rewards_granted = []
        for t in range(1, u["season_tier_claimed"] + 1):
            info = self.get_reward_info(t)
            if info["is_premium"]:
                await self.grant_reward(info)
                rewards_granted.append(info["text"])

        msg = "🌟 **Premium Pass Activated!**"
        if rewards_granted:
            msg += f"\n\n**Retro-claimed:** {', '.join(rewards_granted)}"

        self.update_components()
        await i.response.edit_message(embed=self.get_embed(), view=self)
        await i.followup.send(msg, ephemeral=True)

    async def grant_reward(self, info):
        u = database.get_user_data(self.user_id)
        if info["type"] == "xp":
            database.update_user_stats(self.user_id, {"xp": u["xp"] + 2000})
        elif info["type"] == "gold":
            database.update_user_stats(self.user_id, {"mo_gold": u["mo_gold"] + 8})
        elif info["type"] == "token":
            database.update_user_stats(
                self.user_id, {"merch_tokens": u["merch_tokens"] + 8}
            )
        elif info["type"] == "kit":
            database.update_user_stats(
                self.user_id, {"chaos_kits": u["chaos_kits"] + 1}
            )
        elif info["type"] == "core":
            database.update_user_stats(
                self.user_id, {"chaos_cores": u["chaos_cores"] + 1}
            )
        elif info["type"] == "random":

            roll = random.random()
            if roll < 0.5:
                database.update_user_stats(
                    self.user_id, {"chaos_cores": u["chaos_cores"] + 1}
                )
            else:
                database.update_user_stats(
                    self.user_id, {"chaos_kits": u["chaos_kits"] + 1}
                )
        elif info["type"] == "item" and info["item_id"]:
            pl, _, _ = utils.get_level_info(u["xp"])
            lvl = max(1, pl - random.randint(0, 2))
            database.add_item_to_inventory(
                self.user_id, info["item_id"], "Standard", lvl
            )

    async def claim_tier(self, i, tier):
        u_data = database.get_user_data(self.user_id)
        shards = u_data["chaos_shards"]
        claimed = u_data["season_tier_claimed"]

        if tier <= MAIN_TIERS_MAX:
            next_claim = self.get_next_claimable_tier()
            if tier != next_claim:
                return await i.response.send_message(
                    f"Claim Tier {next_claim} first!", ephemeral=True
                )
        else:
            if tier != claimed + 1:
                return await i.response.send_message(
                    f"Claim Bonus {claimed+1} first!", ephemeral=True
                )

        info = self.get_reward_info(tier)
        await self.grant_reward(info)
        database.update_user_stats(self.user_id, {"season_tier_claimed": tier})

        if tier == MAIN_TIERS_MAX:
            self.mode = "bonus"
            self.page = 0

        self.update_components()
        await i.response.edit_message(embed=self.get_embed(), view=self)

        msg = f"✅ **Claimed:** {info['text']}"
        await i.followup.send(msg, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ShardHunt(bot))

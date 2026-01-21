import discord
from discord import app_commands
from discord.ext import commands
from mo_co import database, config, utils, game_data
import json
from datetime import datetime


CRATE_URLS = {
    "default": "https://cdn.discordapp.com/emojis/1452309436369600646.png",
    "merch": "https://cdn.discordapp.com/emojis/1455592395075752007.png",
    "merch_xl": "https://cdn.discordapp.com/emojis/1455592422632460565.png",
    "mogold": "https://cdn.discordapp.com/emojis/1455608827973079091.png",
}


class Promo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="promo", description="Redeem a special code")
    @app_commands.describe(code="The code to redeem")
    async def promo(self, interaction: discord.Interaction, code: str):
        clean_code = code.lower().strip()

        promo_data = database.get_promo_code(clean_code)

        if not promo_data:
            return await interaction.response.send_message(
                "❌ **Invalid Code.**", ephemeral=True
            )

        if not promo_data["active"]:
            return await interaction.response.send_message(
                "❌ **This code is no longer active.**", ephemeral=True
            )

        if promo_data["expires_at"]:
            try:
                expiry = datetime.fromisoformat(promo_data["expires_at"])
                if datetime.utcnow() > expiry:
                    return await interaction.response.send_message(
                        "❌ **This code has expired.**", ephemeral=True
                    )
            except ValueError:
                pass

        database.register_user(interaction.user.id)

        if database.has_claimed_promo(interaction.user.id, clean_code):
            return await interaction.response.send_message(
                "⚠️ **You have already claimed this code!**", ephemeral=True
            )

        await self.grant_rewards(interaction, clean_code, dict(promo_data))

    async def grant_rewards(self, interaction, code_key, data):
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)
        rewards = json.loads(data["rewards"])

        updates = {}
        log_lines = []

        if "mo_gold" in rewards:
            updates["mo_gold"] = u_dict["mo_gold"] + rewards["mo_gold"]
            log_lines.append(f"{config.MOGOLD_EMOJI} **+{rewards['mo_gold']}** mo.gold")

        if "merch_tokens" in rewards:
            updates["merch_tokens"] = u_dict["merch_tokens"] + rewards["merch_tokens"]
            log_lines.append(
                f"{config.MERCH_TOKEN_EMOJI} **+{rewards['merch_tokens']}** Tokens"
            )

        if "chaos_cores" in rewards:
            updates["chaos_cores"] = u_dict["chaos_cores"] + rewards["chaos_cores"]
            log_lines.append(
                f"{config.CHAOS_CORE_EMOJI} **+{rewards['chaos_cores']}** Cores"
            )

        if "chaos_kits" in rewards:
            updates["chaos_kits"] = u_dict["chaos_kits"] + rewards["chaos_kits"]
            log_lines.append(
                f"{config.CHAOS_CORE_EMOJI} **+{rewards['chaos_kits']}** Kits"
            )

        if "chaos_shards" in rewards:
            updates["chaos_shards"] = u_dict["chaos_shards"] + rewards["chaos_shards"]
            log_lines.append(
                f"{config.CHAOS_SHARD_EMOJI} **+{rewards['chaos_shards']}** Shards"
            )

        if "xp" in rewards:
            utils.add_user_xp(interaction.user.id, rewards["xp"])
            log_lines.append(f"{config.XP_EMOJI} **+{rewards['xp']}** XP")
            u_dict = dict(database.get_user_data(interaction.user.id))

        if "xp_fuel" in rewards:
            updates["daily_xp_boosted"] = (
                u_dict["daily_xp_boosted"] + rewards["xp_fuel"]
            )
            log_lines.append(
                f"{config.XP_BOOST_3X_EMOJI} **+{rewards['xp_fuel']:,}** Bonus XP Fuel"
            )

        if "shard_hunt_pass" in rewards and rewards["shard_hunt_pass"]:
            updates["has_premium_pass"] = 1
            log_lines.append(f"🌟 **Premium Shard Hunt Pass Unlocked!**")

        if updates:
            database.update_user_stats(interaction.user.id, updates)

        if "items" in rewards:
            player_lvl, _, _ = utils.get_level_info(u_dict["xp"])
            scaled_lvl = min(50, player_lvl)

            for item_def in rewards["items"]:
                i_id = item_def["id"]
                mod = item_def.get("mod", "Standard")
                final_lvl = max(1, scaled_lvl)

                database.add_item_to_inventory(
                    interaction.user.id, i_id, mod, final_lvl
                )

                icon = utils.get_emoji(self.bot, i_id)
                i_name = game_data.get_item(i_id)["name"]
                mod_str = f"[{mod}] " if mod != "Standard" else ""
                log_lines.append(f"{icon} **{mod_str}{i_name}** (Lvl {final_lvl})")

        database.mark_promo_claimed(interaction.user.id, code_key)

        crate_key = data.get("crate_type", "default")
        thumb_url = CRATE_URLS.get(crate_key, CRATE_URLS["default"])

        embed = discord.Embed(
            title="🎁 Code Redeemed!",
            description=f"**{data['description']}**\n\n" + "\n".join(log_lines),
            color=0x2ECC71,
        )
        embed.set_thumbnail(url=thumb_url)
        embed.set_footer(text=f"Code: {code_key}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Promo(bot))

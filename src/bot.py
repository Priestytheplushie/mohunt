import discord
from discord.ext import commands
import json
import os
import sys
import traceback
from datetime import datetime

from keep_alive import keep_alive

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from mo_co import config, database, season_manager, game_data


ADMIN_ID = (
    int(config.ADMIN_ACCESS_CODE)
    if config.ADMIN_ACCESS_CODE.isdigit()
    else 793917026687123477
)


class MoCoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=config.APPLICATION_ID,
        )
        self.config_cache = {}
        self.blacklist_cache = {}
        self.guild_blacklist_cache = {}

    def update_cache(self, key, value):
        """Manually update cache from commands (admin)"""
        self.config_cache[key] = value

    async def setup_hook(self):
        database.init_db()
        season_manager.init_season()

        print("Loading global configuration cache...")
        configs, u_bans, g_bans = database.load_global_cache()
        self.config_cache = configs
        self.blacklist_cache = u_bans
        self.guild_blacklist_cache = g_bans
        print(
            f"Cache loaded. Maintenance Mode: {self.config_cache.get('maintenance_mode', '0')}"
        )

        try:
            emoji_path = "src/mo_co/emoji_map.json"
            if not os.path.exists(emoji_path):
                emoji_path = "mo_co/emoji_map.json"

            with open(emoji_path, "r") as f:
                self.emoji_map = json.load(f)

            self.emoji_map["randb_mixtape"] = "<:randb_mixtape:1452309469827694605>"
            self.emoji_map["chickaboo_eggshell"] = (
                "<:chickaboo_eggshell:1457467769640583208>"
            )
            self.emoji_map["empty_ride"] = "<:empty_ride:1457467688174489630>"

            if "pew3000" in self.emoji_map:
                self.emoji_map["pew_3000"] = self.emoji_map["pew3000"]
            print(f"Loaded {len(self.emoji_map)} emoji mappings.")
        except FileNotFoundError:
            print("WARNING: emoji_map.json not found.")
            self.emoji_map = {}

        extensions = [
            "mo_co.cogs.hunting",
            "mo_co.cogs.inventory",
            "mo_co.cogs.loadout",
            "mo_co.cogs.profile",
            "mo_co.cogs.trading",
            "mo_co.cogs.events",
            "mo_co.cogs.index",
            "mo_co.cogs.jobs",
            "mo_co.cogs.shard_hunt",
            "mo_co.cogs.teams",
            "mo_co.cogs.portal",
            "mo_co.cogs.shop",
            "mo_co.cogs.versus",
            "mo_co.cogs.missions",
            "mo_co.cogs.ellie",
            "mo_co.cogs.elite",
            "mo_co.cogs.coolzone",
            "mo_co.cogs.promo",
            "mo_co.cogs.inbox",
            "mo_co.cogs.admin",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

        self.tree.interaction_check = self.global_interaction_check
        await self.tree.sync()
        print("Slash commands synced and ready.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_interaction(self, interaction: discord.Interaction):
        """Silently update user display name in background to keep leaderboards fresh."""
        try:
            if interaction.user:
                database.register_user(
                    interaction.user.id, interaction.user.display_name
                )
        except:
            pass

    async def global_interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == ADMIN_ID:
            return True

        m_mode = self.config_cache.get("maintenance_mode", "0")
        if m_mode == "1":
            if interaction.type == discord.InteractionType.autocomplete:
                return False
            await interaction.response.send_message(
                "⚠️ **System in Maintenance Mode.** The developers are working on an update. Please try again later.",
                ephemeral=True,
            )
            return False

        if interaction.guild:
            if interaction.guild.id in self.guild_blacklist_cache:
                g_row = self.guild_blacklist_cache[interaction.guild.id]
                if interaction.type == discord.InteractionType.autocomplete:
                    return False
                await interaction.response.send_message(
                    f"⛔ **This server is blacklisted.**\nReason: {g_row['public_reason']}",
                    ephemeral=True,
                )
                return False

        if interaction.user.id in self.blacklist_cache:
            u_row = self.blacklist_cache[interaction.user.id]
            expiry = u_row["expires_at"]
            is_banned = False

            if expiry == "PERMANENT":
                is_banned = True
            else:
                try:
                    if datetime.fromisoformat(expiry) > datetime.utcnow():
                        is_banned = True
                    else:

                        del self.blacklist_cache[interaction.user.id]
                except:
                    pass

            if is_banned:
                if expiry != "PERMANENT":
                    try:
                        ts = int(datetime.fromisoformat(expiry).timestamp())
                        expiry_str = f"<t:{ts}:R>"
                    except:
                        expiry_str = expiry
                else:
                    expiry_str = "Never"

                if interaction.type == discord.InteractionType.autocomplete:
                    return False

                await interaction.response.send_message(
                    f"⛔ **You are banned from using this bot.**\nReason: {u_row['reason']}\nExpires: {expiry_str}",
                    ephemeral=True,
                )
                return False

        return True


if __name__ == "__main__":
    keep_alive()
    bot = MoCoBot()
    bot.run(config.TOKEN)

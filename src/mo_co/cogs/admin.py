import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import (
    View,
    Button,
    Select,
    Modal,
    TextInput,
    UserSelect,
    ChannelSelect,
)
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from mo_co import database, config, game_data, utils, season_manager
from mo_co.game_data.missions import MISSIONS
import os


ADMIN_ID = (
    int(config.ADMIN_ACCESS_CODE)
    if config.ADMIN_ACCESS_CODE.isdigit()
    else 793917026687123477
)


INBOX_TEMPLATES = [
    {
        "label": "Small Comp",
        "title": "Compensation",
        "body": "Sorry for the inconvenience! Here is a small gift.",
        "rewards": {"mo_gold": 50},
    },
    {
        "label": "Medium Comp",
        "title": "Compensation",
        "body": "Thanks for your patience during the downtime.",
        "rewards": {"mo_gold": 200, "merch_tokens": 20},
    },
    {
        "label": "Large Comp",
        "title": "Service Restore",
        "body": "We apologize for the extended outage.",
        "rewards": {"mo_gold": 500, "chaos_cores": 2},
    },
    {
        "label": "Bug Hunter",
        "title": "Bug Report Reward",
        "body": "Thank you for reporting that bug! 🐛",
        "rewards": {"merch_tokens": 50, "chaos_kits": 1},
    },
    {
        "label": "Exploit Report",
        "title": "Security Bounty",
        "body": "Excellent find. You helped keep the game safe.",
        "rewards": {"elite_tokens": 100, "chaos_cores": 5},
    },
    {
        "label": "Contest Winner",
        "title": "Contest Winner!",
        "body": "Congratulations on winning the community event! 🎉",
        "rewards": {"mo_gold": 1000, "chaos_shards": 500},
    },
    {
        "label": "Contest Participant",
        "title": "Event Participation",
        "body": "Thanks for taking part in our event!",
        "rewards": {"mo_gold": 100},
    },
    {
        "label": "Fan Art",
        "title": "Art Showcase",
        "body": "We loved your art! Keep it up! 🎨",
        "rewards": {"merch_tokens": 100},
    },
    {
        "label": "Wiki Contrib",
        "title": "Wiki Contributor",
        "body": "Thanks for helping document the game! 📚",
        "rewards": {"mo_gold": 300, "chaos_kits": 2},
    },
    {
        "label": "Beta Tester",
        "title": "Beta Reward",
        "body": "Thank you for testing the new features.",
        "rewards": {"chaos_cores": 3},
    },
    {
        "label": "Welcome Pack",
        "title": "Welcome!",
        "body": "Welcome to the Elite Hunter Program!",
        "rewards": {"mo_gold": 100, "chaos_kits": 1},
    },
    {
        "label": "Prestige Bonus",
        "title": "Ascension Gift",
        "body": "Good luck on your new journey.",
        "rewards": {"xp_fuel": 50000},
    },
    {
        "label": "Season Catchup",
        "title": "Season Supply",
        "body": "Here is a boost for the current season.",
        "rewards": {"chaos_shards": 200},
    },
    {
        "label": "Lost Item Restore",
        "title": "Item Restoration",
        "body": "We have restored your lost item.",
        "rewards": {
            "items": [{"id": "monster_slugger", "level": 1, "mod": "Standard"}]
        },
    },
    {
        "label": "Warning",
        "title": "Behavior Warning",
        "body": "Please review the community rules. Further breaches will result in a ban.",
        "rewards": {},
    },
    {
        "label": "Staff Pay (W)",
        "title": "Weekly Salary",
        "body": "Thanks for your hard work this week!",
        "rewards": {"mo_gold": 2000},
    },
    {
        "label": "Staff Pay (M)",
        "title": "Monthly Salary",
        "body": "Thanks for your hard work this month!",
        "rewards": {"mo_gold": 10000, "elite_tokens": 500},
    },
    {
        "label": "Booster Pack",
        "title": "XP Boost",
        "body": "Get back into the fight!",
        "rewards": {"xp_fuel": 20000},
    },
    {
        "label": "Gold Stimulus",
        "title": "Economic Adjustment",
        "body": "A gift from the Bureau.",
        "rewards": {"mo_gold": 500},
    },
    {
        "label": "Token Stimulus",
        "title": "Token Grant",
        "body": "Spend these at the shop!",
        "rewards": {"merch_tokens": 50},
    },
    {
        "label": "Core Stimulus",
        "title": "Core Grant",
        "body": "Upgrade your gear.",
        "rewards": {"chaos_cores": 3},
    },
    {
        "label": "Kit Stimulus",
        "title": "Kit Grant",
        "body": "Upgrade your gear.",
        "rewards": {"chaos_kits": 3},
    },
    {
        "label": "Shard Stimulus",
        "title": "Shard Grant",
        "body": "Advance your pass.",
        "rewards": {"chaos_shards": 100},
    },
    {
        "label": "Elite Stimulus",
        "title": "Elite Grant",
        "body": "For the Elite Shop.",
        "rewards": {"elite_tokens": 50},
    },
    {
        "label": "Custom (Empty)",
        "title": "System Message",
        "body": "Message Body",
        "rewards": {},
    },
]


def is_admin_ctx(ctx):
    return ctx.author.id == ADMIN_ID


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="migrate_db")
    @commands.check(is_admin_ctx)
    async def migrate_db(self, ctx):
        """
        One-time command to migrate local SQLite file (uploaded to server)
        to the Turso cloud database.
        """
        await ctx.send("🔄 **Starting Migration...** This may take a minute.")

        if not config.TURSO_DB_URL or not config.TURSO_AUTH_TOKEN:
            return await ctx.send("❌ Turso credentials not found in environment.")

        local_db = "moco_v2.db"
        if not os.path.exists(local_db):
            return await ctx.send(
                f"❌ Local database file `{local_db}` not found on server."
            )

        try:
            import libsql_experimental as libsql
        except ImportError:
            return await ctx.send(
                "❌ `libsql-experimental` not installed. Cannot connect to Turso."
            )

        TABLES = [
            "users",
            "inventory",
            "gear_kits",
            "loadouts",
            "inbox_messages",
            "season_config",
            "shop_state",
            "active_deals",
            "active_system_events",
            "promo_codes",
            "promo_history",
            "system_config",
            "user_blacklist",
            "guild_blacklist",
            "user_snapshots",
        ]

        log_msg = "```\n"

        try:
            local = sqlite3.connect(local_db)
            local.row_factory = sqlite3.Row
            l_cur = local.cursor()

            remote = libsql.connect(
                database=config.TURSO_DB_URL, auth_token=config.TURSO_AUTH_TOKEN
            )

            for table in TABLES:
                try:
                    rows = l_cur.execute(f"SELECT * FROM {table}").fetchall()
                    if not rows:
                        log_msg += f"Skipping {table} (Empty)\n"
                        continue

                    keys = rows[0].keys()
                    cols = ", ".join(keys)
                    placeholders = ", ".join(["?" for _ in keys])
                    query = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"

                    remote.execute("BEGIN TRANSACTION")
                    count = 0
                    for row in rows:
                        remote.execute(query, tuple(row))
                        count += 1
                    remote.commit()
                    log_msg += f"✅ {table}: Migrated {count} rows.\n"

                except Exception as e:
                    log_msg += f"❌ {table}: Error - {e}\n"

            local.close()

            log_msg += "```"
            await ctx.send(f"**Migration Complete.**\n{log_msg}")
        except Exception as e:
            await ctx.send(f"💥 **Critical Migration Failure:** {e}")

    @commands.command(name="admin")
    @commands.check(is_admin_ctx)
    async def admin_panel(self, ctx):
        try:
            await ctx.message.delete()
        except:
            pass

                                                
        with database.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT user_id, display_name, xp, is_elite, prestige_level, current_title, last_hunt_time 
                FROM users 
                ORDER BY last_hunt_time DESC 
                LIMIT 25
            """
            ).fetchall()

                                                          
        options = []
        for row in rows:
            uid = row["user_id"]
            db_name = row["display_name"]

                                                      
            if not db_name:
                user = self.bot.get_user(uid)
                name = user.display_name if user else f"Hunter {uid}"
            else:
                name = db_name

            lvl, _, _ = utils.get_level_info(row["xp"])
            emblem_str = utils.get_emblem(
                lvl, bool(row["is_elite"]), row["prestige_level"]
            )
            emoji = (
                discord.PartialEmoji.from_str(emblem_str)
                if emblem_str.startswith("<")
                else None
            )

            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=str(uid),
                    description=f"Lvl {lvl} | {row['current_title'] or 'No Title'}",
                    emoji=emoji,
                )
            )

        if not options:
            options.append(
                discord.SelectOption(label="No Active Hunters", value="none")
            )

        view = AdminEntryView(self.bot, options, mode="recent")
        await ctx.send("Select a Hunter", view=view)


class AdminEntryView(View):
    def __init__(self, bot, recent_options, mode="recent"):
        super().__init__(timeout=None)
        self.bot = bot
        self.recent_options = recent_options
        self.mode = mode
        self.update_components()

    def update_components(self):
        self.clear_items()

        if self.mode == "recent":
            self.add_item(HunterRecentSelect(self.bot, self.recent_options))
        elif self.mode == "search":
            self.add_item(HunterUserSelect(self.bot))
        elif self.mode == "guild":
            top_guilds = sorted(
                self.bot.guilds, key=lambda g: g.member_count, reverse=True
            )[:25]
            self.add_item(GuildSelect(self.bot, top_guilds))

        if self.mode == "recent":
            next_mode = "search"
            btn_label = "Toggle Query"
            btn_style = discord.ButtonStyle.secondary
        elif self.mode == "search":
            next_mode = "guild"
            btn_label = "Toggle Query (Guilds)"
            btn_style = discord.ButtonStyle.primary
        else:
            next_mode = "recent"
            btn_label = "Reset Query"
            btn_style = discord.ButtonStyle.secondary

        self.add_item(ToggleQueryButton(next_mode, btn_label, btn_style))

        if self.mode == "guild":
            self.add_item(GuildIDSearchButton())


class ToggleQueryButton(Button):
    def __init__(self, next_mode, label, style):
        super().__init__(label=label, style=style, emoji="🔍", row=1)
        self.next_mode = next_mode

    async def callback(self, i: discord.Interaction):
        if i.user.id != ADMIN_ID:
            return await i.response.send_message("⛔ Access Denied.", ephemeral=True)
        self.view.mode = self.next_mode
        self.view.update_components()
        await i.response.edit_message(view=self.view)


class HunterRecentSelect(Select):
    def __init__(self, bot, options):
        self.bot = bot
        super().__init__(
            placeholder="Select a Hunter...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message(
                "⛔ Access Denied.", ephemeral=True
            )
        if self.values[0] == "none":
            return
        await handle_admin_selection(self.bot, interaction, int(self.values[0]))


class HunterUserSelect(UserSelect):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            placeholder="Search Discord User...",
            min_values=1,
            max_values=1,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message(
                "⛔ Access Denied.", ephemeral=True
            )
        target_user = self.values[0]
                                                                      
        database.register_user(target_user.id, target_user.display_name)
        await handle_admin_selection(self.bot, interaction, target_user.id)


class GuildSelect(Select):
    def __init__(self, bot, guilds):
        self.bot = bot
        options = []
        for g in guilds:
            label = g.name[:100]
            desc = f"ID: {g.id} | Members: {g.member_count}"
            options.append(
                discord.SelectOption(
                    label=label, value=str(g.id), description=desc, emoji="🏰"
                )
            )

        if not options:
            options.append(discord.SelectOption(label="No Guilds Found", value="none"))

        super().__init__(
            placeholder="Select a Server...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != ADMIN_ID:
            return await interaction.response.send_message(
                "⛔ Access Denied.", ephemeral=True
            )
        if self.values[0] == "none":
            return
        await handle_guild_selection(self.bot, interaction, int(self.values[0]))


class GuildIDSearchButton(Button):
    def __init__(self):
        super().__init__(
            label="Search Guild ID",
            style=discord.ButtonStyle.primary,
            emoji="🔢",
            row=1,
        )

    async def callback(self, i: discord.Interaction):
        if i.user.id != ADMIN_ID:
            return await i.response.send_message("⛔ Access Denied.", ephemeral=True)
        await i.response.send_modal(GuildIDModal(self.view.bot))


class GuildIDModal(Modal):
    def __init__(self, bot):
        super().__init__(title="Search Guild")
        self.bot = bot
        self.gid = TextInput(
            label="Guild ID", min_length=15, max_length=25, required=True
        )
        self.add_item(self.gid)

    async def on_submit(self, i: discord.Interaction):
        if i.user.id != ADMIN_ID:
            return await i.response.send_message("⛔ Access Denied.", ephemeral=True)
        try:
            target_id = int(self.gid.value)
            await handle_guild_selection(self.bot, i, target_id)
        except ValueError:
            await i.response.send_message("Invalid ID format.", ephemeral=True)


async def handle_admin_selection(bot, interaction: discord.Interaction, target_id: int):
                                       
    target_user = bot.get_user(target_id)

                                                                         
    name = f"Unknown ({target_id})"

    if target_user:
        name = target_user.name
    else:
                            
        u_data = database.get_user_data(target_id)
        if u_data and u_data["display_name"]:
            name = u_data["display_name"]
        else:
                                       
            try:
                target_user = await bot.fetch_user(target_id)
                name = target_user.name
                                
                database.register_user(target_id, name)
            except:
                pass

    try:
        if isinstance(interaction.message, discord.Message):
            await interaction.message.delete()
    except:
        pass

    view = GMPanelView(bot, target_id)
    await interaction.response.send_message(
        content=f"🔓 **Accessing:** {name}",
        embed=view.get_embed(),
        view=view,
        ephemeral=True,
    )


async def handle_guild_selection(bot, interaction: discord.Interaction, guild_id: int):
    guild = bot.get_guild(guild_id)
    if not guild:
        try:
            guild = await bot.fetch_guild(guild_id)
        except:
            pass

    name = guild.name if guild else f"Unknown Guild ({guild_id})"

    try:
        if isinstance(interaction.message, discord.Message):
            await interaction.message.delete()
    except:
        pass

    view = GuildPanelView(bot, guild_id, guild)
    await interaction.response.send_message(
        content=f"🛡️ **Guild Manager:** {name}",
        embed=view.get_embed(),
        view=view,
        ephemeral=True,
    )


class GuildPanelView(View):
    def __init__(self, bot, guild_id, guild_obj):
        super().__init__(timeout=900)
        self.bot = bot
        self.guild_id = guild_id
        self.guild_obj = guild_obj
        self.update_components()

    def get_embed(self):
        embed = discord.Embed(
            title=f"🏰 Server: {self.guild_obj.name if self.guild_obj else 'Unknown ID'}",
            color=0x3498DB,
        )
        is_banned, row = database.is_guild_blacklisted(self.guild_id)

        if self.guild_obj:
            embed.description = (
                f"**ID:** `{self.guild_id}`\n"
                f"**Members:** {self.guild_obj.member_count:,}\n"
                f"**Owner:** {self.guild_obj.owner_id} ({self.guild_obj.owner})"
            )
            if self.guild_obj.icon:
                embed.set_thumbnail(url=self.guild_obj.icon.url)
        else:
            embed.description = f"**ID:** `{self.guild_id}`\n⚠️ **Bot is not in this server (or intent restricted).**\nYou can still blacklist this ID."

        if is_banned:
            embed.add_field(
                name="⛔ BLACKLISTED",
                value=f"**Reason:** {row['public_reason']}\n**Staff Note:** {row['staff_reason']}",
                inline=False,
            )
            embed.color = 0xFF0000
        else:
            embed.add_field(name="✅ Status", value="Active / Allowed", inline=False)
            embed.color = 0x2ECC71

        return embed

    def update_components(self):
        self.clear_items()
        is_banned, _ = database.is_guild_blacklisted(self.guild_id)

        if is_banned:
            self.add_item(UnbanGuildButton(self.guild_id))
        else:
            self.add_item(BanGuildButton(self.guild_id))

        if self.guild_obj:
            self.add_item(LeaveGuildButton(self.guild_id))
            self.add_item(TriggerEventButton(self.guild_obj))


class BanGuildButton(Button):
    def __init__(self, guild_id):
        super().__init__(
            label="Blacklist Guild",
            style=discord.ButtonStyle.danger,
            emoji="🔨",
        )
        self.guild_id = guild_id

    async def callback(self, i: discord.Interaction):
        await i.response.send_modal(GuildBlacklistModal(self.guild_id, self.view))


class UnbanGuildButton(Button):
    def __init__(self, guild_id):
        super().__init__(
            label="Unblacklist", style=discord.ButtonStyle.success, emoji="🕊️"
        )
        self.guild_id = guild_id

    async def callback(self, i: discord.Interaction):
        database.unblacklist_guild(self.guild_id)
        if self.guild_id in self.view.bot.guild_blacklist_cache:
            del self.view.bot.guild_blacklist_cache[self.guild_id]

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await i.followup.send("✅ Guild unblacklisted.", ephemeral=True)


class LeaveGuildButton(Button):
    def __init__(self, guild_id):
        super().__init__(
            label="Force Leave",
            style=discord.ButtonStyle.secondary,
            emoji="🚪",
        )
        self.guild_id = guild_id

    async def callback(self, i: discord.Interaction):
        guild = self.view.bot.get_guild(self.guild_id)
        if guild:
            await guild.leave()
            await i.response.send_message(f"👋 Left **{guild.name}**.", ephemeral=True)
            self.view.guild_obj = None
            self.view.update_components()
            await i.edit_original_response(embed=self.view.get_embed(), view=self.view)
        else:
            await i.response.send_message(
                "❌ Could not find guild to leave.", ephemeral=True
            )


class TriggerEventButton(Button):
    def __init__(self, guild):
        super().__init__(
            label="Start Event",
            style=discord.ButtonStyle.primary,
            emoji="🎉",
            row=1,
        )
        self.guild = guild

    async def callback(self, i: discord.Interaction):
        await i.response.send_message(
            view=EventTriggerView(self.view.bot, self.guild), ephemeral=True
        )


class EventTriggerView(View):
    def __init__(self, bot, guild):
        super().__init__(timeout=120)
        self.bot = bot
        self.guild = guild
        self.selected_channel = None
        self.selected_type = None

        self.add_item(EventChannelSelect())
        self.add_item(EventTypeSelect())
        self.add_item(StartEventButton())


class EventChannelSelect(ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select Channel...",
            channel_types=[
                discord.ChannelType.text,
                discord.ChannelType.public_thread,
            ],
            row=0,
        )

    async def callback(self, i: discord.Interaction):
        self.view.selected_channel = self.values[0]
        await i.response.defer()


class EventTypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Invasion Alert",
                value="invasion",
                emoji=utils.safe_emoji(config.CHAOS_ALERT),
            ),
            discord.SelectOption(
                label="Merch Crate",
                value="crate",
                emoji=utils.safe_emoji(config.MOCO_CRATE_EMOJI),
            ),
            discord.SelectOption(
                label="Chaos Core",
                value="core",
                emoji=utils.safe_emoji(config.CHAOS_CORE_EMOJI),
            ),
        ]
        super().__init__(placeholder="Select Event Type...", options=options, row=1)

    async def callback(self, i: discord.Interaction):
        self.view.selected_type = self.values[0]
        await i.response.defer()


class StartEventButton(Button):
    def __init__(self):
        super().__init__(label="Start", style=discord.ButtonStyle.success, row=2)

    async def callback(self, i: discord.Interaction):
        view = self.view
        if not view.selected_channel or not view.selected_type:
            return await i.response.send_message(
                "Please select a channel and event type.", ephemeral=True
            )

        cog = view.bot.get_cog("ChaosEvents")
        if not cog:
            return await i.response.send_message(
                "Events module not loaded.", ephemeral=True
            )

        channel = view.selected_channel

        real_channel = view.bot.get_channel(channel.id)
        if not real_channel:
            try:
                real_channel = await view.bot.fetch_channel(channel.id)
            except:
                return await i.response.send_message(
                    "Could not resolve channel.", ephemeral=True
                )

        if view.selected_type == "invasion":
            await cog.spawn_invasion_event(real_channel)
        elif view.selected_type == "crate":
            await cog.spawn_merch_crate(real_channel)
        elif view.selected_type == "core":
            await cog.spawn_chaos_core(real_channel)

        await i.response.send_message(
            f"✅ Event started in {real_channel.mention}", ephemeral=True
        )


class GuildBlacklistModal(Modal):
    def __init__(self, guild_id, parent_view):
        super().__init__(title=f"Blacklist Guild {guild_id}")
        self.guild_id = guild_id
        self.parent_view = parent_view
        self.pub_reason = TextInput(
            label="Public Message",
            placeholder="Shown to users when they try to use the bot",
            style=discord.TextStyle.paragraph,
        )
        self.staff_reason = TextInput(
            label="Internal Note",
            placeholder="Why are we banning them?",
            required=False,
        )
        self.add_item(self.pub_reason)
        self.add_item(self.staff_reason)

    async def on_submit(self, i):
        database.blacklist_guild(
            i.user.id,
            self.guild_id,
            self.pub_reason.value,
            self.staff_reason.value,
        )
        database.log_gm_action(
            i.user.id,
            self.guild_id,
            "BAN_GUILD",
            {
                "public": self.pub_reason.value,
                "internal": self.staff_reason.value,
            },
        )
                      
        i.client.guild_blacklist_cache[self.guild_id] = {
            "guild_id": self.guild_id,
            "public_reason": self.pub_reason.value,
            "staff_reason": self.staff_reason.value,
        }

        self.parent_view.update_components()
        await i.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )
        await i.followup.send(f"⛔ **Guild Blacklisted.**", ephemeral=True)


class GMPanelView(View):
    def __init__(self, bot, target_id, tab="profile", scope="user"):
        super().__init__(timeout=900)
        self.bot = bot
        self.target_id = target_id
        self.tab = tab
        self.scope = scope
        self.inv_filter = "weapon"
        self.inv_item_id = None
        self.message = None

        self.cart = {
            "profile": {},
            "inv_add": [],
            "inv_edit": {},
            "inv_del": [],
        }
        self.update_components()

    def capture_message(self, interaction):
        self.message = interaction.message

    def get_embed(self):
        raw_u_data = database.get_user_data(self.target_id)
        u_data = dict(raw_u_data) if raw_u_data and self.scope == "user" else {}

        embed = discord.Embed(color=0x2B2D31)
        scope_str = (
            f"User: {self.target_id}" if self.scope == "user" else "GLOBAL SCOPE"
        )
        embed.set_footer(text=f"{scope_str} | Tab: {self.tab.upper()}")

        if self.tab == "profile":
            if not u_data:
                embed.description = "⚠️ **User Not Registered.**\nYou can still use Moderation or Inbox tools."
                embed.color = 0xE74C3C
            else:
                state_str = ""
                if u_data.get("account_state") != "LEGIT":
                    state_str = f"\n⚠️ **MODE:** {u_data['account_state']}"

                lvl, _, _ = utils.get_level_info(u_data["xp"])
                elite = bool(u_data.get("is_elite", 0))
                desc = (
                    f"{config.XP_EMOJI} **XP:** {u_data['xp']:,} (Lvl {lvl})\n"
                    f"{config.ELITE_EMOJI} **Elite XP:** {u_data.get('elite_xp', 0):,}\n"
                    f"{config.MOGOLD_EMOJI} **Gold:** {u_data['mo_gold']:,}\n"
                    f"{config.MERCH_TOKEN_EMOJI} **Tokens:** {u_data['merch_tokens']:,}\n"
                    f"{config.CHAOS_CORE_EMOJI} **Cores:** {u_data['chaos_cores']:,} | **Kits:** {u_data['chaos_kits']:,}\n"
                    f"{config.CHAOS_SHARD_EMOJI} **Shards:** {u_data['chaos_shards']:,}\n"
                    f"**HP:** {u_data['current_hp']} | **Elite:** {'✅' if elite else '❌'}"
                    f"{state_str}"
                )
                embed.title, embed.description = (
                    f"{config.ELITE_HUNTER_ICON} Profile Editor",
                    desc,
                )

        elif self.tab == "inventory":
            inv = database.get_user_inventory(self.target_id)
            embed.title = (
                f"{utils.get_emoji(self.bot, 'empty_gadget')} Inventory Manager"
            )
            embed.description = (
                f"**Total Items:** {len(inv)}\nSelect a filter then an item."
            )
            if self.inv_item_id:
                r = database.get_item_instance(self.inv_item_id)
                if r:
                    d = game_data.get_item(r["item_id"])
                    embed.add_field(
                        name="Selected",
                        value=f"{utils.get_emoji(self.bot, r['item_id'])} **{d['name']}**\nLvl: {r['level']} | Mod: {r['modifier']}",
                        inline=False,
                    )

        elif self.tab == "god_mode":
            state = u_data.get("account_state", "LEGIT")
            embed.title = f"⚡ God Mode Control: {state}"

            if state == "LEGIT":
                embed.description = (
                    "**Status:** LEGITIMATE ACCOUNT\n"
                    "You can switch this user to **GOD MODE** or **SANDBOX** for testing.\n\n"
                    "⚠️ **Safety:** A backup of the LEGIT data will be verified/created before switching."
                )
                embed.color = 0x3498DB
            elif state == "GOD":
                embed.description = (
                    "**Status:** ⚡ GOD MODE ACTIVE\n"
                    "• All items unlocked (Max Level)\n"
                    "• Infinite Currency\n"
                    "• Max Prestige\n\n"
                    "To return to the user's normal account, click **Return to Legit**."
                )
                embed.color = 0xF1C40F
            elif state == "SANDBOX":
                embed.description = (
                    "**Status:** 📦 SANDBOX MODE ACTIVE\n"
                    "• Fresh Level 1 Account State\n"
                    "• Used for testing New Player Experience\n\n"
                    "To return to the user's normal account, click **Return to Legit**."
                )
                embed.color = 0xE74C3C

            snap = database.get_snapshot(self.target_id)
            if snap:
                ts = snap.get("user", {}).get("last_hunt_time", "Unknown")
                embed.add_field(
                    name="💾 Backup Status",
                    value=f"✅ **Safe Snapshot Found**\nTime: {ts}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="💾 Backup Status",
                    value="⚠️ **No Backup Found**\nBackup will be created upon mode switch.",
                    inline=False,
                )

        elif self.tab == "inbox":
            embed.title = "📨 Inbox Wizard"
            embed.description = "Compose mail with attachments using the Builder flow."

        elif self.tab == "db":
            embed.title = f"{config.GEAR_POWER_EMOJI} Database Console"
            embed.description = f"**Scope:** {self.scope.upper()}\nBrowse tables and edit values directly."

        elif self.tab == "moderation":
            embed.title = f"{config.DOJO_ICON} Moderation Tools"
            is_banned, row = database.is_user_blacklisted(self.target_id)
            if is_banned:
                embed.description = f"🛑 **USER IS BANNED**\n**Reason:** {row['reason']}\n**Expires:** {row['expires_at']}"
                embed.color = 0xFF0000
            else:
                embed.description = (
                    "✅ User is active.\nUse the dropdown below to take action."
                )
                embed.color = 0x2ECC71

        elif self.tab == "global":
            embed.title = "🌐 Global Control"
            m_mode = self.bot.config_cache.get("maintenance_mode", "0")
            status = "🔴 ACTIVE" if m_mode == "1" else "🟢 INACTIVE"
            embed.description = f"**Maintenance Mode:** {status}\n\nUse this tab to control global bot state."

        elif self.tab == "sql":
            embed.title = "⚠️ Raw SQL Executor"
            embed.description = "Execute raw SQL queries against the database.\n**WARNING:** Actions here cannot be undone."
            embed.color = 0xFF0000

        elif self.tab == "promo":
            embed.title = "🎁 Promo Code Manager"
            embed.description = "Create, edit, or delete promo codes."

            with database.get_connection() as conn:
                codes = conn.execute(
                    "SELECT code_key, description, active FROM promo_codes ORDER BY code_key ASC LIMIT 10"
                ).fetchall()

            lines = []
            for c in codes:
                status = "✅" if c["active"] else "🛑"
                lines.append(f"{status} `{c['code_key']}`")
            if not lines:
                lines.append("*No promo codes found.*")
            embed.add_field(name="Recent Codes", value="\n".join(lines), inline=False)

        pending_txt = []
        for col, val in self.cart["profile"].items():
            if col == "toggle_elite":
                pending_txt.append("• **Toggle:** Elite Status")
            elif col == "heal":
                pending_txt.append("• **Action:** Full Heal")
            else:
                sign = "+" if val > 0 else ""
                pending_txt.append(f"• **{col}:** {sign}{val}")
        for item in self.cart["inv_add"]:
            pending_txt.append(f"• **Add:** {item['item']} (Lvl {item['lvl']})")
        for iid, changes in self.cart["inv_edit"].items():
            pending_txt.append(f"• **Edit #{iid}:** {changes}")
        for iid in self.cart["inv_del"]:
            pending_txt.append(f"• **Delete:** Item #{iid}")

        if pending_txt:
            embed.add_field(
                name="🛒 Pending Changes",
                value="\n".join(pending_txt),
                inline=False,
            )

        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(NavSelect(self.tab, self.bot))

        if any(self.cart.values()):
            self.add_item(CommitButton())
            self.add_item(DiscardButton())

        if self.tab == "profile":
            self.add_item(ProfileEditSelect(self.bot))
        elif self.tab == "inventory":
            self.add_item(InvFilterSelect(self.bot, self.inv_filter))
            inv = database.get_user_inventory(self.target_id)
            filtered = [
                i
                for i in inv
                if game_data.get_item(i["item_id"])["type"] == self.inv_filter
            ]
            filtered.sort(key=lambda x: x["level"], reverse=True)
            if filtered:
                self.add_item(InvItemSelect(self.bot, filtered[:25]))
            else:
                self.add_item(Button(label="Empty Category", disabled=True, row=2))
            if self.inv_item_id:
                self.add_item(EditItemLevelButton(self.inv_item_id))
                self.add_item(EditItemModButton(self.inv_item_id))
                self.add_item(DeleteItemButton(self.inv_item_id))
            self.add_item(AddItemButton())

        elif self.tab == "god_mode":
            u = database.get_user_data(self.target_id)
            state = u["account_state"] if u else "LEGIT"

            if state == "LEGIT":
                self.add_item(EnterGodModeBtn())
                self.add_item(EnterSandboxBtn())
            else:
                self.add_item(ReturnLegitBtn())
                self.add_item(ResetModeBtn(state))

        elif self.tab == "inbox":
            self.add_item(InboxTemplateSelect())
            self.add_item(InboxWizardButton())
            self.add_item(SendCustomMailButton())
        elif self.tab == "db":
            self.add_item(ScopeToggleButton(self.scope))
            self.add_item(DBTableSelect(self.scope))
        elif self.tab == "moderation":
            self.add_item(ModerationActionSelect(self.target_id))
        elif self.tab == "global":
            self.add_item(GlobalActionSelect())
        elif self.tab == "sql":
            self.add_item(RunSQLButton())
            self.add_item(GMGuideButton())
        elif self.tab == "promo":
            self.add_item(CreatePromoButton())
            self.add_item(EditPromoSelect(self.bot))

    async def commit_changes(self, interaction):
        logs = []
        u = (
            dict(database.get_user_data(self.target_id))
            if database.get_user_data(self.target_id)
            else {}
        )
        updates = {}
        for col, delta in self.cart["profile"].items():
            if col == "toggle_elite":
                updates["is_elite"] = 0 if u.get("is_elite") else 1
                logs.append("Toggled Elite")
            elif col == "heal":
                lvl, _, _ = utils.get_level_info(u.get("xp", 0))
                updates["current_hp"] = utils.get_max_hp(self.target_id, lvl)
                logs.append("Healed User")
            else:
                current = u.get(col, 0)
                updates[col] = max(0, current + delta)
                logs.append(f"{col}: {delta:+}")

        if updates:
            database.update_user_stats(self.target_id, updates)
        for item in self.cart["inv_add"]:
            database.add_item_to_inventory(
                self.target_id, item["item"], item["mod"], item["lvl"]
            )
            logs.append(f"Added {item['item']}")

        with database.get_connection() as conn:
            for iid, changes in self.cart["inv_edit"].items():
                for col, val in changes.items():
                    conn.execute(
                        f"UPDATE inventory SET {col} = ? WHERE instance_id = ?",
                        (val, iid),
                    )
            conn.commit()
        if self.cart["inv_edit"]:
            logs.append(f"Edited {len(self.cart['inv_edit'])} items")
        for iid in self.cart["inv_del"]:
            database.delete_inventory_item(iid)
        if self.cart["inv_del"]:
            logs.append(f"Deleted {len(self.cart['inv_del'])} items")

        database.log_gm_action(
            interaction.user.id,
            self.target_id,
            "BATCH_COMMIT",
            {"summary": logs},
        )
        self.cart = {
            "profile": {},
            "inv_add": [],
            "inv_edit": {},
            "inv_del": [],
        }
        self.inv_item_id = None
        self.update_components()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class CommitButton(Button):
    def __init__(self):
        super().__init__(
            label="Commit Changes",
            style=discord.ButtonStyle.success,
            emoji="💾",
            row=4,
        )

    async def callback(self, i):
        await self.view.commit_changes(i)


class DiscardButton(Button):
    def __init__(self):
        super().__init__(
            label="Discard", style=discord.ButtonStyle.danger, emoji="🗑️", row=4
        )

    async def callback(self, i):
        self.view.cart = {
            "profile": {},
            "inv_add": [],
            "inv_edit": {},
            "inv_del": [],
        }
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class NavSelect(Select):
    def __init__(self, current, bot):
        def e(k):
            return utils.safe_emoji(utils.get_emoji(bot, k))

        opts = [
            discord.SelectOption(
                label="Profile",
                value="profile",
                emoji=utils.safe_emoji(config.ELITE_HUNTER_ICON),
                default=(current == "profile"),
            ),
            discord.SelectOption(
                label="Inventory",
                value="inventory",
                emoji=e("empty_gadget"),
                default=(current == "inventory"),
            ),
            discord.SelectOption(
                label="God Mode",
                value="god_mode",
                emoji="⚡",
                default=(current == "god_mode"),
                description="Data Injection Tools",
            ),
            discord.SelectOption(
                label="Inbox",
                value="inbox",
                emoji="📨",
                default=(current == "inbox"),
            ),
            discord.SelectOption(
                label="Promo Codes",
                value="promo",
                emoji="🎁",
                default=(current == "promo"),
            ),
            discord.SelectOption(
                label="Moderation",
                value="moderation",
                emoji=utils.safe_emoji(config.DOJO_ICON),
                default=(current == "moderation"),
            ),
            discord.SelectOption(
                label="DB Console",
                value="db",
                emoji=utils.safe_emoji(config.GEAR_POWER_EMOJI),
                default=(current == "db"),
            ),
            discord.SelectOption(
                label="Global Control",
                value="global",
                emoji="🌐",
                default=(current == "global"),
            ),
            discord.SelectOption(
                label="Raw SQL",
                value="sql",
                emoji="⚠️",
                default=(current == "sql"),
            ),
        ]
        super().__init__(placeholder="Navigate...", options=opts, row=0)

    async def callback(self, i):
        self.view.tab = self.values[0]
        self.view.inv_item_id = None
        if self.view.tab in [
            "profile",
            "inventory",
            "inbox",
            "moderation",
            "god_mode",
        ]:
            self.view.scope = "user"
        else:
            self.view.scope = "global"
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class EnterGodModeBtn(Button):
    def __init__(self):
        super().__init__(
            label="Enter GOD MODE",
            style=discord.ButtonStyle.danger,
            emoji="⚡",
            row=1,
        )

    async def callback(self, i):
        target_id = self.view.target_id

        success, msg = database.backup_account(target_id)
        if not success:
            return await i.response.send_message(
                f"❌ **Safety Stop:** Backup Failed.\nReason: {msg}",
                ephemeral=True,
            )

        database.inject_god_mode(target_id)

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await i.followup.send(
            "⚡ **GOD MODE ACTIVATED.** Backup created.", ephemeral=True
        )


class EnterSandboxBtn(Button):
    def __init__(self):
        super().__init__(
            label="Enter SANDBOX",
            style=discord.ButtonStyle.secondary,
            emoji="📦",
            row=1,
        )

    async def callback(self, i):
        target_id = self.view.target_id

        success, msg = database.backup_account(target_id)
        if not success:
            return await i.response.send_message(
                f"❌ **Safety Stop:** Backup Failed.\nReason: {msg}",
                ephemeral=True,
            )

        database.inject_sandbox_mode(target_id)

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await i.followup.send(
            "📦 **SANDBOX ACTIVATED.** Backup created.", ephemeral=True
        )


class ReturnLegitBtn(Button):
    def __init__(self):
        super().__init__(
            label="Return to Legit",
            style=discord.ButtonStyle.success,
            emoji="🔙",
            row=1,
        )

    async def callback(self, i):
        target_id = self.view.target_id

        success, msg = database.restore_account(target_id)
        if not success:
            return await i.response.send_message(
                f"❌ Restore Failed: {msg}\nCheck user_snapshots table.",
                ephemeral=True,
            )

        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        await i.followup.send("✅ **Restored Legit Account.**", ephemeral=True)


class ResetModeBtn(Button):
    def __init__(self, state):
        super().__init__(
            label=f"Reset {state}",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=2,
        )
        self.state = state

    async def callback(self, i):
        if self.state == "GOD":
            database.inject_god_mode(self.view.target_id)
        else:
            database.inject_sandbox_mode(self.view.target_id)

        await i.response.send_message(f"✅ **{self.state} Refreshed.**", ephemeral=True)


class ProfileEditSelect(Select):
    def __init__(self, bot):
        def e(k):
            return utils.safe_emoji(k)

        opts = [
            discord.SelectOption(label="XP", value="xp", emoji=e(config.XP_EMOJI)),
            discord.SelectOption(
                label="Elite XP", value="elite_xp", emoji=e(config.ELITE_EMOJI)
            ),
            discord.SelectOption(
                label="Mo.Gold", value="mo_gold", emoji=e(config.MOGOLD_EMOJI)
            ),
            discord.SelectOption(
                label="Tokens",
                value="merch_tokens",
                emoji=e(config.MERCH_TOKEN_EMOJI),
            ),
            discord.SelectOption(
                label="Cores",
                value="chaos_cores",
                emoji=e(config.CHAOS_CORE_EMOJI),
            ),
            discord.SelectOption(
                label="Kits",
                value="chaos_kits",
                emoji=e(config.CHAOS_CORE_EMOJI),
            ),
            discord.SelectOption(
                label="Shards",
                value="chaos_shards",
                emoji=e(config.CHAOS_SHARD_EMOJI),
            ),
            discord.SelectOption(
                label="Toggle Elite Status",
                value="toggle_elite",
                emoji=utils.safe_emoji(config.ELITE_HUNTER_ICON),
            ),
            discord.SelectOption(label="Full Heal", value="heal", emoji="❤️"),
        ]
        super().__init__(placeholder="Modify...", options=opts, row=1)

    async def callback(self, i):
        val = self.values[0]
        if val == "toggle_elite":
            self.view.cart["profile"]["toggle_elite"] = 1
            self.view.update_components()
            await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        elif val == "heal":
            self.view.cart["profile"]["heal"] = 1
            self.view.update_components()
            await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        else:
            await i.response.send_modal(NumberEditModal(self.view, val))


class NumberEditModal(Modal):
    def __init__(self, view, col):
        super().__init__(title=f"Edit {col}")
        self.view = view
        self.col = col
        self.val = TextInput(label="Amount (+/-)", placeholder="+500")
        self.add_item(self.val)

    async def on_submit(self, i):
        try:
            inp = self.val.value.strip()
            delta = int(inp)
            curr = self.view.cart["profile"].get(self.col, 0)
            self.view.cart["profile"][self.col] = curr + delta
            self.view.update_components()
            await i.response.edit_message(embed=self.view.get_embed(), view=self.view)
        except:
            await i.response.send_message("Invalid number.", ephemeral=True)


class InvFilterSelect(Select):
    def __init__(self, bot, current):
        def e(k):
            return utils.safe_emoji(utils.get_emoji(bot, k))

        opts = [
            discord.SelectOption(
                label="Weapons",
                value="weapon",
                emoji=e("empty_weapon"),
                default=(current == "weapon"),
            ),
            discord.SelectOption(
                label="Gadgets",
                value="gadget",
                emoji=e("empty_gadget"),
                default=(current == "gadget"),
            ),
            discord.SelectOption(
                label="Passives",
                value="passive",
                emoji=e("empty_passive"),
                default=(current == "passive"),
            ),
            discord.SelectOption(
                label="Rings",
                value="smart_ring",
                emoji=e("empty_ring"),
                default=(current == "smart_ring"),
            ),
            discord.SelectOption(
                label="Modules",
                value="elite_module",
                emoji=e("empty_module"),
                default=(current == "elite_module"),
            ),
        ]
        super().__init__(placeholder="Filter...", options=opts, row=1)

    async def callback(self, i):
        self.view.inv_filter = self.values[0]
        self.view.inv_item_id = None
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class InvItemSelect(Select):
    def __init__(self, bot, items):
        opts = []
        for r in items:
            d = game_data.get_item(r["item_id"])
            lbl = f"Lvl {r['level']} {d['name']}"[:100]
            opts.append(
                discord.SelectOption(
                    label=lbl,
                    value=str(r["instance_id"]),
                    emoji=utils.safe_emoji(utils.get_emoji(bot, r["item_id"])),
                )
            )
        super().__init__(placeholder="Select Item...", options=opts, row=2)

    async def callback(self, i):
        self.view.inv_item_id = int(self.values[0])
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class EditItemModButton(Button):
    def __init__(self, inst_id):
        super().__init__(label="Mod", style=discord.ButtonStyle.secondary, row=3)
        self.inst_id = inst_id

    async def callback(self, i):
        self.view.capture_message(i)
        await i.response.send_message(
            "Select Mod:",
            view=ModSelectView(self.view, self.inst_id),
            ephemeral=True,
        )


class ModSelectView(View):
    def __init__(self, parent_view, inst_id):
        super().__init__(timeout=6)
        self.add_item(ModSelect(parent_view, inst_id))


class ModSelect(Select):
    def __init__(self, parent_view, inst_id):
        super().__init__(
            placeholder="Mod...",
            options=[
                discord.SelectOption(label=m, value=m) for m in config.VALID_MODIFIERS
            ],
        )
        self.parent_view, self.inst_id = parent_view, inst_id

    async def callback(self, i):
        if self.inst_id not in self.parent_view.cart["inv_edit"]:
            self.parent_view.cart["inv_edit"][self.inst_id] = {}
        self.parent_view.cart["inv_edit"][self.inst_id]["modifier"] = self.values[0]
        self.parent_view.update_components()
        await self.parent_view.message.edit(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )
        await i.response.send_message(f"Staged: {self.values[0]}", ephemeral=True)


class EditItemLevelButton(Button):
    def __init__(self, inst_id):
        super().__init__(label="Lvl", style=discord.ButtonStyle.primary, row=3)
        self.inst_id = inst_id

    async def callback(self, i):
        self.view.capture_message(i)
        await i.response.send_modal(ItemLevelModal(self.view, self.inst_id))


class ItemLevelModal(Modal):
    def __init__(self, view, inst_id):
        super().__init__(title="Level")
        self.view, self.inst_id, self.val = (
            view,
            inst_id,
            TextInput(label="1-50"),
        )
        self.add_item(self.val)

    async def on_submit(self, i):
        try:
            v = int(self.val.value)
            if 1 <= v <= 50:
                if self.inst_id not in self.view.cart["inv_edit"]:
                    self.view.cart["inv_edit"][self.inst_id] = {}
                self.view.cart["inv_edit"][self.inst_id]["level"] = v
                self.view.update_components()
                await self.view.message.edit(
                    embed=self.view.get_embed(), view=self.view
                )
                await i.response.send_message("Staged.", ephemeral=True)
            else:
                await i.response.send_message("1-50 only.", ephemeral=True)
        except:
            await i.response.send_message("Invalid.", ephemeral=True)


class DeleteItemButton(Button):
    def __init__(self, inst_id):
        super().__init__(label="Delete", style=discord.ButtonStyle.danger, row=3)
        self.inst_id = inst_id

    async def callback(self, i):
        if self.inst_id not in self.view.cart["inv_del"]:
            self.view.cart["inv_del"].append(self.inst_id)
        self.view.inv_item_id = None
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class AddItemButton(Button):
    def __init__(self):
        super().__init__(
            label="Spawn New Item", style=discord.ButtonStyle.success, row=4
        )

    async def callback(self, i):
        self.view.capture_message(i)
        await i.response.send_message(
            view=AddItemView(self.view.bot, self.view), ephemeral=True
        )


class AddItemView(View):
    def __init__(self, bot, parent):
        super().__init__(timeout=60)
        self.bot, self.parent_view = bot, parent
        self.add_item(AddItemCategorySelect())


class AddItemCategorySelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Category...",
            options=[
                discord.SelectOption(label=l, value=v)
                for l, v in [
                    ("Weapon", "weapon"),
                    ("Gadget", "gadget"),
                    ("Passive", "passive"),
                    ("Ring", "smart_ring"),
                ]
            ],
        )

    async def callback(self, i):
        await i.response.send_message(
            view=AddItemItemSelectView(
                self.view.bot, self.values[0], self.view.parent_view
            ),
            ephemeral=True,
        )


class AddItemItemSelectView(View):
    def __init__(self, bot, cat, parent):
        super().__init__(timeout=60)
        items = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == cat][:25]
        self.add_item(AddItemFinalSelect(items, bot, parent))


class AddItemFinalSelect(Select):
    def __init__(self, items, bot, parent):
        self.parent_view = parent
        opts = [
            discord.SelectOption(
                label=game_data.get_item(k)["name"],
                value=k,
                emoji=utils.safe_emoji(utils.get_emoji(bot, k)),
            )
            for k in items
        ]
        super().__init__(placeholder="Item...", options=opts)

    async def callback(self, i):
        self.parent_view.cart["inv_add"].append(
            {"item": self.values[0], "mod": "Standard", "lvl": 1}
        )
        self.parent_view.update_components()
        await self.parent_view.message.edit(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )
        await i.response.send_message(f"Staged Add: {self.values[0]}", ephemeral=True)


class ScopeToggleButton(Button):
    def __init__(self, scope):
        label = "Switch to Global" if scope == "user" else "Switch to User"
        style = (
            discord.ButtonStyle.danger
            if scope == "user"
            else discord.ButtonStyle.success
        )
        super().__init__(label=label, style=style, row=1)

    async def callback(self, i):
        self.view.scope = "global" if self.view.scope == "user" else "user"
        self.view.update_components()
        await i.response.edit_message(embed=self.view.get_embed(), view=self.view)


class DBTableSelect(Select):
    def __init__(self, scope):
        tables = (
            [
                "users",
                "inventory",
                "gear_kits",
                "inbox_messages",
                "user_blacklist",
            ]
            if scope == "user"
            else [
                "shop_state",
                "active_deals",
                "active_system_events",
                "promo_codes",
                "season_config",
                "system_config",
                "guild_blacklist",
            ]
        )
        super().__init__(
            placeholder="Select Table...",
            options=[discord.SelectOption(label=t, value=t) for t in tables],
            row=2,
        )

    async def callback(self, i):
        self.view.capture_message(i)
        await i.response.send_message(
            view=DBRowView(
                self.view.bot,
                self.view.target_id,
                self.values[0],
                self.view.scope,
                self.view,
            ),
            ephemeral=True,
        )


class DBRowView(View):
    def __init__(self, bot, target_id, table, scope, parent):
        super().__init__(timeout=300)
        (
            self.bot,
            self.table,
            self.parent_view,
            self.target_id,
            self.scope,
            self.selected_pk,
        ) = (bot, table, parent, target_id, scope, None)
        self.pk_name = "user_id" if scope == "user" else self.get_pk_name(table)
        if scope == "global":
            self.add_item(DBGlobalRowSelect(self.get_rows(table), self.pk_name))
        else:
            self.selected_pk = target_id
            self.add_cols()
            self.show_row_data()
        self.add_item(AddRowButton(table, target_id if scope == "user" else None))
        self.add_item(BackButton(parent))

    def get_pk_name(self, table):
        if table == "shop_state":
            return "id"
        if table == "active_deals":
            return "deal_id"
        if table == "promo_codes":
            return "code_key"
        if table == "season_config":
            return "season_id"
        if table == "guild_blacklist":
            return "guild_id"
        if table == "system_config":
            return "key"
        return "id"

    def get_rows(self, table):
        pk = self.get_pk_name(table)
        with database.get_connection() as conn:
            return conn.execute(
                f"SELECT * FROM {table} ORDER BY {pk} DESC LIMIT 25"
            ).fetchall()

    def show_row_data(self):
        embed = discord.Embed(title=f"Table: {self.table}", color=0x95A5A6)
        try:
            with database.get_connection() as conn:
                row = conn.execute(
                    f"SELECT * FROM {self.table} WHERE {self.pk_name} = ?",
                    (self.selected_pk,),
                ).fetchone()
            if row:
                desc = ""
                for k in row.keys():
                    val = str(row[k])
                    if len(val) > 50:
                        val = val[:50] + "..."
                    desc += f"**{k}**: `{val}`\n"
                embed.description = desc
            else:
                embed.description = "Row not found."
        except Exception as e:
            embed.description = f"Error: {e}"
        return embed

    def add_cols(self):
        try:
            with database.get_connection() as conn:
                info = conn.execute(f"PRAGMA table_info({self.table})").fetchall()
                cols = [r["name"] for r in info]
        except:
            cols = []
        if cols:
            self.add_item(
                DBColumnSelect(cols[:25], self.table, self.selected_pk, self.pk_name)
            )

        if self.selected_pk:
            self.add_item(DeleteRowButton(self.table, self.pk_name, self.selected_pk))


class AddRowButton(Button):
    def __init__(self, table, target_id=None):
        super().__init__(
            label="Add Row",
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=3,
        )
        self.table = table
        self.target_id = target_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            InsertRowModal(self.table, self.target_id)
        )


class InsertRowModal(Modal):
    def __init__(self, table, target_id=None):
        super().__init__(title=f"Insert into {table}")
        self.table = table

        default_val = ""
        if target_id and table in ["inventory", "gear_kits", "inbox_messages"]:
            default_val = f'{{"user_id": {target_id}}}'

        self.data = TextInput(
            label="Row Data (JSON)",
            style=discord.TextStyle.paragraph,
            placeholder='{"column": "value", ...}',
            default=default_val,
            required=True,
        )
        self.add_item(self.data)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            data = json.loads(self.data.value)
        except:
            return await interaction.response.send_message(
                "Invalid JSON format.", ephemeral=True
            )

        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(["?"] * len(values))
        col_str = ", ".join(columns)

        sql = f"INSERT INTO {self.table} ({col_str}) VALUES ({placeholders})"

        try:
            with database.get_connection() as conn:
                conn.execute(sql, values)
                conn.commit()
            await interaction.response.send_message(
                f"✅ Row added to `{self.table}`.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ SQL Error: {e}", ephemeral=True
            )


class DBGlobalRowSelect(Select):
    def __init__(self, rows, pk_name):
        opts = []
        for r in rows:
            val = str(r[pk_name])
            label = str(val)
            for k in ["name", "code_key", "offer_name", "key"]:
                if k in r.keys():
                    label = f"{val} ({r[k]})"
                    break
            opts.append(discord.SelectOption(label=label, value=val))
        if not opts:
            opts.append(discord.SelectOption(label="Empty Table", value="none"))
        super().__init__(placeholder="Select Row...", options=opts)

    async def callback(self, i):
        if self.values[0] == "none":
            return
        self.view.selected_pk = self.values[0]
        self.view.add_cols()
        self.view.remove_item(self)
        embed = self.view.show_row_data()
        await i.response.edit_message(embed=embed, view=self.view)


class DeleteRowButton(Button):
    def __init__(self, table, pk_name, pk_val):
        super().__init__(
            label="Delete Row",
            style=discord.ButtonStyle.danger,
            row=3,
            emoji="🗑️",
        )
        self.table = table
        self.pk_name = pk_name
        self.pk_val = pk_val

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            DeleteRowConfirmModal(self.table, self.pk_name, self.pk_val)
        )


class DeleteRowConfirmModal(Modal):
    def __init__(self, table, pk_name, pk_val):
        super().__init__(title="Confirm Deletion")
        self.table = table
        self.pk_name = pk_name
        self.pk_val = pk_val
        self.verify = TextInput(
            label="Type DELETE",
            placeholder="DELETE",
            min_length=6,
            max_length=6,
            required=True,
        )
        self.add_item(self.verify)

    async def on_submit(self, i: discord.Interaction):
        if self.verify.value.upper() != "DELETE":
            return await i.response.send_message("Deletion cancelled.", ephemeral=True)

        try:
            with database.get_connection() as conn:
                conn.execute(
                    f"DELETE FROM {self.table} WHERE {self.pk_name} = ?",
                    (self.pk_val,),
                )
                conn.commit()
            await i.response.send_message(
                f"✅ Row `{self.pk_val}` deleted from `{self.table}`.",
                ephemeral=True,
            )
        except Exception as e:
            await i.response.send_message(f"❌ Error: {e}", ephemeral=True)


class DBColumnSelect(Select):
    def __init__(self, cols, table, pk_val, pk_name):
        self.table, self.pk_val, self.pk_name = table, pk_val, pk_name
        super().__init__(
            placeholder="Select Column to Edit...",
            options=[discord.SelectOption(label=c, value=c) for c in cols],
        )

    async def callback(self, i):
        col, curr_val = self.values[0], ""
        try:
            with database.get_connection() as conn:
                row = conn.execute(
                    f"SELECT {col} FROM {self.table} WHERE {self.pk_name} = ?",
                    (self.pk_val,),
                ).fetchone()
                curr_val = str(row[0]) if row else ""
        except:
            pass
        if col == "mission_state":
            await i.response.send_message(
                view=MissionWizardView(
                    self.view.bot,
                    self.view.parent_view.target_id,
                    self.view.parent_view,
                ),
                ephemeral=True,
            )
        elif col == "active_jobs":
            await i.response.send_message(
                view=JobWizardView(
                    self.view.bot,
                    self.view.parent_view.target_id,
                    self.view.parent_view,
                ),
                ephemeral=True,
            )
        else:
            await i.response.send_modal(
                RawEditorModal(
                    self.view.parent_view,
                    col,
                    curr_val,
                    self.table,
                    self.pk_name,
                    self.pk_val,
                )
            )


class MissionWizardView(View):
    def __init__(self, bot, target_id, parent):
        super().__init__(timeout=60)
        self.bot, self.target_id, self.parent_view = bot, target_id, parent
        self.add_item(MissionSelect())
        self.add_item(MissionActionSelect())


class MissionSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Mission...",
            options=[discord.SelectOption(label=k, value=k) for k in MISSIONS.keys()],
        )


class MissionActionSelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Action...",
            options=[
                discord.SelectOption(label=l, value=v)
                for l, v in [
                    ("Set Active", "active"),
                    ("Complete", "complete"),
                    ("Step 0", "step_0"),
                ]
            ],
        )

    async def callback(self, i):
        mid, action = self.view.children[0].values[0], self.values[0]
        u = dict(database.get_user_data(self.view.target_id))
        ms = json.loads(u["mission_state"])
        if action == "active":
            if mid not in ms["active"]:
                ms["active"].append(mid)
            if mid in ms["completed"]:
                ms["completed"].remove(mid)
            ms["states"][mid] = {"step": 0, "prog": 0}
        elif action == "complete":
            if mid in ms["active"]:
                ms["active"].remove(mid)
            if mid not in ms["completed"]:
                ms["completed"].append(mid)
        database.update_user_stats(
            self.view.target_id, {"mission_state": json.dumps(ms)}
        )
        await i.response.send_message("Updated.", ephemeral=True)


class JobWizardView(View):
    def __init__(self, bot, target_id, parent):
        super().__init__(timeout=60)
        self.target_id = target_id
        self.add_item(Button(label="Clear", custom_id="c"))
        self.add_item(Button(label="Add", custom_id="a"))

    async def interaction_check(self, i):
        if i.data["custom_id"] == "c":
            database.update_user_stats(self.target_id, {"active_jobs": "[]"})
        else:
            cog = i.client.get_cog("Jobs")
            new = cog.generate_jobs(self.target_id, 1)
            u = dict(database.get_user_data(self.target_id))
            jobs = json.loads(u["active_jobs"]) + new
            database.update_user_stats(
                self.target_id, {"active_jobs": json.dumps(jobs)}
            )
        await i.response.send_message("Done.", ephemeral=True)
        return False


class RawEditorModal(Modal):
    def __init__(self, view, col, default, table=None, pk_name=None, pk_val=None):
        super().__init__(title=f"Edit {col}")
        (
            self.view,
            self.col,
            self.table,
            self.pk_name,
            self.pk_val,
            self.val,
        ) = (
            view,
            col,
            table,
            pk_name,
            pk_val,
            TextInput(
                label="Value",
                default=default,
                style=discord.TextStyle.paragraph,
            ),
        )
        self.add_item(self.val)

    async def on_submit(self, i):
        tbl, pk, val = (
            self.table or "users",
            self.pk_name or "user_id",
            self.pk_val or self.view.target_id,
        )
        with database.get_connection() as c:
            c.execute(
                f"UPDATE {tbl} SET {self.col} = ? WHERE {pk} = ?",
                (self.val.value, val),
            )
            c.commit()
        await i.response.send_message("Updated.", ephemeral=True)


class GlobalActionSelect(Select):
    def __init__(self):
        m_mode = database.get_config("maintenance_mode", "0")
        mode_label, mode_emoji = (
            ("Disable Maintenance", "🟢")
            if m_mode == "1"
            else ("Enable Maintenance", "🔴")
        )
        options = [
            discord.SelectOption(
                label=mode_label, value="toggle_maintenance", emoji=mode_emoji
            ),
            discord.SelectOption(
                label="Force Shop Refresh", value="refresh_shop", emoji="🔄"
            ),
            discord.SelectOption(
                label="Force Season Rotation", value="rotate_season", emoji="🗓️"
            ),
        ]
        super().__init__(placeholder="Global Actions...", options=options, row=1)

    async def callback(self, i: discord.Interaction):
        val = self.values[0]
        if val == "toggle_maintenance":
            current = database.get_config("maintenance_mode", "0")
            new_val = "1" if current == "0" else "0"
            database.set_config("maintenance_mode", new_val)
                                                    
            self.view.bot.update_cache("maintenance_mode", new_val)

            await i.response.send_message(
                f"Maintenance Mode set to: {new_val}", ephemeral=True
            )
        elif val == "refresh_shop":
            database.update_shop_seed(12345, "2000-01-01")
            await i.response.send_message("Shop date reset.", ephemeral=True)
        elif val == "rotate_season":
            season_manager.rotate_season(datetime.now())
            await i.response.send_message("Season rotated.", ephemeral=True)
        self.view.update_components()
        await i.edit_original_response(embed=self.view.get_embed(), view=self.view)


class ModerationActionSelect(Select):
    def __init__(self, target_id):
        self.target_id = target_id
        is_banned, _ = database.is_user_blacklisted(target_id)
        options = [
            discord.SelectOption(
                label="Reset Daily Limits", value="reset_dailies", emoji="☀️"
            )
        ]
        (
            options.append(
                discord.SelectOption(label="Unban User", value="unban", emoji="🕊️")
            )
            if is_banned
            else options.append(
                discord.SelectOption(label="Blacklist User", value="ban", emoji="🔨")
            )
        )
        super().__init__(placeholder="Take Action...", options=options, row=1)

    async def callback(self, i: discord.Interaction):
        val = self.values[0]
        if val == "reset_dailies":
            database.update_user_stats(
                self.target_id,
                {
                    "daily_xp_total": config.XP_PER_DAY,
                    "daily_fusions": 0,
                    "last_daily_reset": "2000-01-01T00:00:00",
                },
            )
            await i.response.send_message("✅ Dailies force-reset.", ephemeral=True)
        elif val == "unban":
            database.unblacklist_user(self.target_id)
                                      
            if self.target_id in self.view.bot.blacklist_cache:
                del self.view.bot.blacklist_cache[self.target_id]

            await i.response.send_message("User unbanned.", ephemeral=True)
            self.view.update_components()
            await i.edit_original_response(embed=self.view.get_embed(), view=self.view)
        elif val == "ban":
            await i.response.send_message(
                view=UserBlacklistDateView(self.view.bot, self.target_id),
                ephemeral=True,
            )


class RunSQLButton(Button):
    def __init__(self):
        super().__init__(
            label="EXECUTE RAW SQL",
            style=discord.ButtonStyle.danger,
            emoji="⚠️",
            row=1,
        )

    async def callback(self, i):
        await i.response.send_modal(SQLModal())


class GMGuideButton(Button):
    def __init__(self):
        super().__init__(
            label="GM Guide",
            style=discord.ButtonStyle.secondary,
            emoji="❓",
            row=1,
        )

    async def callback(self, i):
        embed = discord.Embed(title="GM Guide", color=0x3498DB)
        embed.description = '**Table Quick Reference**\n`users`: user_id, xp, mo_gold, active_jobs (JSON)\n`inventory`: instance_id, user_id, item_id, modifier\n`gear_kits`: kit_id, user_id, weapon_id (instance_id)\n\n**JSON Examples**\n`active_jobs`: `[{"target": "Drog", "count": 5, "progress": 0}]`\n**WARNING:** Deleting rows in `users` cascades deletes to inventory!'
        await i.response.send_message(embed=embed, ephemeral=True)


class SQLModal(Modal):
    def __init__(self):
        super().__init__(title="DANGER: Raw SQL Executor")
        self.query = TextInput(
            label="Query",
            style=discord.TextStyle.paragraph,
            required=True,
            custom_id="sql_query",
        )
        self.add_item(self.query)

    async def on_submit(self, i):
        try:
            result, rowcount = database.run_raw_sql(self.query.value)
            res_str = (
                "\n".join([str(tuple(r)) for r in result[:10]])
                + ("\n... (truncated)" if len(result) > 10 else "")
                if result
                else f"Rows modified: {rowcount}"
            )
            await i.response.send_message(
                f"✅ **Success.** Result:\n```\n{res_str}\n```", ephemeral=True
            )
        except Exception as e:
            await i.response.send_message(
                f"❌ **Error:**\n```\n{e}\n```", ephemeral=True
            )


class UserBlacklistDateView(View):
    def __init__(self, bot, target_id):
        super().__init__(timeout=60)
        self.bot, self.target_id = bot, target_id
        opts = [
            discord.SelectOption(label=l, value=v)
            for l, v in [
                ("1 Day", "1d"),
                ("3 Days", "3d"),
                ("1 Week", "7d"),
                ("1 Month", "30d"),
                ("1 Year", "365d"),
            ]
        ] + [
            discord.SelectOption(label="Permanent", value="perm", emoji="🛑"),
            discord.SelectOption(label="Custom Date", value="custom", emoji="📅"),
        ]
        self.add_item(UserBlacklistDateSelect(opts))


class UserBlacklistDateSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="Select Duration...", options=options)

    async def callback(self, i):
        val = self.values[0]
        if val == "custom":
            await i.response.send_modal(
                UserBlacklistCustomDateModal(self.view.target_id)
            )
        else:
            expiry = (
                "PERMANENT"
                if val == "perm"
                else (datetime.utcnow() + timedelta(days=int(val[:-1]))).isoformat()
            )
            await i.response.send_modal(
                UserBlacklistReasonModal(self.view.target_id, expiry)
            )


class UserBlacklistCustomDateModal(Modal):
    def __init__(self, target_id):
        super().__init__(title="Custom Ban Date")
        self.target_id = target_id
        self.date_in = TextInput(label="YYYY-MM-DD", placeholder="2025-12-31")
        self.add_item(self.date_in)

    async def on_submit(self, i):
        try:
            dt = datetime.strptime(self.date_in.value, "%Y-%m-%d")
            if dt < datetime.utcnow():
                return await i.response.send_message(
                    "Date must be in the future.", ephemeral=True
                )
            await i.response.send_modal(
                UserBlacklistReasonModal(self.target_id, dt.isoformat())
            )
        except:
            await i.response.send_message(
                "Invalid date format. Use YYYY-MM-DD.", ephemeral=True
            )


class UserBlacklistReasonModal(Modal):
    def __init__(self, target_id, expiry):
        super().__init__(title="Ban Reason")
        self.target_id, self.expiry, self.reason = (
            target_id,
            expiry,
            TextInput(label="Reason", style=discord.TextStyle.paragraph),
        )
        self.add_item(self.reason)

    async def on_submit(self, i):
        database.blacklist_user(
            i.user.id, self.target_id, self.reason.value, self.expiry
        )
        database.log_gm_action(
            i.user.id,
            self.target_id,
            "BAN_USER",
            {"expiry": self.expiry, "reason": self.reason.value},
        )

                                      
        i.client.blacklist_cache[self.target_id] = {
            "user_id": self.target_id,
            "reason": self.reason.value,
            "expires_at": self.expiry,
        }

        await i.response.send_message(
            f"⛔ **User Blacklisted.**\nExpires: {self.expiry}", ephemeral=True
        )


class InboxWizardButton(Button):
    def __init__(self):
        super().__init__(label="Inbox Wizard", style=discord.ButtonStyle.primary, row=2)

    async def callback(self, i):

        self.view.capture_message(i)
        await i.response.send_modal(InboxMetadataModal(self.view))


class InboxTemplateSelect(Select):
    def __init__(self):
        opts = [
            discord.SelectOption(
                label=tpl["label"],
                value=str(idx),
                description=tpl["title"][:100],
            )
            for idx, tpl in enumerate(INBOX_TEMPLATES)
        ]
        super().__init__(placeholder="Start with Template...", options=opts, row=1)

    async def callback(self, i):
        template = INBOX_TEMPLATES[int(self.values[0])]
        self.view.capture_message(i)

        await i.response.send_modal(InboxMetadataModal(self.view, template))


class InboxMetadataModal(Modal):
    def __init__(self, view, template=None):
        super().__init__(title="Inbox Wizard: Metadata")
        self.view = view
        self.template = template

        self.title_in = TextInput(
            label="Title", default=template["title"] if template else None
        )
        self.msg = TextInput(
            label="Message Body",
            style=discord.TextStyle.paragraph,
            default=template["body"] if template else None,
            required=False,
        )
        self.sender = TextInput(
            label="Sender Name", default="GM System", required=False
        )

        self.add_item(self.title_in)
        self.add_item(self.msg)
        self.add_item(self.sender)

    async def on_submit(self, i):
        rewards = self.template["rewards"].copy() if self.template else {}

        builder = RewardBuilderView(
            self.view.bot,
            i.user.id,
            target_id=self.view.target_id,
            mode="inbox",
            initial_data={
                "title": self.title_in.value,
                "body": self.msg.value if self.msg.value else "System Message",
                "sender": self.sender.value,
                "rewards": rewards,
            },
        )

        builder.message = await i.response.send_message(
            embed=builder.get_embed(), view=builder, ephemeral=True
        )


class SendCustomMailButton(Button):
    def __init__(self):
        super().__init__(label="Raw JSON", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, i):
        await i.response.send_modal(CustomMailModal(self.view))


class CustomMailModal(Modal):
    def __init__(self, view):
        super().__init__(title="Raw")
        self.view, self.js = view, TextInput(
            label="JSON", style=discord.TextStyle.paragraph
        )
        self.add_item(self.js)

    async def on_submit(self, i):
        try:
            d = json.loads(self.js.value)
            database.send_inbox_message(
                self.view.target_id, "System", "Raw", "Debug", d
            )
            await i.response.send_message("Sent.", ephemeral=True)
        except:
            await i.response.send_message("Bad JSON", ephemeral=True)


class CreatePromoButton(Button):
    def __init__(self):
        super().__init__(
            label="Create Promo Code",
            style=discord.ButtonStyle.success,
            emoji="🎁",
            row=1,
        )

    async def callback(self, i):
        await i.response.send_modal(PromoMetadataModal(self.view.bot))


class EditPromoSelect(Select):
    def __init__(self, bot):
        self.bot = bot

        with database.get_connection() as conn:
            rows = conn.execute(
                "SELECT code_key, description, active FROM promo_codes ORDER BY rowid DESC LIMIT 25"
            ).fetchall()

        options = []
        for r in rows:
            icon = "✅" if r["active"] else "🛑"
            options.append(
                discord.SelectOption(
                    label=r["code_key"],
                    description=r["description"][:50],
                    emoji=icon,
                )
            )

        if not options:
            options.append(discord.SelectOption(label="No Codes Found", value="none"))

        super().__init__(placeholder="Edit Existing Code...", options=options, row=2)

    async def callback(self, i):
        if self.values[0] == "none":
            return

        code_key = self.values[0]
        data = database.get_promo_code(code_key)
        if not data:
            return await i.response.send_message("Code not found.", ephemeral=True)

        rewards = json.loads(data["rewards"])

        builder = RewardBuilderView(
            self.bot,
            i.user.id,
            mode="promo",
            initial_data={
                "code_key": data["code_key"],
                "description": data["description"],
                "expires_at": data["expires_at"],
                "crate_type": data["crate_type"],
                "rewards": rewards,
            },
        )
        builder.message = await i.response.send_message(
            embed=builder.get_embed(), view=builder, ephemeral=True
        )


class PromoMetadataModal(Modal):
    def __init__(self, bot, initial_data=None):
        title = "Edit Promo Code" if initial_data else "Create Promo Code"
        super().__init__(title=title)
        self.bot = bot
        self.initial = initial_data

        self.code = TextInput(
            label="Code Key (Unique)",
            placeholder="SUMMER2026",
            default=initial_data["code_key"] if initial_data else None,
        )
        self.desc = TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            default=initial_data["description"] if initial_data else None,
        )

        default_exp = initial_data["expires_at"] if initial_data else None
        if not default_exp:

            default_exp = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "T" in default_exp:
            default_exp = default_exp.split("T")[0]

        self.expiry = TextInput(
            label="Expiration (YYYY-MM-DD)",
            placeholder="2026-12-31",
            default=default_exp,
        )
        self.crate = TextInput(
            label="Crate Icon (default, merch, mogold)",
            placeholder="default",
            default=initial_data["crate_type"] if initial_data else "default",
        )

        self.add_item(self.code)
        self.add_item(self.desc)
        self.add_item(self.expiry)
        self.add_item(self.crate)

    async def on_submit(self, i):

        try:
            exp_dt = datetime.strptime(self.expiry.value, "%Y-%m-%d")

            exp_iso = exp_dt.replace(hour=23, minute=59, second=59).isoformat()
        except:
            return await i.response.send_message(
                "Invalid Date Format. Use YYYY-MM-DD.", ephemeral=True
            )

        data = {
            "code_key": self.code.value.lower().strip(),
            "description": self.desc.value,
            "expires_at": exp_iso,
            "crate_type": self.crate.value.lower().strip(),
        }

        rewards = {}
        if self.initial and "rewards" in self.initial:
            rewards = self.initial["rewards"]

        data["rewards"] = rewards

        builder = RewardBuilderView(
            self.bot, i.user.id, mode="promo", initial_data=data
        )
        builder.message = await i.response.send_message(
            embed=builder.get_embed(), view=builder, ephemeral=True
        )


class RewardBuilderView(View):
    def __init__(self, bot, admin_id, mode="inbox", target_id=None, initial_data=None):
        super().__init__(timeout=900)
        self.bot = bot
        self.admin_id = admin_id
        self.mode = mode
        self.target_id = target_id
        self.data = initial_data or {"rewards": {}}
        if "rewards" not in self.data:
            self.data["rewards"] = {}
        self.message = None

        self.update_components()

    def get_embed(self):
        title = "🎁 Reward Builder"
        if self.mode == "promo":
            title = f"🎁 Promo Editor: {self.data.get('code_key')}"
            desc = f"**Description:** {self.data.get('description')}\n**Expires:** {self.data.get('expires_at')}\n**Icon:** {self.data.get('crate_type')}"
        else:
            title = "📨 Inbox Composer"
            desc = f"**To:** {self.target_id}\n**Title:** {self.data.get('title')}\n**Sender:** {self.data.get('sender')}\n\n**Body:**\n{self.data.get('body')}"

        rewards = self.data["rewards"]
        reward_lines = []

        if "mo_gold" in rewards:
            reward_lines.append(
                f"• {config.MOGOLD_EMOJI} **{rewards['mo_gold']:,}** Gold"
            )
        if "merch_tokens" in rewards:
            reward_lines.append(
                f"• {config.MERCH_TOKEN_EMOJI} **{rewards['merch_tokens']:,}** Tokens"
            )
        if "chaos_cores" in rewards:
            reward_lines.append(
                f"• {config.CHAOS_CORE_EMOJI} **{rewards['chaos_cores']}** Cores"
            )
        if "chaos_kits" in rewards:
            reward_lines.append(
                f"• {config.CHAOS_CORE_EMOJI} **{rewards['chaos_kits']}** Kits"
            )
        if "chaos_shards" in rewards:
            reward_lines.append(
                f"• {config.CHAOS_SHARD_EMOJI} **{rewards['chaos_shards']:,}** Shards"
            )
        if "xp" in rewards:
            reward_lines.append(f"• {config.XP_EMOJI} **{rewards['xp']:,}** XP")
        if "xp_fuel" in rewards:
            reward_lines.append(
                f"• {config.XP_BOOST_3X_EMOJI} **{rewards['xp_fuel']:,}** Fuel"
            )
        if "elite_tokens" in rewards:
            reward_lines.append(
                f"• {config.ELITE_TOKEN_EMOJI} **{rewards['elite_tokens']:,}** Elite Tokens"
            )

        if "items" in rewards:
            for it in rewards["items"]:
                mod_str = f"[{it['mod']}] " if it["mod"] != "Standard" else ""
                i_def = game_data.get_item(it["id"])
                name = i_def["name"] if i_def else it["id"]
                reward_lines.append(f"• 📦 **{mod_str}{name}** (Lvl {it['level']})")

        if not reward_lines:
            reward_lines.append("*No rewards added yet.*")

        embed = discord.Embed(title=title, description=desc, color=0x9B59B6)
        embed.add_field(
            name="Attached Rewards",
            value="\n".join(reward_lines),
            inline=False,
        )
        return embed

    def update_components(self):
        self.clear_items()

        self.add_item(AddCurrencyBtn("mo_gold", "Gold", config.MOGOLD_EMOJI, 0))
        self.add_item(
            AddCurrencyBtn("merch_tokens", "Tokens", config.MERCH_TOKEN_EMOJI, 0)
        )
        self.add_item(
            AddCurrencyBtn("chaos_cores", "Cores", config.CHAOS_CORE_EMOJI, 0)
        )

        self.add_item(AddCurrencyBtn("chaos_kits", "Kits", config.CHAOS_CORE_EMOJI, 1))
        self.add_item(
            AddCurrencyBtn("chaos_shards", "Shards", config.CHAOS_SHARD_EMOJI, 1)
        )
        self.add_item(
            AddCurrencyBtn("elite_tokens", "Elite T", config.ELITE_TOKEN_EMOJI, 1)
        )
        self.add_item(AddCurrencyBtn("xp", "XP", config.XP_EMOJI, 1))

        self.add_item(AddItemBuilderBtn())
        self.add_item(ClearItemsBtn())

        if self.mode == "promo":
            self.add_item(EditMetadataBtn("Edit Details"))

        self.add_item(SaveRewardBtn(self.mode))

        if self.mode == "promo" and self.data.get("code_key"):
            self.add_item(DeletePromoBtn(self.data["code_key"]))

        self.add_item(CancelRewardBtn())

    async def add_item_to_cart(self, item_dict):
        if "items" not in self.data["rewards"]:
            self.data["rewards"]["items"] = []
        self.data["rewards"]["items"].append(item_dict)


class AddCurrencyBtn(Button):
    def __init__(self, key, label, emoji, row):
        super().__init__(
            label=label,
            emoji=discord.PartialEmoji.from_str(emoji),
            style=discord.ButtonStyle.secondary,
            row=row,
        )
        self.key = key

    async def callback(self, i):
        await i.response.send_modal(CurrencyAmountModal(self.view, self.key))


class CurrencyAmountModal(Modal):
    def __init__(self, view, key):
        super().__init__(title=f"Add {key.replace('_', ' ').title()}")
        self.view = view
        self.key = key
        self.qty = TextInput(label="Amount", placeholder="100")
        self.add_item(self.qty)

    async def on_submit(self, i):
        try:
            val = int(self.qty.value)
            self.view.data["rewards"][self.key] = (
                self.view.data["rewards"].get(self.key, 0) + val
            )
            await i.response.edit_message(embed=self.view.get_embed())
        except:
            await i.response.send_message("Invalid number.", ephemeral=True)


class AddItemBuilderBtn(Button):
    def __init__(self):
        super().__init__(
            label="Add Item",
            emoji="🛠️",
            style=discord.ButtonStyle.primary,
            row=2,
        )

    async def callback(self, i):

        await i.response.send_message(
            view=ItemBuilderView(self.view.bot, self.view), ephemeral=True
        )


class ClearItemsBtn(Button):
    def __init__(self):
        super().__init__(label="Clear Items", style=discord.ButtonStyle.danger, row=2)

    async def callback(self, i):
        if "items" in self.view.data["rewards"]:
            del self.view.data["rewards"]["items"]
        await i.response.edit_message(embed=self.view.get_embed())


class EditMetadataBtn(Button):
    def __init__(self, label):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, i):
        if self.view.mode == "promo":
            await i.response.send_modal(
                PromoMetadataModal(self.view.bot, self.view.data)
            )


class SaveRewardBtn(Button):
    def __init__(self, mode):
        label = "Send Message" if mode == "inbox" else "Save Promo Code"
        style = discord.ButtonStyle.success
        super().__init__(label=label, style=style, row=4)
        self.mode = mode

    async def callback(self, i):
        d = self.view.data
        if self.mode == "inbox":
            database.send_inbox_message(
                self.view.target_id,
                d.get("sender", "System"),
                d.get("title", "No Title"),
                d.get("body", ""),
                d["rewards"],
            )
            await i.response.edit_message(
                content="✅ **Message Sent!**", embed=None, view=None
            )
        else:

            database.create_promo_code(
                d["code_key"],
                d["rewards"],
                d["description"],
                d["expires_at"],
                d["crate_type"],
            )
            await i.response.edit_message(
                content=f"✅ **Promo Code '{d['code_key']}' Saved!**",
                embed=None,
                view=None,
            )


class CancelRewardBtn(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, i):
        await i.response.edit_message(content="❌ Cancelled.", embed=None, view=None)


class DeletePromoBtn(Button):
    def __init__(self, code_key):
        super().__init__(
            label="Delete Code",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=4,
        )
        self.code_key = code_key

    async def callback(self, i: discord.Interaction):
        database.delete_promo_code(self.code_key)
        await i.response.edit_message(
            content=f"🗑️ Promo Code `{self.code_key}` deleted.",
            embed=None,
            view=None,
        )


class ItemBuilderView(View):
    def __init__(self, bot, parent_view):
        super().__init__(timeout=120)
        self.bot = bot
        self.parent_view = parent_view
        self.add_item(BuilderCategorySelect(bot))


class BuilderCategorySelect(Select):
    def __init__(self, bot):
        def e(k):
            return utils.safe_emoji(utils.get_emoji(bot, k))

        opts = [
            discord.SelectOption(
                label="Weapon", value="weapon", emoji=e("empty_weapon")
            ),
            discord.SelectOption(
                label="Gadget", value="gadget", emoji=e("empty_gadget")
            ),
            discord.SelectOption(
                label="Passive", value="passive", emoji=e("empty_passive")
            ),
            discord.SelectOption(
                label="Ring", value="smart_ring", emoji=e("empty_ring")
            ),
            discord.SelectOption(
                label="Module", value="elite_module", emoji=e("empty_module")
            ),
        ]
        super().__init__(placeholder="Select Category...", options=opts)

    async def callback(self, i):
        cat = self.values[0]
        items = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == cat]
        items.sort()
        await i.response.edit_message(
            view=BuilderItemSelectView(self.view.bot, self.view.parent_view, items[:25])
        )


class BuilderItemSelectView(View):
    def __init__(self, bot, parent_view, items):
        super().__init__(timeout=120)
        self.add_item(BuilderItemSelect(items, bot, parent_view))


class BuilderItemSelect(Select):
    def __init__(self, items, bot, parent_view):
        self.parent_view = parent_view
        opts = []
        for k in items:
            name = game_data.get_item(k)["name"]
            emoji = utils.safe_emoji(utils.get_emoji(bot, k))
            opts.append(discord.SelectOption(label=name, value=k, emoji=emoji))
        super().__init__(placeholder="Select Item...", options=opts)

    async def callback(self, i):
        await i.response.send_modal(BuilderStatsModal(self.parent_view, self.values[0]))


class BuilderStatsModal(Modal):
    def __init__(self, parent_view, item_id):
        super().__init__(title="Item Stats")
        self.parent_view = parent_view
        self.item_id = item_id
        self.lvl = TextInput(label="Level (1-50)", default="1")
        self.mod = TextInput(
            label="Modifier (Standard, Elite, Overcharged...)",
            default="Standard",
        )
        self.add_item(self.lvl)
        self.add_item(self.mod)

    async def on_submit(self, i):
        try:
            level = int(self.lvl.value)
            modifier = self.mod.value.strip()

            item_data = {"id": self.item_id, "level": level, "mod": modifier}

            await self.parent_view.add_item_to_cart(item_data)

            if self.parent_view.message:
                try:
                    await self.parent_view.message.edit(
                        embed=self.parent_view.get_embed()
                    )
                except:
                    pass

            await i.response.edit_message(
                content="✅ **Item Added!** Dismiss this message to continue.",
                view=None,
            )

        except ValueError:
            await i.response.send_message("Invalid Level.", ephemeral=True)


class BackButton(Button):
    def __init__(self, parent):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=4)
        self.parent_view = parent

    async def callback(self, i):
        await i.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


async def setup(bot):
    await bot.add_cog(Admin(bot))

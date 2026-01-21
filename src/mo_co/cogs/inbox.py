import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Select
import json
import asyncio
from datetime import datetime
from mo_co import database, config, utils, game_data


class Inbox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inbox", description="Check your messages and rewards")
    async def inbox(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)

        view = InboxListView(self.bot, interaction.user.id, show_history=False)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )


class InboxListView(View):
    def __init__(self, bot, user_id, show_history=False, page=0):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.show_history = show_history
        self.page = page
        self.page_size = 5
        self.messages = []
        self.refresh_data()
        self.update_components()

    def refresh_data(self):

        all_msgs = database.get_user_inbox(self.user_id, include_claimed=True)

        if self.show_history:

            self.messages = [m for m in all_msgs if m["is_claimed"]]
        else:

            self.messages = [m for m in all_msgs if not m["is_claimed"]]

    def get_embed(self):
        title = "🗄️ Message History" if self.show_history else "📬 Inbox"
        color = 0x95A5A6 if self.show_history else 0x3498DB

        embed = discord.Embed(title=title, color=color)

        if not self.messages:
            state = "claimed messages" if self.show_history else "new messages"
            embed.description = f"*No {state} found.*"
            embed.set_footer(text="Check the other tab?")
            return embed

        total_pages = max(1, (len(self.messages) - 1) // self.page_size + 1)
        self.page = max(0, min(self.page, total_pages - 1))

        start = self.page * self.page_size
        end = start + self.page_size
        chunk = self.messages[start:end]

        lines = []
        for i, msg in enumerate(chunk):

            rewards = json.loads(msg["rewards"])
            has_rewards = bool(rewards)

            icon = "✉️"
            if has_rewards:
                icon = "✅" if msg["is_claimed"] else "🎁"

            if self.show_history:
                ts = int(datetime.fromisoformat(msg["sent_at"]).timestamp())
                time_str = f"Received <t:{ts}:R>"
            else:
                try:
                    exp_ts = int(datetime.fromisoformat(msg["expires_at"]).timestamp())
                    time_str = f"Expires <t:{exp_ts}:R>"
                except:
                    time_str = "No Expiry"

            t_title = msg["title"]
            if len(t_title) > 30:
                t_title = t_title[:27] + "..."

            lines.append(
                f"`{start + i + 1}.` {icon} **{t_title}**\n└ ⏳ {time_str} • *{msg['sender_text']}*"
            )

        embed.description = "\n\n".join(lines)
        embed.set_footer(
            text=f"Page {self.page + 1}/{total_pages} • Total: {len(self.messages)}"
        )

        return embed

    def update_components(self):
        self.clear_items()

        if self.messages:
            start = self.page * self.page_size
            end = start + self.page_size
            chunk = self.messages[start:end]

            options = []
            for i, msg in enumerate(chunk):
                rewards = json.loads(msg["rewards"])
                icon = "✅" if msg["is_claimed"] else ("🎁" if rewards else "✉️")
                lbl = f"{start + i + 1}. {msg['title']}"[:100]
                options.append(
                    discord.SelectOption(
                        label=lbl, value=str(msg["message_id"]), emoji=icon
                    )
                )

            self.add_item(InboxSelect(options))

        total_pages = max(1, (len(self.messages) - 1) // self.page_size + 1)

        self.add_item(
            NavButton(label="Newer", emoji="⬆️", disabled=(self.page == 0), delta=-1)
        )

        toggle_label = "View Inbox" if self.show_history else "View History"
        toggle_style = (
            discord.ButtonStyle.primary
            if self.show_history
            else discord.ButtonStyle.secondary
        )
        self.add_item(FilterButton(label=toggle_label, style=toggle_style))

        self.add_item(
            NavButton(
                label="Older",
                emoji="⬇️",
                disabled=(self.page >= total_pages - 1),
                delta=1,
            )
        )


class InboxSelect(Select):
    def __init__(self, options):
        super().__init__(placeholder="Open Message...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        msg_id = int(self.values[0])
        msg = database.get_inbox_message(msg_id)
        if not msg:
            return await interaction.response.send_message(
                "Message not found.", ephemeral=True
            )

        view = MessageDetailView(
            self.view.bot, self.view.user_id, msg, parent_view=self.view
        )
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class NavButton(Button):
    def __init__(self, label, emoji, disabled, delta):
        super().__init__(
            label=label,
            emoji=emoji,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            row=1,
        )
        self.delta = delta

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return
        self.view.page += self.delta
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class FilterButton(Button):
    def __init__(self, label, style):
        super().__init__(label=label, style=style, emoji="🔄", row=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return

        self.view.show_history = not self.view.show_history
        self.view.page = 0
        self.view.refresh_data()
        self.view.update_components()
        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )


class MessageDetailView(View):
    def __init__(self, bot, user_id, message_row, parent_view):
        super().__init__(timeout=180)
        self.bot = bot
        self.user_id = user_id
        self.msg = message_row
        self.parent_view = parent_view
        self.rewards = json.loads(self.msg["rewards"])

        if not self.msg["is_claimed"] and self.rewards:
            self.add_item(ClaimButton(self.msg["message_id"]))
        elif self.msg["is_claimed"]:

            btn = Button(
                label="Claimed",
                disabled=True,
                style=discord.ButtonStyle.secondary,
                emoji="✅",
            )
            self.add_item(btn)

        self.add_item(BackButton(parent_view))

    def get_embed(self):

        color = 0x2ECC71 if self.msg["is_claimed"] else 0xF1C40F

        embed = discord.Embed(
            title=f"📨 {self.msg['title']}",
            description=self.msg["body"],
            color=color,
        )
        embed.set_author(name=f"From: {self.msg['sender_text']}")

        try:
            exp_ts = int(datetime.fromisoformat(self.msg["expires_at"]).timestamp())
            exp_str = f"<t:{exp_ts}:R>"
        except:
            exp_str = "Never"

        embed.add_field(name="⏳ Expires", value=exp_str, inline=True)

        sent_ts = int(datetime.fromisoformat(self.msg["sent_at"]).timestamp())
        embed.add_field(name="📅 Received", value=f"<t:{sent_ts}:f>", inline=True)

        reward_lines = []
        for k, v in self.rewards.items():
            if k == "items":
                for item in v:
                    i_name = game_data.get_item(item["id"])["name"]
                    lvl = item.get("level", 1)

                    icon = utils.get_emoji(self.bot, item["id"])
                    mod_str = (
                        f"[{item.get('mod','Standard')}] "
                        if item.get("mod") != "Standard"
                        else ""
                    )

                    reward_lines.append(f"{icon} **{mod_str}{i_name}** (Lvl {lvl})")
            else:
                emoji = ""
                if k == "mo_gold":
                    emoji = config.MOGOLD_EMOJI
                elif k == "merch_tokens":
                    emoji = config.MERCH_TOKEN_EMOJI
                elif k == "chaos_cores":
                    emoji = config.CHAOS_CORE_EMOJI
                elif k == "chaos_kits":
                    emoji = config.CHAOS_CORE_EMOJI
                elif k == "xp":
                    emoji = config.XP_EMOJI
                elif k == "chaos_shards":
                    emoji = config.CHAOS_SHARD_EMOJI
                elif k == "elite_tokens":
                    emoji = config.ELITE_TOKEN_EMOJI
                elif k == "xp_fuel":
                    emoji = config.XP_BOOST_3X_EMOJI

                name_fmt = k.replace("_", " ").title()
                reward_lines.append(f"{emoji} **{v:,} {name_fmt}**")

        if reward_lines:
            status_text = (
                "✅ Rewards Claimed"
                if self.msg["is_claimed"]
                else "🎁 Attached Rewards"
            )
            embed.add_field(
                name=status_text, value="\n".join(reward_lines), inline=False
            )

        return embed


class ClaimButton(Button):
    def __init__(self, msg_id):
        super().__init__(
            label="Claim Rewards",
            style=discord.ButtonStyle.success,
            emoji="🎁",
        )
        self.msg_id = msg_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return

        msg = database.get_inbox_message(self.msg_id)
        if msg["is_claimed"]:
            return await interaction.response.send_message(
                "Already claimed!", ephemeral=True
            )

        rewards = json.loads(msg["rewards"])
        u_data = database.get_user_data(self.view.user_id)
        u_dict = dict(u_data)
        updates = {}
        log_lines = []

        for key in [
            "mo_gold",
            "merch_tokens",
            "chaos_cores",
            "chaos_kits",
            "chaos_shards",
            "elite_tokens",
        ]:
            if key in rewards:
                current = u_dict.get(key, 0)
                updates[key] = current + rewards[key]
                log_lines.append(
                    f"**+{rewards[key]:,}** {key.replace('_', ' ').title()}"
                )

        if "xp" in rewards:
            utils.add_user_xp(self.view.user_id, rewards["xp"])
            log_lines.append(f"**+{rewards['xp']:,}** XP")

        if "xp_fuel" in rewards:
            updates["daily_xp_boosted"] = (
                u_dict["daily_xp_boosted"] + rewards["xp_fuel"]
            )
            log_lines.append(f"**+{rewards['xp_fuel']:,}** XP Fuel")

        if updates:
            database.update_user_stats(self.view.user_id, updates)

        if "items" in rewards:

            u_xp = u_dict["xp"] + rewards.get("xp", 0)
            pl, _, _ = utils.get_level_info(u_xp)

            for item in rewards["items"]:
                iid = item["id"]
                mod = item.get("mod", "Standard")
                ilvl = item.get("level", pl)
                ilvl = min(50, max(1, ilvl))

                database.add_item_to_inventory(self.view.user_id, iid, mod, ilvl)
                icon = utils.get_emoji(self.view.bot, iid)
                name = game_data.get_item(iid)["name"]
                log_lines.append(f"{icon} **{name}** (Lvl {ilvl})")

        database.mark_message_claimed(self.msg_id)
        embed = discord.Embed(
            title="🎉 Rewards Acquired",
            color=0x2ECC71,
            description="\n".join(log_lines),
        )
        self.disabled = True
        self.label = "Claimed"
        self.style = discord.ButtonStyle.secondary
        self.emoji = "✅"

        self.view.msg = database.get_inbox_message(self.msg_id)

        await interaction.response.edit_message(
            embed=self.view.get_embed(), view=self.view
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class BackButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, emoji="🔙")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.user_id:
            return

        self.parent_view.refresh_data()
        self.parent_view.update_components()

        await interaction.response.edit_message(
            embed=self.parent_view.get_embed(), view=self.parent_view
        )


async def setup(bot):
    await bot.add_cog(Inbox(bot))

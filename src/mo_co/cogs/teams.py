import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
from mo_co import database, config, utils, game_data
from mo_co import rift_engine
import asyncio
import typing
import json
import time

ACTIVE_LOBBIES = {}


class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.matchmaker.start()

    def cog_unload(self):
        self.matchmaker.cancel()

    @tasks.loop(seconds=5)
    async def matchmaker(self):
        """Scans active lobbies with matchmaking enabled and merges them."""

        candidates = []
        for tid, lob in list(ACTIVE_LOBBIES.items()):
            if (
                lob.get("matchmaking")
                and len(lob["members"]) < 4
                and not lob.get("game_started")
            ):
                candidates.append(lob)

        grouped = {}
        for lob in candidates:
            key = (
                lob["guild_id"],
                lob["rift"],
                lob.get("difficulty", "Normal"),
            )
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(lob)

        for key, lobbies in grouped.items():
            if len(lobbies) < 2:
                continue

            lobbies.sort(key=lambda x: len(x["members"]), reverse=True)

            target = lobbies[0]
            sources = lobbies[1:]

            for src in sources:
                space_needed = len(src["members"])
                space_avail = 4 - len(target["members"])

                if space_needed <= space_avail:

                    await self.merge_lobbies(target, src)
                    if len(target["members"]) >= 4:
                        break

    async def merge_lobbies(self, target, source):
        """Moves members from Source to Target."""

        for uid in source["members"]:
            target["members"].append(uid)
            target["ready"][uid] = False
            target["member_info"][uid] = source["member_info"][uid]

        try:
            s_thread = self.bot.get_channel(source["thread_id"])
            if s_thread:
                t_thread = self.bot.get_channel(target["thread_id"])
                link = t_thread.jump_url if t_thread else "the other lobby"
                await s_thread.send(
                    embed=discord.Embed(
                        title="Squad Found!",
                        description=f"Merging with another squad... [Click to Join]({link})",
                        color=0x2ECC71,
                    )
                )

        except:
            pass

        if source["thread_id"] in ACTIVE_LOBBIES:
            del ACTIVE_LOBBIES[source["thread_id"]]

        t_thread = self.bot.get_channel(target["thread_id"])
        if t_thread:

            await t_thread.send(
                f"**{len(source['members'])} Hunter(s) joined the squad!**"
            )

    async def rift_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> typing.List[app_commands.Choice[str]]:
        user = database.get_user_data(interaction.user.id)
        if not user:
            return []
        player_lvl, _, _ = utils.get_level_info(user["xp"])
        options = []
        for rset in game_data.RIFT_SETS:
            if player_lvl >= rset["unlock_lvl"]:
                for rift_key in rset["rifts"]:
                    r_def = game_data.RIFTS.get(rift_key)
                    if not r_def:
                        continue
                    if current.lower() in r_def["name"].lower():
                        options.append(
                            app_commands.Choice(
                                name=f"Rift: {r_def['name']}", value=rift_key
                            )
                        )
        return options[:25]

    @app_commands.command(name="team", description="Create a hunting Team for Rifts")
    @app_commands.describe(activity="Select specific Rift", message="LFG Message")
    @app_commands.autocomplete(activity=rift_autocomplete)
    async def team(
        self,
        interaction: discord.Interaction,
        activity: str = None,
        message: str = "Join my Team!",
    ):
        await interaction.response.defer(ephemeral=True)
        database.register_user(interaction.user.id)
        initial_rift = activity if activity in game_data.RIFTS else "No Location"

        if initial_rift != "No Location":
            success, reason = self.check_user_requirements(
                interaction.user.id, initial_rift
            )
            if not success:
                return await interaction.followup.send(f"❌ {reason}", ephemeral=True)

        context = utils.get_user_combat_profile(interaction.user.id)
        if not context:
            return await interaction.followup.send("Profile error.", ephemeral=True)

        lvl = context["level"]
        gp = context["gp"]

        member_data = {
            interaction.user.id: {
                "name": interaction.user.display_name,
                "lvl": lvl,
                "gp": gp,
                "emblem": utils.get_emblem(lvl),
            }
        }

        embed = self.create_lfg_embed(
            interaction.user.display_name,
            interaction.user.display_avatar.url,
            initial_rift,
            message,
            member_data,
        )
        view = LFGView(self.bot, interaction.user.id)

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        public_embed = embed.copy()
        public_view = LFGView(self.bot, interaction.user.id)

        lfg_msg = await interaction.channel.send(embed=public_embed, view=public_view)

        try:
            thread = await interaction.channel.create_thread(
                name=f"Team: {interaction.user.display_name}",
                type=discord.ChannelType.private_thread,
            )
            await thread.add_user(interaction.user)

            ACTIVE_LOBBIES[thread.id] = {
                "leader": interaction.user.id,
                "members": [interaction.user.id],
                "member_info": member_data,
                "ready": {interaction.user.id: False},
                "rift": initial_rift,
                "difficulty": "Normal",
                "guild_id": interaction.guild_id,
                "lfg_channel_id": interaction.channel_id,
                "lfg_message_id": lfg_msg.id,
                "thread_id": thread.id,
                "message": message,
                "matchmaking": False,
                "is_solo": False,
                "game_started": False,
            }

            lobby_view = LobbyView(self.bot, thread.id)
            lobby_msg = await thread.send(embed=lobby_view.get_embed(), view=lobby_view)
            ACTIVE_LOBBIES[thread.id]["lobby_message_id"] = lobby_msg.id

        except Exception as e:
            print(f"Team Creation Error: {e}")
            await interaction.followup.send(
                "Failed to create team thread. Check bot permissions.",
                ephemeral=True,
            )

    def create_lfg_embed(
        self, leader_name, leader_avatar, rift_key, message, member_info
    ):
        loc_name = (
            game_data.RIFTS[rift_key]["name"]
            if rift_key in game_data.RIFTS
            else "No Location"
        )
        embed = discord.Embed(
            title=f"{config.RIFTS_EMOJI} New Team: {loc_name}",
            description=f"**{message}**",
            color=0x2ECC71,
        )
        if leader_avatar:
            embed.set_author(name=f"{leader_name}'s Team", icon_url=leader_avatar)
        else:
            embed.set_author(name=f"{leader_name}'s Team")

        member_lines = []
        total_gp = 0
        uids = list(member_info.keys())
        for idx in range(4):
            if idx < len(uids):
                uid = uids[idx]
                info = member_info[uid]
                member_lines.append(
                    f"{idx+1}. {info['emblem']} **{info['name']}** (Lvl {info['lvl']} | {config.GEAR_POWER_EMOJI} {info['gp']:,})"
                )
                total_gp += info["gp"]
            else:
                member_lines.append(f"{idx+1}. --")

        avg_gp = total_gp / max(1, len(uids))
        embed.add_field(
            name=f"Members ({len(uids)}/4)",
            value="\n".join(member_lines),
            inline=False,
        )
        embed.add_field(
            name="Team Avg GP",
            value=f"{config.GEAR_POWER_EMOJI} {int(avg_gp):,}",
            inline=True,
        )
        return embed

    def check_user_requirements(self, user_id, rift_key):
        if rift_key not in game_data.RIFTS:
            return True, None

        context = utils.get_user_combat_profile(user_id)
        if not context:
            return False, "User not registered"

        player_lvl = context["level"]
        u_data = context["user_data"]

        required_lvl = 1
        r_def = game_data.RIFTS[rift_key]
        for s in game_data.RIFT_SETS:
            if rift_key in s["rifts"]:
                required_lvl = s["unlock_lvl"]
                break
        if player_lvl < required_lvl:
            return False, f"Hunter Level too low (Needs Lvl {required_lvl})"
        req = r_def.get("req_rift")
        if req:
            try:
                completed = json.loads(u_data.get("completed_rifts", "[]"))
            except:
                completed = []
            if req not in completed:
                req_name = game_data.RIFTS.get(req, {}).get("name", "Previous Rift")
                return False, f"Complete **{req_name}** first"
        return True, None


class LFGView(View):
    def __init__(self, bot, leader_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.leader_id = leader_id

    @discord.ui.button(label="Join Team", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        thread_id = None
        for tid, data in ACTIVE_LOBBIES.items():
            if data.get("lfg_message_id") == interaction.message.id:
                thread_id = tid
                break
        if not thread_id or thread_id not in ACTIVE_LOBBIES:
            return await interaction.response.send_message(
                "❌ This team no longer exists.", ephemeral=True
            )
        lobby = ACTIVE_LOBBIES[thread_id]
        if interaction.user.id in lobby["members"]:
            return await interaction.response.send_message(
                "You are already in this team!", ephemeral=True
            )
        if len(lobby["members"]) >= 4:
            return await interaction.response.send_message(
                "Team is full!", ephemeral=True
            )
        teams_cog = self.bot.get_cog("Teams")
        if lobby["rift"] != "No Location":
            success, reason = teams_cog.check_user_requirements(
                interaction.user.id, lobby["rift"]
            )
            if not success:
                return await interaction.response.send_message(
                    f"❌ **Requirement not met:** {reason}", ephemeral=True
                )
        database.register_user(interaction.user.id)

        context = utils.get_user_combat_profile(interaction.user.id)

        lobby["members"].append(interaction.user.id)
        lobby["ready"][interaction.user.id] = False
        lobby["member_info"][interaction.user.id] = {
            "name": interaction.user.display_name,
            "lvl": context["level"],
            "gp": context["gp"],
            "emblem": utils.get_emblem(context["level"]),
        }
        thread = interaction.guild.get_thread(thread_id)
        if thread:
            await thread.add_user(interaction.user)
        await self.update_all_uis(interaction.guild, thread_id)
        await interaction.response.send_message("Joined the team!", ephemeral=True)

    async def update_all_uis(self, guild, thread_id):
        lobby = ACTIVE_LOBBIES.get(thread_id)
        if not lobby:
            return
        lfg_chan = guild.get_channel(lobby["lfg_channel_id"])
        if lfg_chan:
            try:
                msg = await lfg_chan.fetch_message(lobby["lfg_message_id"])
                leader_info = lobby["member_info"][lobby["leader"]]
                teams_cog = self.bot.get_cog("Teams")
                new_embed = teams_cog.create_lfg_embed(
                    leader_info["name"],
                    None,
                    lobby["rift"],
                    lobby["message"],
                    lobby["member_info"],
                )
                await msg.edit(embed=new_embed)
            except:
                pass
        thread = guild.get_thread(thread_id)
        if thread:
            try:
                msg = await thread.fetch_message(lobby["lobby_message_id"])
                view = LobbyView(self.bot, thread_id)
                await msg.edit(embed=view.get_embed(), view=view)
            except:
                pass


class LobbyView(View):
    def __init__(self, bot, thread_id):
        super().__init__(timeout=None)
        self.bot, self.thread_id, self.lobby = (
            bot,
            thread_id,
            ACTIVE_LOBBIES.get(thread_id),
        )
        self.update_components()

    def update_components(self):
        self.clear_items()
        if not self.lobby:
            return
        self.add_item(RiftSelectMenu(self.bot, self.lobby["rift"]))
        self.add_item(DifficultySelect(self.lobby.get("difficulty", "Normal")))
        self.add_item(ReadyButton())
        self.add_item(LoadoutButton())
        self.add_item(LeaveButton())
        all_ready = (
            all(self.lobby["ready"].values()) and self.lobby["rift"] != "No Location"
        )
        self.add_item(StartButton(disabled=not all_ready))

    def get_embed(self):
        if not self.lobby:
            return discord.Embed(title="Lobby Closed", color=0xE74C3C)
        rift_key = self.lobby["rift"]
        diff = self.lobby.get("difficulty", "Normal")

        color = 0x3498DB
        if diff == "Hard":
            color = 0xE67E22
        elif diff == "Nightmare":
            color = 0xE74C3C

        if rift_key == "No Location":
            embed = discord.Embed(
                title=f"{config.RIFTS_EMOJI} Rift Lobby",
                description="Select a Rift to start!",
                color=0x95A5A6,
            )
        else:
            r = game_data.RIFTS[rift_key]
            icon = utils.get_emoji(self.bot, r["icon"])
            embed = discord.Embed(
                title=f"{config.RIFTS_EMOJI} Rift Lobby: {r['name']}",
                color=color,
            )
            embed.description = (
                f"**Boss:** {icon} {r['boss']}\n**Difficulty:** {diff}\n*{r['desc']}*"
            )
            total_gp = sum(info["gp"] for info in self.lobby["member_info"].values())
            avg_gp = int(total_gp / len(self.lobby["members"]))
            rec_gp = r.get("recommended_gp", 0)
            status_icon = "🟢" if avg_gp >= rec_gp else "🔴"
            embed.add_field(
                name="Bureau Intel",
                value=f"{status_icon} **Team Avg GP:** {config.GEAR_POWER_EMOJI} {avg_gp:,}\n{config.GEAR_POWER_EMOJI} **Recommended GP:** {rec_gp:,}",
                inline=False,
            )
        lines = []
        for uid in self.lobby["members"]:
            info = self.lobby["member_info"][uid]
            ready_icon = "✅" if self.lobby["ready"].get(uid) else "❌"
            role = " (Host)" if uid == self.lobby["leader"] else ""
            lines.append(f"{ready_icon} | {info['emblem']} | **{info['name']}**{role}")
        embed.add_field(
            name=f"Team ({len(self.lobby['members'])}/4)",
            value="\n".join(lines),
            inline=False,
        )
        return embed


class DifficultySelect(Select):
    def __init__(self, current):
        options = [
            discord.SelectOption(
                label="Normal", value="Normal", default=(current == "Normal")
            ),
            discord.SelectOption(
                label="Hard",
                value="Hard",
                emoji="🔥",
                default=(current == "Hard"),
            ),
            discord.SelectOption(
                label="Nightmare",
                value="Nightmare",
                emoji="💀",
                default=(current == "Nightmare"),
            ),
        ]
        super().__init__(placeholder="Select Difficulty...", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        lobby = ACTIVE_LOBBIES.get(interaction.channel_id)
        if not lobby or interaction.user.id != lobby["leader"]:
            return await interaction.response.send_message(
                "Only the Host can change the Difficulty!", ephemeral=True
            )
        lobby["difficulty"] = self.values[0]

        for m in lobby["ready"]:
            lobby["ready"][m] = False

        view = LobbyView(interaction.client, interaction.channel_id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class RiftSelectMenu(Select):
    def __init__(self, bot, current):
        options = [
            discord.SelectOption(
                label="Select a Rift...",
                value="No Location",
                default=(current == "No Location"),
            )
        ]
        for key, data in game_data.RIFTS.items():
            icon_str = utils.get_emoji(bot, data.get("icon"))
            options.append(
                discord.SelectOption(
                    label=data["name"],
                    value=key,
                    description=f"Boss: {data['boss']}",
                    default=(key == current),
                    emoji=utils.safe_emoji(icon_str),
                )
            )
        super().__init__(
            placeholder="Change Rift (Host Only)...", options=options, row=0
        )

    async def callback(self, interaction: discord.Interaction):
        lobby = ACTIVE_LOBBIES.get(interaction.channel_id)
        if not lobby or interaction.user.id != lobby["leader"]:
            return await interaction.response.send_message(
                "Only the Host can change the Rift!", ephemeral=True
            )
        new_rift = self.values[0]
        if new_rift != "No Location":
            teams_cog = interaction.client.get_cog("Teams")
            failed_lines = []
            for uid in lobby["members"]:
                success, reason = teams_cog.check_user_requirements(uid, new_rift)
                if not success:
                    info = lobby["member_info"][uid]
                    failed_lines.append(
                        f"❌ {info['emblem']} **{info['name']}**: {reason}"
                    )
            if failed_lines:
                return await interaction.response.send_message(
                    "**Requirements not met by:**\n" + "\n".join(failed_lines),
                    ephemeral=True,
                )
        lobby["rift"] = new_rift
        for m in lobby["ready"]:
            lobby["ready"][m] = False
        lfg_view = LFGView(interaction.client, lobby["leader"])
        await lfg_view.update_all_uis(interaction.guild, interaction.channel_id)
        await interaction.response.defer()


class ReadyButton(Button):
    def __init__(self):
        super().__init__(label="Ready Up", style=discord.ButtonStyle.success, row=2)

    async def callback(self, interaction: discord.Interaction):
        lobby = ACTIVE_LOBBIES.get(interaction.channel_id)
        if not lobby or interaction.user.id not in lobby["members"]:
            return
        if lobby["rift"] != "No Location":
            teams_cog = interaction.client.get_cog("Teams")
            success, reason = teams_cog.check_user_requirements(
                interaction.user.id, lobby["rift"]
            )
            if not success:
                return await interaction.response.send_message(
                    f"❌ **Cannot Ready:** {reason}", ephemeral=True
                )
        lobby["ready"][interaction.user.id] = not lobby["ready"].get(
            interaction.user.id, False
        )
        view = LobbyView(interaction.client, interaction.channel_id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class StartButton(Button):
    def __init__(self, disabled=True):
        super().__init__(
            label="Start Hunt",
            style=discord.ButtonStyle.primary,
            emoji=utils.safe_emoji(config.ELITE_EMOJI),
            row=2,
            disabled=disabled,
        )

    async def callback(self, interaction: discord.Interaction):
        lobby = ACTIVE_LOBBIES.get(interaction.channel_id)
        if not lobby or interaction.user.id != lobby["leader"]:
            return await interaction.response.send_message(
                "Only Host can start!", ephemeral=True
            )

        lobby["matchmaking"] = True
        matchmaking_view = MatchmakingView(interaction.client, interaction.channel_id)
        await interaction.response.edit_message(
            embed=matchmaking_view.get_embed(), view=matchmaking_view
        )
        asyncio.create_task(matchmaking_view.start_counter(interaction))


class LeaveButton(Button):
    def __init__(self):
        super().__init__(label="Leave", style=discord.ButtonStyle.danger, row=2)

    async def callback(self, interaction: discord.Interaction):
        thread_id = interaction.channel_id
        lobby = ACTIVE_LOBBIES.get(thread_id)
        if not lobby or interaction.user.id not in lobby["members"]:
            return
        lobby["members"].remove(interaction.user.id)
        if interaction.user.id in lobby["ready"]:
            del lobby["ready"][interaction.user.id]
        if interaction.user.id in lobby["member_info"]:
            del lobby["member_info"][interaction.user.id]
        if not lobby["members"]:
            lfg_chan = interaction.guild.get_channel(lobby["lfg_channel_id"])
            if lfg_chan:
                try:
                    msg = await lfg_chan.fetch_message(lobby["lfg_message_id"])
                    await msg.delete()
                except:
                    pass

            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            else:
                del ACTIVE_LOBBIES[thread_id]
            return

        if interaction.user.id == lobby["leader"]:
            lobby["leader"] = lobby["members"][0]
        lfg_view = LFGView(interaction.client, lobby["leader"])
        await lfg_view.update_all_uis(interaction.guild, thread_id)
        await interaction.response.send_message("You left the team.", ephemeral=True)


class LoadoutButton(Button):
    def __init__(self):
        super().__init__(label="Loadout", style=discord.ButtonStyle.secondary, row=2)

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Loadout")
        await interaction.response.send_message(
            embed=cog.generate_kit_embed(
                interaction.user.id, interaction.user.display_name
            ),
            ephemeral=True,
        )


class MatchmakingView(View):
    def __init__(self, bot, thread_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.thread_id = thread_id
        self.lobby = ACTIVE_LOBBIES.get(thread_id)
        self.elapsed = 0
        self.cancelled = False
        self.message = None
        self.add_item(ForceStartButton())
        self.add_item(CancelMatchButton())

    def get_embed(self):
        if not self.lobby or "rift" not in self.lobby:
            return discord.Embed(
                title="Error",
                description="Lobby session lost.",
                color=0xE74C3C,
            )

        r_def = game_data.RIFTS.get(self.lobby["rift"])
        r_name = r_def["name"] if r_def else "Unknown Rift"
        diff = self.lobby.get("difficulty", "Normal")

        embed = discord.Embed(
            title=f"{config.RIFTS_EMOJI} Matchmaking: {r_name}", color=0x3498DB
        )

        status = "Searching for Hunters in your Guild..."
        if len(self.lobby["members"]) >= 4:
            status = "Squad Full! Preparing to launch..."

        embed.description = (
            f"**Difficulty:** {diff}\n"
            f"{status} ({len(self.lobby['members'])}/4)\n"
            f"{config.LOADING_EMOJI} **Searching:** {self.elapsed}s\n\n"
            f"*Other teams running the same Rift will be merged automatically.*"
        )

        m_list = [
            f"✅ **{info['name']}**" for info in self.lobby["member_info"].values()
        ]
        embed.add_field(name="Current Squad", value="\n".join(m_list))
        return embed

    async def start_counter(self, interaction):
        try:
            self.message = await interaction.original_response()
        except:
            pass

        while not self.cancelled:

            if self.thread_id not in ACTIVE_LOBBIES:
                break

            self.lobby = ACTIVE_LOBBIES[self.thread_id]

            if len(self.lobby["members"]) >= 4:
                await self.launch_game(None, self.message)
                break

            await asyncio.sleep(2)
            self.elapsed += 2

            try:
                if self.message:
                    await self.message.edit(embed=self.get_embed(), view=self)
                else:
                    await interaction.edit_original_response(
                        embed=self.get_embed(), view=self
                    )
            except:
                break

    async def launch_game(self, interaction=None, message=None):
        self.cancelled = True

        self.lobby["game_started"] = True

        if interaction:
            await interaction.response.edit_message(
                content=f"{config.RIFTS_EMOJI} **Entering...**",
                embed=None,
                view=None,
            )
            channel = interaction.channel
        elif message:
            await message.edit(
                content=f"{config.RIFTS_EMOJI} **Entering...**",
                embed=None,
                view=None,
            )
            channel = message.channel
        else:
            return

        instance = rift_engine.RiftInstance(self.bot, channel, self.lobby)

        instance.difficulty = self.lobby.get("difficulty", "Normal")
        asyncio.create_task(instance.start_loop())

        lfg_chan = channel.guild.get_channel(self.lobby["lfg_channel_id"])
        if lfg_chan and self.lobby["lfg_message_id"]:
            try:
                msg = await lfg_chan.fetch_message(self.lobby["lfg_message_id"])
                await msg.delete()
            except:
                pass

        await asyncio.sleep(3)
        try:
            if interaction:
                await interaction.delete_original_response()
            elif message:
                await message.delete()
        except:
            pass


class ForceStartButton(Button):
    def __init__(self):
        super().__init__(
            label="Force Start (Solo/Bots)",
            style=discord.ButtonStyle.success,
            emoji="🤖",
        )

    async def callback(self, interaction: discord.Interaction):
        lobby = ACTIVE_LOBBIES.get(self.view.thread_id)
        if not lobby or interaction.user.id != lobby["leader"]:
            return await interaction.response.send_message(
                "Only Host can force start!", ephemeral=True
            )

        self.view.cancelled = True
        await self.view.launch_game(interaction=interaction)


class CancelMatchButton(Button):
    def __init__(self):
        super().__init__(label="Cancel", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        self.view.cancelled = True
        lobby = ACTIVE_LOBBIES.get(self.view.thread_id)

        if lobby and lobby.get("is_solo"):
            del ACTIVE_LOBBIES[self.view.thread_id]
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            else:
                await interaction.message.delete()
            return

        if lobby:
            lobby["matchmaking"] = False
        view = LobbyView(self.view.bot, self.view.thread_id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)
        self.view.stop()


async def setup(bot):
    await bot.add_cog(Teams(bot))

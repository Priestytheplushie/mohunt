import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button
from mo_co import database, config, utils, versus_engine
import asyncio
import time
import random
import math
import json
from mo_co.game_data.missions import MISSIONS
from mo_co.mission_engine import MissionEngine

MM_QUEUE = []


class Versus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.matchmaker.start()

    def cog_unload(self):
        self.matchmaker.cancel()

    @app_commands.command(name="versus", description="Start a Friendly Duel")
    @app_commands.describe(opponent="Opponent to challenge")
    async def versus(self, interaction: discord.Interaction, opponent: discord.User):
        if opponent.id == interaction.user.id or opponent.bot:
            return await interaction.response.send_message(
                "Invalid opponent.", ephemeral=True
            )

        self.update_versus_mission(interaction.user.id, "challenge")

        view = FriendlyChallengeView(self.bot, interaction.user, opponent)
        await interaction.response.send_message(
            f"{opponent.mention}, **{interaction.user.name}** challenges you to a duel!",
            view=view,
        )

    @tasks.loop(seconds=5)
    async def matchmaker(self):
        while len(MM_QUEUE) >= 2:
            entry1 = MM_QUEUE.pop(0)
            entry2 = MM_QUEUE.pop(0)
            await self.create_match(entry1, entry2)

        now = time.time()
        for i in range(len(MM_QUEUE) - 1, -1, -1):
            uid, join_time, interaction = MM_QUEUE[i]
            if now - join_time > 60:
                entry = MM_QUEUE.pop(i)
                bot_name = random.choice(versus_engine.VERSUS_BOT_NAMES)
                bot_entry = (f"BOT_{bot_name}", 0, None)
                await self.create_match(entry, bot_entry)

    async def create_match(self, p1_entry, p2_entry):
        p1_id, _, p1_int = p1_entry
        p2_id, _, p2_int = p2_entry

        if isinstance(p1_id, int):
            self.update_versus_mission(p1_id, "play")
        if isinstance(p2_id, int):
            self.update_versus_mission(p2_id, "play")

        guild = p1_int.guild
        channel = p1_int.channel
        if not guild or not channel:
            return
        try:
            p1_name = p1_int.user.display_name
            p2_name = "Bot"
            if isinstance(p2_id, int):
                p2_name = p2_int.user.display_name
            elif isinstance(p2_id, str):
                p2_name = p2_id.replace("BOT_", "")

            thread_name = f"Versus: {p1_name} vs {p2_name}"
            thread = await channel.create_thread(
                name=thread_name, type=discord.ChannelType.private_thread
            )
            await thread.add_user(p1_int.user)
            if isinstance(p2_id, int):
                await thread.add_user(p2_int.user)

            view = View()
            view.add_item(
                Button(
                    label="Jump to Arena",
                    style=discord.ButtonStyle.link,
                    url=thread.jump_url,
                )
            )
            embed = discord.Embed(
                description=f"✅ **Match Found!** vs **{p2_name}**",
                color=0x2ECC71,
            )
            try:
                await p1_int.followup.send(embed=embed, view=view, ephemeral=True)
            except:
                pass
            try:
                await p1_int.delete_original_response()
            except:
                pass
            if isinstance(p2_id, int):
                try:
                    await p2_int.followup.send(embed=embed, view=view, ephemeral=True)
                except:
                    pass
                try:
                    await p2_int.delete_original_response()
                except:
                    pass
            name_map = {p1_id: p1_name}
            if isinstance(p2_id, int):
                name_map[p2_id] = p2_name
            engine = versus_engine.VersusInstance(
                self.bot,
                p1_id,
                p2_id,
                is_ranked=True,
                channel=thread,
                names=name_map,
            )
            await asyncio.sleep(1)
            asyncio.create_task(engine.start_loop(thread))
        except Exception as e:
            print(f"Versus Match Creation Error: {e}")

    async def join_queue(self, interaction):
        uid = interaction.user.id
        if any(q[0] == uid for q in MM_QUEUE):
            return await interaction.response.send_message(
                "Already in queue!", ephemeral=True
            )
        MM_QUEUE.append((uid, time.time(), interaction))
        view = VersusSearchingView(interaction)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )
        asyncio.create_task(view.update_timer())

    def update_versus_mission(self, user_id, event_type, value=1):
        """
        Updates mission progress for Versus events.
        event_type: 'play', 'win', 'challenge'
        value: unused for simple counts, but future proofing
        """
        u_data = database.get_user_data(user_id)
        if not u_data:
            return
        try:
            m_state = json.loads(u_data["mission_state"])
            active_list = m_state.get("active", [])
            for mid in active_list:
                m_def = MISSIONS.get(mid)
                if not m_def:
                    continue
                step = m_def["steps"][m_state["states"][mid]["step"]]

                if (
                    step["type"] == "objective_versus"
                    and step.get("sub_type") == event_type
                ):
                    thread_id = u_data["mission_thread_id"]
                    if thread_id:
                        engine = MissionEngine(
                            self.bot,
                            user_id,
                            thread_id,
                            specific_mission_id=mid,
                        )

                        m_state["states"][mid]["prog"] += 1
                        database.update_user_stats(
                            user_id, {"mission_state": json.dumps(m_state)}
                        )

                        asyncio.create_task(engine.progress())

        except Exception as e:
            print(f"Versus Mission Update Error: {e}")


class VersusSearchingView(View):
    def __init__(self, interaction):
        super().__init__(timeout=120)
        self.interaction = interaction
        self.elapsed = 0
        self.cancelled = False

    def get_embed(self):
        embed = discord.Embed(title=f"{config.VERSUS_ICON} Matchmaking", color=0x3498DB)
        embed.description = f"Searching for opponent...\n{config.LOADING_EMOJI} **Time Elapsed:** {self.elapsed}s"
        return embed

    async def update_timer(self):
        while not self.cancelled:
            if not any(q[0] == self.interaction.user.id for q in MM_QUEUE):
                break
            await asyncio.sleep(2)
            self.elapsed += 2

            if self.cancelled:
                break
            try:
                await self.interaction.edit_original_response(
                    embed=self.get_embed(), view=self
                )
            except:
                break

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cancelled = True
        global MM_QUEUE
        MM_QUEUE = [entry for entry in MM_QUEUE if entry[0] != interaction.user.id]
        await interaction.response.edit_message(
            content="❌ Matchmaking Cancelled.", embed=None, view=None
        )
        self.stop()


class FriendlyChallengeView(View):
    def __init__(self, bot, challenger, opponent):
        super().__init__(timeout=60)
        self.bot, self.p1, self.p2 = bot, challenger, opponent

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.p2.id:
            return
        await interaction.response.edit_message(
            content="⚔️ **Duel Accepted!** Preparing arena...", view=None
        )
        names = {
            self.p1.id: self.p1.display_name,
            self.p2.id: self.p2.display_name,
        }

        cog = self.bot.get_cog("Versus")
        if cog:
            cog.update_versus_mission(self.p1.id, "play")
            cog.update_versus_mission(self.p2.id, "play")

        engine = versus_engine.VersusInstance(
            self.bot,
            self.p1.id,
            self.p2.id,
            is_ranked=False,
            channel=interaction.channel,
            names=names,
        )
        asyncio.create_task(engine.start_loop(interaction.channel))

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.p2.id:
            return
        await interaction.message.delete()


class VersusCombatView(View):
    def __init__(self, instance):
        super().__init__(timeout=None)
        self.instance = instance
        self.add_item(
            VersusActionButton(
                "ATTACK_MOB", "Farm Mobs", "👾", discord.ButtonStyle.secondary
            )
        )
        self.add_item(
            VersusActionButton(
                "ATTACK_PLAYER",
                "Attack Rival",
                "⚔️",
                discord.ButtonStyle.danger,
            )
        )
        self.add_item(
            VersusActionButton(
                "DASH",
                "Dash (6s)",
                config.DASH_EMOJI,
                discord.ButtonStyle.success,
            )
        )
        for i in range(3):
            self.add_item(VersusGadgetButton(i))


class VersusActionButton(Button):
    def __init__(self, action, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        p = None
        if interaction.user.id == self.view.instance.team_a.user_id:
            p = self.view.instance.team_a
        elif interaction.user.id == self.view.instance.team_b.user_id:
            p = self.view.instance.team_b
        if not p:
            return await interaction.response.send_message("Spectator.", ephemeral=True)
        if p.hp <= 0:
            return await interaction.response.send_message(
                f"💀 **Respawning in {p.respawn_timer * 2}s...**",
                ephemeral=True,
            )
        if p.action_queue:
            return await interaction.response.send_message(
                "⏳ **Action Pending...** Wait for turn.", ephemeral=True
            )
        p.action_queue = self.action
        await interaction.response.send_message(
            f"✅ **{self.label}** Queued", ephemeral=True
        )


class VersusGadgetButton(Button):
    def __init__(self, idx):
        super().__init__(
            label=f"Gadget {idx+1}",
            emoji=config.EMPTY_GADGET,
            style=discord.ButtonStyle.secondary,
        )
        self.idx = idx

    async def callback(self, interaction: discord.Interaction):
        p = None
        if interaction.user.id == self.view.instance.team_a.user_id:
            p = self.view.instance.team_a
        elif interaction.user.id == self.view.instance.team_b.user_id:
            p = self.view.instance.team_b
        if not p:
            return
        if p.hp <= 0:
            return await interaction.response.send_message(
                f"💀 **Respawning in {p.respawn_timer * 2}s...**",
                ephemeral=True,
            )
        if self.idx >= len(p.gadgets):
            return await interaction.response.send_message(
                "No gadget in this slot!", ephemeral=True
            )
        cd = p.gadgets[self.idx]["cd"]
        if cd > 0:
            return await interaction.response.send_message(
                f"⏳ **Cooldown:** {int(math.ceil(cd))}s", ephemeral=True
            )
        if p.action_queue:
            return await interaction.response.send_message(
                "⏳ **Action Pending...** Wait for turn.", ephemeral=True
            )
        p.action_queue = f"GADGET_{self.idx}"
        g_name = p.gadgets[self.idx]["name"]
        await interaction.response.send_message(
            f"✅ **{g_name}** Queued", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Versus(bot))

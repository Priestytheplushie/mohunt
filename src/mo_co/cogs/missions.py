import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
import json
from mo_co import database, config, utils
from mo_co.game_data.missions import MISSIONS
from mo_co.mission_engine import MissionEngine


class Missions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="missions", description="Mo.Co Phone: Missions & Jobs")
    async def missions(self, interaction: discord.Interaction):
        database.register_user(interaction.user.id)
        u_data = dict(database.get_user_data(interaction.user.id))

        raw_state = u_data.get("mission_state")
        if not raw_state:
            default = {
                "active": ["welcome2moco"],
                "states": {"welcome2moco": {"step": 0, "prog": 0}},
                "completed": [],
            }
            database.update_user_stats(
                interaction.user.id, {"mission_state": json.dumps(default)}
            )
            m_state = default
        else:
            m_state = json.loads(raw_state)
            if isinstance(m_state.get("active"), str):
                old_active = m_state["active"]
                m_state["active"] = [old_active]
                if "states" not in m_state:
                    m_state["states"] = {
                        old_active: {
                            "step": m_state.get("step", 0),
                            "prog": m_state.get("prog", 0),
                        }
                    }
                database.update_user_stats(
                    interaction.user.id, {"mission_state": json.dumps(m_state)}
                )

        player_lvl, _, _ = utils.get_level_info(u_data.get("xp", 0))

        if (
            "debugging" in m_state.get("completed", [])
            and "chaos" not in m_state.get("completed", [])
            and "chaos" not in m_state.get("active", [])
            and player_lvl >= 9
        ):
            m_state["active"].append("chaos")
            m_state["states"]["chaos"] = {"step": 0, "prog": 0}
            database.update_user_stats(
                interaction.user.id, {"mission_state": json.dumps(m_state)}
            )

        if (
            "fight" not in m_state.get("completed", [])
            and "fight" not in m_state.get("active", [])
            and player_lvl >= 15
        ):
            m_state["active"].append("fight")
            m_state["states"]["fight"] = {"step": 0, "prog": 0}
            database.update_user_stats(
                interaction.user.id, {"mission_state": json.dumps(m_state)}
            )

        if (
            "basictraining" not in m_state.get("completed", [])
            and "basictraining" not in m_state.get("active", [])
            and player_lvl >= 14
        ):
            m_state["active"].append("basictraining")
            m_state["states"]["basictraining"] = {"step": 0, "prog": 0}
            database.update_user_stats(
                interaction.user.id, {"mission_state": json.dumps(m_state)}
            )

        if (
            "spiritual" in m_state.get("completed", [])
            and "bugstastic" not in m_state.get("completed", [])
            and "bugstastic" not in m_state.get("active", [])
            and player_lvl >= 16
        ):
            m_state["active"].append("bugstastic")
            m_state["states"]["bugstastic"] = {"step": 0, "prog": 0}
            database.update_user_stats(
                interaction.user.id, {"mission_state": json.dumps(m_state)}
            )

        view = PhoneDashboardView(self.bot, interaction.user.id, m_state)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )


class PhoneDashboardView(View):
    def __init__(self, bot, user_id, mission_state):
        super().__init__(timeout=300)
        self.bot, self.user_id, self.mission_state = (
            bot,
            user_id,
            mission_state,
        )
        self.update_components()

    def refresh(self):
        u_dict = dict(database.get_user_data(self.user_id))
        self.mission_state = json.loads(u_dict["mission_state"])
        self.thread_id = u_dict.get("mission_thread_id")
        return u_dict

    def get_embed(self):
        self.refresh()
        embed = discord.Embed(title="📱 mo.co Phone", color=0x2B2D31)
        active_list = self.mission_state.get("active", [])

        if not active_list:
            embed.description = "No active missions. Check back later!"
            return embed

        mission_emoji = config.MISSION_EMOJI

        for m_id in active_list:
            m_def = MISSIONS.get(m_id)
            if not m_def:
                continue
            m_data = self.mission_state["states"].get(m_id, {"step": 0, "prog": 0})
            step = m_def["steps"][m_data["step"]]

            status = "New Message"
            if step["type"] in [
                "objective_hunt",
                "objective_versus",
                "objective_dojo",
                "objective_level",
            ]:
                status = f"{step['desc']} ({m_data['prog']}/{step['count']})"
            elif step["type"] == "objective_checklist":
                pl = m_data["prog"]
                if isinstance(pl, int):
                    pl = [0] * len(step["targets"])
                done = sum(
                    1 for i, t in enumerate(step["targets"]) if pl[i] >= t["count"]
                )
                status = f"{step['desc']} ({done}/{len(step['targets'])})"
            elif "objective" in step["type"]:
                status = step.get("desc", "Pending Objective")

            char = m_def["character"]
            icon = config.BOT_EMOJIS.get(m_def.get("character_icon", char), "👤")
            embed.add_field(
                name=f"{icon} {char}",
                value=f"{mission_emoji} **{m_def['name']}**\n> *{status}*",
                inline=False,
            )

        if getattr(self, "thread_id", None):
            embed.set_footer(text="Chat session active.")
        return embed

    def update_components(self):
        self.clear_items()
        active_list = self.mission_state.get("active", [])
        for m_id in active_list:
            m_def = MISSIONS.get(m_id)
            if not m_def:
                continue
            label = f"{m_def['character']} {m_def['name']}"
            emoji = config.BOT_EMOJIS.get(
                m_def.get("character_icon", m_def["character"]), "💬"
            )
            self.add_item(MissionChatButton(label, utils.safe_emoji(emoji), m_id))

        u_data = dict(database.get_user_data(self.user_id))

        player_lvl, _, _ = utils.get_level_info(u_data.get("xp", 0))
        jobs_unlocked = player_lvl >= 9

        m_state = json.loads(u_data.get("mission_state", "{}"))
        projs_unlocked = "paidovertime" in m_state.get(
            "completed", []
        ) or "paidovertime" in m_state.get("active", [])

        self.add_item(JobsAppButton(disabled=not jobs_unlocked))
        self.add_item(ProjectsAppButton(disabled=not projs_unlocked))


class MissionChatButton(Button):
    def __init__(self, label, emoji, m_id):
        super().__init__(
            label=label, style=discord.ButtonStyle.green, emoji=emoji, row=0
        )
        self.m_id = m_id

    async def callback(self, i: discord.Interaction):
        if i.user.id != self.view.user_id:
            return
        u_data = dict(database.get_user_data(self.view.user_id))
        if u_data.get("mission_thread_id"):
            try:
                t = await self.view.bot.fetch_channel(u_data["mission_thread_id"])
                return await i.response.send_message(
                    f"Go to {t.mention}!", ephemeral=True
                )
            except:
                pass

        await i.response.defer()
        m_def = MISSIONS[self.m_id]
        name = f"{m_def['character'].lower()}-{m_def['name'].replace('#','')}"
        target = (
            i.channel.parent if isinstance(i.channel, discord.Thread) else i.channel
        )
        try:
            thread = await target.create_thread(
                name=name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
            )
            await thread.add_user(i.user)
            database.update_user_stats(
                self.view.user_id, {"mission_thread_id": thread.id}
            )
            engine = MissionEngine(
                self.view.bot,
                self.view.user_id,
                thread.id,
                specific_mission_id=self.m_id,
            )
            await engine.progress()
            await i.followup.send(f"Chat opened: {thread.mention}", ephemeral=True)
            try:
                await i.message.delete()
            except:
                pass
        except Exception as e:
            await i.followup.send(
                f"Failed to create chat. Permissions? {e}", ephemeral=True
            )


class JobsAppButton(Button):
    def __init__(self, disabled):
        super().__init__(
            label="Daily Jobs",
            style=discord.ButtonStyle.primary,
            emoji=utils.safe_emoji(config.DAILY_JOB_EMOJI),
            disabled=disabled,
            row=1,
        )

    async def callback(self, i):
        from mo_co.cogs.jobs import JobsDashboardView

        await i.response.edit_message(
            embed=JobsDashboardView(
                self.view.bot, self.view.user_id, "daily"
            ).get_embed(),
            view=JobsDashboardView(self.view.bot, self.view.user_id, "daily"),
        )


class ProjectsAppButton(Button):
    def __init__(self, disabled):
        super().__init__(
            label="Projects",
            style=discord.ButtonStyle.primary,
            emoji=utils.safe_emoji(config.PROJECT_EMOJI),
            disabled=disabled,
            row=1,
        )

    async def callback(self, i):
        from mo_co.cogs.jobs import JobsDashboardView

        await i.response.edit_message(
            embed=JobsDashboardView(
                self.view.bot, self.view.user_id, "projects"
            ).get_embed(),
            view=JobsDashboardView(self.view.bot, self.view.user_id, "projects"),
        )


async def setup(bot):
    await bot.add_cog(Missions(bot))

import discord
from discord.ui import View, Button
import asyncio
import json
import random
from mo_co import database, config, game_data, utils
from mo_co.game_data.missions import MISSIONS


class MissionEngine:
    def __init__(self, bot, user_id, thread_id, specific_mission_id=None):
        self.bot = bot
        self.user_id = user_id
        self.thread_id = thread_id
        self.specific_mission_id = specific_mission_id
        self.thread = None
        self.u_data = None
        self.state = None

    async def initialize(self):
        row = database.get_user_data(self.user_id)
        if not row:
            return False
        self.u_data = dict(row)

        raw_state = json.loads(self.u_data.get("mission_state", "{}"))
        if "states" not in raw_state:
            new_state = {
                "active": [],
                "states": {},
                "completed": raw_state.get("completed", []),
            }
            old_active = raw_state.get("active")
            if old_active and isinstance(old_active, str):
                new_state["active"].append(old_active)
                new_state["states"][old_active] = {
                    "step": raw_state.get("step", 0),
                    "prog": raw_state.get("prog", 0),
                }
            self.state = new_state
            database.update_user_stats(
                self.user_id, {"mission_state": json.dumps(self.state)}
            )
        else:
            self.state = raw_state

        try:
            self.thread = await self.bot.fetch_channel(self.thread_id)
        except:
            return False
        return True

    async def progress(self):
        """Checks ALL active missions for progress."""
        if not await self.initialize():
            return

        targets = (
            [self.specific_mission_id]
            if self.specific_mission_id
            else list(self.state["active"])
        )

        for m_id in targets:
            if m_id not in self.state["active"]:
                continue
            try:
                await self._process_mission(m_id)
            except Exception as e:
                print(f"Mission Error ({m_id}): {e}")

    async def _process_mission(self, m_id):
        m_def = MISSIONS.get(m_id)
        if not m_def:
            return

        if m_id not in self.state["states"]:
            self.state["states"][m_id] = {"step": 0, "prog": 0}
            self.save_state()

        m_data = self.state["states"][m_id]

        while True:

            if m_data["step"] >= len(m_def["steps"]):
                await self.finish_mission(m_id)
                break

            step = m_def["steps"][m_data["step"]]
            sType = step["type"]

            if sType == "npc":
                await self.send_npc_message(m_def, step["text"])
                delay = step.get("delay", 1.5) * 0.7
                await asyncio.sleep(delay)
                self.advance_step(m_id)

                m_data = self.state["states"][m_id]

            elif sType == "player_choice":

                await self.send_choice_menu(m_id, step["options"])
                break

            elif sType == "objective_hunt":
                prog = m_data["prog"]
                req = step["count"]
                if prog >= req:
                    await self.update_live_message(m_id)
                    await asyncio.sleep(1.0)
                    await self.send_system_message(
                        f"✅ **Objective Complete:** {step['desc']}"
                    )
                    await asyncio.sleep(1.0)
                    self.advance_step(m_id)
                    m_data = self.state["states"][m_id]
                else:
                    await self.send_objective_status(m_def, step, prog, req)
                    break

            elif sType == "objective_checklist":
                if isinstance(m_data["prog"], int):
                    m_data["prog"] = [0] * len(step["targets"])
                    self.state["states"][m_id]["prog"] = m_data["prog"]
                    self.save_state()

                prog_list = m_data["prog"]
                is_complete = True
                for i, t in enumerate(step["targets"]):
                    if prog_list[i] < t["count"]:
                        is_complete = False
                        break

                if is_complete:
                    await self.update_live_message(m_id)
                    await asyncio.sleep(1.0)
                    await self.send_system_message(
                        f"✅ **Objective Complete:** {step['desc']}"
                    )
                    await asyncio.sleep(1.0)
                    self.advance_step(m_id)
                    m_data = self.state["states"][m_id]
                else:
                    await self.send_objective_status(
                        m_def, step, prog_list, step["targets"]
                    )
                    break

            elif sType in [
                "objective_job",
                "objective_project",
                "objective_rift_boss",
                "objective_versus",
            ]:

                if sType == "objective_versus" and step.get("sub_type") == "rank":
                    current_stars = self.u_data.get("versus_stars", 0)

                    if current_stars >= step["count"]:
                        await self.send_system_message(
                            f"✅ **Objective Complete:** {step['desc']}"
                        )
                        await asyncio.sleep(1.0)
                        self.advance_step(m_id)
                        m_data = self.state["states"][m_id]
                        continue
                    else:
                        m_data["prog"] = current_stars
                        await self.send_objective_status(
                            m_def, step, current_stars, step["count"]
                        )
                        break

                prog = m_data["prog"]
                req = step.get("count", 1)

                if prog >= req:
                    await self.send_system_message(
                        f"✅ **Objective Complete:** {step['desc']}"
                    )
                    await asyncio.sleep(1.0)
                    self.advance_step(m_id)
                    m_data = self.state["states"][m_id]
                else:

                    await self.send_objective_status(m_def, step, prog, req)
                    break

            elif sType == "objective_equip":
                if self.check_equip(step["item_id"]):
                    await self.send_system_message(
                        f"✅ **Objective Complete:** Item Equipped"
                    )
                    self.advance_step(m_id)
                    m_data = self.state["states"][m_id]
                else:
                    await self.send_equip_mission_msg(step, m_id)
                    break

            elif sType == "objective_buy_skin":
                if self.check_buy_skin():
                    await self.send_system_message(
                        f"✅ **Objective Complete:** Merch Acquired!"
                    )
                    self.advance_step(m_id)
                    m_data = self.state["states"][m_id]
                else:
                    await self.thread.send(
                        embed=discord.Embed(
                            description=f"**{step['desc']}**\nUse `/shop` to buy Merch.",
                            color=0x3498DB,
                        )
                    )
                    break

            elif sType == "reward":
                await self.send_reward_claim(step, m_id)
                break

    def advance_step(self, m_id):

        if m_id not in self.state["states"]:
            self.state["states"][m_id] = {"step": 0, "prog": 0}

        self.state["states"][m_id]["step"] += 1
        self.state["states"][m_id]["prog"] = 0
        self.save_state()

    def save_state(self):
        database.update_user_stats(
            self.user_id, {"mission_state": json.dumps(self.state)}
        )

    async def finish_mission(self, m_id):
        m_def = MISSIONS.get(m_id)
        if not m_def:
            return

        if m_id not in self.state["completed"]:
            self.state["completed"].append(m_id)

        if m_id in self.state["active"]:
            self.state["active"].remove(m_id)
        if m_id in self.state["states"]:
            del self.state["states"][m_id]

        next_ids = m_def.get("next_mission")
        if next_ids:
            if isinstance(next_ids, str):
                next_ids = [next_ids]

            new_additions = []
            for nid in next_ids:
                if (
                    nid
                    and nid not in self.state["completed"]
                    and nid not in self.state["active"]
                ):
                    self.state["active"].append(nid)
                    self.state["states"][nid] = {"step": 0, "prog": 0}
                    new_additions.append(nid)

            self.save_state()

            if new_additions:

                if len(new_additions) == 1:
                    await self.notify_new_mission(new_additions[0])
                else:
                    await self.notify_multiple_missions(new_additions)
        else:
            self.save_state()
            await self.send_system_message("✅ **All current tasks complete.**")

    async def notify_new_mission(self, m_id):
        m_def = MISSIONS.get(m_id)
        if not m_def:
            return
        embed = discord.Embed(title="📱 Incoming Message", color=0x2ECC71)
        char_icon = config.BOT_EMOJIS.get(m_def.get("character_icon"), "👤")
        embed.description = (
            f"**From:** {char_icon} {m_def['character']}\n\n*Click below to open.*"
        )

        view = NewMessageView(self.bot, self.user_id, m_id)

        if self.thread:
            await self.thread.parent.send(f"<@{self.user_id}>", embed=embed, view=view)
            try:
                await self.thread.delete()
            except:
                pass
            database.update_user_stats(self.user_id, {"mission_thread_id": 0})

    async def notify_multiple_missions(self, m_ids):
        embed = discord.Embed(
            title="📱 Multiple Messages",
            description=f"You received **{len(m_ids)}** new messages!",
            color=0x2ECC71,
        )
        view = NewMessageView(self.bot, self.user_id, m_ids[0])

        if self.thread:
            await self.thread.parent.send(f"<@{self.user_id}>", embed=embed, view=view)
            try:
                await self.thread.delete()
            except:
                pass
            database.update_user_stats(self.user_id, {"mission_thread_id": 0})

    async def update_live_message(self, m_id):

        if self.state is None:
            await self.initialize()
            if self.state is None:
                return

        m_def = MISSIONS.get(m_id)
        if not m_def:
            return

        if m_id not in self.state["states"]:
            return
        step = m_def["steps"][self.state["states"][m_id]["step"]]

        if not self.thread:
            return

        target_msg = None
        async for msg in self.thread.history(limit=10):
            if msg.author.id == self.bot.user.id and msg.embeds:
                if "Mission" in (msg.embeds[0].title or ""):
                    target_msg = msg
                    break

        if not target_msg:
            return

        desc = ""
        m_data = self.state["states"][m_id]
        if step["type"] in [
            "objective_hunt",
            "objective_job",
            "objective_project",
            "objective_versus",
        ]:
            desc = self.render_progress_bar(m_data["prog"], step["count"], step["desc"])
        elif step["type"] == "objective_checklist":
            desc = self.render_checklist(step, m_data["prog"])

        embed = discord.Embed(
            title=f"{config.MISSION_EMOJI} Mission",
            color=0x3498DB,
            description=desc,
        )
        if target_msg.embeds[0].description != desc:
            await target_msg.edit(embed=embed)

    def render_progress_bar(self, prog, req, text):
        pct = min(1.0, prog / max(1, req))
        filled = int(pct * 10)
        bar = "🟦" * filled + "⬛" * (10 - filled)
        return f"**{text}**\n`{bar}` {prog}/{req}"

    def render_checklist(self, step, prog_list):
        if isinstance(prog_list, int):
            prog_list = [0] * len(step["targets"])
        lines = []
        for i, target in enumerate(step["targets"]):
            curr = prog_list[i]
            req = target["count"]
            check = "✅" if curr >= req else "⬜"
            lines.append(f"{check} **{target['desc']} ({curr}/{req})**")
        return "\n".join(lines)

    async def get_webhook(self):
        parent = self.thread.parent
        webhooks = await parent.webhooks()
        wh = next((w for w in webhooks if w.name == "MoCo Mission"), None)
        if not wh:
            wh = await parent.create_webhook(name="MoCo Mission")
        return wh

    async def send_npc_message(self, m_def, text):
        async with self.thread.typing():
            await asyncio.sleep(len(text) * 0.02 + 0.3)
        wh = await self.get_webhook()
        char_name = m_def["character"]
        avatar_url = None
        if m_def.get("character_icon") in config.BOT_EMOJIS:
            parts = config.BOT_EMOJIS[m_def["character_icon"]].split(":")
            if len(parts) == 3:
                avatar_url = (
                    f"https://cdn.discordapp.com/emojis/{parts[2].replace('>', '')}.png"
                )
        await wh.send(
            content=text,
            username=char_name,
            avatar_url=avatar_url,
            thread=self.thread,
        )

    async def send_player_message(self, text, user):
        wh = await self.get_webhook()
        await wh.send(
            content=text,
            username=user.display_name,
            avatar_url=user.display_avatar.url,
            thread=self.thread,
        )

    async def send_choice_menu(self, m_id, options):
        view = ChoiceView(self, m_id, options)
        await self.thread.send(content="** **", view=view)

    async def send_objective_status(self, m_def, step, prog, req_data):
        embed = discord.Embed(
            title=f"{config.MISSION_EMOJI} Mission: {m_def['name']}",
            color=0x3498DB,
        )
        if step["type"] == "objective_checklist":
            desc = self.render_checklist(step, prog)
        else:
            desc = self.render_progress_bar(prog, req_data, step["desc"])

        if step.get("type") == "objective_job":
            desc += "\n\n*Check `/missions` or `/hunt` to see Jobs.*"
        if step.get("type") == "objective_project":
            desc += "\n\n*Check `/missions` or `/hunt` to see Projects.*"

        embed.description = desc
        await self.thread.send(embed=embed)

    async def send_equip_mission_msg(self, step, m_id):
        item_name = game_data.get_item(step["item_id"])["name"]
        embed = discord.Embed(
            title=f"{config.MISSION_EMOJI} Mission",
            description=f"Equip **{item_name}** using `/kit`",
            color=0x3498DB,
        )
        view = EquipCheckView(self, m_id, step["item_id"])
        await self.thread.send(embed=embed, view=view)

    async def send_reward_claim(self, step, m_id):

        if step["reward_type"] == "rift_set_unlock":
            embed = discord.Embed(
                title="🌌 Rift Signal Detected!",
                description=f"**{step['desc']}**",
                color=0x9B59B6,
            )
        else:
            title = "🎁 Reward"
            desc = f"**{step['desc']}**"
            if step["reward_type"] == "item":
                emoji = utils.get_emoji(self.bot, step["item_id"])
                desc = f"{emoji} **{game_data.get_item(step['item_id'])['name']}** (Lvl {step['lvl']})"
            elif step["reward_type"] == "xp":
                desc = f"{config.XP_EMOJI} **{step['amount']} XP**"
            elif step["reward_type"] == "currency":
                desc = f"{config.MOGOLD_EMOJI} **{step['gold']}** | {config.MERCH_TOKEN_EMOJI} **{step['tokens']}**"
            elif step["reward_type"] == "xp_tokens":
                desc = f"{config.XP_EMOJI} **{step['xp']}** | {config.MERCH_TOKEN_EMOJI} **{step['tokens']}**"
            elif step["reward_type"] == "item_xp":
                emoji = utils.get_emoji(self.bot, step["item_id"])
                desc = f"{emoji} **{game_data.get_item(step['item_id'])['name']}** (Lvl {step['lvl']})\n{config.XP_EMOJI} **{step['xp']}**"

            embed = discord.Embed(title=title, description=desc, color=0xF1C40F)

        view = RewardView(self, m_id, step)
        await self.thread.send(embed=embed, view=view)

    async def send_system_message(self, text):
        await self.thread.send(embed=discord.Embed(description=text, color=0x2ECC71))

    def check_equip(self, item_id):
        with database.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM loadouts WHERE user_id=?", (self.user_id,)
            ).fetchone()
        if not row:
            return False
        for key in row.keys():
            if key.endswith("_id") and row[key]:
                inv_item = database.get_item_instance(row[key])
                if inv_item and inv_item["item_id"] == item_id:
                    return True
        return False

    def check_buy_skin(self):
        row = database.get_user_data(self.user_id)
        if row:
            return len(json.loads(dict(row).get("owned_skins", "[]"))) > 0
        return False


class NewMessageView(View):
    def __init__(self, bot, user_id, active_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.active_id = active_id

    @discord.ui.button(label="Open Chat", style=discord.ButtonStyle.green, emoji="💬")
    async def open_chat(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "This isn't your phone!", ephemeral=True
            )

        u_data = dict(database.get_user_data(self.user_id))
        if u_data.get("mission_thread_id"):
            try:
                t = await self.bot.fetch_channel(u_data["mission_thread_id"])
                return await interaction.response.send_message(
                    f"Chat already open: {t.mention}", ephemeral=True
                )
            except:
                pass

        await interaction.response.defer()

        m_def = MISSIONS.get(self.active_id)
        if not m_def:

            if isinstance(self.active_id, list):
                self.active_id = self.active_id[0]
            m_def = MISSIONS.get(self.active_id)
            if not m_def:
                return await interaction.followup.send(
                    "Mission data error.", ephemeral=True
                )

        clean_name = m_def["name"].replace("#", "")
        char = m_def["character"].lower()

        target_channel = interaction.channel
        if isinstance(target_channel, discord.Thread):
            target_channel = target_channel.parent

        try:
            thread = await target_channel.create_thread(
                name=f"{char}-{clean_name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
            )
            await thread.add_user(interaction.user)
            database.update_user_stats(self.user_id, {"mission_thread_id": thread.id})

            engine = MissionEngine(
                self.bot,
                self.user_id,
                thread.id,
                specific_mission_id=self.active_id,
            )
            await engine.progress()

            await interaction.followup.send(
                f"Chat opened: {thread.mention}", ephemeral=True
            )
            try:
                await interaction.message.delete()
            except:
                pass
        except Exception as e:
            await interaction.followup.send(
                f"Failed to create chat. Permissions? {e}", ephemeral=True
            )


class ChoiceView(View):
    def __init__(self, engine, m_id, options):
        super().__init__(timeout=None)
        self.engine = engine
        self.m_id = m_id
        for opt in options:
            self.add_item(ChoiceButton(m_id, opt["label"], opt["text"]))


class ChoiceButton(Button):
    def __init__(self, m_id, label, text):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.reply_text = text
        self.m_id = m_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.engine.user_id:
            return
        await interaction.message.delete()
        await self.view.engine.send_player_message(self.reply_text, interaction.user)
        self.view.engine.advance_step(self.m_id)
        await self.view.engine.progress()


class EquipCheckView(View):
    def __init__(self, engine, m_id, item_id):
        super().__init__(timeout=None)
        self.engine = engine
        self.m_id = m_id
        self.item_id = item_id

    @discord.ui.button(label="Done!", style=discord.ButtonStyle.success)
    async def check(self, interaction, button):
        if interaction.user.id != self.engine.user_id:
            return
        if self.engine.check_equip(self.item_id):
            await interaction.message.delete()
            await self.engine.send_system_message("✅ **Equipment Verified!**")
            self.engine.advance_step(self.m_id)
            await self.engine.progress()
        else:
            await interaction.response.send_message(
                "❌ **Not Equipped!**\nUse `/kit` to equip it first.",
                ephemeral=True,
            )


class RewardView(View):
    def __init__(self, engine, m_id, step):
        super().__init__(timeout=None)
        self.engine = engine
        self.m_id = m_id
        self.step = step

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.success, emoji="🎁")
    async def claim(self, interaction, button):
        if interaction.user.id != self.engine.user_id:
            return

        original_embed = interaction.message.embeds[0]
        new_embed = discord.Embed(
            title=original_embed.title,
            description=original_embed.description,
            color=0x2ECC71,
        )
        new_embed.set_footer(text="✅ Claimed")
        await interaction.response.edit_message(embed=new_embed, view=None)

        step = self.step
        uid = self.engine.user_id
        u_data = dict(database.get_user_data(uid))
        old_xp = u_data["xp"]

        confirmation_msg = ""

        if step["reward_type"] == "rift_set_unlock":
            confirmation_msg = "**System:** 🌌 **Portal Coordinates Updated.** Access new Rifts via `/portal`."

        elif step["reward_type"] in ["item", "item_xp"]:
            item_name = game_data.get_item(step["item_id"])["name"]
            emoji = utils.get_emoji(self.engine.bot, step["item_id"])
            confirmation_msg = f"**Acquired:** {emoji} **{item_name}**"

            database.add_item_to_inventory(
                uid, step["item_id"], "Standard", step["lvl"]
            )
            if step["reward_type"] == "item_xp":
                database.update_user_stats(uid, {"xp": old_xp + step["xp"]})
                confirmation_msg += f" | {config.XP_EMOJI} **{step['xp']} XP**"

        elif step["reward_type"] == "xp":
            database.update_user_stats(uid, {"xp": old_xp + step["amount"]})
            confirmation_msg = (
                f"**Acquired:** {config.XP_EMOJI} **{step['amount']} XP**"
            )

        elif step["reward_type"] == "currency":
            database.update_user_stats(
                uid,
                {
                    "mo_gold": u_data["mo_gold"] + step["gold"],
                    "merch_tokens": u_data["merch_tokens"] + step["tokens"],
                },
            )
            confirmation_msg = f"**Acquired:** {config.MOGOLD_EMOJI} **{step['gold']}** | {config.MERCH_TOKEN_EMOJI} **{step['tokens']}**"

        elif step["reward_type"] == "xp_tokens":
            database.update_user_stats(
                uid,
                {
                    "xp": old_xp + step["xp"],
                    "merch_tokens": u_data["merch_tokens"] + step["tokens"],
                },
            )
            confirmation_msg = f"**Acquired:** {config.XP_EMOJI} **{step['xp']}** | {config.MERCH_TOKEN_EMOJI} **{step['tokens']}**"

        if confirmation_msg:
            await self.engine.thread.send(confirmation_msg)

        new_u = dict(database.get_user_data(uid))
        new_xp = new_u["xp"]
        old_lvl, _, _ = utils.get_level_info(old_xp)
        new_lvl, _, _ = utils.get_level_info(new_xp)
        if new_lvl > old_lvl:
            for lvl in range(old_lvl + 1, new_lvl + 1):
                utils.apply_level_reward(uid, lvl)
            lv_embed = utils.create_level_up_embed(interaction.user, new_lvl)
            await self.engine.thread.send(
                embed=lv_embed,
                view=utils.LevelUpView(self.engine.bot, uid, new_lvl),
            )

        await asyncio.sleep(1.0)
        self.engine.advance_step(self.m_id)
        await self.engine.progress()

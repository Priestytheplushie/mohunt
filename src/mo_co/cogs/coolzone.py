import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
import time
import random
from collections import deque
from mo_co import database, config, utils, game_data
from mo_co.game_data import scaling


MAX_CHAT_LOG = 50
DISPLAY_CHAT_LINES = 8
SYNC_RATE = 2.0


class CoolZoneState:
    """Global state shared across all servers."""

    def __init__(self):
        self.active_hunters = {}
        self.chat_log = deque(maxlen=MAX_CHAT_LOG)
        self.chat_log.append(f"System: Welcome to Cool Zone! 🧊")

    def add_hunter(self, user, interaction_message):

        u_data = database.get_user_data(user.id)
        lvl, _, _ = utils.get_level_info(u_data["xp"]) if u_data else (1, 0, 0)
        is_elite = bool(u_data["is_elite"]) if u_data else False
        prestige = u_data["prestige_level"] if u_data else 0
        emblem = utils.get_emblem(lvl, is_elite, prestige)

        self.active_hunters[user.id] = {
            "user": user,
            "message": interaction_message,
            "join_time": time.time(),
            "last_action": time.time(),
            "target": "Target Dummy",
            "emblem": emblem,
            "cooldowns": {},
            "chat_offset": 0,
            "stats": {
                "damage_dealt": 0,
                "healing_done": 0,
                "damage_taken": 0,
                "sources": {},
            },
        }
        self.add_chat(f"{emblem} **{user.display_name}** entered the zone.")

    def remove_hunter(self, user_id):
        if user_id in self.active_hunters:
            data = self.active_hunters[user_id]
            self.add_chat(f"👋 **{data['user'].display_name}** left.")
            del self.active_hunters[user_id]

    def add_chat(self, msg):
        self.chat_log.append(msg)


ZONE_STATE = CoolZoneState()


class CoolZone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.zone_loop.start()

    def cog_unload(self):
        self.zone_loop.cancel()

    @app_commands.command(name="coolzone", description="Enter the Social Training Area")
    async def coolzone(self, interaction: discord.Interaction):
        if interaction.user.id in ZONE_STATE.active_hunters:
            return await interaction.response.send_message(
                "You are already in the Cool Zone!", ephemeral=True
            )

        database.register_user(interaction.user.id)
        database.ensure_user_has_kit(interaction.user.id)

        u_data = database.get_user_data(interaction.user.id)

        if not u_data["cool_zone_rules_accepted"]:
            embed = discord.Embed(title="📜 Cool Zone Rules", color=0x3498DB)
            embed.description = (
                "Welcome to the Cool Zone, a shared social space for all Hunters!\n\n"
                "**By entering, you agree to:**\n"
                "1. Be respectful to other Hunters.\n"
                "2. No harassment, hate speech, or inappropriate content in Global Chat.\n"
                "3. No spamming commands or chat.\n\n"
                "**Violations will result in a permanent ban from using the bot.**"
            )
            view = CoolZoneRulesView(self.bot, interaction.user.id)
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"{config.DOJO_ICON} Entering Cool Zone...",
            description=f"{config.LOADING_EMOJI} Loading Gear Kit...",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        msg = await interaction.original_response()

        ZONE_STATE.add_hunter(interaction.user, msg)

        view = CoolZoneView(self.bot, interaction.user.id)
        await msg.edit(embed=self.generate_zone_embed(interaction.user.id), view=view)

    def generate_zone_embed(self, user_id):
        session = ZONE_STATE.active_hunters.get(user_id)
        if not session:
            return discord.Embed(title="Disconnected", color=0xE74C3C)

        embed = discord.Embed(title=f"{config.DOJO_ICON} Cool Zone", color=0x9B59B6)

        full_log = list(ZONE_STATE.chat_log)
        total_msgs = len(full_log)
        offset = session.get("chat_offset", 0)

        end_idx = total_msgs - offset
        start_idx = max(0, end_idx - DISPLAY_CHAT_LINES)

        visible_chat = full_log[start_idx:end_idx]
        chat_text = "\n".join(visible_chat)

        if len(chat_text) > 1024:
            chat_text = "..." + chat_text[-(1020):]

        if not chat_text:
            chat_text = "*Silence...*"

        embed.add_field(
            name="💬 Global Chat & Combat Log", value=chat_text, inline=False
        )

        hunters_text = []
        sorted_hunters = sorted(
            ZONE_STATE.active_hunters.items(),
            key=lambda x: x[1]["join_time"],
            reverse=True,
        )

        for uid, data in sorted_hunters[:8]:
            status_icon = "🟢" if time.time() - data["last_action"] < 60 else "💤"
            duration = max(1, time.time() - data["join_time"])
            dps = int(data["stats"]["damage_dealt"] / duration)

            stat_str = f" | {dps:,} DPS" if dps > 0 else ""
            is_me = " **(YOU)**" if uid == user_id else ""

            hunters_text.append(
                f"{status_icon} {data['emblem']} **{data['user'].display_name}**{is_me}{stat_str}"
            )

        if len(ZONE_STATE.active_hunters) > 8:
            hunters_text.append(f"...and {len(ZONE_STATE.active_hunters)-8} others.")

        embed.add_field(
            name=f"Hunters Nearby ({len(ZONE_STATE.active_hunters)})",
            value="\n".join(hunters_text) or "Just you...",
            inline=False,
        )

        my_stats = session["stats"]
        dur = max(1, time.time() - session["join_time"])
        embed.set_footer(
            text=f"Session: {int(dur)}s | Target: {session['target']} | Dmg: {my_stats['damage_dealt']:,} | Heal: {my_stats['healing_done']:,}"
        )

        return embed

    @tasks.loop(seconds=1.0)
    async def zone_loop(self):
        for uid in list(ZONE_STATE.active_hunters.keys()):
            data = ZONE_STATE.active_hunters.get(uid)
            if not data:
                continue

            rate = utils.get_sync_rate(self.bot, data["last_action"])

            last_edit = data.get("last_edit_ts", 0)
            if time.time() - last_edit >= rate:
                try:
                    embed = self.generate_zone_embed(uid)
                    await data["message"].edit(embed=embed)
                    data["last_edit_ts"] = time.time()
                except:
                    ZONE_STATE.remove_hunter(uid)

    @zone_loop.before_loop
    async def before_zone(self):
        await self.bot.wait_until_ready()


class CoolZoneRulesView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="I Agree", style=discord.ButtonStyle.success)
    async def agree(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return

        database.update_user_stats(self.user_id, {"cool_zone_rules_accepted": 1})

        if interaction.user.id in ZONE_STATE.active_hunters:
            return await interaction.response.send_message(
                "Already in!", ephemeral=True
            )

        embed = discord.Embed(
            title=f"{config.DOJO_ICON} Entering Cool Zone...",
            description=f"{config.LOADING_EMOJI} Loading Gear Kit...",
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        msg = await interaction.original_response()

        ZONE_STATE.add_hunter(interaction.user, msg)

        cog = self.bot.get_cog("CoolZone")
        view = CoolZoneView(self.bot, interaction.user.id)
        await msg.edit(embed=cog.generate_zone_embed(interaction.user.id), view=view)


class CoolZoneView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

        session = ZONE_STATE.active_hunters.get(user_id)
        current_target = session["target"] if session else "Target Dummy"

        self.add_item(TargetSelect(current_target))

        self._build_combat_row()

        self.add_item(InspectSelect(bot, user_id))

        self.add_item(ScrollUpButton())
        self.add_item(ScrollDownButton())
        self.add_item(ChatButton())
        self.add_item(StatsButton())

        self.add_item(LeaveButton())

    def _build_combat_row(self):
        kit = database.get_active_kit(self.user_id)
        session = ZONE_STATE.active_hunters.get(self.user_id)

        if not kit or not session:
            self.add_item(Button(label="Error", disabled=True, row=1))
            return

        now = time.time()

        w_id = "monster_slugger"
        if kit["weapon_id"]:
            w = database.get_item_instance(kit["weapon_id"])
            if w:
                w_id = w["item_id"]

        w_icon = utils.get_emoji(self.bot, w_id)

        self.add_item(CombatButton("weapon", w_id, w_icon, discord.ButtonStyle.primary))

        for i in range(1, 4):
            g_inst_id = kit[f"gadget_{i}_id"]
            if g_inst_id:
                g = database.get_item_instance(g_inst_id)
                if g:
                    g_icon = utils.get_emoji(self.bot, g["item_id"])

                    cd_end = session["cooldowns"].get(g["item_id"], 0)
                    remaining = cd_end - now

                    if remaining > 0:
                        btn = Button(
                            label=f"({int(remaining)}s)",
                            emoji=utils.safe_emoji(g_icon),
                            style=discord.ButtonStyle.secondary,
                            disabled=True,
                            row=1,
                        )
                    else:
                        btn = CombatButton(
                            "gadget",
                            g["item_id"],
                            g_icon,
                            discord.ButtonStyle.secondary,
                        )

                    self.add_item(btn)
            else:
                self.add_item(
                    Button(
                        label="Empty",
                        emoji=utils.safe_emoji(config.EMPTY_GADGET),
                        disabled=True,
                        row=1,
                    )
                )


class TargetSelect(Select):
    def __init__(self, current_target):
        options = [
            discord.SelectOption(
                label="Target Dummy",
                description="Infinite HP. Test your DPS.",
                emoji="🎯",
                default=(current_target == "Target Dummy"),
            ),
            discord.SelectOption(
                label="Healing Dummy",
                description="Injured. Test your HPS.",
                emoji="🚑",
                default=(current_target == "Healing Dummy"),
            ),
            discord.SelectOption(
                label="Angry Dummy",
                description="Fights back. Test your defenses.",
                emoji="🥊",
                default=(current_target == "Angry Dummy"),
            ),
        ]
        super().__init__(placeholder="Select Target...", options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        session = ZONE_STATE.active_hunters.get(interaction.user.id)
        if session:
            session["target"] = self.values[0]

            for opt in self.options:
                opt.default = opt.value == self.values[0]

            await interaction.response.edit_message(view=self.view)


class CombatButton(Button):
    def __init__(self, action_type, item_id, emoji_str, style):
        super().__init__(style=style, emoji=utils.safe_emoji(emoji_str), row=1)
        self.action_type = action_type
        self.item_id = item_id

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        session = ZONE_STATE.active_hunters.get(uid)

        if not session:
            try:
                await interaction.response.send_message(
                    "Session expired.", ephemeral=True
                )
            except:
                pass
            return

        session["last_action"] = time.time()

        now = time.time()
        cd_end = session["cooldowns"].get(self.item_id, 0)
        if now < cd_end:
            await interaction.response.defer()
            return

        u_data = database.get_user_data(uid)
        lvl, _, _ = utils.get_level_info(u_data["xp"])
        target = session["target"]
        passives = utils.get_active_passives(uid)
        emblem = session["emblem"]
        name = interaction.user.display_name
        item_icon = self.emoji

        if self.action_type == "weapon":
            base_dmg = scaling.get_weapon_damage(self.item_id, lvl)

            if "really_cool_sticker" in passives:
                base_dmg += scaling.get_passive_value(
                    "really_cool_sticker", passives["really_cool_sticker"]
                )
            if "smelly_socks" in passives:
                base_dmg += scaling.get_passive_value(
                    "smelly_socks", passives["smelly_socks"]
                )
            if "auto_zapper" in passives:
                base_dmg += scaling.get_passive_value(
                    "auto_zapper", passives["auto_zapper"]
                )

            dmg = int(base_dmg * 1.2)

            if target == "Target Dummy":
                session["stats"]["damage_dealt"] += dmg
                ZONE_STATE.add_chat(
                    f"{emblem} **{name}** hit **Dummy** with {item_icon} for **{dmg:,}**"
                )
            elif target == "Healing Dummy":
                ZONE_STATE.add_chat(
                    f"{emblem} **{name}** hit **Healing Dummy**... why? ({dmg})"
                )
            elif target == "Angry Dummy":
                session["stats"]["damage_dealt"] += dmg
                taken = int(dmg * 0.2)
                session["stats"]["damage_taken"] += taken
                ZONE_STATE.add_chat(
                    f"{emblem} **{name}** hit **Angry Dummy** ({dmg}) 💢 Took {taken}!"
                )

            if "vampire_teeth" in passives:
                heal = int(dmg * 0.05)
                session["stats"]["healing_done"] += heal

            if "unstable_lazer" in passives and random.random() < 0.2:
                l_dmg = scaling.get_passive_value(
                    "unstable_lazer", passives["unstable_lazer"]
                )
                session["stats"]["damage_dealt"] += l_dmg
                ZONE_STATE.add_chat(
                    f"{emblem} **{name}** fired **Unstable Lazer** ({l_dmg})!"
                )

            if "unstable_beam" in passives and random.random() < 0.05:
                b_dmg = scaling.get_passive_value(
                    "unstable_beam", passives["unstable_beam"]
                )
                session["stats"]["damage_dealt"] += b_dmg
                ZONE_STATE.add_chat(
                    f"{emblem} **{name}** fired **MEGA BEAM** ({b_dmg})!"
                )

        elif self.action_type == "gadget":
            base_cd = scaling.get_cooldown(self.item_id)
            session["cooldowns"][self.item_id] = now + base_cd

            val = scaling.get_gadget_value(self.item_id, lvl)

            if "gadget_battery" in passives:
                zap = scaling.get_passive_value(
                    "gadget_battery", passives["gadget_battery"]
                )
                session["stats"]["damage_dealt"] += zap
                ZONE_STATE.add_chat(f"⚡ **{name}** Battery Zap ({zap})!")

            if "unstable_lightning" in passives and random.random() < (
                0.1 + passives["unstable_lightning"] * 0.02
            ):
                l_dmg = 100 + (passives["unstable_lightning"] * 20)
                session["stats"]["damage_dealt"] += l_dmg
                ZONE_STATE.add_chat(f"🔌 **{name}** Unstable Lightning ({l_dmg})!")

            if self.item_id in [
                "splash_heal",
                "revitalizing_mist",
                "vitamin_shot",
                "feel_better_bloom",
            ]:
                session["stats"]["healing_done"] += val
                if target == "Healing Dummy":
                    ZONE_STATE.add_chat(
                        f"{emblem} **{name}** healed **Dummy** with {item_icon} for **{val:,}**"
                    )
                else:
                    ZONE_STATE.add_chat(
                        f"{emblem} **{name}** used {item_icon} (Heal {val:,})"
                    )
            else:
                session["stats"]["damage_dealt"] += val
                if target == "Healing Dummy":
                    ZONE_STATE.add_chat(
                        f"{emblem} **{name}** blasted **Healing Dummy** with {item_icon} ({val})"
                    )
                else:
                    log_extra = ""
                    if target == "Angry Dummy":
                        taken = int(val * 0.1)
                        session["stats"]["damage_taken"] += taken
                        log_extra = f" 💢 Took {taken}!"
                    ZONE_STATE.add_chat(
                        f"{emblem} **{name}** blasted **{target}** with {item_icon} for **{val:,}**{log_extra}"
                    )

        session["stats"]["sources"][self.item_id] = session["stats"]["sources"].get(
            self.item_id, 0
        ) + (val if self.action_type == "gadget" else dmg)

        view = CoolZoneView(self.view.bot, uid)

        cog = self.view.bot.get_cog("CoolZone")
        embed = cog.generate_zone_embed(uid)

        await interaction.response.edit_message(embed=embed, view=view)


class ScrollUpButton(Button):
    def __init__(self):
        super().__init__(label="⬆️", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction):
        session = ZONE_STATE.active_hunters.get(interaction.user.id)
        if session:

            session["chat_offset"] = min(
                len(ZONE_STATE.chat_log) - DISPLAY_CHAT_LINES,
                session["chat_offset"] + 5,
            )

            cog = self.view.bot.get_cog("CoolZone")
            embed = cog.generate_zone_embed(interaction.user.id)
            await interaction.response.edit_message(embed=embed)


class ScrollDownButton(Button):
    def __init__(self):
        super().__init__(label="⬇️", style=discord.ButtonStyle.secondary, row=3)

    async def callback(self, interaction: discord.Interaction):
        session = ZONE_STATE.active_hunters.get(interaction.user.id)
        if session:

            session["chat_offset"] = max(0, session["chat_offset"] - 5)

            cog = self.view.bot.get_cog("CoolZone")
            embed = cog.generate_zone_embed(interaction.user.id)
            await interaction.response.edit_message(embed=embed)


class ChatButton(Button):
    def __init__(self):
        super().__init__(
            label="Chat", style=discord.ButtonStyle.primary, emoji="💬", row=3
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChatModal())


class ChatModal(Modal):
    def __init__(self):
        super().__init__(title="Global Hunter Chat")
        self.msg = TextInput(
            label="Message",
            max_length=100,
            placeholder="Say something cool...",
        )
        self.add_item(self.msg)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id not in ZONE_STATE.active_hunters:
            return await interaction.response.send_message(
                "You left the zone.", ephemeral=True
            )

        session = ZONE_STATE.active_hunters[interaction.user.id]
        content = self.msg.value
        emblem = session["emblem"]
        ZONE_STATE.add_chat(f"{emblem} **{interaction.user.display_name}**: {content}")
        session["last_action"] = time.time()

        cog = interaction.client.get_cog("CoolZone")
        embed = cog.generate_zone_embed(interaction.user.id)
        await interaction.response.edit_message(embed=embed)


class InspectSelect(Select):
    def __init__(self, bot, user_id):
        self.bot = bot
        options = []
        candidates = list(ZONE_STATE.active_hunters.values())
        random.shuffle(candidates)

        count = 0
        for s in candidates:
            if count >= 20:
                break
            u = s["user"]
            if u.id == user_id:
                continue

            options.append(
                discord.SelectOption(label=u.display_name, value=str(u.id), emoji="👤")
            )
            count += 1

        if not options:
            options.append(
                discord.SelectOption(label="No one else here...", value="none")
            )

        super().__init__(placeholder="Inspect / Trade...", options=options, row=2)

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "none":
            return await interaction.response.send_message(
                "Forever alone.", ephemeral=True
            )

        target_id = int(val)
        target_session = ZONE_STATE.active_hunters.get(target_id)
        if not target_session:
            return await interaction.response.send_message("They left.", ephemeral=True)

        target_user = target_session["user"]
        cog = self.bot.get_cog("Loadout")
        embed = cog.generate_kit_embed(target_id, target_user.display_name)

        view = View()
        trade_btn = Button(label="Trade", style=discord.ButtonStyle.success, emoji="🤝")

        async def trade_cb(i):
            trade_cog = self.bot.get_cog("Trading")
            await trade_cog.trade.callback(trade_cog, i, target_user)

        trade_btn.callback = trade_cb
        view.add_item(trade_btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class StatsButton(Button):
    def __init__(self):
        super().__init__(
            label="Stats",
            style=discord.ButtonStyle.secondary,
            emoji="📊",
            row=3,
        )

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid not in ZONE_STATE.active_hunters:
            return

        stats = ZONE_STATE.active_hunters[uid]["stats"]
        join_time = ZONE_STATE.active_hunters[uid]["join_time"]
        duration = max(1, time.time() - join_time)

        dps = stats["damage_dealt"] / duration
        hps = stats["healing_done"] / duration

        embed = discord.Embed(title="📊 Session Statistics", color=0xF1C40F)
        embed.add_field(
            name="Damage",
            value=f"Total: **{stats['damage_dealt']:,}**\nDPS: **{dps:,.1f}**",
            inline=True,
        )
        embed.add_field(
            name="Healing",
            value=f"Total: **{stats['healing_done']:,}**\nHPS: **{hps:,.1f}**",
            inline=True,
        )
        embed.add_field(
            name="Tanked",
            value=f"Taken: **{stats['damage_taken']:,}**",
            inline=True,
        )

        if stats["sources"]:
            breakdown = []
            sorted_src = sorted(
                stats["sources"].items(), key=lambda x: x[1], reverse=True
            )
            for src, amt in sorted_src[:10]:
                i_def = game_data.get_item(src)
                name = i_def["name"] if i_def else src
                icon = utils.get_emoji(self.view.bot, src)
                breakdown.append(f"{icon} **{name}**: {amt:,}")
            embed.add_field(
                name="Top Sources", value="\n".join(breakdown), inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class LeaveButton(Button):
    def __init__(self):
        super().__init__(label="Leave", style=discord.ButtonStyle.danger, row=4)

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        if uid in ZONE_STATE.active_hunters:
            stats = ZONE_STATE.active_hunters[uid]["stats"]
            duration = max(1, time.time() - ZONE_STATE.active_hunters[uid]["join_time"])
            dps = stats["damage_dealt"] / duration

            ZONE_STATE.remove_hunter(uid)

            embed = discord.Embed(
                title="🏠 Left Cool Zone",
                description=f"You hung out for {int(duration)}s.",
                color=0x95A5A6,
            )
            embed.add_field(
                name="Final Performance",
                value=f"DPS: {dps:.1f}\nTotal Damage: {stats['damage_dealt']:,}",
            )

            view = View()
            btn = Button(label="Dismiss", style=discord.ButtonStyle.secondary)

            async def dismiss(i):
                await i.response.edit_message(
                    content="👋 **Session Closed.**", embed=None, view=None
                )

            btn.callback = dismiss
            view.add_item(btn)

            await interaction.response.edit_message(
                content=None, embed=embed, view=view
            )
        else:
            await interaction.response.edit_message(
                content="👋 **Disconnected.**", view=None
            )


async def setup(bot):
    await bot.add_cog(CoolZone(bot))

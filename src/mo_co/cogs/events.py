import discord
from discord.ext import tasks, commands
import random
import asyncio
import time
from datetime import datetime, timedelta
from mo_co import database, config, game_data, utils
from mo_co.game_data import scaling
from mo_co.combat_engine import CombatEngine, CombatEntity


class EventClaimView(discord.ui.View):
    def __init__(self, bot, channel_id, event_type, reward_data):
        super().__init__(timeout=300)
        self.bot = bot
        self.channel_id = channel_id
        self.event_type = event_type
        self.reward_data = reward_data
        self.claimed = False

        label = "Claim"
        emoji = None

        if event_type == "crate":

            qty = reward_data.get("amount", 10)
            emoji = discord.PartialEmoji.from_str(config.MERCH_TOKEN_EMOJI)
            label = "Open Crate"
        elif event_type == "core":
            emoji = discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI)
            label = "Absorb Core"

        self.claim_button.label = label
        self.claim_button.emoji = emoji

    @discord.ui.button(style=discord.ButtonStyle.primary)
    async def claim_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.claimed:
            return await interaction.response.send_message(
                "Already claimed!", ephemeral=True
            )

        self.claimed = True
        u_data = database.get_user_data(interaction.user.id)

        if not u_data:
            database.register_user(interaction.user.id)
            u_data = database.get_user_data(interaction.user.id)

        if not u_data:
            return await interaction.response.send_message(
                "Database error. Try again.", ephemeral=True
            )

        msg = ""
        if self.event_type == "core":
            mn, mx = self.reward_data.get("min", 1), self.reward_data.get("max", 1)
            amount = random.randint(mn, mx)
            database.update_user_stats(
                interaction.user.id,
                {"chaos_cores": u_data["chaos_cores"] + amount},
            )
            msg = f"{config.CHAOS_CORE_EMOJI} **You absorbed {amount} Chaos Core{'s' if amount > 1 else ''}!**"

        elif self.event_type == "crate":
            amount = self.reward_data.get("amount", 10)
            database.update_user_stats(
                interaction.user.id,
                {"merch_tokens": u_data["merch_tokens"] + amount},
            )
            msg = f"{config.MERCH_TOKEN_EMOJI} **You found {amount} Merch Tokens!**"

        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(msg, ephemeral=True)
        self.bot.active_core_channels.discard(self.channel_id)
        self.stop()

    async def on_timeout(self):
        self.bot.active_core_channels.discard(self.channel_id)
        try:
            for item in self.children:
                item.disabled = True
            await self.message.edit(view=self)
        except:
            pass


class InvasionEventView(discord.ui.View):
    def __init__(self, bot, channel_id, boss_data, active_users=1):
        super().__init__(timeout=600)
        self.bot = bot
        self.channel_id = channel_id

        self.boss_name = utils.format_monster_name(boss_data)
        self.boss_icon = config.MOBS.get(boss_data, "👹")

        base_hp = 50000

        scaling_hp = 75000 * max(1, active_users)
        total_pool = base_hp + scaling_hp

        self.max_shield = int(total_pool * 0.4)
        self.current_shield = self.max_shield

        self.max_hp = total_pool
        self.current_hp = self.max_hp

        self.participants = {}
        self.claimed_users = set()

        self.active = True
        self.last_update_ts = 0
        self.update_lock = False

        self.end_ts = int(time.time() + 600)

        self.update_button_label()

    def get_progress_bar(self, current, max_val, color_block="🟩"):
        pct = min(1.0, max(0.0, current / max_val))
        filled = int(pct * 10)
        return color_block * filled + "⬛" * (10 - filled)

    def get_embed(self):
        color = 0xE74C3C
        status_text = "🛡️ **SHIELD ACTIVE**"

        if self.current_shield > 0:
            color = 0xF1C40F
            shield_bar = self.get_progress_bar(
                self.current_shield, self.max_shield, "🟨"
            )
            hp_bar = "🔒 " * 10
            hp_text = "??? / ???"
            mechanic_hint = "\n*💡 Gadgets & Passives deal 200% Dmg to Shields!\n⚠️ Weapons deal 10% Dmg to Shields.*"
        else:
            status_text = "💔 **SHIELD SHATTERED!**"
            shield_bar = "⬛" * 10
            hp_bar = self.get_progress_bar(self.current_hp, self.max_hp, "🟥")
            hp_text = f"{self.current_hp:,} / {self.max_hp:,}"
            mechanic_hint = "\n*🔥 Boss Exposed! All attacks deal 150% Damage!*"

        if self.current_hp <= 0:
            status_text = "💀 **DEFEATED**"
            color = 0x2ECC71
            mechanic_hint = "\n*✅ Threat Neutralized. Claim your rewards below.*"

        embed = discord.Embed(
            title=f"{config.CHAOS_ALERT} INVASION ALERT: {self.boss_name.upper()}",
            color=color,
        )

        embed.add_field(
            name="⏳ Time Remaining",
            value=f"<t:{self.end_ts}:R>",
            inline=False,
        )
        embed.add_field(
            name=status_text,
            value=f"`{shield_bar}` {self.current_shield:,} / {self.max_shield:,}",
            inline=False,
        )
        embed.add_field(name="❤️ HEALTH", value=f"`{hp_bar}` {hp_text}", inline=False)

        sorted_p = sorted(
            self.participants.items(), key=lambda x: x[1]["dmg"], reverse=True
        )[:3]
        lb_text = ""
        for i, (uid, data) in enumerate(sorted_p):
            emblem = data.get("emblem", "👤")
            lb_text += f"#{i+1} {emblem} **{data['name']}**: {data['dmg']:,}\n"

        if not lb_text:
            lb_text = "No damage dealt yet."

        embed.add_field(name="🏆 Top Hunters", value=lb_text, inline=False)
        embed.description = f"Use `/kit` to optimize your loadout!{mechanic_hint}"

        try:
            url = f"https://cdn.discordapp.com/emojis/{self.boss_icon.split(':')[2].replace('>', '')}.png"
            embed.set_thumbnail(url=url)
        except:
            pass

        return embed

    def update_button_label(self):
        self.clear_items()

        if self.current_hp <= 0:
            btn = discord.ui.Button(
                label="Claim Rewards",
                style=discord.ButtonStyle.success,
                emoji="🎁",
                custom_id="invasion_claim",
            )
            btn.callback = self.claim_rewards
            self.add_item(btn)
        else:
            if self.current_shield > 0:
                label = "Intercept (Shielded)"
                style = discord.ButtonStyle.secondary
                emoji = "🛡️"
            else:
                label = "Intercept (Exposed)"
                style = discord.ButtonStyle.danger
                emoji = "⚔️"

            atk_btn = discord.ui.Button(
                label=label,
                style=style,
                emoji=emoji,
                custom_id="invasion_attack",
            )
            atk_btn.callback = self.attack_btn
            self.add_item(atk_btn)

    async def attack_btn(self, interaction: discord.Interaction):
        if not self.active:
            return await interaction.response.send_message(
                "Event ended.", ephemeral=True
            )

        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)
        u_dict = dict(u_data)

        lvl, _, _ = utils.get_level_info(u_dict["xp"])
        is_elite = bool(u_dict.get("is_elite", 0))
        prestige = u_dict.get("prestige_level", 0)
        emblem = utils.get_emblem(lvl, is_elite, prestige)

        engine = CombatEngine(self.bot, gamemode="hunt", mode="sim")
        player = CombatEntity(engine, interaction.user.display_name, is_player=True)
        player.user_id = interaction.user.id
        player.icon = emblem

        kit_data = {
            "weapon": {
                "id": "monster_slugger",
                "modifier": "Standard",
                "level": lvl,
            },
            "gadgets": [],
            "passives": {},
        }

        with database.get_connection() as conn:
            row = conn.execute(
                "SELECT active_kit_index FROM users WHERE user_id=?",
                (interaction.user.id,),
            ).fetchone()
            idx = row["active_kit_index"] if row else 1
            kit = conn.execute(
                "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
                (interaction.user.id, idx),
            ).fetchone()

            if kit:
                if kit["weapon_id"]:
                    w = database.get_item_instance(kit["weapon_id"])
                    if w:
                        kit_data["weapon"] = {
                            "id": w["item_id"],
                            "modifier": w["modifier"],
                            "level": w["level"],
                        }
                for i in range(1, 4):
                    gid = kit[f"gadget_{i}_id"]
                    if gid:
                        g = database.get_item_instance(gid)
                        if g:
                            kit_data["gadgets"].append(
                                {
                                    "id": g["item_id"],
                                    "lvl": g["level"],
                                    "cd": 0,
                                }
                            )
                for i in range(1, 4):
                    pid = kit[f"passive_{i}_id"]
                    if pid:
                        p = database.get_item_instance(pid)
                        if p:
                            kit_data["passives"][p["item_id"]] = p["level"]

        player.setup_stats(
            lvl,
            hp=u_dict["current_hp"],
            weapon=kit_data["weapon"],
            gadgets=kit_data["gadgets"],
            passives=kit_data["passives"],
        )
        engine.add_entity(player, "A")

        dummy = CombatEntity(engine, "Boss", is_player=False)
        dummy.setup_stats(lvl + 10, hp=1000000)
        dummy.taunt = True
        engine.add_entity(dummy, "B")

        for _ in range(5):
            engine.tick()

        raw_damage = player.total_dmg_dealt

        weapon_dmg = 0
        gadget_dmg = 0

        for src, amt in player.damage_sources.items():
            idef = game_data.get_item(src)
            if idef and idef["type"] == "weapon":
                weapon_dmg += amt
            else:
                gadget_dmg += amt

        actual_dealt = 0
        status_msg = ""

        if self.current_shield > 0:
            w_adjusted = int(weapon_dmg * 0.10)
            g_adjusted = int(gadget_dmg * 2.00)
            actual_dealt = w_adjusted + g_adjusted

            self.current_shield = max(0, self.current_shield - actual_dealt)

            status_msg = f"🛡️ **Shield Hit!**\nWeapon: {weapon_dmg} ➔ {w_adjusted} (Resisted)\nGadget: {gadget_dmg} ➔ {g_adjusted} (**Effective!**)"

            if self.current_shield <= 0:
                status_msg += "\n💔 **SHIELD SHATTERED!**"
                self.update_button_label()
        else:
            actual_dealt = int(raw_damage * 1.5)
            self.current_hp = max(0, self.current_hp - actual_dealt)
            status_msg = (
                f"⚔️ **Critical Hit!** (Exposed)\nRaw: {raw_damage} ➔ {actual_dealt}"
            )

        if interaction.user.id not in self.participants:
            self.participants[interaction.user.id] = {
                "dmg": 0,
                "name": interaction.user.display_name,
                "emblem": emblem,
            }

        self.participants[interaction.user.id]["dmg"] += actual_dealt
        self.participants[interaction.user.id]["emblem"] = emblem

        log_txt = "\n".join(engine.logs[-5:])

        embed = discord.Embed(title="⚔️ Skirmish Report", color=0x2B2D31)
        embed.description = f"{status_msg}\n\n**Combat Log:**\n{log_txt}"
        embed.set_footer(text=f"Total Dealt: {actual_dealt:,}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

        if self.current_hp <= 0:
            self.active = False
            self.bot.active_core_channels.discard(self.channel_id)
            self.update_button_label()

            victory_embed = self.get_embed()
            victory_embed.color = 0x2ECC71
            victory_embed.title = f"🎉 {self.boss_name} DEFEATED!"
            victory_embed.description = f"**Threat Neutralized!**\n\nParticipants: {len(self.participants)}\nFinal Blow: {interaction.user.display_name}\n\n*Click 'Claim Rewards' to collect your share!*"

            await self.message.edit(embed=victory_embed, view=self)

        else:
            now = time.time()
            if now - self.last_update_ts > 5 and not self.update_lock:
                self.update_lock = True
                self.last_update_ts = now
                try:
                    await self.message.edit(embed=self.get_embed(), view=self)
                except:
                    pass
                self.update_lock = False

    async def claim_rewards(self, interaction: discord.Interaction):
        uid = interaction.user.id

        if uid in self.claimed_users:
            return await interaction.response.send_message(
                "✅ You have already claimed your rewards.", ephemeral=True
            )

        if uid not in self.participants:
            return await interaction.response.send_message(
                "❌ You did not participate in this hunt.", ephemeral=True
            )

        data = self.participants[uid]
        dmg = data["dmg"]
        threshold = self.max_hp * 0.01

        if dmg < threshold:
            return await interaction.response.send_message(
                "⚠️ Your contribution was too low for rewards (<1%).",
                ephemeral=True,
            )

        player_count = len(self.participants)
        scale_mult = min(1.0, 0.4 + (player_count * 0.15))

        xp = int(5000 * scale_mult)
        gold = int(10 * scale_mult)
        cores = 0
        shards = int(5 * scale_mult)

        sorted_p = sorted(
            self.participants.items(), key=lambda x: x[1]["dmg"], reverse=True
        )
        rank = next((i + 1 for i, x in enumerate(sorted_p) if x[0] == uid), 999)

        if rank <= 3:
            xp += int(3000 * scale_mult)
            gold += int(15 * scale_mult)
            cores += 1
            shards += int(10 * scale_mult)

        self.claimed_users.add(uid)

        u_data = database.get_user_data(uid)
        updates = {
            "xp": u_data["xp"] + xp,
            "mo_gold": u_data["mo_gold"] + gold,
            "chaos_cores": u_data["chaos_cores"] + cores,
            "chaos_shards": u_data["chaos_shards"] + shards,
        }
        database.update_user_stats(uid, updates)

        embed = discord.Embed(title="📦 Hunt Summary", color=0xF1C40F)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        scale_msg = ""
        if scale_mult < 1.0:
            scale_msg = f"\n*(Small Squad Penalty: {int(scale_mult*100)}% Rewards)*"

        embed.description = f"**Rank:** #{rank}\n**Damage:** {dmg:,}\n**Squad Size:** {player_count}{scale_msg}\n\n**Rewards:**"
        embed.add_field(name="XP", value=f"{config.XP_EMOJI} {xp:,}", inline=True)
        embed.add_field(
            name="Currency", value=f"{config.MOGOLD_EMOJI} {gold}", inline=True
        )

        if cores > 0:
            embed.add_field(
                name="Loot",
                value=f"{config.CHAOS_CORE_EMOJI} x{cores}",
                inline=True,
            )
        if shards > 0:
            embed.add_field(
                name="Shards",
                value=f"{config.CHAOS_SHARD_EMOJI} x{shards}",
                inline=True,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_timeout(self):
        if self.active and self.current_hp > 0:
            self.active = False
            self.bot.active_core_channels.discard(self.channel_id)

            for child in self.children:
                child.disabled = True
                child.label = "Boss Fled"
                child.style = discord.ButtonStyle.secondary

            embed = self.get_embed()
            embed.title = f"💨 {self.boss_name} FLED!"
            embed.description = (
                "The invasion force retreated before you could stop them."
            )
            embed.color = 0x95A5A6

            try:
                await self.message.edit(embed=embed, view=self)
            except:
                pass


class ChaosEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.active_elites = []
        self.bot.active_world_events = {}
        self.last_event_spawn = {}
        self.bot.active_core_channels = set()
        self.elite_rotation_loop.start()
        self.world_event_loop.start()

    def cog_unload(self):
        self.elite_rotation_loop.cancel()
        self.world_event_loop.cancel()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        await self.maybe_spawn_event(message.channel, message.author.id)

    async def maybe_spawn_event(self, channel, user_id):
        now = datetime.utcnow()
        if channel.id in self.bot.active_core_channels:
            return
        last = self.last_event_spawn.get(channel.id)
        if last and now - last < timedelta(minutes=15):
            return

        base_chance = 0.02
        passives = utils.get_active_passives(user_id)
        if "bunch_of_dice" in passives:
            luck = scaling.get_passive_value("bunch_of_dice", passives["bunch_of_dice"])
            base_chance *= 1.0 + (luck / 100.0)

        if random.random() > base_chance:
            return

        self.last_event_spawn[channel.id] = now
        self.bot.active_core_channels.add(channel.id)

        roll = random.random()
        if roll < 0.60:
            await self.spawn_merch_crate(channel)
        elif roll < 0.90:
            await self.spawn_invasion_event(channel)
        else:
            await self.spawn_chaos_core(channel)

    def get_active_user_count(self):
        try:
            with database.get_connection() as conn:
                cutoff = (datetime.utcnow() - timedelta(minutes=30)).isoformat()
                row = conn.execute(
                    "SELECT COUNT(*) FROM users WHERE last_hunt_time > ?",
                    (cutoff,),
                ).fetchone()
                return row[0] if row else 1
        except:
            return 1

    async def spawn_invasion_event(self, channel):
        potential_bosses = [
            "Overlord",
            "Bug Lord",
            "Smasher",
            "Big Papa",
            "Berserker",
            "Mama Jumper",
            "Savage Spirit",
            "Mama Boomer",
            "Alpha Charger",
            "Toxic Spitter",
            "Princess Ladybug",
        ]
        boss = random.choice(potential_bosses)

        mod = random.choice(["Megacharged", "Overcharged", "Chaos"])
        boss_name = f"{mod} {boss}"

        active_count = self.get_active_user_count()

        view = InvasionEventView(self.bot, channel.id, boss_name, active_count)
        view.message = await channel.send(embed=view.get_embed(), view=view)

    async def spawn_merch_crate(self, channel):
        roll = random.random()
        if roll < 0.60:
            name = "mo.co Crate"
            emoji_str = config.MOCO_CRATE_EMOJI
            amount = 10
            color = 0x3498DB
        elif roll < 0.90:
            name = "Large mo.co Crate"
            emoji_str = config.MOCO_CRATE_LARGE_EMOJI
            amount = 25
            color = 0x9B59B6
        else:
            name = "XL mo.co Crate"
            emoji_str = config.MOCO_CRATE_XL_EMOJI
            amount = 50
            color = 0xF1C40F

        embed = discord.Embed(
            title=f"{config.MERCH_TOKEN_EMOJI} {name} Found!",
            description=f"Someone lost a shipment! Contains **{amount}** Merch Tokens.",
            color=color,
        )
        try:
            eid = emoji_str.split(":")[2].replace(">", "")
            embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{eid}.png")
        except:
            pass

        view = EventClaimView(self.bot, channel.id, "crate", {"amount": amount})
        view.message = await channel.send(embed=embed, view=view)

    async def spawn_chaos_core(self, channel):
        embed = discord.Embed(
            title=f"{config.CHAOS_CORE_EMOJI} Unstable Core Found!",
            description="A wild Chaos Core appeared! Grab it before it destabilizes.",
            color=0x9B59B6,
        )
        try:
            eid = config.CHAOS_CORE_EMOJI.split(":")[2].replace(">", "")
            embed.set_thumbnail(url=f"https://cdn.discordapp.com/emojis/{eid}.png")
        except:
            pass

        view = EventClaimView(self.bot, channel.id, "core", {"min": 1, "max": 2})
        view.message = await channel.send(embed=embed, view=view)

    @tasks.loop(minutes=60)
    async def elite_rotation_loop(self):
        self.bot.active_elites = [random.choice(game_data.ELITE_POOL_50)]

    @elite_rotation_loop.before_loop
    async def before_rotation(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=10)
    async def world_event_loop(self):
        self.bot.active_world_events = {}
        if random.random() < 0.30:
            return
        pool = [
            w["id"]
            for w in game_data.WORLDS
            if w["id"] not in ["downtown_chaos", "chaos_invasion"]
        ]
        selected = random.sample(pool, max(1, int(len(pool) * 0.33)))
        for wid in selected:
            self.bot.active_world_events[wid] = random.choice(
                ["double_xp", "overcharged", "chaos"]
            )

    @world_event_loop.before_loop
    async def before_world_events(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ChaosEvents(bot))

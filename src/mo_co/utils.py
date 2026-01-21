import discord
from mo_co import config, database, game_data
from mo_co.game_data import scaling
from datetime import datetime, timedelta
import asyncio
import json
import random


def safe_emoji(emoji_str):
    if not emoji_str:
        return None
    if isinstance(emoji_str, discord.PartialEmoji):
        return emoji_str
    if emoji_str.startswith("<"):
        try:
            return discord.PartialEmoji.from_str(emoji_str)
        except:
            return None
    return discord.PartialEmoji(name=emoji_str)


def get_equipped_skin(user_id, item_id):
    kit = database.get_active_kit(user_id)
    if not kit:
        return None

    if kit["weapon_id"]:
        r = database.get_item_instance(kit["weapon_id"])
        if r and r["item_id"] == item_id:
            return kit["weapon_skin"]

    for i in range(1, 4):
        inst_id = kit[f"gadget_{i}_id"]
        if inst_id:
            r = database.get_item_instance(inst_id)
            if r and r["item_id"] == item_id:
                return kit[f"gadget_{i}_skin"]

    if kit["ride_id"]:
        r = database.get_item_instance(kit["ride_id"])
        if r and r["item_id"] == item_id:
            return kit["ride_skin"]

    return None


def get_emoji(bot, key, user_id=None):
    if key == "overcharged_amulet":
        return config.OVERCHARGED_ICON
    if key == "bunch_of_dice":
        return config.BUNCH_OF_DICE_EMOJI
    if key == "turbo_pills":
        return config.TURBO_PILLS_EMOJI
    if key == "golden_boombox":
        return config.GOLDEN_BOOMBOX_EMOJI
    if key == "golden_fireworks":
        return config.GOLDEN_FIREWORKS_EMOJI
    if key == "golden_taser":
        return config.GOLDEN_TASER_EMOJI
    if key == "classic_snow_globe":
        return config.CLASSIC_SNOW_GLOBE_EMOJI
    if key == "classic_shelldon":
        return config.CLASSIC_SHELLDON_EMOJI
    if key == "classic_really_cool_sticker":
        return config.CLASSIC_STICKER_EMOJI
    if key == "classic_lifejacket":
        return config.CLASSIC_LIFEJACKET_EMOJI
    if key == "water_balloon":
        return config.WATER_BALLOON_EMOJI

    if user_id:
        skin_id = get_equipped_skin(user_id, key)
        if skin_id:
            return get_emoji(bot, skin_id)

    if isinstance(key, str) and key.startswith("<") and key.endswith(">"):
        return key

    if bot and hasattr(bot, "emoji_map"):
        if key in bot.emoji_map:
            return bot.emoji_map.get(key, "📦")

    if key in config.MOBS:
        return config.MOBS[key]
    return "📦"


def format_item(
    bot,
    item_data,
    modifier,
    level,
    instance_id,
    show_quote=False,
    user_id=None,
):
    emoji = get_emoji(bot, item_data["id"], user_id)
    mod_str = f"[{modifier}] " if modifier != "Standard" else ""
    quote_str = (
        f"\n*\"{item_data['quote']}\"*" if show_quote and item_data.get("quote") else ""
    )
    if item_data["type"] == "ride":
        return (
            f"`ID: {instance_id}` {emoji} **{mod_str}{item_data['name']}**{quote_str}"
        )
    gp = get_item_gp(item_data["id"], level)
    skin_txt = ""
    if user_id:
        skin_id = get_equipped_skin(user_id, item_data["id"])
        if skin_id:
            skin_def = game_data.get_item(skin_id)
            skin_name = skin_def["name"] if skin_def else "Custom"
            skin_txt = f" *(Skin: {skin_name})*"
    return f"`ID: {instance_id}` {emoji} **{mod_str}{item_data['name']}**{skin_txt} (Lvl {level} | {config.GEAR_POWER_EMOJI} {gp}){quote_str}"


def get_level_info(total_xp):
    cumulative_xp = 0
    for entry in config.LEVEL_DATA:
        level = entry["lvl"]
        cost = entry["xp_cost"]
        if total_xp < cumulative_xp + cost:
            current_progress = total_xp - cumulative_xp
            return level, cost, current_progress
        cumulative_xp += cost
    return config.LEVEL_DATA[-1]["lvl"], 0, 0


def get_max_base_xp():
    return sum(e["xp_cost"] for e in config.LEVEL_DATA)


def get_elite_level_info(elite_xp):
    for i in range(len(config.ELITE_LEVEL_MAP) - 1):
        curr_lvl, curr_xp = config.ELITE_LEVEL_MAP[i]
        next_lvl, next_xp = config.ELITE_LEVEL_MAP[i + 1]
        if elite_xp < next_xp:
            range_xp, range_lvls = next_xp - curr_xp, next_lvl - curr_lvl
            xp_per_lvl = range_xp / range_lvls
            xp_in_range = elite_xp - curr_xp
            levels_gained = int(xp_in_range // xp_per_lvl)
            current_elite_lvl = curr_lvl + levels_gained
            return (
                current_elite_lvl,
                int(xp_per_lvl),
                int(xp_in_range % xp_per_lvl),
            )
    return config.ELITE_LEVEL_MAP[-1][0], 0, 0


def get_active_passives(user_id):
    conn = database.get_connection()
    u = conn.execute(
        "SELECT active_kit_index FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    idx = u["active_kit_index"] if u else 1
    kit = conn.execute(
        "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
        (user_id, idx),
    ).fetchone()
    effects = {}
    if not kit:
        conn.close()
        return effects
    slots = [
        "weapon_id",
        "gadget_1_id",
        "gadget_2_id",
        "gadget_3_id",
        "passive_1_id",
        "passive_2_id",
        "passive_3_id",
        "elite_module_id",
        "ring_1_id",
        "ring_2_id",
        "ring_3_id",
    ]
    for s in slots:
        inst_id = kit[s]
        if inst_id:
            row = conn.execute(
                "SELECT item_id, level FROM inventory WHERE instance_id=?",
                (inst_id,),
            ).fetchone()
            if row:
                effects[row["item_id"]] = row["level"]
    dice = conn.execute(
        "SELECT level FROM inventory WHERE user_id=? AND item_id='bunch_of_dice'",
        (user_id,),
    ).fetchone()
    if dice:
        effects["bunch_of_dice"] = dice[0]
    conn.close()
    return effects


def get_max_hp(user_id, level=None):
    if level is None:
        u = database.get_user_data(user_id)
        if not u:
            return 1600
        level, _, _ = get_level_info(u["xp"])
    base_hp = get_base_hp(level)
    passives = get_active_passives(user_id)
    if "healthy_snacks" in passives:
        item_lvl = passives["healthy_snacks"]
        mult = 0.02 + (item_lvl * 0.005)
        base_hp = int(base_hp * (1 + mult))
    return base_hp


def get_base_hp(level):
    level = min(50, level)
    for entry in config.LEVEL_DATA:
        if entry["lvl"] == level:
            return entry["hp"]
    return config.LEVEL_DATA[-1]["hp"]


def calculate_healing(base_amount, passives):
    if "healing_charm" in passives:
        item_lvl = passives["healing_charm"]
        mult = 0.10 + (item_lvl * 0.01)
        return int(base_amount * (1 + mult))
    return int(base_amount)


def get_tier(level):
    if level <= 10:
        return "Bronze"
    if level <= 25:
        return "Silver"
    if level <= 50:
        return "Gold"
    return "Diamond"


def get_emblem(level, is_elite=False, prestige=0):
    if prestige > 0:
        tier_set = (
            config.PRESTIGE_1
            if prestige == 1
            else (config.PRESTIGE_2 if prestige == 2 else config.PRESTIGE_MAX)
        )
        if level <= 24:
            return tier_set["bronze"]
        if level <= 49:
            return tier_set["silver"]
        return tier_set["gold"]
    if is_elite or level > 50:
        return config.ELITE_EMBLEM
    if level < 10:
        return config.EMBLEMS["bronze"]
    if level < 25:
        return config.EMBLEMS["silver"]
    if level < 50:
        return config.EMBLEMS["gold"]
    return config.EMBLEMS["diamond"]


def get_level_reward(level):
    for entry in config.LEVEL_DATA:
        if entry["lvl"] == level:
            return entry.get("reward", "kit")
    return "kit"


def apply_level_reward(user_id, level):
    reward_raw = get_level_reward(level)
    u_data = database.get_user_data(user_id)
    if "world" in reward_raw:
        return f"Unlocked: {reward_raw.split(':')[-1]}"
    elif "rift" in reward_raw:
        return f"Unlocked Rift: {reward_raw.split(':')[-1]}"
    elif "dojo" in reward_raw:
        return f"Unlocked Dojo: {reward_raw.split(':')[-1]}"
    elif "bundle" in reward_raw:
        return f"Unlocked: Elite Status, Chaos Extreme, Feline Invasion & More!"
    elif "elite" in reward_raw:
        return "Unlocked: Run /elite to enroll!"
    else:
        new_kits = u_data["chaos_kits"] + 1
        database.update_user_stats(user_id, {"chaos_kits": new_kits})
        return "kit"


def get_item_gp(item_id, level):
    item_def = game_data.get_item(item_id)
    if not item_def:
        return 0
    if item_def["type"] == "ride":
        return 0
    type_str = item_def["type"]
    if type_str == "weapon":
        return int(1.25 * (level**2) + 3.0 * level + 10)
    elif type_str in ["gadget", "passive"]:
        return int(0.4 * (level**2) + 1.5 * level + 20)
    elif type_str == "smart_ring":
        return 185 + ((level - 1) * 13)
    return level * 10


def get_total_gp(user_id):
    conn = database.get_connection()
    u = conn.execute(
        "SELECT active_kit_index FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    idx = u["active_kit_index"] if u else 1
    kit = conn.execute(
        "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?",
        (user_id, idx),
    ).fetchone()
    if not kit:
        conn.close()
        return 0
    slots = [
        "weapon_id",
        "gadget_1_id",
        "gadget_2_id",
        "gadget_3_id",
        "passive_1_id",
        "passive_2_id",
        "passive_3_id",
        "elite_module_id",
        "ring_1_id",
        "ring_2_id",
        "ring_3_id",
    ]
    total_gp = 0
    for s in slots:
        inst_id = kit[s]
        if inst_id:
            row = conn.execute(
                "SELECT item_id, level FROM inventory WHERE instance_id=?",
                (inst_id,),
            ).fetchone()
            if row:
                total_gp += get_item_gp(row["item_id"], row["level"])
    conn.close()
    return total_gp


def get_item_stats(item_id, level):
    item_def = game_data.get_item(item_id)
    if not item_def:
        return "Unknown Item", 0
    if item_def["type"] == "ride":
        return "Ride: Active", 0
    desc, val = scaling.get_item_details(item_id, level, item_def["type"])
    if item_id == "toothpick_and_shield":
        desc += "\n*(Passive: -30% Dmg Taken)*"
    elif item_id == "medicne_ball":
        desc += "\n*(Passive: +30% Max HP)*"
    return desc, val


def get_stat_diff(item_id, old_level, new_level):
    if game_data.get_item(item_id)["type"] == "ride":
        return "Ride Upgrade"
    label_old, val_old = get_item_stats(item_id, old_level)
    label_new, val_new = get_item_stats(item_id, new_level)
    if isinstance(val_old, tuple):
        val_old = val_old[0]
    if isinstance(val_new, tuple):
        val_new = val_new[0]
    diff = round(val_new - val_old, 2)
    return f"{label_old} ➔ {label_new} ({diff:+,})"


def create_level_up_embed(user, level, is_elite_lvl=False):
    if is_elite_lvl:
        embed = discord.Embed(
            title=f"Bam-a-lam! Elite Level {level}",
            description=f"{user.mention} reached **Elite Level {level}**!",
            color=0x9B59B6,
        )
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/emojis/1457926066567119063.png"
        )
        embed.add_field(
            name="Elite Perks",
            value=f"Increases Smart Ring Level Cap to {level}!",
            inline=False,
        )
        return embed
    u = database.get_user_data(user.id)
    prestige = u["prestige_level"] if u else 0
    emblem = get_emblem(level, prestige=prestige)
    hp = get_max_hp(user.id, level)
    embed = discord.Embed(
        title=f"Bam-a-lam! You are now Level {level}",
        description=f"{user.mention} reached **Level {level}**!",
        color=0xF1C40F,
    )
    embed.add_field(
        name="Stats",
        value=f"❤️ Max HP: **{hp}**\nBadge: {emblem} {get_tier(level)}",
        inline=False,
    )
    reward_raw = get_level_reward(level)
    if "world" in reward_raw:
        embed.add_field(
            name="Reward",
            value=f"{config.MAP_EMOJI} **Unlocked World: {reward_raw.split(':')[1]}**",
            inline=False,
        )
    elif "rift" in reward_raw:
        embed.add_field(
            name="Reward",
            value=f"{config.RIFTS_EMOJI} **Unlocked Rifts: {reward_raw.split(':')[1]}**",
            inline=False,
        )
    elif "dojo" in reward_raw:
        embed.add_field(
            name="Reward",
            value=f"{config.DOJO_ICON} **Unlocked Dojo: {reward_raw.split(':')[1]}**",
            inline=False,
        )
    elif "bundle" in reward_raw:
        embed.add_field(
            name="Rewards",
            value=f"**Elite Status**\n{config.RIFTS_EMOJI} Chaos Extreme Rifts\n{config.DOJO_ICON} More Advanced Training\n{config.MAP_EMOJI} Feline Invasion",
            inline=False,
        )
    elif "elite" in reward_raw:
        embed.add_field(
            name="Reward",
            value=f"{config.ELITE_EMOJI} **Elite Hunter Program** (Run /elite)",
            inline=False,
        )
    else:
        embed.add_field(
            name="Reward",
            value=f"{config.CHAOS_CORE_EMOJI} **+1 Chaos Kit**",
            inline=False,
        )
    return embed


def add_user_xp(user_id, amount):
    u = database.get_user_data(user_id)
    current_xp, current_elite, is_elite, prestige = (
        u["xp"],
        u["elite_xp"],
        bool(u["is_elite"]),
        u["prestige_level"],
    )
    if prestige > 0:
        amount = int(amount * (1.0 + (0.10 * prestige)))
    old_lvl, _, _ = get_level_info(current_xp)
    old_elite_lvl, _, _ = get_elite_level_info(current_elite)
    max_base = get_max_base_xp()
    xp_to_base, xp_to_elite = 0, 0
    if current_xp < max_base:
        space = max_base - current_xp
        if amount <= space:
            xp_to_base = amount
        else:
            xp_to_base = space
            if is_elite:
                xp_to_elite = amount - space
    else:
        if is_elite:
            xp_to_elite = amount
    new_xp, new_elite = current_xp + xp_to_base, current_elite + xp_to_elite
    database.update_user_stats(user_id, {"xp": new_xp, "elite_xp": new_elite})
    new_lvl, _, _ = get_level_info(new_xp)
    new_elite_lvl, _, _ = get_elite_level_info(new_elite)
    if new_lvl > old_lvl:
        return new_xp, new_elite, True, new_lvl, False
    elif is_elite and new_elite_lvl > old_elite_lvl:
        return new_xp, new_elite, True, new_elite_lvl, True
    return new_xp, new_elite, False, 0, False


def get_effective_level(item_level, player_level):
    return min(item_level, player_level)


class LevelUpView(discord.ui.View):
    def __init__(self, bot, user_id, level):
        super().__init__(timeout=60)
        self.bot, self.user_id, self.level = bot, user_id, level
        if level <= 50 and get_level_reward(level) == "kit":
            for child in self.children:
                if (
                    isinstance(child, discord.ui.Button)
                    and child.label == "Use Kit Now"
                ):
                    child.emoji = discord.PartialEmoji.from_str(config.CHAOS_CORE_EMOJI)
        else:
            self.clear_items()

    @discord.ui.button(label="Use Kit Now", style=discord.ButtonStyle.success)
    async def open_kit(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message(
                "Not your level up!", ephemeral=True
            )
        inv_cog = self.bot.get_cog("Inventory")
        if inv_cog:
            await inv_cog.open_cmd.callback(inv_cog, interaction)
            self.stop()


def check_daily_reset(user_id):
    u_data = database.get_user_data(user_id)
    if not u_data:
        return
    now = datetime.utcnow()
    last_update = (
        datetime.fromisoformat(u_data["last_daily_reset"])
        if u_data["last_daily_reset"]
        else now - timedelta(days=1)
    )
    if now.date() > last_update.date():
        new_base, new_boost = min(
            config.XP_BANK_CAP, u_data["daily_xp_total"] + config.XP_PER_DAY
        ), min(
            config.XP_BOOST_BANK_CAP,
            u_data["daily_xp_boosted"] + config.XP_BOOST_PER_DAY,
        )
        database.update_user_stats(
            user_id,
            {
                "daily_purchases": "[]",
                "daily_fusions": 0,
                "daily_xp_total": new_base,
                "daily_xp_boosted": new_boost,
                "last_daily_reset": now.isoformat(),
            },
        )


def get_xp_display_info(user_data):
    lvl, _, _ = get_level_info(user_data["xp"])
    fuel, bank = user_data["daily_xp_boosted"], user_data["daily_xp_total"]

    if lvl < 10:
        return config.XP_EMOJI, "Normal XP", False, bank, config.XP_BANK_CAP

    if fuel > 0:
        return (
            config.XP_BOOST_3X_EMOJI,
            "Boosted XP",
            True,
            fuel,
            config.XP_BOOST_BANK_CAP,
        )
    elif bank > 0:
        return config.XP_EMOJI, "Normal XP", False, bank, config.XP_BANK_CAP
    else:
        return config.NO_XP_EMOJI, "No Battle XP", False, 0, config.XP_BANK_CAP


async def item_autocomplete(interaction: discord.Interaction, current: str):
    search = current.lower()
    gear, cosmetics, titles = [], [], []
    for k, v in game_data.ALL_ITEMS.items():
        if search in v["name"].lower():
            if v["type"] in [
                "weapon",
                "gadget",
                "passive",
                "smart_ring",
                "elite_module",
            ]:
                gear.append(discord.app_commands.Choice(name=v["name"], value=k))
            elif v["type"] == "title":
                if search:
                    titles.append(
                        discord.app_commands.Choice(name=f"👑 {v['name']}", value=k)
                    )
            else:
                cosmetics.append(discord.app_commands.Choice(name=v["name"], value=k))
    gear.sort(key=lambda x: len(x.name))
    return (gear + cosmetics + titles)[:25]


async def modifier_autocomplete(interaction: discord.Interaction, current: str):
    return [
        discord.app_commands.Choice(name=m, value=m)
        for m in config.VALID_MODIFIERS
        if current.lower() in m.lower()
    ][:25]


def format_monster_name(monster_id):
    lower_id = monster_id.lower()
    if "speajumper" in lower_id or "spear_jumper" in lower_id:
        return "Spear Jumper"
    name = lower_id
    for p in ["rb_", "cw_", "d_", "boss_", "chaos_", "r_"]:
        name = name.replace(p, "")
    return name.replace("_", " ").title()


def generate_fusion_rewards(num_rolls, user_id):
    u = database.get_user_data(user_id)
    lvl, _, _ = get_level_info(u["xp"])
    rewards = {"cores": 0, "kits": 0, "shards": 0, "tokens": 0, "gold": 0}
    for _ in range(num_rolls):
        roll = random.random()
        if roll < 0.30:
            rewards["cores"] += 1
        elif roll < 0.45:
            rewards["kits"] += 1
        elif roll < 0.65:
            if lvl >= 12:
                rewards["shards"] += 10
        elif roll < 0.75:
            rewards["tokens"] += 10
    return rewards


def calculate_fusion_rolls(item_row):
    return 1 + (item_row["level"] // 20)


def get_sync_rate(bot, last_action_time):
    import time

    """Calculates a refresh rate based on bot load and player activity."""

    base_rate = 2.0 if bot.latency < 0.3 else 4.0

    idle_time = time.time() - last_action_time
    if idle_time > 10:
        return 10.0

    return base_rate

import math
from mo_co.config import LEVEL_DATA
from mo_co import database

MECHANICS = {
    "monster_taser": {"cd": 6.0, "status": "STUN", "duration": 2.0},
    "super_loud_whistle": {"cd": 8.0, "status": "TAUNT", "duration": 8.0},
    "revitalizing_mist": {"cd": 14.0, "status": "HEAL", "duration": 0},
    "boom_box": {"cd": 10.0, "status": "STUN", "duration": 1.5},
    "vitamin_shot": {"cd": 12.0, "status": "HASTE", "duration": 5.0},
    "life_jacket": {"cd": 12.0, "status": "SHIELD", "duration": 6.0},
    "pepper_spray": {"cd": 14.0, "status": "SLOW", "duration": 8.0},
    "explosive_6_pack": {"cd": 15.0, "status": "AOE", "duration": 0},
    "splash_heal": {"cd": 20.0, "status": "HEAL", "duration": 0},
    "multi_zapper": {"cd": 18.0, "status": "DMG", "duration": 0},
    "smart_fireworks": {"cd": 20.0, "status": "DMG", "duration": 0},
    "snow_globe": {"cd": 30.0, "status": "SLOW", "duration": 8.0},
    "sheldon": {"cd": 45.0, "status": "SUMMON", "duration": 0},
    "spinsickle": {"status": "SPIN", "duration": 5.0},
    "poison_bow": {"status": "POISON", "duration": 10.0},
}


def get_cooldown(item_id):
    return MECHANICS.get(item_id, {}).get("cd", 15.0)


def get_status_duration(item_id):
    return MECHANICS.get(item_id, {}).get("duration", 0)


def get_weapon_damage(item_id, level):
    global_mult = database.get_config("global_damage_mult", 1.0)
    item_mult = database.get_config(f"mult_{item_id}", 1.0)
    final_mult = global_mult * item_mult

    base = 250
    scale = 45

    if item_id == "monster_slugger":
        base, scale = 250, 15
    elif item_id == "techno_fists":
        base, scale = 120, 8
    elif item_id == "wolf_stick":
        base, scale = 180, 11
    elif item_id == "staff_of_good_vibes":
        base, scale = 140, 9
    elif item_id == "toothpick_and_shield":
        base, scale = 110, 7
    elif item_id == "portable_portal":
        base, scale = 200, 12
    elif item_id == "cpu_bomb":
        base, scale = 230, 14
    elif item_id == "speedshot":
        base, scale = 95, 6
    elif item_id == "medicne_ball":
        base, scale = 190, 11
    elif item_id == "buzz_kill":
        base, scale = 170, 10
    elif item_id == "hornbow":
        base, scale = 150, 9
    elif item_id == "singularity":
        base, scale = 210, 13
    elif item_id == "poison_bow":
        base, scale = 160, 10
    elif item_id == "spinsickle":
        base, scale = 130, 8
    elif item_id == "squid_blades":
        base, scale = 115, 7

    val = base + (level * scale)
    return int(val * final_mult)


def get_gadget_value(item_id, level):
    global_mult = database.get_config("global_damage_mult", 1.0)
    item_mult = database.get_config(f"mult_{item_id}", 1.0)
    final_mult = global_mult * item_mult

    val = 100
    if item_id == "splash_heal":
        val = 100 + (level * 15)
    elif item_id == "vitamin_shot":
        val = 100 + (level * 15)
    elif item_id == "revitalizing_mist":
        val = 200 + (level * 20)
    elif item_id == "feel_better_bloom":
        val = 60 + (level * 8)
    elif item_id == "smart_fireworks":
        val = 220 + (level * 25)
    elif item_id == "boom_box":
        val = 200 + (level * 20)
    elif item_id == "monster_taser":
        val = 500 + (level * 50)
    elif item_id == "pepper_spray":
        val = 150 + (level * 15)
    elif item_id == "multi_zapper":
        val = 350 + (level * 35)
    elif item_id == "life_jacket":
        val = 400 + (level * 30)
    elif item_id == "spicy_dagger":
        val = 450 + (level * 45)
    elif item_id == "explosive_6_pack":
        val = 400 + (level * 40)
    elif item_id == "pew3000":
        val = 120 + (level * 12)
    elif item_id == "very_mean_pendant":
        val = 60 + (level * 6)
    else:
        val = 100 + (level * 10)

    return int(val * final_mult)


def get_passive_value(item_id, level):
    d_mult = database.get_config("global_damage_mult", 1.0)
    if item_id == "healthy_snacks":
        return 50 + (level * 10)
    if item_id == "vampire_teeth":
        return min(2.0 + (level * 0.15), 10.0)
    if item_id == "healing_charm":
        return 5.0 + (level * 0.5)
    if item_id == "cactus_charm":
        return 20 + (level * 1.5)
    if item_id == "pocket_airbag":
        return min(35.0, 10.0 + (level * 0.7))
    if item_id == "chicken_o_matic":
        return 5.0 + (level * 0.5)
    if item_id == "smelly_socks":
        return int((15 + (level * 5)) * d_mult)
    if item_id == "auto_zapper":
        return int((10 + (level * 4)) * d_mult)
    if item_id == "gadget_battery":
        return int((20 + (level * 5)) * d_mult)
    if item_id == "unstable_lazer":
        return int((60 + (level * 10)) * d_mult)
    if item_id == "unstable_beam":
        return int((150 + (level * 20)) * d_mult)
    if item_id == "explode_o_matic_trigger":
        return 15.0 + (level * 0.5)
    if item_id == "unstable_lightning":
        return 10.0 + (level * 1.5)
    if item_id == "bunch_of_dice":
        return 2.0 + (level * 0.2)
    if item_id == "really_cool_sticker":
        return int((10 * level) * d_mult)

    if item_id == "overcharged_amulet":

        return float(level)

    return 0


def get_summon_stats(summon_id, level):
    d_mult = database.get_config("global_damage_mult", 1.0)
    if summon_id == "wolf":
        return (600 + (level * 50), int((120 + (level * 10)) * d_mult))
    if summon_id == "bee":
        return (150 + (level * 15), int((60 + (level * 6)) * d_mult))
    if summon_id == "sheldon":
        return (1500 + (level * 100), 0)
    if summon_id == "turret":
        return (400 + (level * 30), int((90 + (level * 8)) * d_mult))
    if summon_id == "bloom":
        return (500 + (level * 40), 0)
    return (500, 50)


def get_ring_stats(item_id, level):

    idx = min(2, max(0, level - 1))

    if item_id == "insane_attack_speed_ring":
        return [50, 75, 100][idx], 0
    if item_id == "insane_movement_speed_ring":
        return [25, 50, 100][idx], 0
    if item_id == "insane_cooldown_reduction_ring":
        return [50, 75, 90][idx], 0
    if item_id == "insane_pet_attack_speed_ring":
        return [50, 75, 100][idx], 0
    if item_id == "insane_dash_ring":
        return [3.0, 1.5, 0.6][idx], 0
    if item_id == "insane_self_healing_ring":
        return [50, 100, 150][idx], 0
    if item_id == "insane_weapon_damage_ring":
        return [200, 500, 1000][idx], 0
    if item_id == "insane_gadget_damage_ring":
        return [200, 500, 1000][idx], 0
    if item_id == "insane_passive_damage_ring":
        return [200, 500, 1000][idx], 0
    if item_id == "insane_damage_ring":
        return [200, 500, 1000][idx], 0
    if item_id == "insane_slow_attack_gem":
        return [-25, -50, -75][idx], 0
    if item_id == "insane_projectile_ring":
        return [2, 3, 4][idx], 0
    if item_id == "insane_weapon_combo_ring":
        return [200, 400, 10000][idx], 0
    if item_id == "insane_ring_of_projectile_speed":
        return [25, 50, 75][idx], 0

    if "minor" not in item_id:
        if "damage" in item_id:
            return (10 + level * 2), 0
        if "health" in item_id:
            return (50 + level * 20), 0
        if "healing" in item_id:
            return (10 + level * 1.5), 0
        if "cooldown" in item_id or "time" in item_id:
            return (5 + level * 0.5), 0
        if "crit" in item_id:
            return (5 + level * 1), 0
        return (10 + level * 1), 0
    else:
        hp_bonus = 20 + (level * 5)
        if "damage" in item_id:
            return (5 + level * 1), hp_bonus
        if "healing" in item_id:
            return (5 + level * 0.75), hp_bonus
        if "crit" in item_id:
            return (2 + level * 0.5), hp_bonus
        if "health" in item_id:
            return (25 + level * 10), (10 + level * 2)
        return (5 + level * 0.5), hp_bonus


def get_item_details(item_id, level, item_type):
    mech = MECHANICS.get(item_id, {})
    cd = mech.get("cd")
    dur = mech.get("duration")

    if item_type == "weapon":
        dmg = get_weapon_damage(item_id, level)
        details = f"**{dmg}** Damage"
        if item_id == "staff_of_good_vibes":
            details += "\nHeals Team (50% Dmg)"
        elif item_id == "techno_fists":
            details += "\nBounces to targets"
        elif item_id == "monster_slugger":
            details += "\nCleave on Combo"
        elif item_id == "poison_bow":
            details += f"\nPoison ({dur}s)"
        elif item_id == "vampire_teeth":
            details += "\nLifesteal"
        return details, dmg

    elif item_type == "gadget":
        val = get_gadget_value(item_id, level)
        cd_str = f"**{int(cd)}s** CD" if cd else ""
        if item_id in ["splash_heal", "revitalizing_mist", "vitamin_shot"]:
            effect = f"**Heal {val}**"
        elif item_id == "life_jacket":
            effect = f"**Shield {val}** ({dur}s)"
        elif item_id in ["monster_taser", "boom_box"]:
            effect = f"**{val} Dmg** + **Stun** ({dur}s)"
        elif item_id == "snow_globe":
            effect = f"**Slow Area** ({dur}s)"
        elif item_id == "pepper_spray":
            effect = f"**{val} Dmg** + **Slow**"
        elif item_id == "sheldon":
            stats = get_summon_stats("sheldon", level)
            effect = f"**Summon** ({stats[0]} HP)"
        elif item_id == "pew3000":
            stats = get_summon_stats("turret", level)
            effect = f"**Turret** ({stats[1]} Atk)"
        elif item_id == "feel_better_bloom":
            stats = get_summon_stats("bloom", level)
            effect = f"**Bloom** ({stats[0]} HP)"
        else:
            effect = f"**{val} Damage**"
        return f"{effect} | {cd_str}", val

    elif item_type == "passive":
        val = get_passive_value(item_id, level)
        if item_id == "overcharged_amulet":
            mega = val * 0.5
            return (
                f"**+{val:.0f}%** Overcharged, **+{mega:.1f}%** Megacharged",
                val,
            )

        if item_id == "healthy_snacks":
            return f"**+{val}** Max HP", val
        if item_id == "vampire_teeth":
            return f"**{val:.1f}%** Lifesteal", val
        if item_id == "healing_charm":
            return f"**+{val:.1f}%** Healing Received", val
        if item_id == "cactus_charm":
            return f"**{val}%** Dmg Reflection", val
        if item_id == "pocket_airbag":
            return f"**{val:.1f}%** Dodge Chance", val
        if item_id == "chicken_o_matic":
            return f"**{val:.1f}%** Chicken Tank", val
        if item_id == "smelly_socks":
            return f"**{val}** Dmg/sec Aura", val
        if item_id == "auto_zapper":
            return f"**{val}** Passive Zap Dmg", val
        if item_id == "gadget_battery":
            return f"**{val}** Zap on Gadget Use", val
        if item_id == "unstable_lazer":
            return f"**{val}** Lazer Dmg (20%)", val
        if item_id == "unstable_beam":
            return f"**{val}** Beam Dmg (5%)", val
        if item_id == "explode_o_matic_trigger":
            return f"**{val}%** Loot Explosion", val
        if item_id == "unstable_lightning":
            return f"**{val}%** Chain Lightning", val
        if item_id == "bunch_of_dice":
            return f"**+{val:.1f}%** Jackpot & Dodge Chance", val
        if item_id == "really_cool_sticker":
            return f"**+{val}** Attack Power", val
        return f"**{val}** Power", val

    elif item_type == "smart_ring":
        val1, val2 = get_ring_stats(item_id, level)
        if "insane" in item_id:
            if "dash" in item_id:
                return f"**{val1}s** Dash Cooldown", val1
            if "projectile_ring" in item_id:
                return f"**+{val1}** Projectiles", val1
            if "self_healing" in item_id:
                return f"**{val1}/s** Healing", val1
            return f"**{val1:+}**% Boost", val1
        elif "minor" in item_id:
            if "health" in item_id:
                return f"**+{val1}** HP & **{val2}%** Dodge", val1
            return f"**{val1}%** Boost & **+{val2}** HP", val1
        else:
            if "health" in item_id:
                return f"**+{val1}** HP", val1
            return f"**{val1}%** Boost", val1

    elif item_type == "elite_module":
        return "Elite Ability", 0

    return "Unknown Effect", 0

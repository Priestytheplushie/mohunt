from mo_co import config
from .items import ALL_ITEMS
from .worlds import (
    WORLDS,
    ELITE_POOL_30,
    ELITE_POOL_50,
    RIFTS,
    DOJOS,
    get_monsters_for_world,
    get_world,
)

PROJECTS = {}


def clean_display_name(name, is_dojo=False):
    lower_name = name.lower()
    for prefix in ["rb_", "d_", "cw_", "r_"]:
        if lower_name.startswith(prefix):
            name = name[len(prefix) :]
            break
    name = name.lstrip("_ ")
    if not is_dojo:
        if name.lower().startswith("boss"):
            name = name[4:]
    return name.lstrip("_ ").replace("_", " ").title()


def generate_stages(
    group_id,
    base_desc,
    target_type,
    target,
    stages,
    icon=None,
    meta_world=None,
    is_elite=False,
    reward_tokens=0,
):
    for i, count in enumerate(stages):
        tier_val = i + 1
        xp_reward = 1000 + (i * 1000)
        pid = f"{group_id}_t{tier_val}"
        PROJECTS[pid] = {
            "desc": base_desc,
            "target_type": target_type,
            "target": target,
            "count": count,
            "reward_xp": xp_reward,
            "group": group_id,
            "tier": tier_val,
            "is_elite": is_elite,
        }
        if reward_tokens > 0:
            PROJECTS[pid]["reward_tokens"] = reward_tokens
        if icon:
            PROJECTS[pid]["icon"] = icon
        if meta_world:
            PROJECTS[pid]["meta_world"] = meta_world


generate_stages(
    "global_hunt_any",
    "Hunt Monsters",
    "hunt_any",
    None,
    [100, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000],
)
generate_stages(
    "global_open_cores",
    "Open Chaos Cores",
    "open_core",
    None,
    [1, 5, 25, 50, 100],
)
generate_stages(
    "global_collect_gear",
    "Collect Unique Gear",
    "collect_item",
    None,
    [5, 10, 25, 50, 100],
)

PROJECTS.update(
    {
        "global_level_t1": {
            "desc": "Reach Level 10",
            "target_type": "reach_level",
            "target": 10,
            "count": 10,
            "reward_xp": 1000,
            "group": "global_level",
            "tier": 1,
        },
        "global_level_t2": {
            "desc": "Reach Level 20",
            "target_type": "reach_level",
            "target": 20,
            "count": 20,
            "reward_xp": 2000,
            "group": "global_level",
            "tier": 2,
        },
        "global_level_t3": {
            "desc": "Reach Level 30",
            "target_type": "reach_level",
            "target": 30,
            "count": 30,
            "reward_xp": 5000,
            "group": "global_level",
            "tier": 3,
        },
        "global_level_t4": {
            "desc": "Reach Level 40",
            "target_type": "reach_level",
            "target": 40,
            "count": 40,
            "reward_xp": 10000,
            "group": "global_level",
            "tier": 4,
        },
        "global_level_t5": {
            "desc": "Reach Level 50",
            "target_type": "reach_level",
            "target": 50,
            "count": 50,
            "reward_xp": 20000,
            "group": "global_level",
            "tier": 5,
        },
    }
)

generate_stages(
    "global_hunt_cat",
    "Hunt in Cat Worlds",
    "hunt_world_type",
    "catworld",
    [50, 250, 500, 1000, 2500],
)
generate_stages(
    "global_hunt_dragon",
    "Hunt in Dragonling Worlds",
    "hunt_world_type",
    "dragonworld",
    [50, 250, 500, 1000, 2500],
)
generate_stages(
    "global_hunt_bug",
    "Hunt in Royal Bug Worlds",
    "hunt_world_type",
    "bugworld",
    [50, 250, 500, 1000, 2500],
)
generate_stages(
    "global_hunt_overcharged",
    "Hunt Overcharged Monsters",
    "hunt_type",
    "Overcharged",
    [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)


generate_stages(
    "global_world_boss",
    "Defeat World Threats",
    "hunt_shared_boss",
    None,
    [1, 5, 10, 25, 50],
    icon=config.CHAOS_ALERT,
    reward_tokens=5,
)


generate_stages(
    "ally_jax",
    "Fight alongside Jax",
    "fight_with_npc",
    "Jax",
    [1, 10, 50],
    icon=config.BOT_EMOJIS["Jax"],
    reward_tokens=5,
)

generate_stages(
    "ally_luna",
    "Fight alongside Luna",
    "fight_with_npc",
    "Luna",
    [1, 10, 50],
    icon=config.BOT_EMOJIS["Luna"],
    reward_tokens=5,
)

generate_stages(
    "ally_manny",
    "Fight alongside Manny",
    "fight_with_npc",
    "Manny",
    [1, 10, 50],
    icon=config.BOT_EMOJIS["Manny"],
    reward_tokens=5,
)

all_worlds = WORLDS + ELITE_POOL_30 + ELITE_POOL_50
for w in all_worlds:
    if w["id"] not in ["downtown_chaos", "chaos_invasion"]:
        generate_stages(
            f"proj_{w['id']}_hunt",
            f"Hunt in {w['name']}",
            "hunt_world",
            w["id"],
            [50, 150, 300],
            icon=config.WORLD_ICONS.get(w.get("type"), config.MAP_EMOJI),
            meta_world=w["id"],
        )
    monsters_in_world = get_monsters_for_world(w["id"], w.get("type"))
    for m in monsters_in_world:
        clean_n = clean_display_name(m, is_dojo=False)
        group_id = f"per_world_{w['id']}_mob_{m}"
        is_boss = (
            "boss" in m.lower()
            or "Guardian" in m
            or m
            in [
                "Overlord",
                "Bug Lord",
                "Smasher",
                "Big Papa",
                "Draymor",
                "Bug Lord",
            ]
        )
        stages = [10, 25, 75] if is_boss else [30, 60, 150]
        for i, count in enumerate(stages):
            PROJECTS[f"proj_{w['id']}_mob_{m}_t{i+1}"] = {
                "desc": f"Hunt {clean_n} in {w['name']}",
                "target_type": "hunt_mob_world",
                "target": m,
                "count": count,
                "reward_xp": 1000 + (i * 1000),
                "group": group_id,
                "tier": i + 1,
                "meta_world": w["id"],
                "icon": m,
            }

for d_id, d_def in DOJOS.items():
    clean_n = clean_display_name(d_def["name"], is_dojo=True)
    PROJECTS[f"proj_{d_id}_time_90"] = {
        "desc": f"Defeat {clean_n} in under 1:30",
        "target_type": "dojo_time",
        "target": f"{d_id}:90",
        "count": 1,
        "reward_xp": 10000,
        "group": f"dojo_{d_id}",
        "tier": 1,
    }
    PROJECTS[f"proj_{d_id}_time_60"] = {
        "desc": f"Defeat {clean_n} in under 1:00",
        "target_type": "dojo_time",
        "target": f"{d_id}:60",
        "count": 1,
        "reward_xp": 10000,
        "group": f"dojo_{d_id}",
        "tier": 2,
    }

FORCE_HEAL_ITEMS = {
    "splash_heal",
    "vitamin_shot",
    "super_loud_whistle",
    "revitalizing_mist",
    "medicne_ball",
    "staff_of_good_vibes",
}
for iid, idef in ALL_ITEMS.items():
    if idef["type"] not in ("weapon", "gadget", "passive") or iid == "pocket_airbag":
        continue
    rar_mult = {"Common": 1.0, "Rare": 1.4, "Epic": 1.8, "Legendary": 2.2}.get(
        idef.get("rarity", "Common"), 1.0
    )
    clean_n = clean_display_name(idef["name"])
    if iid in FORCE_HEAL_ITEMS:
        generate_stages(
            f"proj_heal_{iid}",
            f"Heal using {clean_n}",
            "heal_with",
            iid,
            [int(x * rar_mult) for x in [150000, 450000, 850000]],
            icon=iid,
        )
    else:
        generate_stages(
            f"proj_damage_{iid}",
            f"Deal damage with {clean_n}",
            "deal_damage_with",
            iid,
            [int(x * rar_mult) for x in [250000, 750000, 1400000]],
            icon=iid,
        )

generate_stages(
    "global_complete_daily_jobs",
    "Complete Daily Jobs",
    "complete_daily_jobs",
    None,
    [20, 50, 150],
)
generate_stages(
    "global_loot_xp",
    "Loot XP from Monsters",
    "loot_xp",
    None,
    [20000, 50000, 200000],
)
generate_stages(
    "global_hunt_chaos",
    "Hunt Chaos Monsters",
    "hunt_type",
    "Chaos",
    [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)
generate_stages(
    "global_hunt_megacharged",
    "Hunt Megacharged Monsters",
    "hunt_type",
    "Megacharged",
    [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
)

for r_id, r_def in RIFTS.items():
    clean_n = r_def["name"]
    PROJECTS[f"proj_{r_id}_time_180"] = {
        "desc": f"Clear {clean_n} in under 3:00",
        "target_type": "rift_time",
        "target": f"{r_id}:180",
        "count": 1,
        "reward_xp": 10000,
        "group": f"rift_{r_id}",
        "tier": 1,
        "icon": r_def["icon"],
    }
    PROJECTS[f"proj_{r_id}_time_120"] = {
        "desc": f"Clear {clean_n} in under 2:00",
        "target_type": "rift_time",
        "target": f"{r_id}:120",
        "count": 1,
        "reward_xp": 15000,
        "group": f"rift_{r_id}",
        "tier": 2,
        "icon": r_def["icon"],
    }


elite_stages = [50 * (i + 1) for i in range(10)]
generate_stages(
    "elite_hunt_corrupted",
    "Hunt in Corrupted Worlds",
    "hunt_corrupted",
    None,
    elite_stages,
    is_elite=True,
    reward_tokens=10,
)


for r_id, r_def in RIFTS.items():
    clean_n = r_def["name"]

    PROJECTS[f"elite_hard_{r_id}"] = {
        "desc": f"Clear {clean_n} - HARD",
        "target_type": "clear_rift_hard",
        "target": r_id,
        "count": 1,
        "reward_xp": 10000,
        "reward_tokens": 20,
        "is_elite": True,
        "icon": r_def["icon"],
        "group": f"elite_priority_{r_id}",
    }

    PROJECTS[f"elite_nightmare_{r_id}"] = {
        "desc": f"Clear {clean_n} - NIGHTMARE",
        "target_type": "clear_rift_nightmare",
        "target": r_id,
        "count": 1,
        "reward_xp": 20000,
        "reward_tokens": 50,
        "is_elite": True,
        "icon": r_def["icon"],
        "group": f"elite_priority_{r_id}_nm",
    }

    for t_val, t_str in [(210, "3:30"), (180, "3:00"), (120, "2:00")]:
        PROJECTS[f"elite_hard_speed_{r_id}_{t_val}"] = {
            "desc": f"{clean_n} (Hard) < {t_str}",
            "target_type": "rift_speedrun_hard",
            "target": f"{r_id}:{t_val}",
            "count": 1,
            "reward_xp": 5000,
            "reward_tokens": 20,
            "is_elite": True,
            "icon": r_def["icon"],
            "group": f"elite_speed_{r_id}",
        }
        PROJECTS[f"elite_nm_speed_{r_id}_{t_val}"] = {
            "desc": f"{clean_n} (Nightmare) < {t_str}",
            "target_type": "rift_speedrun_nightmare",
            "target": f"{r_id}:{t_val}",
            "count": 1,
            "reward_xp": 10000,
            "reward_tokens": 50,
            "is_elite": True,
            "icon": r_def["icon"],
            "group": f"elite_speed_nm_{r_id}",
        }

for d_id, d_def in DOJOS.items():
    clean_n = clean_display_name(d_def["name"], is_dojo=True)

    PROJECTS[f"elite_hard_{d_id}"] = {
        "desc": f"Defeat {clean_n} - HARD",
        "target_type": "clear_dojo_hard",
        "target": d_id,
        "count": 1,
        "reward_xp": 10000,
        "reward_tokens": 20,
        "is_elite": True,
        "icon": config.DOJO_ICON,
        "group": f"elite_priority_{d_id}",
    }

    PROJECTS[f"elite_nightmare_{d_id}"] = {
        "desc": f"Defeat {clean_n} - NIGHTMARE",
        "target_type": "clear_dojo_nightmare",
        "target": d_id,
        "count": 1,
        "reward_xp": 20000,
        "reward_tokens": 50,
        "is_elite": True,
        "icon": config.DOJO_ICON,
        "group": f"elite_priority_{d_id}_nm",
    }


elite_bosses = [
    "Bone Smasher",
    "Axe Hopper",
    "Big Papa",
    "Berserker",
    "Mama Jumper",
    "Savage Spirit",
    "Mama Boomer",
    "Alpha Charger",
    "Mega Overlord",
    "Toxic Spitter",
    "Master Summoner",
    "Princess Ladybug",
    "Royal Rider",
]
for boss in elite_bosses:
    pid = f"elite_mega_{boss.lower().replace(' ', '_')}"
    PROJECTS[pid] = {
        "desc": f"Hunt Megacharged {boss}",
        "target_type": "hunt_megacharged_boss",
        "target": boss,
        "count": 1,
        "reward_xp": 2000,
        "reward_tokens": 20,
        "is_elite": True,
        "icon": config.CHAOS_ALERT,
        "group": "elite_mega_bosses",
    }


PROJECTS["elite_collect_rings"] = {
    "desc": "Collect Smart Rings",
    "target_type": "collect_smart_rings",
    "target": None,
    "count": 45,
    "reward_xp": 5000,
    "reward_tokens": 20,
    "is_elite": True,
    "icon": "empty_ring",
    "group": "elite_collection",
}


for i in range(1, 11):
    lvl = i * 10
    PROJECTS[f"elite_reach_lvl_{lvl}"] = {
        "desc": f"Reach Elite Level {lvl}",
        "target_type": "reach_elite_level",
        "target": lvl,
        "count": lvl,
        "reward_xp": 10000,
        "reward_tokens": 50,
        "is_elite": True,
        "icon": config.ELITE_EMBLEM,
        "group": "elite_level_prog",
    }


generate_stages(
    "elite_pull_merch",
    "Pull Merch",
    "pull_merch",
    None,
    [1, 5, 10],
    is_elite=True,
    reward_tokens=20,
)


elite_hunt_stages = [100 * (i + 1) for i in range(20)]
generate_stages(
    "elite_hunt_any",
    "Hunt Monsters (Elite)",
    "hunt_monsters_elite",
    None,
    elite_hunt_stages,
    is_elite=True,
    reward_tokens=10,
)

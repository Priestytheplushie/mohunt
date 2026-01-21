from mo_co import config

WORLDS = [
    {
        "id": "downtown_chaos",
        "name": "Downtown Chaos",
        "unlock_lvl": 1,
        "recommended_lvl": 1,
        "type": "homeworld",
    },
    {
        "id": "chaos_invasion",
        "name": "Chaos Invasion",
        "unlock_lvl": 1,
        "recommended_lvl": 1,
        "type": "dragonworld",
    },
    {
        "id": "shrine_village",
        "name": "Shrine Village",
        "unlock_lvl": 1,
        "recommended_lvl": 2,
        "type": "dragonworld",
    },
    {
        "id": "overgrown_ruins",
        "name": "Overgrown Ruins",
        "unlock_lvl": 3,
        "recommended_lvl": 5,
        "type": "dragonworld",
    },
    {
        "id": "infested_forest",
        "name": "Infested Forest",
        "unlock_lvl": 6,
        "recommended_lvl": 9,
        "type": "bugworld",
    },
    {
        "id": "cave_of_spirits",
        "name": "Cave of Spirits",
        "unlock_lvl": 12,
        "recommended_lvl": 15,
        "type": "dragonworld",
    },
    {
        "id": "castle_walls",
        "name": "Castle Walls",
        "unlock_lvl": 16,
        "recommended_lvl": 19,
        "type": "bugworld",
    },
    {
        "id": "summoning_grounds",
        "name": "Summoning Grounds",
        "unlock_lvl": 20,
        "recommended_lvl": 24,
        "type": "dragonworld",
    },
    {
        "id": "sewers",
        "name": "Sewers",
        "unlock_lvl": 25,
        "recommended_lvl": 28,
        "type": "bugworld",
    },
    {
        "id": "feline_invasion",
        "name": "Feline Invasion",
        "unlock_lvl": 30,
        "recommended_lvl": 32,
        "type": "homeworld",
    },
    {
        "id": "ceremonial_square",
        "name": "Ceremonial Square",
        "unlock_lvl": 33,
        "recommended_lvl": 36,
        "type": "dragonworld",
    },
    {
        "id": "castle_undercroft",
        "name": "Castle Undercroft",
        "unlock_lvl": 37,
        "recommended_lvl": 40,
        "type": "bugworld",
    },
    {
        "id": "sanctum_gardens",
        "name": "Sanctum Gardens",
        "unlock_lvl": 40,
        "recommended_lvl": 42,
        "type": "dragonworld",
    },
    {
        "id": "royal_quarters",
        "name": "Royal Quarters",
        "unlock_lvl": 43,
        "recommended_lvl": 45,
        "type": "bugworld",
    },
    {
        "id": "frostpaw_dock",
        "name": "Frostpaw Dock",
        "unlock_lvl": 46,
        "recommended_lvl": 48,
        "type": "catworld",
    },
]

DOJO_SETS = [
    {
        "id": "basic_training",
        "name": "Basic Training",
        "unlock_lvl": 14,
        "dojos": ["dojo_basics", "dojo_heavy", "dojo_boss"],
    },
    {
        "id": "advanced_training",
        "name": "Advanced Training",
        "unlock_lvl": 23,
        "dojos": [
            "dojo_double_dragon",
            "dojo_crowd_control",
            "dojo_helping_hands",
        ],
    },
    {
        "id": "more_advanced_training",
        "name": "More Advanced Training",
        "unlock_lvl": 30,
        "dojos": [
            "dojo_taking_hits",
            "dojo_target_priority",
            "dojo_one_on_one",
        ],
    },
]

DOJOS = {
    "dojo_basics": {
        "name": "The Basics",
        "recommended_gp": 750,
        "companions": ["Luna"],
        "mobs": [
            {"id": "Drog", "lvl": 15, "count": 19, "is_swarm": True},
            {"id": "d_slasher", "lvl": 20, "count": 6, "is_swarm": True},
            {"id": "d_jumper", "lvl": 25, "count": 6, "is_swarm": True},
        ],
    },
    "dojo_heavy": {
        "name": "Heavy Hitting",
        "recommended_gp": 1000,
        "companions": ["Luna"],
        "mobs": [
            {"id": "d_jumper", "lvl": 25, "count": 10, "is_swarm": True},
            {"id": "d_charger", "lvl": 30, "count": 4, "is_swarm": False},
        ],
    },
    "dojo_boss": {
        "name": "Boss Beat",
        "recommended_gp": 1250,
        "companions": ["Luna"],
        "mobs": [
            {"id": "d_boss_Juggler", "lvl": 30, "count": 2, "is_swarm": False},
            {
                "id": "d_boss_bone_smasher",
                "lvl": 35,
                "count": 1,
                "is_boss": True,
            },
        ],
    },
    "dojo_double_dragon": {
        "name": "Double Dragon",
        "recommended_gp": 4500,
        "companions": ["Luna"],
        "mobs": [{"id": "d_jumper", "lvl": 35, "count": 2, "is_swarm": False}],
    },
    "dojo_crowd_control": {
        "name": "Crowd Control",
        "recommended_gp": 5200,
        "companions": ["Luna"],
        "mobs": [
            {"id": "rb_knight", "lvl": 38, "count": 6, "is_swarm": False},
            {"id": "Drog", "lvl": 38, "count": 40, "is_swarm": True},
        ],
    },
    "dojo_helping_hands": {
        "name": "Helping Hands",
        "recommended_gp": 6000,
        "companions": ["Manny", "Jax"],
        "mobs": [{"id": "d_boss_Juggler", "lvl": 42, "count": 1, "is_boss": True}],
    },
    "dojo_taking_hits": {
        "name": "Taking Hits",
        "recommended_gp": 6500,
        "companions": ["Jax"],
        "mobs": [
            {"id": "rb_knight", "lvl": 35, "count": 10, "is_swarm": False},
            {"id": "Guard", "lvl": 35, "count": 5, "is_swarm": False},
        ],
    },
    "dojo_target_priority": {
        "name": "Target Priority",
        "recommended_gp": 6800,
        "companions": [],
        "mobs": [
            {"id": "Drog", "lvl": 32, "count": 50, "is_swarm": True},
            {"id": "rb_knight", "lvl": 35, "count": 5, "is_swarm": False},
        ],
    },
    "dojo_one_on_one": {
        "name": "One on One",
        "recommended_gp": 7200,
        "companions": [],
        "mobs": [{"id": "Berserker", "lvl": 38, "count": 1, "is_boss": True}],
    },
}

RIFT_SETS = [
    {
        "id": "enter_the_chaos",
        "name": "Enter the Chaos",
        "unlock_lvl": 9,
        "rifts": [
            "rift_dead_end",
            "rift_street_fight",
            "rift_overlords_chamber",
        ],
    },
    {
        "id": "smash_and_mash",
        "name": "Smash & Mash",
        "unlock_lvl": 14,
        "rifts": [
            "rift_rage_room",
            "rift_double_hop",
            "rift_twilight_takedown",
        ],
    },
    {
        "id": "hunt_for_mama",
        "name": "Hunt for Mama",
        "unlock_lvl": 17,
        "rifts": [
            "rift_deep_gorge",
            "rift_cave_of_corruption",
            "rift_breeding_grounds",
        ],
    },
    {
        "id": "monster_games",
        "name": "Monster Games",
        "unlock_lvl": 22,
        "rifts": [
            "rift_van_defense",
            "rift_hunting_party",
            "rift_monster_chase",
        ],
    },
    {
        "id": "the_showdown",
        "name": "The Showdown",
        "unlock_lvl": 26,
        "rifts": [
            "rift_canyon_gauntlet",
            "rift_rooftop_rumble",
            "rift_sewer_showdown",
        ],
    },
    {
        "id": "chaos_extreme",
        "name": "Chaos Extreme",
        "unlock_lvl": 30,
        "rifts": [
            "rift_ramparts",
            "rift_moonlit_ruins",
            "rift_tournament_grounds",
        ],
    },
]

RIFTS = {
    "rift_dead_end": {
        "name": "Dead End",
        "boss": "Bone Smasher",
        "icon": "d_boss_bone_smasher",
        "desc": "Enter the Chaos!",
        "recommended_gp": 400,
        "req_rift": None,
        "waves": [
            "2 Slashers",
            "2 Jumpers",
            "2 Slashers + 1 Jumper",
            "2 Slashers",
            "2 Jumpers + 2 Slashers",
            "BOSS: Bone Smasher",
        ],
    },
    "rift_street_fight": {
        "name": "Street Fight",
        "boss": "Axe Hopper",
        "icon": "rb_boss_Axe_Hopper",
        "desc": "Survive the streets. 8 Waves of chaos.",
        "recommended_gp": 600,
        "req_rift": "rift_dead_end",
        "waves": [
            "2 Jumpers + 3 Slashers",
            "12 Slashers",
            "6 Jumpers",
            "3 Slashers + 1 Juggler",
            "5 Knights",
            "3 Jumpers + 3 Slashers",
            "4 Spitters",
            "6 Knights + BOSS: Axe Hopper",
        ],
    },
    "rift_overlords_chamber": {
        "name": "Overlord's Chamber",
        "boss": "The Overlord",
        "icon": config.OVERLORD_ICON,
        "desc": "For serious hunters only.",
        "recommended_gp": 900,
        "req_rift": "rift_street_fight",
        "waves": ["6 Knights", "6 Knights", "BOSS: The Overlord"],
    },
    "rift_rage_room": {
        "name": "Rage Room",
        "boss": "Berserker",
        "icon": "d_boss_beserker",
        "desc": "He gets faster the more you hurt him.",
        "recommended_gp": 1100,
        "req_rift": "rift_overlords_chamber",
        "waves": [
            "2 Slashers + 2 Jumpers",
            "4 Slashers",
            "3 Chargers",
            "2 Spear Jumpers + 2 Jumpers",
            "BOSS: Berserker",
        ],
    },
    "rift_double_hop": {
        "name": "Double Hop",
        "boss": "Axe Hopper Duo",
        "icon": "rb_boss_Axe_Hopper",
        "desc": "Double the trouble.",
        "recommended_gp": 1300,
        "req_rift": "rift_rage_room",
        "waves": [
            "3 Knights",
            "5 Mini Slimes",
            "2 Guards",
            "2 Knights + 2 Guards",
            "BOSS: Axe Hopper + BOSS: Axe Hopper",
        ],
    },
    "rift_twilight_takedown": {
        "name": "Twilight Takedown",
        "boss": "Big Papa",
        "icon": "d_boss_Big_Papa",
        "desc": "Break the eggs before they hatch!",
        "recommended_gp": 1500,
        "req_rift": "rift_double_hop",
        "waves": ["BOSS: Big Papa"],
    },
    "rift_deep_gorge": {
        "name": "Deep Gorge",
        "boss": "Mama Jumper",
        "icon": "d_jumper",
        "desc": "She bounces around stunning everyone.",
        "recommended_gp": 1600,
        "req_rift": "rift_twilight_takedown",
        "waves": [
            "4 Slashers",
            "3 Scorchers",
            "2 Chargers + 3 Scorchers",
            "2 Chargers",
            "2 Slashers + 2 Chargers",
            "BOSS: Mama Jumper + 3 Spear Jumpers",
        ],
    },
    "rift_cave_of_corruption": {
        "name": "Cave of Corruption",
        "boss": "Savage Spirit",
        "icon": "d_boss_Savage_Spirit",
        "desc": "Watch out for the fury swipes.",
        "recommended_gp": 2000,
        "req_rift": "rift_deep_gorge",
        "waves": [
            "4 Chargers",
            "2 Spear Jumpers",
            "2 Chargers + 2 Spear Jumpers",
            "6 Slashers",
            "BOSS: Savage Spirit",
        ],
    },
    "rift_breeding_grounds": {
        "name": "Breeding Grounds",
        "boss": "Mama Boomer",
        "icon": "d_boss_mama_boomer",
        "desc": "Fire, beams, and slams.",
        "recommended_gp": 2400,
        "req_rift": "rift_cave_of_corruption",
        "waves": ["BOSS: Mama Boomer"],
    },
    "rift_van_defense": {
        "name": "Van Defense",
        "boss": "Horde",
        "icon": "d_boss_Juggler",
        "desc": "Protect the Research Van! No advancing.",
        "recommended_gp": 2800,
        "req_rift": "rift_breeding_grounds",
        "waves": [
            "10 Drogs",
            "4 Chargers",
            "4 Toxic Blooms + 5 Drogs",
            "4 Slashers + 4 Chargers",
            "2 Overgrown Vines",
            "2 Savage Spirits",
            "BOSS: Big Red",
            "BOSS: Mama Boomer + 3 Spear Jumpers",
        ],
    },
    "rift_hunting_party": {
        "name": "Hunting Party",
        "boss": "Boss Rush",
        "icon": "d_boss_Big_Red",
        "desc": "10 Waves of Bosses. Good luck.",
        "recommended_gp": 3400,
        "req_rift": "rift_van_defense",
        "waves": [
            "BOSS: Big Red",
            "BOSS: Savage Spirit",
            "BOSS: Bone Smasher",
            "BOSS: Berserker",
            "BOSS: Juggler",
            "BOSS: Mama Boomer",
            "BOSS: Big Red",
            "BOSS: Mama Jumper",
            "BOSS: Bone Smasher",
            "BOSS: Overgrown Vine",
        ],
    },
    "rift_monster_chase": {
        "name": "Monster Chase",
        "boss": "Mega Overlord",
        "icon": config.OVERLORD_ICON,
        "desc": "Chase him down!",
        "recommended_gp": 4000,
        "req_rift": "rift_hunting_party",
        "waves": ["BOSS: Mega Overlord"],
    },
    "rift_canyon_gauntlet": {
        "name": "Canyon Gauntlet",
        "boss": "Alpha Charger",
        "icon": "d_boss_Alpha_Charger",
        "desc": "He hits harder when burning.",
        "recommended_gp": 4500,
        "req_rift": "rift_monster_chase",
        "waves": [
            "5 Scorchers",
            "3 Jumpers + 3 Spear Jumpers",
            "2 Chargers",
            "7 Scorchers",
            "3 Spear Jumpers",
            "BOSS: Alpha Charger",
        ],
    },
    "rift_rooftop_rumble": {
        "name": "Rooftop Rumble",
        "boss": "Horde",
        "icon": "rb_boss_Axe_Hopper",
        "desc": "Chaos on the roof.",
        "recommended_gp": 5500,
        "req_rift": "rift_canyon_gauntlet",
        "waves": [
            "4 Chargers",
            "5 Spear Jumpers",
            "8 Scorchers",
            "BOSS: Big Red + BOSS: Big Red",
            "4 Slashers + 5 Spear Jumpers",
            "20 Drogs",
            "8 Scorchers",
            "4 Axe Hoppers",
        ],
    },
    "rift_sewer_showdown": {
        "name": "Sewer Showdown",
        "boss": "Toxic Spitter",
        "icon": "d_boss_Toxic_Spitter",
        "desc": "Don't step in the goop.",
        "recommended_gp": 6500,
        "req_rift": "rift_rooftop_rumble",
        "waves": [
            "4 Guards",
            "4 Guards",
            "3 Knights",
            "2 Mini Slimes",
            "4 Guards",
            "BOSS: Toxic Spitter",
        ],
    },
    "rift_ramparts": {
        "name": "Ramparts",
        "boss": "Master Summoner",
        "icon": "bug_lord",
        "desc": "He calls friends from other worlds.",
        "recommended_gp": 7000,
        "req_rift": "rift_sewer_showdown",
        "waves": [
            "4 Guards",
            "4 Guards",
            "4 Guards",
            "4 Guards",
            "BOSS: Master Summoner",
        ],
    },
    "rift_moonlit_ruins": {
        "name": "Moonlit Ruins",
        "boss": "Princess Ladybug",
        "icon": "rb_boss_Princess_Ladybug",
        "desc": "Beware the purple puddles.",
        "recommended_gp": 8000,
        "req_rift": "rift_ramparts",
        "waves": [
            "4 Guards",
            "2 Knights + 2 Guards",
            "4 Guards + 2 Knights",
            "8 Knights",
            "BOSS: Princess Ladybug",
        ],
    },
    "rift_tournament_grounds": {
        "name": "Tournament Grounds",
        "boss": "Royal Rider",
        "icon": "rb_boss_Royal_Knight",
        "desc": "The ultimate duel. 3 Phases.",
        "recommended_gp": 9500,
        "req_rift": "rift_moonlit_ruins",
        "waves": ["BOSS: Royal Rider"],
    },
}

ELITE_POOL_30 = [
    {
        "id": "corrupted_village",
        "name": "Corrupted Village",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "dragonworld",
    },
    {
        "id": "corrupted_ruins",
        "name": "Corrupted Ruins",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "dragonworld",
    },
    {
        "id": "corrupted_forest",
        "name": "Corrupted Forest",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "bugworld",
    },
    {
        "id": "corrupted_cave",
        "name": "Corrupted Cave",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "dragonworld",
    },
    {
        "id": "corrupted_castle",
        "name": "Corrupted Castle",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "bugworld",
    },
    {
        "id": "corrupted_shrine",
        "name": "Corrupted Shrine",
        "unlock_lvl": 30,
        "recommended_lvl": 35,
        "type": "dragonworld",
    },
]

ELITE_POOL_50 = [
    {
        "id": "corrupted_sewers",
        "name": "Corrupted Sewers",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "bugworld",
    },
    {
        "id": "corrupted_square",
        "name": "Corrupted Square",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "dragonworld",
    },
    {
        "id": "corrupted_undercroft",
        "name": "Corrupted Undercroft",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "bugworld",
    },
    {
        "id": "corrupted_gardens",
        "name": "Corrupted Gardens",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "dragonworld",
    },
    {
        "id": "corrupted_quarters",
        "name": "Corrupted Quarters",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "bugworld",
    },
    {
        "id": "corrupted_dock",
        "name": "Corrupted Dock",
        "unlock_lvl": 50,
        "recommended_lvl": 55,
        "type": "catworld",
    },
]


def get_world(world_id):
    all_worlds = WORLDS + ELITE_POOL_30 + ELITE_POOL_50
    for w in all_worlds:
        if w["id"] == world_id:
            return w
    return None


MONSTER_REGISTRY = [
    "chaos_Guardian_Juggler",
    "cw_Harpooner",
    "cw_Katchmi",
    "cw_arrowcat",
    "cw_boss_Kyudo",
    "cw_boss_blue_herring",
    "cw_skitter",
    "d_Awakened Statue",
    "d_Scorcher",
    "d_Spear_Jumper",
    "d_boss_Alpha_Charger",
    "d_boss_Big_Papa",
    "d_boss_Big_Red",
    "d_boss_Juggler",
    "d_boss_Overgrown_Vine",
    "d_boss_Savage_Spirit",
    "d_boss_Toxic_Spitter",
    "d_boss_beserker",
    "d_boss_bone_smasher",
    "d_boss_mama_boomer",
    "d_charger",
    "d_jumper",
    "d_slasher",
    "d_snoutter",
    "d_toxic_bloom",
    "d_toxic_sapling",
    "r_boss_Slayer",
    "rb_bean",
    "rb_boss_Alarm_Bell",
    "rb_boss_Axe_Hopper",
    "rb_boss_Prince",
    "rb_boss_Princess_Ladybug",
    "rb_boss_Royal_Knight",
    "rb_knight",
    "rb_mini_slime",
    "rb_scavanger",
    "rb_spitter",
    "Overlord",
    "Bug Lord",
    "Smasher",
    "Mega Slime",
    "Guard",
    "Big Papa",
    "Drog",
    "Draymor",
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
    "Royal Grub",
    "Royal Knight",
    "Scorcher",
]

WORLD_POOLS = {
    "dragonworld": ["d_", "r_"],
    "bugworld": ["rb_"],
    "catworld": ["cw_"],
    "homeworld": ["d_", "cw_", "rb_"],
}

WORLD_SPECIFIC_POOLS = {
    "downtown_chaos": ["d_"],
    "feline_invasion": ["cw_"],
    "chaos_invasion": ["d_", "rb_", "cw_", "chaos_"],
    "shrine_village": ["d_", "Drog"],
}


def get_monsters_for_world(world_id, world_type):
    pool_prefixes = WORLD_SPECIFIC_POOLS.get(world_id) or WORLD_POOLS.get(
        world_type, ["d_"]
    )
    eligible = []
    for m in MONSTER_REGISTRY:
        if any(m.startswith(p) for p in pool_prefixes) or m in pool_prefixes:
            eligible.append(m)

    if world_type == "bugworld":
        eligible.extend(["Overlord", "Bug Lord", "Mega Slime", "Guard"])
    elif world_type == "dragonworld":
        eligible.extend(["Smasher", "Big Papa", "Drog"])

    w_def = get_world(world_id)
    if w_def and w_def.get("unlock_lvl", 1) >= 33:
        eligible.append("Draymor")

    return list(set(eligible))

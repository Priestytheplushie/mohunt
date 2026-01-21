import os
import sys
from dotenv import load_dotenv


root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
dotenv_path = os.path.join(root_dir, ".env")

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")
ADMIN_ACCESS_CODE = os.getenv("ADMIN_ACCESS_CODE", "0000")


TURSO_DB_URL = os.getenv("TURSO_DB_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if not TOKEN:
    print("WARNING: DISCORD_TOKEN missing from environment.")


MOGOLD_EMOJI = "<:mogold:1452310658530934865>"
MERCH_TOKEN_EMOJI = "<:merchtoken:1455088798089347169>"
MAP_EMOJI = "<:map:1452381378522906754>"
ELITE_EMOJI = "<:elite:1452381420130537606>"
CHAOS_SHARD_EMOJI = "<:chaosshard:1452415046029414501>"
DAILY_JOB_EMOJI = "<:dailyjob:1452418984984186890>"
PROJECT_EMOJI = "<:project:1452418974410084515>"
XP_BOOST_ICON = "<:boost:1452423876112810165>"
XP_BOOST_3X_EMOJI = "<:boostedxp3x:1457211790823002297>"
NO_XP_EMOJI = "<:noxp:1457214747580698869>"
OVERCHARGED_ICON = "<:overchargedalert:1455070562060603447>"
CHAOS_CORE_EMOJI = "<:chaos_core:1452309436369600646>"
CHAOS_ALERT = "<:chaos_alert:1452502637210501276>"
MISSION_EMOJI = "<:mission:1452765525464580238>"
XP_EMOJI = "<:xp:1452309498617139310>"
SHARD_HUNT_EMOJI = "<:shardhunt:1452763522390954174>"
DOUBLE_XP_EMOJI = "<:doublexp:1455063013597118587>"
CHAOS_CRACK_EMOJI = "<:chaoscrack:1455064913117446326>"


MOCO_CRATE_EMOJI = "<:mococrate:1455592395075752007>"
MOCO_CRATE_LARGE_EMOJI = "<:mococratelarge:1455592407704928431>"
MOCO_CRATE_XL_EMOJI = "<:mococratexl:1455592422632460565>"
MOGOLD_CRATE_EMOJI = "<:mogoldcrate:1455608827973079091>"


MANNY_EMOJI = "<:manny:1455320328518762686>"
BUNCH_OF_DICE_EMOJI = "<:bunch_of_dice:1452824141408374935>"
TURBO_PILLS_EMOJI = "<:turbo_pills:1452828577484640296>"
GOLDEN_BOOMBOX_EMOJI = "<:golden_boombox:1452824199403147304>"
GOLDEN_FIREWORKS_EMOJI = "<:golden_fireworks:1452824189202333870>"
GOLDEN_TASER_EMOJI = "<:golden_taser:1452824175206207592>"
CLASSIC_SNOW_GLOBE_EMOJI = "<:classicSnowGlobe:1455598629262983169>"
CLASSIC_SHELLDON_EMOJI = "<:classicSheldon:1455598703954890782>"
CLASSIC_STICKER_EMOJI = "<:classic_really_cool_sticker:1455598713958301819>"
CLASSIC_LIFEJACKET_EMOJI = "<:classicLifeJacket:1455599583047712964>"
WATER_BALLOON_EMOJI = "<:WaterBalloon:1455599622360662180>"


DASH_EMOJI = "<:dash:1455228645772886189>"
OVERLORD_ICON = "<:overlord:1455228423885557801>"
RIFTS_EMOJI = "<:rifts:1455226802653106330>"
DOJO_ICON = "<:Dojo:1455234601923645574>"
VERSUS_ICON = "<:Versus:1455234640586739858>"


MOBS = {
    "Overlord": "<:overlord:1455228423885557801>",
    "Bug Lord": "<:bug_lord:1455308599487365332>",
    "Smasher": "<:smasher:1455308707813654651>",
    "Mega Slime": "<:mega_slime:1455308724963901713>",
    "Guard": "<:guard:1455308738134151240>",
    "Big Papa": "<:bigpapa:1455588934540202056>",
    "Drog": "<:drog:1455308748280168562>",
    "Draymor": "<:dramynor_the_vibe_vampire:1455308917860204661>",
    "d_boss_Juggler": "<:juggler:1452460280629166221>",
    "mo.co Crate": MOCO_CRATE_EMOJI,
}


LOADING_EMOJI = "<a:loading:1455320750088130734>"
UNKNOWN_ICON = "<:unknown:1458977831316095092>"
ELLIE_ICON = "<:ellie:1458981935207547082>"

BOT_EMOJIS = {
    "Jax": "<:jax:1455320379928346695>",
    "Luna": "<:luna:1455320365676105870>",
    "Manny": "<:manny:1455320328518762686>",
    "??Unknown??": UNKNOWN_ICON,
    "Ellie": ELLIE_ICON,
}


EMPTY_WEAPON = "<:empty_weapon:1452313607835484336>"
EMPTY_GADGET = "<:empty_gadget:1452313593050824826>"
EMPTY_PASSIVE = "<:empty_passive:1452313593856004248>"
EMPTY_MODULE = "<:empty_module:1452313591976955965>"
EMPTY_RING = "<:empty_ring:1452313595378401361>"
EMPTY_RIDE = "<:empty_ride:1457467688174489630>"


ELITE_HUNTER_ICON = "<:elitehunter:1452821753188585635>"
ELITE_TOKEN_EMOJI = "<:elitetoken:1452821824940544182>"
GEAR_POWER_EMOJI = "<:gearpower:1452824127273697470>"
ELITE_EMBLEM = "<:elite_emblem:1457930553083953276>"


PRESTIGE_1 = {
    "bronze": "<:prestige1_bronze:1452825680227074068>",
    "silver": "<:prestige1_silver:1452825640565866669>",
    "gold": "<:prestige1_gold:1452825681397285007>",
}
PRESTIGE_2 = {
    "bronze": "<:prestige2_bronze:1452825641614311505>",
    "silver": "<:prestige2_silver:1452825644193808434>",
    "gold": "<:prestige2_gold:1452825642717417493>",
}
PRESTIGE_MAX = {
    "bronze": "<:prestigemax_bronze:1452825646081507503>",
    "silver": "<:prestigemax_silver:1452825648719466496>",
    "gold": "<:prestigemax_gold:1452825647545323643>",
}


YELLOW_BELT = "<:yellowbelt:1455996161750994965>"
BLUE_BELT = "<:bluebelt:1455996174019330118>"
PURPLE_BELT = "<:purplebelt:1455996205241729125>"
BROWN_BELT = "<:brownbelt:1455996230261014548>"
BLACK_BELT = "<:blackbelt:1455996219808809086>"


BELT_THRESHOLDS = {"Yellow": 0, "Blue": 30, "Purple": 100, "Brown": 200, "Black": 350}

BELT_EMOJIS = {
    "Yellow": YELLOW_BELT,
    "Blue": BLUE_BELT,
    "Purple": PURPLE_BELT,
    "Brown": BROWN_BELT,
    "Black": BLACK_BELT,
}


XP_BANK_CAP = 420000
XP_BOOST_BANK_CAP = 210000
XP_PER_DAY = 60000
XP_BOOST_PER_DAY = 20000
XP_BOOST_MULT = 3


XP_DAILY_CAP = XP_BANK_CAP


MULT_OVERCHARGED = 16
MULT_MEGACHARGED = 32
MULT_CHAOS_ADDER = 8


WORLD_ICONS = {
    "homeworld": "<:homeworld:1452385168210792588>",
    "dragonworld": "<:dragonworld:1452385158773870602>",
    "catworld": "<:catworld:1452385148031995954>",
    "bugworld": "<:bugworld:1452385147000193166>",
}


WORLD_RGP = {
    "downtown_chaos": 14,
    "chaos_invasion": 30,
    "shrine_village": 50,
    "overgrown_ruins": 120,
    "infested_forest": 200,
    "cave_of_spirits": 800,
    "castle_walls": 1400,
    "summoning_grounds": 2400,
    "sewers": 3600,
    "feline_invasion": 4800,
    "ceremonial_square": 6000,
    "castle_undercroft": 7200,
    "sanctum_gardens": 8400,
    "royal_quarters": 9600,
    "frostpaw_dock": 10800,
    "corrupted_village": 11600,
    "corrupted_ruins": 12400,
    "corrupted_forest": 13200,
    "corrupted_cave": 14000,
    "corrupted_castle": 14800,
    "corrupted_shrine": 15600,
    "corrupted_sewers": 16400,
    "corrupted_square": 17000,
    "corrupted_undercroft": 17600,
    "corrupted_gardens": 18200,
    "corrupted_quarters": 18800,
    "corrupted_dock": 19400,
}


EMBLEMS = {
    "bronze": "<:bronze:1452375847385174060>",
    "silver": "<:silver:1452375864636477470>",
    "gold": "<:gold:1452375856294133961>",
    "diamond": "<:diamond:1452375834731085922>",
}


VALID_MODIFIERS = [
    "Standard",
    "Overcharged",
    "Megacharged",
    "Chaos",
    "Overcharged Chaos",
    "Megacharged Chaos",
    "Toxic",
    "Elite",
]
HUNT_MODS = [
    "Standard",
    "Overcharged",
    "Megacharged",
    "Chaos",
    "Toxic",
    "Overcharged Chaos",
    "Megacharged Chaos",
]
HUNT_WEIGHTS = [90.0, 6.0, 3.0, 0.8, 0.15, 0.04, 0.01]


PREMIUM_PASS_PRICE = 1000
SEASON_TYPES = [
    {
        "type": "Standard",
        "name": "Shard Hunt",
        "weight": 60,
        "desc": "Standard Rewards",
    },
    {
        "type": "Weapon",
        "name": "Weapon Mastery",
        "weight": 10,
        "desc": "All items are Weapons",
    },
    {
        "type": "Gadget",
        "name": "Gadget Mastery",
        "weight": 10,
        "desc": "All items are Gadgets",
    },
    {
        "type": "Passive",
        "name": "Passive Power",
        "weight": 10,
        "desc": "All items are Passives",
    },
    {"type": "Chaos", "name": "Chaos Theory", "weight": 1, "desc": "Chaos Rewards"},
    {
        "type": "XP_Rush",
        "name": "XP Rush",
        "weight": 5,
        "desc": "Only XP Rewards (No Pass)",
    },
]


LEVEL_DATA = [
    {"lvl": 1, "xp_cost": 1000, "hp": 1600, "reward": "kit"},
    {"lvl": 2, "xp_cost": 2000, "hp": 1700, "reward": "kit"},
    {"lvl": 3, "xp_cost": 3000, "hp": 1800, "reward": "world:Overgrown Ruins"},
    {"lvl": 4, "xp_cost": 4000, "hp": 1900, "reward": "kit"},
    {"lvl": 5, "xp_cost": 5000, "hp": 2000, "reward": "kit"},
    {"lvl": 6, "xp_cost": 6000, "hp": 2100, "reward": "world:Infested Forest"},
    {"lvl": 7, "xp_cost": 8000, "hp": 2200, "reward": "kit"},
    {"lvl": 8, "xp_cost": 10000, "hp": 2300, "reward": "kit"},
    {"lvl": 9, "xp_cost": 15000, "hp": 2400, "reward": "rift:Enter the Chaos"},
    {"lvl": 10, "xp_cost": 20000, "hp": 2500, "reward": "kit"},
    {"lvl": 11, "xp_cost": 30000, "hp": 2600, "reward": "kit"},
    {"lvl": 12, "xp_cost": 40000, "hp": 2700, "reward": "world:Cave of Spirits"},
    {"lvl": 13, "xp_cost": 50000, "hp": 2800, "reward": "kit"},
    {"lvl": 14, "xp_cost": 55000, "hp": 2900, "reward": "dojo:Basic Training"},
    {"lvl": 15, "xp_cost": 60000, "hp": 3000, "reward": "kit"},
    {"lvl": 16, "xp_cost": 65000, "hp": 3100, "reward": "world:Castle Walls"},
    {"lvl": 17, "xp_cost": 70000, "hp": 3300, "reward": "rift:Hunt for Mama"},
    {"lvl": 18, "xp_cost": 75000, "hp": 3500, "reward": "kit"},
    {"lvl": 19, "xp_cost": 80000, "hp": 3700, "reward": "kit"},
    {"lvl": 20, "xp_cost": 85000, "hp": 3900, "reward": "world:Summoning Grounds"},
    {"lvl": 21, "xp_cost": 90000, "hp": 4100, "reward": "kit"},
    {"lvl": 22, "xp_cost": 95000, "hp": 4300, "reward": "rift:Monster Games"},
    {"lvl": 23, "xp_cost": 100000, "hp": 4500, "reward": "dojo:Advanced Training"},
    {"lvl": 24, "xp_cost": 100000, "hp": 4700, "reward": "kit"},
    {"lvl": 25, "xp_cost": 100000, "hp": 5000, "reward": "world:Srs"},
    {"lvl": 26, "xp_cost": 100000, "hp": 5300, "reward": "rift:The Showdown"},
    {"lvl": 27, "xp_cost": 100000, "hp": 5600, "reward": "kit"},
    {"lvl": 28, "xp_cost": 100000, "hp": 5900, "reward": "kit"},
    {"lvl": 29, "xp_cost": 100000, "hp": 6200, "reward": "kit"},
    {"lvl": 30, "xp_cost": 100000, "hp": 6500, "reward": "rift:Chaos Extreme"},
    {"lvl": 31, "xp_cost": 100000, "hp": 6800, "reward": "kit"},
    {"lvl": 32, "xp_cost": 100000, "hp": 7200, "reward": "kit"},
    {"lvl": 33, "xp_cost": 100000, "hp": 7500, "reward": "world:Ceremonial Square"},
    {"lvl": 34, "xp_cost": 100000, "hp": 7900, "reward": "kit"},
    {"lvl": 35, "xp_cost": 100000, "hp": 8300, "reward": "kit"},
    {"lvl": 36, "xp_cost": 100000, "hp": 8700, "reward": "kit"},
    {"lvl": 37, "xp_cost": 100000, "hp": 9200, "reward": "world:Castle Undercroft"},
    {"lvl": 38, "xp_cost": 100000, "hp": 9600, "reward": "kit"},
    {"lvl": 39, "xp_cost": 100000, "hp": 10100, "reward": "kit"},
    {"lvl": 40, "xp_cost": 100000, "hp": 10600, "reward": "world:Sanctum Gardens"},
    {"lvl": 41, "xp_cost": 100000, "hp": 11200, "reward": "kit"},
    {"lvl": 42, "xp_cost": 100000, "hp": 11700, "reward": "kit"},
    {"lvl": 43, "xp_cost": 100000, "hp": 12300, "reward": "world:Royal Quarters"},
    {"lvl": 44, "xp_cost": 100000, "hp": 12900, "reward": "kit"},
    {"lvl": 45, "xp_cost": 100000, "hp": 13600, "reward": "kit"},
    {"lvl": 46, "xp_cost": 100000, "hp": 14300, "reward": "world:Frostpaw Dock"},
    {"lvl": 47, "xp_cost": 100000, "hp": 15000, "reward": "kit"},
    {"lvl": 48, "xp_cost": 100000, "hp": 15700, "reward": "kit"},
    {"lvl": 49, "xp_cost": 100000, "hp": 16500, "reward": "kit"},
    {"lvl": 50, "xp_cost": 20000, "hp": 17400, "reward": "elite:Elite Hunter Program"},
]


ELITE_LEVEL_MAP = [
    (1, 0),
    (2, 20000),
    (10, 216000),
    (15, 371000),
    (20, 551000),
    (25, 756000),
    (30, 986000),
    (35, 1241000),
    (40, 1521000),
    (45, 1826000),
    (50, 2156000),
    (55, 2511000),
    (60, 2891000),
    (65, 3296000),
    (70, 3726000),
    (80, 4661000),
    (90, 5732000),
    (100, 7002000),
    (200, 30702000),
    (300, 74402000),
    (400, 138102000),
]

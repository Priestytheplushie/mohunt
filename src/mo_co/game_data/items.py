from mo_co import config


def to_key(name):
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "")


TITLE_ENTRIES = {
    "title_elite": {
        "name": "Beyond Elite",
        "rarity": "Legendary",
        "desc": "The best of the best!",
    },
    "title_master": {
        "name": "Master of CHs",
        "rarity": "Epic",
        "desc": "Master of the grind!",
    },
    "title_overcharged": {
        "name": "Overcharged",
        "rarity": "Epic",
        "desc": "Chaos energy surges!",
    },
    "title_megacharged": {
        "name": "Megacharged",
        "rarity": "Legendary",
        "desc": "Embrace the Chaos",
    },
    "title_gatekeeper": {
        "name": "The Gatekeeper",
        "rarity": "Epic",
        "desc": "Holder of keys!",
    },
    "title_boss": {
        "name": "Final Boss",
        "rarity": "Legendary",
        "desc": "The final obstucle!",
    },
    "title_xp": {
        "name": "XP Sentinel",
        "rarity": "Epic",
        "desc": "XP flows through you!",
    },
    "title_xp_boosted": {
        "name": "XP Titan",
        "rarity": "Legendary",
        "desc": "Priesty ran out of ideas...",
    },
    "title_prime": {
        "name": "Prime Hunter",
        "rarity": "Epic",
        "desc": "Prime form!",
    },
    "title_neo": {
        "name": "Neo Hunter",
        "rarity": "Legendary",
        "desc": "Will neo mo.co ever come to mo.hunt?",
    },
    "title_heir": {
        "name": "Elite Heir",
        "rarity": "Epic",
        "desc": "Heir of the throne!",
    },
    "title_monarch": {
        "name": "Elite Monarch",
        "rarity": "Legendary",
        "desc": "Monarch of the Royal Bug World",
    },
    "title_timeless": {
        "name": "Timeless",
        "rarity": "Epic",
        "desc": "Timeless",
    },
    "title_grass": {
        "name": "What's Grass",
        "rarity": "Legendary",
        "desc": "Touch Grass!",
    },
    "title_meow": {
        "name": "meow",
        "rarity": "Epic",
        "desc": "ne.co apporved!",
    },
    "title_meowow": {
        "name": "meowow",
        "rarity": "Legendary",
        "desc": "meow...?!",
    },
    "title_moco": {
        "name": "No Lifer",
        "rarity": "Legendary",
        "desc": "Get off the game",
    },
    "title_good": {
        "name": "Git Gud",
        "rarity": "Rare",
        "desc": "Have you tried getting good?",
    },
    "title_vibes": {
        "name": "Professor Vibes",
        "rarity": "Rare",
        "desc": "Bascially a beta tester...",
    },
    "title_brawl": {
        "name": "Brawl Player",
        "rarity": "Rare",
        "desc": "You play brawl star?",
    },
    "title_reddit": {
        "name": "Reddit Army",
        "rarity": "Rare",
        "desc": "Master of Complaning",
    },
    "title_army": {
        "name": "One Man Army",
        "rarity": "Rare",
        "desc": "Do it yourself",
    },
    "title_cool": {
        "name": "Cool Zoner",
        "rarity": "Rare",
        "desc": "I'm just so cool!",
    },
    "title_button": {
        "name": "Button Masher",
        "rarity": "Rare",
        "desc": "No fun allowed!",
    },
    "title_hunter_intern": {
        "name": "Hunting Intern",
        "rarity": "Common",
        "desc": "You gotta start somewhere",
    },
    "title_junior": {
        "name": "Junior Thwacker",
        "rarity": "Common",
        "desc": "Keep going!",
    },
    "title_associate": {
        "name": "Associate Hunter",
        "rarity": "Common",
        "desc": "Asscoiate",
    },
    "title_damage": {
        "name": "Damage Consultant",
        "rarity": "Common",
        "desc": "If you need damage, you know who to call...",
    },
    "title_vp": {
        "name": "Hunter VP",
        "rarity": "Common",
        "desc": "Rising through the ranks!",
    },
    "title_head": {"name": "Head Hunter", "rarity": "Mythic", "desc": "Luna"},
    "title_tech": {"name": "Tech Guy", "rarity": "Mythic", "desc": "Manny"},
    "title_combat": {
        "name": "Combat Specialist",
        "rarity": "Mythic",
        "desc": "Jax",
    },
    "title_chapter1": {
        "name": "C1 Elite Hunter",
        "rarity": "Legendary",
        "desc": "Welcome to the big leagues!",
    },
    "title_legend": {
        "name": "Living Legend",
        "rarity": "Legendary",
        "desc": "The man, the myth, the legend!",
    },
}

WEAPON_ENTRIES = [
    {
        "name": "Monster Slugger",
        "rarity": "Common",
        "main": "Swing your Bat to deal **area damage** in front of you at close range",
        "combo": "Every 4th attack is a BIG swing that does damage over a larger area and Slows all non-boss monsters. ",
        "quote": "Get into the swing of things!",
    },
    {
        "name": "Techno Fists",
        "rarity": "Common",
        "main": "Fling Energy Balls at long range that deal **damage** and **bounce** 2 times between enemies, Stunning small monsters",
        "combo": "Every 10th attack flings a MEGA Ball that deals more damage and has 10 bounces, Stunning all non-boss monsters.",
        "quote": "Fire bouncing balls of destruction!",
    },
    {
        "name": "Wolf Stick",
        "rarity": "Common",
        "main": "Shoot to **damage** single enemies at long range",
        "combo": "Your 6th attack **summons** a big blue wolf to fight alongside you.",
        "quote": "Theres a wolf in the stick! Chaos Energy is wild!",
    },
    {
        "name": "Staff of Good vibes",
        "rarity": "Rare",
        "main": "Shoot your Staff to **heal** friendly targets and **damage** enemies in front of you at long range",
        "combo": "Every 10th attack is a 360 degree attack that heals more and deals more damage",
        "quote": "Everyone loves a healer!",
    },
    {
        "name": "Toothpick and Shield",
        "rarity": "Common",
        "main": "Poke your Pick to deal **area damage** in front of you at close range",
        "combo": "After you recieve 15 hits from enemies, your next attack is a area slam that deals damage in a large area around you and Stuns non-boss monsters",
        "quote": "Tank the damage! and keep your teeth clean...!",
        "desc": "Shield Passive: Take 30% less damage from all sources at all times.",
    },
    {
        "name": "Portable Portal",
        "rarity": "Rare",
        "main": "Shoots a Squiggle that deals **area damage** at long range.",
        "combo": "Fill the combo bar to activate your **rightmost gadget** for free.",
        "quote": "Pocket friendly portal tech!",
    },
    {
        "name": "CPU Bomb",
        "rarity": "Rare",
        "main": "Lob overclocked CPUs that deal **area damage** at long range.",
        "combo": "Every 8th attack is a MEGA BOMB that explodes after a short delay, Stunning non-boss monsters and casuing more damage",
        "quote": "Overclocked to explode!",
    },
    {
        "name": "Speedshot",
        "rarity": "Epic",
        "main": "Shoot arrows that damage a **single** enemy.",
        "combo": "After 10 attacks, enter SPEED mode, shooting really fast",
        "quote": "Single and ready to mangle!",
    },
    {
        "name": "Medicne Ball",
        "rarity": "Common",
        "main": "Swing your Ball to deal **area damage** in front of you at close range.",
        "combo": "Every 3rd attack also **heals** you and all nearby friendlies in a big area all around you",
        "quote": "The secret to good health!",
        "desc": "Health Passive: Increase your max health by 30%.",
    },
    {
        "name": "Buzz Kill",
        "rarity": "Epic",
        "main": "Swing to deal **area damage** in front of you at close range",
        "combo": "Every 3rd attack, you **summon** a bee to fight alongside you",
        "quote": "To bee or not to bee.",
    },
    {
        "name": "Hornbow",
        "rarity": "Rare",
        "main": "Shoot 3 bolts that deal damage at **medium range**.",
        "combo": "Every 3rd attack is a MEGASHOT that shoots 5 **pericing** bolts in a wider area, dealing even more damage.",
        "quote": "Say hello to my little friend!",
    },
    {
        "name": "Singularity",
        "rarity": "Epic",
        "main": "Swing your Claw to deal **area damage** in front of you at close range",
        "combo": "Every 6th attack deals damage to enemies around you and **removes** 1.5 seconds from all Gadget that are on cooldown.",
        "quote": "Time is on your side!",
    },
    {
        "name": "Poison Bow",
        "rarity": "Rare",
        "main": "Shoot arrows that **damage** single enemies at long range",
        "combo": "Every 5th attack, shoot a **volley** of 3 poison arrows that explode in a small area, dealing **damage over time** and slowing non-boss monsters ",
        "quote": "Float like a a butterfly, sting like a bow!",
    },
    {
        "name": "Spinsickle",
        "rarity": "Rare",
        "main": "Swing to deal area damage in front of you at **close range**",
        "combo": "After 6 attacks, enter **SPIN mode**, where you can pass hrough enemies, you gain a 25% chance to avoid any enemy attacks and you attack faster and deal area damage all around you.",
        "quote": "Spin it to win it!",
    },
    {
        "name": "Squid Blades",
        "rarity": "Epic",
        "main": "Repeatedly stab a single enemy at **close range** with high attack speed.",
        "combo": "**INVISIBILITY** Stop attacking and using Gadgets to fill up the Invisibility bar. When filled, you turn Insivible to enemies. **AMBUSH**: When Invisible, your next attack dashes towards the closest enemy dealing massive damage, Stunning non-boss monsters.",
        "quote": "Hidden and dangerous!",
    },
]

GADGET_ENTRIES = [
    {"name": "Splash Heal", "rarity": "Rare", "quote": "Stay hydrated!!"},
    {
        "name": "Smart Fireworks",
        "rarity": "Rare",
        "quote": "Monster seeking sparklers!",
    },
    {
        "name": "Boom Box",
        "rarity": "Rare",
        "quote": "Blast monsters with sick beats!",
    },
    {
        "name": "Vitamin Shot",
        "rarity": "Rare",
        "quote": "Increases your firing rate, healing and levels of vitamin D!",
    },
    {
        "name": "Monster Taser",
        "rarity": "Rare",
        "quote": "Shockingly accurate! Feel the tingles.",
    },
    {
        "name": "Pepper Spray",
        "rarity": "Rare",
        "quote": "Great for slowing and damaging monsters, and tacos!",
    },
    {
        "name": "Multi Zapper",
        "rarity": "Rare",
        "quote": "Thunderbolts and lightning, very very frightening!",
    },
    {
        "name": "Snow Globe",
        "rarity": "Rare",
        "quote": "A snow storm to slow down Chaos Monsters",
    },
    {
        "name": "Life Jacket",
        "rarity": "Rare",
        "quote": "Just pull the pin and inflate!",
    },
    {
        "name": "Spicy Dagger",
        "rarity": "Rare",
        "quote": "Red hot chilly daggers!",
    },
    {"name": "Explosive 6 Pack", "rarity": "Rare", "quote": "Bombs away!"},
    {
        "name": "Super Loud Whistle",
        "rarity": "Rare",
        "quote": "The best way to get attention!",
    },
    {
        "name": "Revitalizing Mist",
        "rarity": "Rare",
        "quote": "Instant mood lift!",
    },
    {
        "name": "Really Cool Sticker",
        "rarity": "Rare",
        "quote": "Stick it onto your Weapon for a boost!",
    },
    {"name": "Sheldon", "rarity": "Rare", "quote": "Your half-shell hero!"},
    {
        "name": "Very Mean Pendant",
        "rarity": "Rare",
        "quote": "Take it all for yourself!",
    },
    {
        "name": "Feel Better Bloom",
        "rarity": "Rare",
        "quote": "Bask in the glow!",
    },
    {
        "name": "PEW 3000",
        "rarity": "Rare",
        "quote": "Pew pew pew! (Mariokart)",
    },
]

PASSIVE_ENTRIES = [
    {
        "name": "Auto Zapper",
        "rarity": "Common",
        "quote": "Automated lightning!",
        "desc": "Deals damage every turn. 15% chance to STUN non-boss monsters, preventing incoming damage.",
    },
    {
        "name": "Vampire Teeth",
        "rarity": "Common",
        "quote": "A little heal in every bite!",
        "desc": "Heals you for a percentage of the damage you deal. Scales with Item Level.",
    },
    {
        "name": "Smelly Socks",
        "rarity": "Common",
        "quote": "Chaos monsters hate the smell of Manny's old socks!",
        "desc": "Emits a stinky aura that deals constant extra damage to enemies.",
    },
    {
        "name": "Unstable Lazer",
        "rarity": "Common",
        "quote": "Your odds of shooting lazers at chaos monsters just increased!",
        "desc": "20% chance to fire a laser that deals damage and grants +10% Bonus XP.",
    },
    {
        "name": "Explode O Matic Trigger",
        "rarity": "Common",
        "quote": "The end is just the begining... of an explosion",
        "desc": "Chance on kill to trigger an explosion that finds extra loot (Bonus Roll).",
    },
    {
        "name": "R&B Mixtape",
        "rarity": "Common",
        "quote": "Great vibes that heal all around!",
        "desc": "Heals a flat amount of HP after every successful hunt.",
    },
    {
        "name": "Unstable Beam",
        "rarity": "Common",
        "quote": "Focus on whats important!",
        "desc": "5% chance to fire a massive beam. Deals huge damage!",
    },
    {
        "name": "Unstable Lightning",
        "rarity": "Common",
        "quote": "Zip zap Zoop!",
        "desc": "Chance to trigger chain lightning when using gadgets.",
    },
    {
        "name": "Healthy Snacks",
        "rarity": "Common",
        "quote": "Delicous AND healthy!",
        "desc": "Increases your Max HP by a percentage. Scales with Item Level.",
    },
    {
        "name": "Healing Charm",
        "rarity": "Common",
        "quote": "Feel every heal!",
        "desc": "Increases all healing received from other sources (Vampire, R&B, Potions).",
    },
    {
        "name": "Chicken O Matic",
        "rarity": "Common",
        "quote": "Look at all those chickens",
        "desc": "Chance to spawn a chicken that tanks 100% of damage for one turn.",
    },
    {
        "name": "Pocket Airbag",
        "rarity": "Common",
        "quote": "Ultimate crash proection",
        "desc": "Chance to completely dodge an incoming attack.",
    },
    {
        "name": "Gadget Battery",
        "rarity": "Common",
        "quote": "Zaps all around",
        "desc": "Using a gadget zaps a nearby enemy, dealing damage and Stunning non-boss monsters",
    },
    {
        "name": "Cactus Charm",
        "rarity": "Common",
        "quote": "The recolition in every action!",
        "desc": "Reflects a percentage of damage taken back at the attacker.",
    },
    {
        "name": "Bunch of Dice",
        "rarity": "Legendary",
        "quote": "High roller!",
        "desc": "Increases Luck. Chance for x4 XP Jackpot, more loot drops, and finding Crates.",
    },
    {
        "name": "Overcharged Amulet",
        "rarity": "Legendary",
        "quote": "Chaos energy resonates.",
        "desc": "Increases the chance of finding an Overcharged or Megacharged Monster.",
        "shop_exclusive": True,
    },
]

MODULE_ENTRIES = [
    {
        "name": "Elite Dash Module",
        "rarity": "Epic",
        "quote": "Reduces the cooldown of your dash.",
    },
    {
        "name": "Speed Kill",
        "rarity": "Epic",
        "quote": "If you or your pets deal the final blow, than you gian a short movement speed boost",
    },
    {
        "name": "Healing Ride",
        "rarity": "Epic",
        "quote": "Constantly heal yourself while on your Ride!",
    },
]

RING_ENTRIES = [
    {
        "name": "Major Executioner Ring",
        "rarity": "Epic",
        "effect": "You and your pets deal more damage to enemies below 20% health.",
    },
    {
        "name": "Major Damage Ring",
        "rarity": "Epic",
        "effect": "Increases all damage you and your pets deal.",
    },
    {
        "name": "Major Passive Ring",
        "rarity": "Epic",
        "effect": "Increases your passive damage and gives passive attacks a chance to deal 3x damage.",
    },
    {
        "name": "Major Gadget Ring",
        "rarity": "Epic",
        "effect": "Increases your gadget damage and gives gadget attacks a chance to deal 3x damage.",
    },
    {
        "name": "Major Healing Ring",
        "rarity": "Epic",
        "effect": "Increases all healing you and your pets do and gives a chance to restore 3x as much health.",
    },
    {
        "name": "Major Health Ring",
        "rarity": "Epic",
        "effect": "Increases your health and all healing you and your pets receive.",
    },
    {
        "name": "Major Crit Ring",
        "rarity": "Epic",
        "effect": "You and your pets gain a chance to deal 3x damage on all attacks.",
    },
    {
        "name": "Major Pet Ring",
        "rarity": "Epic",
        "effect": "Increases the damage of your pets and gives them a chance to deal 3x damage.",
    },
    {
        "name": "Major Pet Health Ring",
        "rarity": "Epic",
        "effect": "Increases the health of your pets and all healing you and your pets receive.",
    },
    {
        "name": "Warrior's Ring",
        "rarity": "Epic",
        "effect": "Increase your Weapon attack speed & damage.",
    },
    {
        "name": "Precision Ring",
        "rarity": "Epic",
        "effect": "Gain a chance to do a critical hit that deals 3x damage whenever you deal damage with your Weapon.",
    },
    {
        "name": "Time Ring",
        "rarity": "Epic",
        "effect": "Reduce the cooldown of all your Gadgets and increase their damage.",
    },
    {
        "name": "Explosive Ring",
        "rarity": "Epic",
        "effect": "Gain a chance to do a critical hit that deals 3x damage whenever you deal damage with your Gadgets.",
    },
    {
        "name": "Frenzy Ring",
        "rarity": "Epic",
        "effect": "Increase your pets' attack speed and damage.",
    },
    {
        "name": "Savage Ring",
        "rarity": "Epic",
        "effect": "Your pets gain a chance to do a critical hit that deals 3x damage whenever they deal damage.",
    },
    {
        "name": "Pulse Ring",
        "rarity": "Epic",
        "effect": "Increase all damage done by your Passives.",
    },
    {
        "name": "Echo Ring",
        "rarity": "Epic",
        "effect": "Gain a chance to do a critical hit that deals 3x damage whenever you deal damage with your Passives.",
    },
    {
        "name": "Restoration Ring",
        "rarity": "Epic",
        "effect": "Increase all healing you and your pets do.",
    },
    {
        "name": "Vitality Ring",
        "rarity": "Epic",
        "effect": "Gain a chance to do a critical heal that heals 3x health whenever you or your pets do any healing.",
    },
    {
        "name": "Bulk Ring",
        "rarity": "Epic",
        "effect": "Increase your total health.",
    },
    {
        "name": "Guard Ring",
        "rarity": "Epic",
        "effect": "Gain a chance to avoid any enemy attack.",
    },
    {
        "name": "Beast Ring",
        "rarity": "Legendary",
        "effect": "Increase your pets' health.",
    },
    {
        "name": "Minor Executioner Ring",
        "rarity": "Rare",
        "effect": "You and your pets deal slightly more damage to enemies below 20% health and increases your health.",
    },
    {
        "name": "Minor Damage Ring",
        "rarity": "Rare",
        "effect": "Slightly increases all damage you and your pets deal and your health.",
    },
    {
        "name": "Minor Passive Ring",
        "rarity": "Rare",
        "effect": "Slightly increases your passive damage and your health.",
    },
    {
        "name": "Minor Gadget Ring",
        "rarity": "Rare",
        "effect": "Slightly increases your gadget damage and your health.",
    },
    {
        "name": "Minor Healing Ring",
        "rarity": "Rare",
        "effect": "Slightly increases all healing you and your pets do and increases your health.",
    },
    {
        "name": "Minor Health Ring",
        "rarity": "Rare",
        "effect": "Slightly increases your health and gives a chance to dodge enemy attacks.",
    },
    {
        "name": "Minor Crit Ring",
        "rarity": "Rare",
        "effect": "You and your pets gain a small chance to deal 3x damage on all attacks and increases your health.",
    },
    {
        "name": "Minor Pet Ring",
        "rarity": "Rare",
        "effect": "Slightly increases the damage of your pets and your health.",
    },
    {
        "name": "Minor Pet Health Ring",
        "rarity": "Rare",
        "effect": "Slightly increases the health of you and your pets.",
    },
    {
        "name": "Insane Attack Speed Ring",
        "rarity": "Legendary",
        "effect": "Insanely fast weapon attacks.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Movement Speed Ring",
        "rarity": "Legendary",
        "effect": "Insanely fast movement.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Cooldown Reduction Ring",
        "rarity": "Legendary",
        "effect": "Insanely fast gadget cooldowns.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Pet Attack Speed Ring",
        "rarity": "Legendary",
        "effect": "Insanely fast pet attacks.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Dash Ring",
        "rarity": "Legendary",
        "effect": "Insanely fast dash cooldown.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Self Healing Ring",
        "rarity": "Legendary",
        "effect": "Insane self Healing!",
        "event_exclusive": True,
    },
    {
        "name": "Insane Weapon Damage Ring",
        "rarity": "Legendary",
        "effect": "Insane Damage Boost to your Weapon!",
        "event_exclusive": True,
    },
    {
        "name": "Insane Gadget Damage Ring",
        "rarity": "Legendary",
        "effect": "Insane Damage Boost to your Gadgets!",
        "event_exclusive": True,
    },
    {
        "name": "Insane Passive Damage Ring",
        "rarity": "Legendary",
        "effect": "Insane Damage Boost to your Passives!",
        "event_exclusive": True,
    },
    {
        "name": "Insane Damage Ring",
        "rarity": "Legendary",
        "effect": "Insane Damage Boost to all damage you deal!",
        "event_exclusive": True,
    },
    {
        "name": "Insane Slow Attack Gem",
        "rarity": "Legendary",
        "effect": "Insanely slows down your weapon attack speed.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Projectile Ring",
        "rarity": "Legendary",
        "effect": "Increase Weapon Projectile Count.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Weapon Combo Ring",
        "rarity": "Legendary",
        "effect": "Changes how quickly you get the weapon combo.",
        "event_exclusive": True,
    },
    {
        "name": "Insane Ring of Projectile Speed",
        "rarity": "Legendary",
        "effect": "Slow down and smell the roses.",
        "event_exclusive": True,
    },
]

SKIN_ENTRIES = [
    {"name": "Turbo Pills", "rarity": "Epic", "base_item": "vitamin_shot"},
    {"name": "Golden Boombox", "rarity": "Legendary", "base_item": "boom_box"},
    {
        "name": "Golden Fireworks",
        "rarity": "Legendary",
        "base_item": "smart_fireworks",
    },
    {
        "name": "Golden Taser",
        "rarity": "Legendary",
        "base_item": "monster_taser",
    },
    {
        "name": "Classic Snow Globe",
        "rarity": "Common",
        "base_item": "snow_globe",
    },
    {"name": "Classic Shelldon", "rarity": "Common", "base_item": "sheldon"},
    {
        "name": "Classic Really Cool Sticker",
        "rarity": "Common",
        "base_item": "really_cool_sticker",
    },
    {
        "name": "Classic LifeJacket",
        "rarity": "Common",
        "base_item": "life_jacket",
    },
    {"name": "Water Balloon", "rarity": "Epic", "base_item": "splash_heal"},
]

RIDE_ENTRIES = [
    {
        "name": "Chickaboo Eggshell",
        "rarity": "Epic",
        "desc": "A trusty feathery steed! +10% Dodge Chance in hunts.",
        "quote": "Kweh!",
    }
]

CLASSIC_COLLECTION_BOX = [
    "turbo_pills",
    "golden_boombox",
    "golden_fireworks",
    "golden_taser",
    "classic_snow_globe",
    "classic_shelldon",
    "classic_really_cool_sticker",
    "classic_lifejacket",
    "og_crew_title",
]

ALL_ITEMS = {}

for k, v in TITLE_ENTRIES.items():
    ALL_ITEMS[k] = {
        "id": k,
        "name": v["name"],
        "type": "title",
        "rarity": v.get("rarity", "Common"),
        "description": v.get("desc", ""),
        "quote": None,
    }


def build_registry(entries, type_str):
    for entry in entries:
        key = to_key(entry["name"])
        if "R&B" in entry["name"]:
            key = "randb_mixtape"

        item_data = {
            "id": key,
            "name": entry["name"],
            "type": type_str,
            "rarity": entry.get("rarity", "Common"),
            "quote": entry.get("quote", None),
            "event_exclusive": entry.get("event_exclusive", False),
            "shop_exclusive": entry.get("shop_exclusive", False),
        }

        if type_str == "weapon":
            item_data["main_attack"] = entry.get("main", "Attack")
            item_data["combo_attack"] = entry.get("combo", "Combo")
            item_data["effect"] = None
            item_data["description"] = None
        elif type_str == "smart_ring":
            item_data["effect"] = entry.get("effect", "No effect listed.")
            item_data["description"] = None
        elif type_str == "skin":
            item_data["base_item"] = entry.get("base_item")
            item_data["description"] = (
                f"Skin for {entry.get('base_item').replace('_', ' ').title()}"
            )
        else:
            item_data["description"] = (
                entry.get("desc")
                or entry.get("effect")
                or entry.get("quote", "No info.")
            )
            item_data["effect"] = entry.get("effect", None)

        ALL_ITEMS[key] = item_data


build_registry(WEAPON_ENTRIES, "weapon")
build_registry(GADGET_ENTRIES, "gadget")
build_registry(PASSIVE_ENTRIES, "passive")
build_registry(MODULE_ENTRIES, "elite_module")
build_registry(RING_ENTRIES, "smart_ring")
build_registry(SKIN_ENTRIES, "skin")
build_registry(RIDE_ENTRIES, "ride")


def get_item(item_id):
    return ALL_ITEMS.get(item_id)

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
import json
import math
from mo_co import database, game_data, utils, config, pedia
from mo_co.mission_engine import MissionEngine
from mo_co.game_data.missions import MISSIONS
from mo_co import config


ICON_MONSTER = "<:unknown_monster:1457470433258373293>"
ICON_GEAR = "<:empty_weapon:1452313607835484336>"
ICON_WORLD = "<:Map:1452381378522906754>"
ICON_MISSION = "<:mission:1452765525464580238>"
ICON_SKIN = "<:classic_really_cool_sticker:1455598713958301819>"
ICON_BELT = "<:yellowbelt:1455996161750994965>"
ICON_ARCHIVE = "<:chaos_core:1452309436369600646>"

ICON_BUG_WORLD = "<:bugworld:1452385147000193166>"
ICON_CAT_WORLD = "<:catworld:1452385148031995954>"
ICON_DRAGON_WORLD = "<:dragonworld:1452385158773870602>"
ICON_HOME_WORLD = "<:homeworld:1452385168210792588>"
ICON_CHAOS_WORLD = "<:chaoscrack:1455064913117446326>"

ICON_WPN = "<:empty_weapon:1452313607835484336>"
ICON_RING = "<:empty_ring:1452313595378401361>"
ICON_PASSIVE = "<:empty_passive:1452313593856004248>"
ICON_GADGET = "<:empty_gadget:1452313593050824826>"
ICON_MODULE = "<:empty_module:1452313591976955965>"

ICON_MINOR = "<:minor_damage_ring:1456685520414441645>"
ICON_MAJOR = "<:damage_ring:1452309438265561138>"
ICON_INSANE = "<:guard_ring:1452309479411679313>"
ICON_SPECIAL = "<:warriors_ring:1452309484713152734>"


class Index(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="community", description="Join the official mo.hunt community"
    )
    async def community(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{config.CHAOS_CORE_EMOJI} Chaos Conquest",
            description="Join our support server for updates, trading, and community events, as well as Brawl Stars and mo.co!",
            color=0x5865F2,
        )
        embed.add_field(
            name="Invite Link",
            value="https://discord.gg/sqjSwtQ7Nj",
            inline=False,
        )

        view = View()
        view.add_item(
            Button(
                label="Join Server",
                url="https://discord.gg/sqjSwtQ7Nj",
                style=discord.ButtonStyle.link,
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="index", description="Access the mo.copedia")
    @app_commands.describe(target="Directly open a specific entry (Optional)")
    @app_commands.autocomplete(target=utils.item_autocomplete)
    async def index(self, interaction: discord.Interaction, target: str = None):
        database.register_user(interaction.user.id)
        u_data = database.get_user_data(interaction.user.id)
        lvl, _, _ = utils.get_level_info(u_data["xp"])

        if lvl < 12:
            return await interaction.response.send_message(
                "🚫 **mo.copedia unlocks at Hunter Level 12!**", ephemeral=True
            )

        if target:
            dtype = None

            item_def = game_data.get_item(target)
            if item_def:
                t = item_def["type"]
                if t in [
                    "weapon",
                    "gadget",
                    "passive",
                    "smart_ring",
                    "elite_module",
                ]:
                    dtype = "gear"
                elif t in ["skin", "ride"]:
                    dtype = "skin"

            if not dtype and target in game_data.MONSTER_REGISTRY:
                dtype = "monster"

            if not dtype:
                w_def = game_data.get_world(target)
                if w_def:
                    dtype = "world"

            if dtype:
                view = DetailView(self.bot, interaction.user.id, dtype, target)
                await interaction.response.send_message(
                    embed=view.get_embed(), view=view, ephemeral=True
                )
                return
            else:

                pass

        view = MocopediaHomeView(self.bot, interaction.user.id)
        await interaction.response.send_message(
            embed=view.get_embed(), view=view, ephemeral=True
        )


class MocopediaHomeView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.pdata = pedia._get_data(user_id)
        self.update_components()

    def get_embed(self):
        embed = discord.Embed(
            title=f"{config.CHAOS_CRACK_EMOJI} mo.copedia", color=0x3498DB
        )
        embed.description = "Welcome to the **mo.copedia**! Explore the parallel worlds and research Chaos Energy to fill out the index and earn rewards!"

        ring_items = [
            k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "smart_ring"
        ]
        insane_rings = [r for r in ring_items if "insane" in r.lower()]
        total_items = len(game_data.ALL_ITEMS) - len(insane_rings)

        total_mobs = len(game_data.MONSTER_REGISTRY)

        total_gear = len(
            [
                k
                for k, v in game_data.ALL_ITEMS.items()
                if v["type"] not in ["title", "skin", "ride"] and k not in insane_rings
            ]
        )

        total_worlds = len(game_data.WORLDS)
        total_missions = len(MISSIONS)
        total_skins = len(
            [k for k, v in game_data.ALL_ITEMS.items() if v["type"] in ["skin", "ride"]]
        )
        total_belts = 5

        found_mobs = len(
            [k for k, v in self.pdata["monsters"].items() if v["k"] > 0 or v["d"] > 0]
        )

        found_gear = len(
            [
                k
                for k in self.pdata["gear"].keys()
                if k not in insane_rings
                and game_data.get_item(k)["type"] not in ["title", "skin", "ride"]
            ]
        )

        found_worlds = len([k for k, v in self.pdata["worlds"].items() if v["v"] > 0])
        found_skins = len(self.pdata["skins"])

        u = dict(database.get_user_data(self.user_id))
        try:
            m_comp = json.loads(u["mission_state"])["completed"]
            found_missions = len(m_comp)
        except:
            found_missions = 0

        stars = u.get("versus_stars", 0)
        found_belts = 0
        for k in ["Yellow", "Blue", "Purple", "Brown", "Black"]:
            if stars >= config.BELT_THRESHOLDS[k]:
                found_belts += 1

        global_total = (
            total_mobs
            + total_gear
            + total_worlds
            + total_missions
            + total_skins
            + total_belts
        )
        global_found = (
            found_mobs
            + found_gear
            + found_worlds
            + found_missions
            + found_skins
            + found_belts
        )

        pct = int((global_found / global_total) * 100) if global_total > 0 else 0
        bar = "🟦" * (pct // 10) + "⬛" * (10 - (pct // 10))

        embed.add_field(
            name="Global Completion",
            value=f"`{bar}` **{pct}%**\n({global_found}/{global_total})",
            inline=False,
        )

        def calc_pct(found, total):
            return int((found / total) * 100) if total > 0 else 0

        breakdown = (
            f"{ICON_MONSTER} Monsters: {found_mobs}/{total_mobs} ({calc_pct(found_mobs, total_mobs)}%)\n"
            f"{ICON_GEAR} Gear: {found_gear}/{total_gear} ({calc_pct(found_gear, total_gear)}%)\n"
            f"{ICON_WORLD} Worlds: {found_worlds}/{total_worlds} ({calc_pct(found_worlds, total_worlds)}%)\n"
            f"{ICON_MISSION} Missions: {found_missions}/{total_missions} ({calc_pct(found_missions, total_missions)}%)\n"
            f"🎨 Skins & Rides: {found_skins}/{total_skins} ({calc_pct(found_skins, total_skins)}%)\n"
            f"{ICON_BELT} Belts: {found_belts}/{total_belts} ({calc_pct(found_belts, total_belts)}%)"
        )

        embed.add_field(name="Breakdown", value=breakdown, inline=False)
        return embed

    def update_components(self):
        self.clear_items()
        self.add_item(CategorySelect(self.bot, self.user_id))


class CategorySelect(Select):
    def __init__(self, bot, user_id):
        options = [
            discord.SelectOption(
                label="Monsters",
                value="monsters",
                emoji=discord.PartialEmoji.from_str(ICON_MONSTER),
            ),
            discord.SelectOption(
                label="Gear",
                value="gear",
                emoji=discord.PartialEmoji.from_str(ICON_GEAR),
            ),
            discord.SelectOption(
                label="Worlds",
                value="worlds",
                emoji=discord.PartialEmoji.from_str(ICON_WORLD),
            ),
            discord.SelectOption(
                label="Missions",
                value="missions",
                emoji=discord.PartialEmoji.from_str(ICON_MISSION),
            ),
            discord.SelectOption(label="Skins & Rides", value="skins", emoji="🎨"),
            discord.SelectOption(
                label="PvP Belts",
                value="belts",
                emoji=discord.PartialEmoji.from_str(ICON_BELT),
            ),
            discord.SelectOption(
                label="Chaos Archive",
                value="archive",
                emoji=discord.PartialEmoji.from_str(ICON_ARCHIVE),
            ),
        ]
        super().__init__(placeholder="Select Category...", options=options, row=0)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        cat = self.values[0]

        if cat == "monsters":
            view = MonsterWorldSelectView(self.bot, self.user_id)
        elif cat == "gear":
            view = GearListView(self.bot, self.user_id)
        elif cat == "worlds":
            view = WorldListView(self.bot, self.user_id)
        elif cat == "missions":
            view = MissionListView(self.bot, self.user_id)
        elif cat == "skins":
            view = SkinsListView(self.bot, self.user_id)
        elif cat == "belts":
            view = BeltsListView(self.bot, self.user_id)
        elif cat == "archive":
            view = ArchiveView(self.bot, self.user_id)

        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class MonsterWorldSelectView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.add_item(MonsterWorldSelect(bot, user_id))
        self.add_item(BackButton())

    def get_embed(self):
        return discord.Embed(
            title=f"{ICON_MONSTER} Monster Index",
            description="Select a region to view local fauna.",
            color=0xE74C3C,
        )


class MonsterWorldSelect(Select):
    def __init__(self, bot, user_id):
        options = [
            discord.SelectOption(
                label="Dragonling World",
                value="dragon",
                emoji=discord.PartialEmoji.from_str(ICON_DRAGON_WORLD),
            ),
            discord.SelectOption(
                label="Royal Bug World",
                value="bug",
                emoji=discord.PartialEmoji.from_str(ICON_BUG_WORLD),
            ),
            discord.SelectOption(
                label="Cat World",
                value="cat",
                emoji=discord.PartialEmoji.from_str(ICON_CAT_WORLD),
            ),
            discord.SelectOption(
                label="Home World",
                value="home",
                emoji=discord.PartialEmoji.from_str(ICON_HOME_WORLD),
            ),
            discord.SelectOption(
                label="Chaos World",
                value="chaos",
                emoji=discord.PartialEmoji.from_str(ICON_CHAOS_WORLD),
            ),
        ]
        super().__init__(placeholder="Select Region...", options=options)
        self.bot = bot
        self.user_id = user_id

    async def callback(self, i):
        if i.user.id != self.user_id:
            return
        view = MonsterListView(self.bot, self.user_id, self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class MonsterListView(View):
    def __init__(self, bot, user_id, region):
        super().__init__(timeout=300)
        self.bot, self.user_id, self.region = bot, user_id, region
        self.pdata = pedia._get_data(user_id)
        self.mobs = self.get_mobs_for_region(region)
        self.add_item(MonsterSelect(bot, user_id, self.mobs, self.pdata["monsters"]))
        self.add_item(BackButton(target=MonsterWorldSelectView))

    def get_mobs_for_region(self, region):
        mapped = []

        chaos_mobs = [
            "Draymor",
            "Overlord",
            "Bug Lord",
            "Smasher",
            "Mega Slime",
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

        for m in game_data.MONSTER_REGISTRY:
            m_lower = m.lower()

            if region == "chaos":
                if m in chaos_mobs or "chaos_" in m_lower or "guardian" in m_lower:
                    mapped.append(m)

            elif region == "dragon":

                if m.startswith("d_") and m not in chaos_mobs:
                    mapped.append(m)

            elif region == "bug":
                if m.startswith("rb_") and m not in chaos_mobs:
                    mapped.append(m)

            elif region == "cat":
                if m.startswith("cw_") and m not in chaos_mobs:
                    mapped.append(m)

            elif region == "home":

                if (
                    not any(x in m_lower for x in ["d_", "rb_", "cw_", "chaos_"])
                    and m not in chaos_mobs
                ):
                    mapped.append(m)

        return sorted(list(set(mapped)))

    def get_embed(self):
        region_map = {
            "dragon": "Dragonling World",
            "bug": "Royal Bug World",
            "cat": "Cat World",
            "home": "Home World",
            "chaos": "Chaos World",
        }
        total = len(self.mobs)

        found = len(
            [m for m in self.mobs if self.pdata["monsters"].get(m, {}).get("k", 0) > 0]
        )
        pct = int((found / total) * 100) if total > 0 else 0
        return discord.Embed(
            title=f"{ICON_MONSTER} {region_map.get(self.region, 'Unknown')} Monsters",
            description=f"**Completion:** {pct}%\nSelect a monster to view Research Tasks.",
            color=0xE74C3C,
        )


class MonsterSelect(Select):
    def __init__(self, bot, user_id, mobs, mob_data):
        options = []
        for m_name in mobs[:25]:

            data = mob_data.get(m_name, {"k": 0})
            is_discovered = data["k"] > 0

            label = utils.format_monster_name(m_name) if is_discovered else "???"

            emoji_str = ICON_MONSTER
            if is_discovered:

                if m_name in config.MOBS:
                    emoji_str = config.MOBS[m_name]
                else:

                    emoji_str = utils.get_emoji(bot, m_name)

            emoji = utils.safe_emoji(emoji_str)
            desc = f"Kills: {data['k']}" if is_discovered else "Undiscovered"

            options.append(
                discord.SelectOption(
                    label=label, value=m_name, emoji=emoji, description=desc
                )
            )

        super().__init__(placeholder="Select Monster...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, interaction):
        if interaction.user.id != self.user_id:
            return
        view = DetailView(self.bot, self.user_id, "monster", self.values[0])
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class GearListView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.add_item(GearTypeSelect(bot, user_id))
        self.add_item(BackButton())

    def get_embed(self):
        return discord.Embed(
            title=f"{ICON_GEAR} Gear Index",
            description="Select a gear type.",
            color=0x95A5A6,
        )


class GearTypeSelect(Select):
    def __init__(self, bot, user_id):
        options = [
            discord.SelectOption(
                label="Weapons",
                value="weapon",
                emoji=discord.PartialEmoji.from_str(ICON_WPN),
            ),
            discord.SelectOption(
                label="Gadgets",
                value="gadget",
                emoji=discord.PartialEmoji.from_str(ICON_GADGET),
            ),
            discord.SelectOption(
                label="Passives",
                value="passive",
                emoji=discord.PartialEmoji.from_str(ICON_PASSIVE),
            ),
            discord.SelectOption(
                label="Elite Modules",
                value="elite_module",
                emoji=discord.PartialEmoji.from_str(ICON_MODULE),
            ),
            discord.SelectOption(
                label="Minor Rings",
                value="ring_minor",
                emoji=discord.PartialEmoji.from_str(ICON_MINOR),
            ),
            discord.SelectOption(
                label="Major Rings",
                value="ring_major",
                emoji=discord.PartialEmoji.from_str(ICON_MAJOR),
            ),
            discord.SelectOption(
                label="Special Rings",
                value="ring_special",
                emoji=discord.PartialEmoji.from_str(ICON_SPECIAL),
            ),
            discord.SelectOption(
                label="Insane Rings",
                value="ring_insane",
                emoji=discord.PartialEmoji.from_str(ICON_INSANE),
            ),
        ]
        super().__init__(placeholder="Filter Type...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, i):
        if i.user.id != self.user_id:
            return
        view = GearItemSelectView(self.bot, self.user_id, self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class GearItemSelectView(View):
    def __init__(self, bot, user_id, gtype):
        super().__init__(timeout=300)
        self.bot, self.user_id, self.gtype = bot, user_id, gtype
        self.pdata = pedia._get_data(user_id)

        items = []
        if gtype.startswith("ring_"):
            sub = gtype.split("_")[1]
            ring_pool = [
                k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "smart_ring"
            ]
            if sub == "minor":
                items = [r for r in ring_pool if "minor" in r.lower()]
            elif sub == "major":
                items = [r for r in ring_pool if "major" in r.lower()]
            elif sub == "insane":
                items = [r for r in ring_pool if "insane" in r.lower()]
            elif sub == "special":
                items = [
                    r
                    for r in ring_pool
                    if "minor" not in r.lower()
                    and "major" not in r.lower()
                    and "insane" not in r.lower()
                ]
        else:
            items = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == gtype]

        self.items = items
        self.add_item(GearSelect(bot, user_id, items, self.pdata["gear"]))
        self.add_item(BackButton(target=GearListView))

    def get_embed(self):
        total = len(self.items)
        found = len([i for i in self.items if i in self.pdata["gear"]])
        pct = int((found / total) * 100) if total > 0 else 0
        return discord.Embed(
            title=f"⚙️ {self.gtype.replace('_', ' ').title()} Index",
            description=f"**Completion:** {pct}%",
            color=0x95A5A6,
        )


class GearSelect(Select):
    def __init__(self, bot, user_id, items, gear_data):
        options = []
        items.sort()
        for iid in items[:25]:
            entry = gear_data.get(iid)
            if entry:
                d = game_data.get_item(iid)
                label = d["name"]
                emoji = utils.safe_emoji(utils.get_emoji(bot, iid))
            else:
                label = "???"
                emoji = discord.PartialEmoji.from_str(ICON_GEAR)
            options.append(discord.SelectOption(label=label, value=iid, emoji=emoji))
        super().__init__(placeholder="Select Item...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, i):
        if i.user.id != self.user_id:
            return
        view = DetailView(self.bot, self.user_id, "gear", self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class WorldListView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.pdata = pedia._get_data(user_id)
        self.add_item(WorldSelect(bot, user_id, self.pdata["worlds"]))
        self.add_item(BackButton())

    def get_embed(self):
        return discord.Embed(
            title=f"{ICON_WORLD} World Index",
            description="Select a world.",
            color=0x2ECC71,
        )


class WorldSelect(Select):
    def __init__(self, bot, user_id, world_data):
        options = []
        for w in game_data.WORLDS:
            entry = world_data.get(w["id"])
            if entry:
                label = w["name"]
                icon = config.WORLD_ICONS.get(w["type"], "🗺️")
                desc = f"Visits: {entry['v']}"
            else:
                label = "???"
                icon = "🔒"
                desc = "Locked"
            options.append(
                discord.SelectOption(
                    label=label,
                    value=w["id"],
                    emoji=utils.safe_emoji(icon),
                    description=desc,
                )
            )
        super().__init__(placeholder="Select World...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, i):
        if i.user.id != self.user_id:
            return
        view = DetailView(self.bot, self.user_id, "world", self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class MissionListView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.u_data = database.get_user_data(user_id)
        self.m_state = json.loads(self.u_data["mission_state"])
        self.add_item(MissionSelect(bot, user_id, self.m_state["completed"]))
        self.add_item(BackButton())

    def get_embed(self):
        return discord.Embed(
            title=f"{ICON_MISSION} Mission Archive",
            description="Select a completed mission to replay or view transcript.",
            color=0xF1C40F,
        )


class MissionSelect(Select):
    def __init__(self, bot, user_id, completed_ids):
        options = []
        for mid in completed_ids:
            m = MISSIONS.get(mid)
            if m:
                options.append(
                    discord.SelectOption(label=m["name"], value=mid, emoji="✅")
                )
        if not options:
            options.append(
                discord.SelectOption(label="No completed missions", value="none")
            )
        super().__init__(placeholder="Select Mission...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, i):
        if i.user.id != self.user_id or self.values[0] == "none":
            return
        view = DetailView(self.bot, self.user_id, "mission", self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class SkinsListView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.pdata = pedia._get_data(user_id)
        self.add_item(SkinSelect(bot, user_id, self.pdata["skins"]))
        self.add_item(BackButton())

    def get_embed(self):
        return discord.Embed(
            title=f"{ICON_SKIN} Skins & Rides",
            description="Track your collection.",
            color=0x9B59B6,
        )


class SkinSelect(Select):
    def __init__(self, bot, user_id, skin_data):
        options = []
        all_cosmetics = [
            k for k, v in game_data.ALL_ITEMS.items() if v["type"] in ["skin", "ride"]
        ]
        for iid in all_cosmetics[:25]:
            entry = skin_data.get(iid)
            d = game_data.get_item(iid)
            if entry or iid in skin_data:
                label = d["name"]
                e_str = utils.get_emoji(bot, iid)
                emoji = utils.safe_emoji(e_str)
            else:
                label = "???"
                emoji = "❓"
            options.append(discord.SelectOption(label=label, value=iid, emoji=emoji))
        super().__init__(placeholder="Select Cosmetic...", options=options)
        self.bot, self.user_id = bot, user_id

    async def callback(self, i):
        if i.user.id != self.user_id:
            return
        view = DetailView(self.bot, self.user_id, "skin", self.values[0])
        await i.response.edit_message(embed=view.get_embed(), view=view)


class BeltsListView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.add_item(BackButton())

    def get_embed(self):
        u = dict(database.get_user_data(self.user_id))
        stars = u.get("versus_stars", 0)
        embed = discord.Embed(title=f"{ICON_BELT} PvP Belt Rack", color=0xF1C40F)
        embed.description = f"**Current Stars:** {stars} ⭐"
        belts = [
            ("Yellow", config.YELLOW_BELT),
            ("Blue", config.BLUE_BELT),
            ("Purple", config.PURPLE_BELT),
            ("Brown", config.BROWN_BELT),
            ("Black", config.BLACK_BELT),
        ]
        for name, icon in belts:
            thresh = config.BELT_THRESHOLDS[name]
            status = "✅ Earned" if stars >= thresh else f"🔒 Need {thresh} Stars"
            embed.add_field(name=f"{icon} {name} Belt", value=status, inline=False)
        return embed


class ArchiveView(View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)
        self.bot, self.user_id = bot, user_id
        self.pdata = pedia._get_data(user_id)
        self.page = 0
        self.add_item(BackButton())

    def get_embed(self):
        logs = self.pdata["archive"]
        embed = discord.Embed(title=f"{ICON_ARCHIVE} Chaos Archive", color=0x9B59B6)
        if not logs:
            embed.description = "No history found."
            return embed
        lines = []
        for l in logs[:10]:
            d = game_data.get_item(l["res"])
            name = d["name"] if d else "Unknown"
            ts = f"<t:{l['ts']}:R>"
            src_icon = config.CHAOS_CORE_EMOJI if l["src"] == "Core" else "📦"
            lines.append(
                f"{src_icon} **{l['src']}** ➔ {utils.get_emoji(self.bot, l['res'])} **{name}** ({l['rar']}) {ts}"
            )
        embed.description = "\n".join(lines)
        return embed


class DetailView(View):
    def __init__(self, bot, user_id, dtype, target_id):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.dtype = dtype
        self.target_id = target_id
        self.pdata = pedia._get_data(user_id)
        self.update_tasks()

        if self.is_discovered():
            if dtype == "gear":
                self.add_item(InspectButton(self.target_id))
            elif dtype == "monster":
                self.add_item(
                    Button(
                        label="View Projects",
                        style=discord.ButtonStyle.primary,
                        disabled=True,
                    )
                )
            elif dtype == "mission":
                self.add_item(ReplayMissionButton(self.target_id))

        self.add_item(BackButton())

    def is_discovered(self):
        if self.dtype == "monster":
            return self.pdata["monsters"].get(self.target_id, {}).get("k", 0) > 0
        if self.dtype == "gear":
            return len(self.pdata["gear"].get(self.target_id, {}).get("mods", [])) > 0
        if self.dtype == "world":
            return self.pdata["worlds"].get(self.target_id, {}).get("v", 0) > 0
        if self.dtype == "skin":
            return self.target_id in self.pdata["skins"]
        if self.dtype == "mission":
            return True
        return True

    def get_corrupted_variant(self, world_id):
        for w in game_data.ELITE_POOL_30 + game_data.ELITE_POOL_50:
            if world_id.replace("shrine_village", "shrine") in w["id"]:
                return True
            base = world_id.split("_")[1] if "_" in world_id else world_id
            if base in w["id"]:
                return True
        return False

    def update_tasks(self):
        self.tasks = []
        if self.dtype == "monster":
            data = self.pdata["monsters"].get(
                self.target_id,
                {"k": 0, "oc": 0, "ch": 0, "mg": 0, "d": 0, "cl": []},
            )
            is_boss = "boss" in self.target_id.lower() or "Overlord" in self.target_id
            self.add_task(
                0,
                f"Hunt {utils.format_monster_name(self.target_id)}",
                data["k"],
                50 if is_boss else 1000,
                data["cl"],
            )
            self.add_task(1, "Hunt Overcharged", data["oc"], 15, data["cl"])
            self.add_task(2, "Hunt Megacharged", data["mg"], 5, data["cl"])
            self.add_task(3, "Hunt Chaos", data["ch"], 10, data["cl"])
            self.add_task(4, "Get defeated by", data["d"], 1, data["cl"])
        elif self.dtype == "gear":
            data = self.pdata["gear"].get(
                self.target_id, {"mods": [], "shop": 0, "l50": 0, "cl": []}
            )
            d = game_data.get_item(self.target_id)
            self.add_task(
                0,
                f"Acquire {d['name']}",
                1 if data["mods"] else 0,
                1,
                data["cl"],
            )
            for i, mod in enumerate(config.HUNT_MODS):
                self.add_task(
                    10 + i,
                    f"Acquire [{mod}]",
                    1 if mod in data["mods"] else 0,
                    1,
                    data["cl"],
                )
            self.add_task(100, "Buy from Shop", data["shop"], 1, data["cl"])
            self.add_task(101, "Upgrade to Lvl 50", data["l50"], 1, data["cl"])
        elif self.dtype == "world":
            data = self.pdata["worlds"].get(
                self.target_id, {"v": 0, "c": 0, "h": 0, "corr": 0, "cl": []}
            )
            w = game_data.get_world(self.target_id)
            self.add_task(0, f"Find Crates in {w['name']}", data["c"], 10, data["cl"])
            self.add_task(1, "Hunt Monsters", data["h"], 10000, data["cl"])
            self.add_task(2, "Visit World", data["v"], 1, data["cl"])
            if self.get_corrupted_variant(self.target_id):
                self.add_task(3, "Visit Corrupted", data["corr"], 1, data["cl"])
        elif self.dtype == "skin":
            data = self.pdata["skins"].get(self.target_id, {"app": 0, "cl": []})
            self.add_task(0, "Apply Skin", data["app"], 1, data["cl"])

        for t in self.tasks:
            if t["curr"] >= t["req"] and not t["claimed"]:
                self.add_item(
                    ClaimTaskButton(self.dtype, self.target_id, t["id"], t["desc"])
                )

    def add_task(self, tid, desc, curr, req, claimed_list):
        self.tasks.append(
            {
                "id": tid,
                "desc": desc,
                "curr": curr,
                "req": req,
                "claimed": tid in claimed_list,
            }
        )

    def get_embed(self):

        if not self.is_discovered():
            name = "???"
            desc = "This entry has not been discovered yet."
            icon_url = None
            thumb = ICON_MONSTER if self.dtype == "monster" else ICON_GEAR
        else:
            name = self.target_id
            if self.dtype == "gear":
                name = game_data.get_item(self.target_id)["name"]
            elif self.dtype == "world":
                name = game_data.get_world(self.target_id)["name"]
            elif self.dtype == "monster":
                name = utils.format_monster_name(self.target_id)
            elif self.dtype == "skin":
                name = game_data.get_item(self.target_id)["name"]
            elif self.dtype == "mission":
                m = MISSIONS.get(self.target_id)
                name = m["name"] if m else self.target_id

            desc = "Progress & Research"
            try:
                raw_icon = utils.get_emoji(self.bot, self.target_id)
                thumb = raw_icon if raw_icon.startswith("<") else None
                icon_url = (
                    f"https://cdn.discordapp.com/emojis/{raw_icon.split(':')[2].replace('>', '')}.png"
                    if thumb
                    else None
                )
            except:
                icon_url = None

        embed = discord.Embed(title=f"📖 {name}", description=desc, color=0xF1C40F)
        if icon_url:
            embed.set_thumbnail(url=icon_url)

        if self.is_discovered():
            if self.dtype == "monster":
                data = self.pdata["monsters"].get(self.target_id, {"k": 0})
                embed.add_field(
                    name="Statistics",
                    value=f"Total Kills: **{data['k']}**",
                    inline=False,
                )
            elif self.dtype == "gear":
                data = self.pdata["gear"].get(self.target_id, {"mods": []})
                mods = ", ".join(data["mods"]) if data["mods"] else "None"
                embed.add_field(name="Found Modifiers", value=mods, inline=False)

                d = game_data.get_item(self.target_id)
                if d.get("quote"):
                    embed.add_field(name="Quote", value=f"*{d['quote']}*", inline=False)
                if d.get("description") and d["description"] != "No info.":
                    embed.add_field(name="Effect", value=d["description"], inline=False)
            elif self.dtype == "mission":
                embed.description = "Replay the story or check objectives."

        task_txt = ""
        for t in self.tasks:
            icon = "✅" if t["claimed"] else ("🟦" if t["curr"] >= t["req"] else "⬛")
            display_desc = t["desc"]
            if not self.is_discovered():
                display_desc = display_desc.replace(
                    utils.format_monster_name(self.target_id), "???"
                )
                display_desc = display_desc.replace(
                    (
                        game_data.get_item(self.target_id)["name"]
                        if self.dtype == "gear"
                        else ""
                    ),
                    "???",
                )

            reward_str = " | 🎁 2k XP + 25 Tokens" if not t["claimed"] else ""
            task_txt += (
                f"{icon} **{display_desc}** ({t['curr']}/{t['req']}){reward_str}\n"
            )

        if task_txt:
            embed.add_field(name="Research Tasks", value=task_txt, inline=False)
        return embed


class ClaimTaskButton(Button):
    def __init__(self, dtype, target, task_id, desc):
        super().__init__(label="Claim", style=discord.ButtonStyle.success)
        self.dtype = dtype
        self.target = target
        self.task_id = task_id

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        pdata = pedia._get_data(self.view.user_id)
        key = (
            "monsters"
            if self.dtype == "monster"
            else (
                "gear"
                if self.dtype == "gear"
                else ("worlds" if self.dtype == "world" else "skins")
            )
        )
        if self.target not in pdata[key]:
            return
        if self.task_id not in pdata[key][self.target]["cl"]:
            pdata[key][self.target]["cl"].append(self.task_id)
            pedia._save_data(self.view.user_id, pdata)
            u = database.get_user_data(self.view.user_id)
            database.update_user_stats(
                self.view.user_id,
                {"xp": u["xp"] + 2000, "merch_tokens": u["merch_tokens"] + 25},
            )
            await interaction.response.send_message(
                f"✅ Claimed! +2,000 XP & +25 Tokens", ephemeral=True
            )
            new_view = DetailView(
                self.view.bot, self.view.user_id, self.dtype, self.target
            )
            await interaction.message.edit(embed=new_view.get_embed(), view=new_view)
        else:
            await interaction.response.send_message("Already claimed.", ephemeral=True)


class ReplayMissionButton(Button):
    def __init__(self, mission_id):
        super().__init__(label="Replay Mission", style=discord.ButtonStyle.success)
        self.mission_id = mission_id

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return

        u_data = database.get_user_data(self.view.user_id)
        if u_data["mission_thread_id"]:
            try:
                t = await self.view.bot.fetch_channel(u_data["mission_thread_id"])
                return await interaction.response.send_message(
                    f"Finish your current chat first: {t.mention}",
                    ephemeral=True,
                )
            except:
                pass

        await interaction.response.defer()
        m_def = MISSIONS.get(self.mission_id)
        if not m_def:
            return await interaction.followup.send("Mission not found.", ephemeral=True)

        name = f"replay-{m_def['name'].replace('#','')}"
        target = interaction.channel
        if isinstance(target, discord.Thread):
            target = target.parent

        try:
            thread = await target.create_thread(
                name=name,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=60,
            )
            await thread.add_user(interaction.user)

            database.update_user_stats(
                self.view.user_id, {"mission_thread_id": thread.id}
            )

            engine = MissionEngine(
                self.view.bot,
                self.view.user_id,
                thread.id,
                specific_mission_id=self.mission_id,
                is_replay=True,
            )
            await engine.progress()

            await interaction.followup.send(
                f"Replay started: {thread.mention}", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"Failed to start replay: {e}", ephemeral=True
            )


class InspectButton(Button):
    def __init__(self, item_id):
        super().__init__(label="Inspect Item", style=discord.ButtonStyle.secondary)
        self.item_id = item_id

    async def callback(self, interaction):
        if interaction.user.id != self.view.user_id:
            return
        await interaction.response.send_message(
            "Select version to inspect:",
            view=PediaInspectSelectView(self.view.bot, self.view.user_id, self.item_id),
            ephemeral=True,
        )


class PediaInspectSelectView(View):
    def __init__(self, bot, user_id, item_id):
        super().__init__(timeout=60)
        self.bot = bot
        self.user_id = user_id
        self.item_id = item_id

        options = []

        u_data = database.get_user_data(user_id)
        lvl, _, _ = utils.get_level_info(u_data["xp"])
        options.append(
            discord.SelectOption(
                label=f"Generic (Lvl {lvl})",
                value="generic",
                description="Standard stats at your level",
            )
        )

        inv = database.get_user_inventory(user_id)
        owned = [i for i in inv if i["item_id"] == item_id]
        owned.sort(key=lambda x: x["level"], reverse=True)

        for o in owned[:20]:
            mod_str = f"[{o['modifier']}]" if o["modifier"] != "Standard" else ""
            options.append(
                discord.SelectOption(
                    label=f"Owned: Lvl {o['level']} {mod_str}",
                    value=str(o["instance_id"]),
                )
            )

        self.add_item(PediaInspectSelect(options, item_id, lvl))


class PediaInspectSelect(Select):
    def __init__(self, options, item_id, player_lvl):
        super().__init__(placeholder="Choose version...", options=options)
        self.item_id = item_id
        self.player_lvl = player_lvl

    async def callback(self, interaction):
        val = self.values[0]
        if val == "generic":

            cog = interaction.client.get_cog("Inventory")
            await cog.inspect.callback(
                cog,
                interaction,
                game_data.get_item(self.item_id)["name"],
                self.player_lvl,
                "Standard",
            )
        else:

            iid = int(val)

            from mo_co.cogs.inventory import DetailedInspectView

            view = DetailedInspectView(interaction.client, interaction.user.id, iid)
            await interaction.response.send_message(
                embed=view.get_embed(), view=view, ephemeral=True
            )


class BackButton(Button):
    def __init__(self, target=MocopediaHomeView):
        super().__init__(label="Back", style=discord.ButtonStyle.secondary, row=4)
        self.target = target

    async def callback(self, i):
        view = self.target(self.view.bot, self.view.user_id)
        await i.response.edit_message(embed=view.get_embed(), view=view)


async def setup(bot):
    await bot.add_cog(Index(bot))

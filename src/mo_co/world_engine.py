import time
import random
import asyncio
from mo_co import config, game_data, utils
from mo_co.game_data import names


NPC_CONFIG = {
    "Luna": {
        "weapon": "staff_of_good_vibes",
        "hp": 5000,
        "emoji": config.BOT_EMOJIS["Luna"],
    },
    "Jax": {
        "weapon": "spinsickle",
        "hp": 8000,
        "emoji": config.BOT_EMOJIS["Jax"],
    },
    "Manny": {
        "weapon": "techno_fists",
        "hp": 6000,
        "emoji": config.BOT_EMOJIS["Manny"],
    },
}


class WorldState:
    def __init__(self, world_id):
        self.world_id = world_id
        self.world_def = game_data.get_world(world_id)

        self.hunters = {}

        self.ghosts = {}

        self.bots = []

        self.boss = None
        self.npc = None

    def add_hunter(self, user_id, name, lvl, emblem, kit_data):

        if user_id in self.ghosts:
            del self.ghosts[user_id]

        self.hunters[user_id] = {
            "name": name,
            "lvl": lvl,
            "emblem": emblem,
            "join_time": time.time(),
            "last_action": time.time(),
            "type": "player",
            "kit_data": kit_data,
        }

    def remove_hunter(self, user_id):
        if user_id in self.hunters:

            data = self.hunters[user_id]
            data["expiry"] = time.time() + random.randint(300, 3600)
            data["type"] = "ghost"
            self.ghosts[user_id] = data
            del self.hunters[user_id]

    def _generate_bot(self):

        if len(self.bots) >= random.randint(0, 3):
            return

        base_lvl = self.world_def.get("unlock_lvl", 1)
        lvl = random.randint(base_lvl, base_lvl + 5)

        name = f"*{names.get_random_bot_name()}*"
        emblem = utils.get_emblem(lvl)

        w_pool = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "weapon"]
        if not w_pool:
            w_pool = ["monster_slugger"]
        w_id = random.choice(w_pool)

        g_pool = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "gadget"]
        if not g_pool:
            g_pool = ["smart_fireworks"]
        g_picks = random.sample(g_pool, k=min(len(g_pool), random.randint(1, 2)))
        gadgets = [{"id": gid, "lvl": lvl, "cd": 0} for gid in g_picks]

        p_pool = [k for k, v in game_data.ALL_ITEMS.items() if v["type"] == "passive"]
        if not p_pool:
            p_pool = ["healthy_snacks"]
        p_picks = random.sample(p_pool, k=min(len(p_pool), random.randint(1, 2)))
        passives = {pid: lvl for pid in p_picks}

        mod = "Standard"
        if random.random() < 0.10:
            mod = random.choice(["Overcharged", "Toxic", "Chaos"])

        kit_data = {
            "weapon": {"id": w_id, "modifier": mod, "level": lvl},
            "gadgets": gadgets,
            "passives": passives,
        }

        bot_data = {
            "name": name,
            "lvl": lvl,
            "emblem": emblem,
            "expiry": time.time() + random.randint(120, 300),
            "type": "bot",
            "kit_data": kit_data,
        }
        self.bots.append(bot_data)

    def cleanup(self):
        now = time.time()

        expired_ghosts = [uid for uid, g in self.ghosts.items() if now > g["expiry"]]
        for uid in expired_ghosts:
            del self.ghosts[uid]

        self.bots = [b for b in self.bots if now < b["expiry"]]

        total_pop = len(self.hunters) + len(self.ghosts) + len(self.bots)
        if total_pop < 3:
            if random.random() < 0.3:
                self._generate_bot()

    def get_nearby_allies(self, exlcude_id=None, count=2):

        candidates = []

        for uid, h in self.hunters.items():
            if uid == exlcude_id:
                continue
            if time.time() - h["last_action"] > 300:
                continue
            candidates.append(
                {
                    "type": "player",
                    "name": h["name"],
                    "lvl": h["lvl"],
                    "emblem": h["emblem"],
                    "kit": h["kit_data"],
                }
            )

        ghost_list = list(self.ghosts.values())
        random.shuffle(ghost_list)
        for g in ghost_list[:2]:
            candidates.append(
                {
                    "type": "ghost",
                    "name": g["name"],
                    "lvl": g["lvl"],
                    "emblem": g["emblem"],
                    "kit": g["kit_data"],
                }
            )

        for b in self.bots:
            candidates.append(
                {
                    "type": "bot",
                    "name": b["name"],
                    "lvl": b["lvl"],
                    "emblem": b["emblem"],
                    "kit": b["kit_data"],
                }
            )

        if self.npc:
            candidates.append(
                {
                    "type": "npc",
                    "name": self.npc["name"],
                    "lvl": 50,
                    "weapon": self.npc["weapon"],
                    "hp": self.npc["hp"],
                    "max_hp": self.npc["max_hp"],
                    "emoji": self.npc["emoji"],
                    "timer": self.npc["timer"],
                }
            )

        if not candidates:
            return []

        return random.sample(candidates, min(len(candidates), count))

    def spawn_boss(self, boss_name, hp, level, duration_sec, tier_id):
        expiry_ts = int(time.time() + duration_sec)
        self.boss = {
            "name": boss_name,
            "max_hp": hp,
            "hp": hp,
            "participants": {},
            "start_time": time.time(),
            "level": level,
            "expiry": expiry_ts,
            "tier": tier_id,
        }
        return self.boss

    def check_boss_timeout(self):
        if self.boss and time.time() > self.boss["expiry"]:
            self.boss = None
            return True
        return False

    def damage_boss(self, amount, user_id):
        if self.check_boss_timeout():
            return False
        if not self.boss:
            return False

        self.boss["hp"] -= amount
        current_dmg = self.boss["participants"].get(user_id, 0)
        self.boss["participants"][user_id] = current_dmg + amount

        if self.boss["hp"] <= 0:
            return True
        return False

    def spawn_npc(self):
        name = random.choice(list(NPC_CONFIG.keys()))
        cfg = NPC_CONFIG[name]
        self.npc = {
            "name": name,
            "max_hp": cfg["hp"],
            "hp": cfg["hp"],
            "timer": 60,
            "weapon": cfg["weapon"],
            "emoji": cfg["emoji"],
        }

    def tick_npc(self, amount=5):
        if not self.npc:
            return False
        if self.npc["hp"] <= 0:
            self.npc = None
            return "DIED"
        self.npc["timer"] -= amount
        if self.npc["timer"] <= 0:
            return "DEPARTED"
        return False

    def damage_npc(self, amount):
        if self.npc:
            self.npc["hp"] = max(0, self.npc["hp"] - amount)


class WorldManager:
    def __init__(self):
        self.worlds = {}

    def get_world(self, world_id):
        if world_id not in self.worlds:
            self.worlds[world_id] = WorldState(world_id)
        return self.worlds[world_id]

    def check_in(self, world_id, user_id, name, lvl, emblem, kit_data):
        ws = self.get_world(world_id)

        total_pop = len(ws.hunters) + len(ws.ghosts) + len(ws.bots)

        if total_pop < 2:

            ws._generate_bot()
            if random.random() < 0.5:
                ws._generate_bot()

        ws.add_hunter(user_id, name, lvl, emblem, kit_data)

    def check_out(self, world_id, user_id):
        if world_id in self.worlds:
            self.worlds[world_id].remove_hunter(user_id)

    async def npc_spawner_loop(self):
        while True:
            await asyncio.sleep(10)

            for wid, ws in self.worlds.items():
                ws.cleanup()

            if random.random() < 0.16:
                active_worlds = [
                    wid for wid, ws in self.worlds.items() if len(ws.hunters) > 0
                ]
                if not active_worlds:
                    continue

                target = random.choice(active_worlds)
                ws = self.worlds[target]

                if not ws.npc and not ws.boss and random.random() < 0.15:
                    ws.spawn_npc()


WORLD_MGR = WorldManager()

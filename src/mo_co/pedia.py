import json
import time
from mo_co import database, game_data


KEY_MONSTERS = "monsters"
KEY_GEAR = "gear"
KEY_WORLDS = "worlds"
KEY_SKINS = "skins"
KEY_ARCHIVE = "archive"


MAX_ARCHIVE_LOGS = 50


def get_default_pedia():
    return {
        KEY_MONSTERS: {},
        KEY_GEAR: {},
        KEY_WORLDS: {},
        KEY_SKINS: {},
        KEY_ARCHIVE: [],
    }


def _get_data(user_id):
    u = database.get_user_data(user_id)
    if not u:
        return get_default_pedia()
    raw = u["pedia_data"]

    if not raw or raw == "{}":
        data = get_default_pedia()

        _backfill_inventory(user_id, data)

        _save_data(user_id, data)
        return data

    try:
        data = json.loads(raw)

        defaults = get_default_pedia()
        changed = False
        for k, v in defaults.items():
            if k not in data:
                data[k] = v
                changed = True
        if changed:
            _save_data(user_id, data)
        return data
    except:

        data = get_default_pedia()
        _save_data(user_id, data)
        return data


def _save_data(user_id, data):
    database.update_user_stats(user_id, {"pedia_data": json.dumps(data)})


def _backfill_inventory(user_id, data):
    inv = database.get_user_inventory(user_id)
    for item in inv:
        iid = item["item_id"]
        mod = item["modifier"]
        lvl = item["level"]

        if iid not in data[KEY_GEAR]:
            data[KEY_GEAR][iid] = {"mods": [], "shop": 0, "l50": 0, "cl": []}

        if mod not in data[KEY_GEAR][iid]["mods"]:
            data[KEY_GEAR][iid]["mods"].append(mod)

        if lvl >= 50:
            data[KEY_GEAR][iid]["l50"] = 1

    u = database.get_user_data(user_id)
    try:
        owned_skins = json.loads(u["owned_skins"])
        for s in owned_skins:
            if s not in data[KEY_SKINS]:
                data[KEY_SKINS][s] = {"app": 0, "cl": []}
    except:
        pass


def track_kill(
    user_id,
    monster_name,
    is_overcharged=False,
    is_chaos=False,
    is_megacharged=False,
):
    data = _get_data(user_id)
    if monster_name not in data[KEY_MONSTERS]:
        data[KEY_MONSTERS][monster_name] = {
            "k": 0,
            "oc": 0,
            "ch": 0,
            "mg": 0,
            "d": 0,
            "cl": [],
        }

    entry = data[KEY_MONSTERS][monster_name]
    entry["k"] += 1
    if is_overcharged:
        entry["oc"] += 1
    if is_chaos:
        entry["ch"] += 1
    if is_megacharged:
        entry["mg"] += 1

    _save_data(user_id, data)


def track_death(user_id, monster_name):
    data = _get_data(user_id)
    if monster_name not in data[KEY_MONSTERS]:
        data[KEY_MONSTERS][monster_name] = {
            "k": 0,
            "oc": 0,
            "ch": 0,
            "mg": 0,
            "d": 0,
            "cl": [],
        }

    data[KEY_MONSTERS][monster_name]["d"] += 1
    _save_data(user_id, data)


def track_gear(user_id, item_id, modifier="Standard", source="drop"):
    data = _get_data(user_id)
    if item_id not in data[KEY_GEAR]:
        data[KEY_GEAR][item_id] = {"mods": [], "shop": 0, "l50": 0, "cl": []}

    entry = data[KEY_GEAR][item_id]
    if modifier not in entry["mods"]:
        entry["mods"].append(modifier)

    if source == "shop":
        entry["shop"] = 1

    _save_data(user_id, data)


def track_upgrade(user_id, item_id, new_level):
    if new_level < 50:
        return
    data = _get_data(user_id)
    if item_id not in data[KEY_GEAR]:
        data[KEY_GEAR][item_id] = {"mods": [], "shop": 0, "l50": 0, "cl": []}

    data[KEY_GEAR][item_id]["l50"] = 1
    _save_data(user_id, data)


def track_world_visit(user_id, world_id):
    data = _get_data(user_id)
    if world_id not in data[KEY_WORLDS]:
        data[KEY_WORLDS][world_id] = {
            "v": 0,
            "c": 0,
            "h": 0,
            "corr": 0,
            "cl": [],
        }

    entry = data[KEY_WORLDS][world_id]
    entry["v"] += 1

    is_corr = False
    for w in game_data.ELITE_POOL_30 + game_data.ELITE_POOL_50:
        if w["id"] == world_id:
            is_corr = True
            break

    if is_corr:
        entry["corr"] += 1
    _save_data(user_id, data)


def track_world_hunt(user_id, world_id, count=1):
    data = _get_data(user_id)
    if world_id not in data[KEY_WORLDS]:
        data[KEY_WORLDS][world_id] = {
            "v": 0,
            "c": 0,
            "h": 0,
            "corr": 0,
            "cl": [],
        }

    data[KEY_WORLDS][world_id]["h"] += count
    _save_data(user_id, data)


def track_crate(user_id, world_id):
    data = _get_data(user_id)
    if world_id not in data[KEY_WORLDS]:
        data[KEY_WORLDS][world_id] = {
            "v": 0,
            "c": 0,
            "h": 0,
            "corr": 0,
            "cl": [],
        }

    data[KEY_WORLDS][world_id]["c"] += 1
    _save_data(user_id, data)


def track_skin(user_id, skin_id):
    data = _get_data(user_id)
    if skin_id not in data[KEY_SKINS]:
        data[KEY_SKINS][skin_id] = {"app": 0, "cl": []}

    data[KEY_SKINS][skin_id]["app"] = 1
    _save_data(user_id, data)


def track_archive(user_id, source_type, result_id, rarity):
    data = _get_data(user_id)
    log = {
        "ts": int(time.time()),
        "src": source_type,
        "res": result_id,
        "rar": rarity,
    }
    data[KEY_ARCHIVE].insert(0, log)
    if len(data[KEY_ARCHIVE]) > MAX_ARCHIVE_LOGS:
        data[KEY_ARCHIVE] = data[KEY_ARCHIVE][:MAX_ARCHIVE_LOGS]

    _save_data(user_id, data)

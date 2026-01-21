import json
import random
import datetime
from mo_co import database, game_data, config


def init_season():
    """Checks for active season, rotates if expired."""
    current = database.get_active_season()
    now = datetime.datetime.now()

    needs_new = False
    if not current:
        needs_new = True
    else:
        end_date = datetime.datetime.fromisoformat(current["end_date"])
        if now > end_date:
            needs_new = True

    if needs_new:
        rotate_season(now)


def rotate_season(start_time, forced_type=None):

    types = config.SEASON_TYPES

    if forced_type:
        chosen = next(
            (t for t in types if t["type"].lower() == forced_type.lower()),
            None,
        )
        if not chosen:
            chosen = types[0]
    else:
        weights = [t["weight"] for t in types]
        chosen = random.choices(types, weights=weights, k=1)[0]

    end_time = start_time + datetime.timedelta(days=14)

    premium_ids = []
    free_ids = []

    if chosen["type"] != "XP_Rush":

        base_pool = [
            k
            for k, v in game_data.ALL_ITEMS.items()
            if v["type"] not in ["smart_ring", "elite_module", "title"]
        ]

        title_pool = [
            k
            for k, v in game_data.ALL_ITEMS.items()
            if v["type"] == "title" and v.get("rarity") == "Rare"
        ]

        pool = []
        if chosen["type"] in ["Standard", "Chaos"]:
            pool = base_pool
        else:
            filter_type = chosen["type"].lower()
            pool = [
                k for k in base_pool if game_data.get_item(k)["type"] == filter_type
            ]

        if not pool:
            pool = base_pool

        if pool:

            gear_needed = 8
            if len(pool) < gear_needed:

                selected_gear = random.choices(pool, k=gear_needed)
            else:
                selected_gear = random.sample(pool, k=gear_needed)

            prem_gear = selected_gear[:4]
            free_gear = selected_gear[4:]

            title_item = None
            if title_pool:
                title_item = random.choice(title_pool)

            premium_ids = prem_gear

            if title_item:
                premium_ids.append(title_item)
            elif len(pool) > gear_needed:

                extra = random.choice(pool)
                premium_ids.append(extra)
            else:

                premium_ids.append(selected_gear[0])

            free_ids = free_gear

    with database.get_connection() as conn:
        conn.execute(
            """INSERT INTO season_config (name, type, start_date, end_date, premium_items, free_items)
                     VALUES (?, ?, ?, ?, ?, ?)""",
            (
                chosen["name"],
                chosen["type"],
                start_time.isoformat(),
                end_time.isoformat(),
                json.dumps(premium_ids),
                json.dumps(free_ids),
            ),
        )

        conn.execute(
            "UPDATE users SET chaos_shards = 0, season_tier_claimed = 0, has_premium_pass = 0"
        )
        conn.commit()

    print(f"SEASON ROTATION: Started {chosen['name']} (Ends {end_time})")


def force_season_type(type_name):
    """Admin tool to force a specific season type immediately."""
    rotate_season(datetime.datetime.now(), forced_type=type_name)


def check_user_season_reset(user_id):
    """Ensures user is synced to current season ID."""
    season = database.get_active_season()
    if not season:
        return

    u = database.get_user_data(user_id)
    if not u:
        return

    if u["season_id_seen"] != season["season_id"]:
        database.update_user_stats(
            user_id,
            {
                "season_id_seen": season["season_id"],
                "season_tier_claimed": 0,
                "has_premium_pass": 0,
            },
        )

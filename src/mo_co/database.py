import sqlite3
import json
import random
import shutil
import os
import time
from datetime import datetime, timedelta
from mo_co import config, game_data
from collections.abc import Mapping

USE_TURSO = False
try:
    import libsql_experimental as libsql

    if config.TURSO_DB_URL and config.TURSO_AUTH_TOKEN:
        USE_TURSO = True
except ImportError:
    pass

DB_PATH = "moco_v2.db"


class RowAdapter(Mapping):
    def __init__(self, cols, values):
        self._cols = cols
        self._values = values
        self._map = {col: val for col, val in zip(cols, values)}

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._map[key]

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._map.keys()


class TursoCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def execute(self, sql, params=()):
        if isinstance(params, list):
            params = tuple(params)
        self._cursor.execute(sql, params)
        return self

    def _make_row(self, values):
        if values is None:
            return None
        cols = [d[0] for d in self._cursor.description]
        return RowAdapter(cols, values)

    def fetchone(self):
        row = self._cursor.fetchone()
        return self._make_row(row)

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._cursor.description]
        return [RowAdapter(cols, r) for r in rows]


class TursoConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None

    def cursor(self):
        return TursoCursorWrapper(self._conn.cursor())

    def execute(self, sql, params=()):
        if isinstance(params, list):
            params = tuple(params)
        cur = self._conn.execute(sql, params)
        return TursoCursorWrapper(cur)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.commit()
        else:
            pass


def get_connection():
    if USE_TURSO:
        raw_conn = libsql.connect(
            database=config.TURSO_DB_URL, auth_token=config.TURSO_AUTH_TOKEN
        )
        return TursoConnectionWrapper(raw_conn)
    else:
        conn = sqlite3.connect(DB_PATH, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn


def init_db():
    conn = get_connection()

    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        display_name TEXT,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        mo_gold INTEGER DEFAULT 0,
        chaos_cores INTEGER DEFAULT 0,
        chaos_kits INTEGER DEFAULT 0,
        chaos_shards INTEGER DEFAULT 0,
        current_hp INTEGER DEFAULT 1600,
        daily_xp_total INTEGER DEFAULT 60000,
        daily_xp_boosted INTEGER DEFAULT 30000,
        last_daily_reset TEXT,
        last_hunt_time TIMESTAMP,
        death_timestamp TIMESTAMP,
        active_jobs TEXT DEFAULT '[]',
        pending_loot TEXT DEFAULT '[]',
        last_job_spawn TIMESTAMP,
        current_title TEXT,
        owned_titles TEXT DEFAULT '[]',
        last_world TEXT,
        project_progress TEXT DEFAULT '{}',
        job_completion_count INTEGER DEFAULT 0,
        season_shards INTEGER DEFAULT 0,
        season_tier_claimed INTEGER DEFAULT 0,
        has_premium_pass BOOLEAN DEFAULT 0,
        season_id_seen INTEGER DEFAULT 0,
        weapon_combo_count INTEGER DEFAULT 0,
        elite_xp INTEGER DEFAULT 0,
        elite_tokens INTEGER DEFAULT 0,
        is_elite BOOLEAN DEFAULT 0,
        owned_skins TEXT DEFAULT '[]',
        equipped_skins TEXT DEFAULT '{}',
        completed_rifts TEXT DEFAULT '[]',
        merch_tokens INTEGER DEFAULT 0,
        completed_dojos TEXT DEFAULT '[]',
        dojo_best_times TEXT DEFAULT '{}',
        daily_purchases TEXT DEFAULT '[]',
        daily_fusions INTEGER DEFAULT 0,
        versus_stars INTEGER DEFAULT 0,
        mission_state TEXT DEFAULT '{"active": "welcome2moco", "step": 0, "prog": 0, "completed": []}',
        mission_thread_id INTEGER DEFAULT 0,
        pedia_data TEXT DEFAULT '{}',
        prestige_level INTEGER DEFAULT 0,
        active_kit_index INTEGER DEFAULT 1,
        cool_zone_rules_accepted BOOLEAN DEFAULT 0,
        account_state TEXT DEFAULT 'LEGIT'
    )"""
    )

    conn.execute(
        """CREATE TABLE IF NOT EXISTS inventory (
        instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_id TEXT,
        level INTEGER DEFAULT 1,
        modifier TEXT,
        acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        locked BOOLEAN DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gear_kits (
        kit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        slot_index INTEGER,
        name TEXT DEFAULT 'Gear Kit',
        weapon_id INTEGER,
        weapon_skin TEXT,
        gadget_1_id INTEGER,
        gadget_1_skin TEXT,
        gadget_2_id INTEGER,
        gadget_2_skin TEXT,
        gadget_3_id INTEGER,
        gadget_3_skin TEXT,
        passive_1_id INTEGER,
        passive_2_id INTEGER,
        passive_3_id INTEGER,
        elite_module_id INTEGER,
        ring_1_id INTEGER,
        ring_2_id INTEGER,
        ring_3_id INTEGER,
        ride_id INTEGER,
        ride_skin TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS inbox_messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sender_text TEXT,
        title TEXT,
        body TEXT,
        rewards TEXT,
        is_claimed BOOLEAN DEFAULT 0,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS loadouts (
        user_id INTEGER PRIMARY KEY,
        weapon_id INTEGER,
        gadget_1_id INTEGER,
        gadget_2_id INTEGER,
        gadget_3_id INTEGER,
        passive_1_id INTEGER,
        passive_2_id INTEGER,
        passive_3_id INTEGER,
        elite_module_id INTEGER,
        ring_1_id INTEGER,
        ring_2_id INTEGER,
        ring_3_id INTEGER,
        ride_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )"""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS guild_config (guild_id INTEGER PRIMARY KEY, spawn_channel_id INTEGER)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS season_config (season_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, start_date TIMESTAMP, end_date TIMESTAMP, premium_items TEXT, free_items TEXT)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS shop_state (
        id INTEGER PRIMARY KEY, 
        last_refresh_date TEXT, 
        daily_seed INTEGER,
        elite_shop_item TEXT,
        elite_refreshes_at TEXT
    )"""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS active_deals (deal_id INTEGER PRIMARY KEY AUTOINCREMENT, item_type TEXT, item_id TEXT, price_type TEXT, price_amount INTEGER, offer_name TEXT, expiration_timestamp TEXT, is_active BOOLEAN DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS active_system_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, multiplier REAL, target_guild_id INTEGER, display_message TEXT, end_timestamp TEXT)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS promo_codes (
        code_key TEXT PRIMARY KEY,
        rewards TEXT,
        description TEXT,
        active BOOLEAN DEFAULT 1,
        expires_at TEXT,
        crate_type TEXT DEFAULT 'default'
    )"""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS promo_history (user_id INTEGER, code_key TEXT, claimed_at TIMESTAMP, PRIMARY KEY (user_id, code_key))"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gm_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        target_id INTEGER,
        action_type TEXT,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS user_blacklist (
        user_id INTEGER PRIMARY KEY,
        reason TEXT,
        expires_at TIMESTAMP,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        banned_by INTEGER
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS guild_blacklist (
        guild_id INTEGER PRIMARY KEY,
        public_reason TEXT,
        staff_reason TEXT,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        banned_by INTEGER
    )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS user_snapshots (
        user_id INTEGER PRIMARY KEY,
        data_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    try:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN active_kit_index INTEGER DEFAULT 1")
    except:
        pass
    try:
        conn.execute(
            "ALTER TABLE users ADD COLUMN cool_zone_rules_accepted BOOLEAN DEFAULT 0"
        )
    except:
        pass
    try:
        conn.execute("ALTER TABLE shop_state ADD COLUMN elite_shop_item TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE shop_state ADD COLUMN elite_refreshes_at TEXT")
    except:
        pass
    try:
        conn.execute("ALTER TABLE users ADD COLUMN account_state TEXT DEFAULT 'LEGIT'")
    except:
        pass

    conn.commit()
    conn.close()


def register_user(user_id, display_name=None):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, display_name FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

        if row:

            if display_name and row["display_name"] != display_name:
                conn.execute(
                    "UPDATE users SET display_name = ? WHERE user_id = ?",
                    (display_name, user_id),
                )
                conn.commit()
            ensure_user_has_kit(user_id)
            return

        now = datetime.utcnow().isoformat()
        start_jobs_time = (datetime.utcnow() - timedelta(hours=12)).isoformat()
        conn.execute(
            """INSERT INTO users (user_id, display_name, current_hp, daily_xp_total, daily_xp_boosted, last_daily_reset, last_job_spawn, owned_titles, project_progress, active_jobs, completed_rifts, owned_skins, equipped_skins, merch_tokens, completed_dojos, dojo_best_times, daily_purchases, daily_fusions, versus_stars, mission_state, mission_thread_id, pedia_data, prestige_level, active_kit_index, cool_zone_rules_accepted, account_state) 
                     VALUES (?, ?, 1600, ?, ?, ?, ?, '["Hunter"]', '{}', '[]', '[]', '[]', '{}', 0, '[]', '{}', '[]', 0, 0, '{"active": "welcome2moco", "step": 0, "prog": 0, "completed": []}', 0, '{}', 0, 1, 0, 'LEGIT')""",
            (
                user_id,
                display_name,
                config.XP_PER_DAY,
                config.XP_BOOST_PER_DAY,
                now,
                start_jobs_time,
            ),
        )
        conn.execute(
            "INSERT INTO inventory (user_id, item_id, modifier, level) VALUES (?, 'monster_slugger', 'Standard', 1)",
            (user_id,),
        )
        starter_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO gear_kits (user_id, slot_index, name, weapon_id) VALUES (?, 1, 'Gear Kit 1', ?)",
            (user_id, starter_id),
        )
        conn.execute(
            "INSERT INTO loadouts (user_id, weapon_id) VALUES (?, ?)",
            (user_id, starter_id),
        )
        conn.commit()


def load_global_cache():
    """Fetches all configuration and blacklists for rapid access."""
    conn = get_connection()
    try:
        config_rows = conn.execute("SELECT key, value FROM system_config").fetchall()
        configs = {r["key"]: r["value"] for r in config_rows}

        user_bans = conn.execute(
            "SELECT user_id, expires_at, reason FROM user_blacklist"
        ).fetchall()
        u_blacklist = {r["user_id"]: dict(r) for r in user_bans}

        guild_bans = conn.execute(
            "SELECT guild_id, public_reason FROM guild_blacklist"
        ).fetchall()
        g_blacklist = {r["guild_id"]: dict(r) for r in guild_bans}

        return configs, u_blacklist, g_blacklist
    finally:
        conn.close()


def get_leaderboard_data(limit=100):
    conn = get_connection()
    try:
        users = conn.execute(
            f"SELECT user_id, display_name, xp, elite_xp, is_elite, prestige_level, current_title FROM users WHERE account_state = 'LEGIT' ORDER BY xp DESC LIMIT {limit}"
        ).fetchall()
        return [dict(u) for u in users]
    finally:
        conn.close()


def ensure_user_has_kit(user_id):
    with get_connection() as conn:
        kits = conn.execute(
            "SELECT count(*) FROM gear_kits WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        if kits == 0:

            old_loadout = conn.execute(
                "SELECT * FROM loadouts WHERE user_id=?", (user_id,)
            ).fetchone()
            u_data = conn.execute(
                "SELECT equipped_skins FROM users WHERE user_id=?", (user_id,)
            ).fetchone()
            if old_loadout:
                skins = json.loads(u_data["equipped_skins"]) if u_data else {}

                def resolve_skin(inst_id):
                    if not inst_id:
                        return None
                    row = conn.execute(
                        "SELECT item_id FROM inventory WHERE instance_id=?", (inst_id,)
                    ).fetchone()
                    if row and row[0] in skins:
                        return skins[row[0]]
                    return None

                conn.execute(
                    """INSERT INTO gear_kits (
                    user_id, slot_index, name, 
                    weapon_id, weapon_skin,
                    gadget_1_id, gadget_1_skin,
                    gadget_2_id, gadget_2_skin,
                    gadget_3_id, gadget_3_skin,
                    passive_1_id, passive_2_id, passive_3_id,
                    elite_module_id,
                    ring_1_id, ring_2_id, ring_3_id,
                    ride_id, ride_skin
                ) VALUES (?, 1, 'Gear Kit 1', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        old_loadout["weapon_id"],
                        resolve_skin(old_loadout["weapon_id"]),
                        old_loadout["gadget_1_id"],
                        resolve_skin(old_loadout["gadget_1_id"]),
                        old_loadout["gadget_2_id"],
                        resolve_skin(old_loadout["gadget_2_id"]),
                        old_loadout["gadget_3_id"],
                        resolve_skin(old_loadout["gadget_3_id"]),
                        old_loadout["passive_1_id"],
                        old_loadout["passive_2_id"],
                        old_loadout["passive_3_id"],
                        old_loadout["elite_module_id"],
                        old_loadout["ring_1_id"],
                        old_loadout["ring_2_id"],
                        old_loadout["ring_3_id"],
                        old_loadout["ride_id"],
                        resolve_skin(old_loadout["ride_id"]),
                    ),
                )
                conn.commit()


def create_new_kit(user_id):
    with get_connection() as conn:
        count = conn.execute(
            "SELECT count(*) FROM gear_kits WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        if count >= 12:
            return False
        used_indices = [
            row[0]
            for row in conn.execute(
                "SELECT slot_index FROM gear_kits WHERE user_id=?", (user_id,)
            ).fetchall()
        ]
        new_index = 1
        while new_index in used_indices:
            new_index += 1
        conn.execute(
            "INSERT INTO gear_kits (user_id, slot_index, name) VALUES (?, ?, ?)",
            (user_id, new_index, f"Gear Kit {new_index}"),
        )
        conn.execute(
            "UPDATE users SET active_kit_index = ? WHERE user_id = ?",
            (new_index, user_id),
        )
        conn.commit()
        return True


def delete_gear_kit(user_id, slot_index):
    with get_connection() as conn:
        count = conn.execute(
            "SELECT count(*) FROM gear_kits WHERE user_id=?", (user_id,)
        ).fetchone()[0]
        if count <= 1:
            return False, "Cannot delete the last kit."
        conn.execute(
            "DELETE FROM gear_kits WHERE user_id=? AND slot_index=?",
            (user_id, slot_index),
        )
        u = conn.execute(
            "SELECT active_kit_index FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if u["active_kit_index"] == slot_index:
            first = conn.execute(
                "SELECT slot_index FROM gear_kits WHERE user_id=? ORDER BY slot_index ASC LIMIT 1",
                (user_id,),
            ).fetchone()
            if first:
                conn.execute(
                    "UPDATE users SET active_kit_index=? WHERE user_id=?",
                    (first["slot_index"], user_id),
                )
        conn.commit()
        return True, "Kit deleted."


def get_active_kit(user_id):
    conn = get_connection()
    u = conn.execute(
        "SELECT active_kit_index FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    idx = u["active_kit_index"] if u else 1
    kit = conn.execute(
        "SELECT * FROM gear_kits WHERE user_id=? AND slot_index=?", (user_id, idx)
    ).fetchone()
    if not kit:
        kit = conn.execute(
            "SELECT * FROM gear_kits WHERE user_id=? ORDER BY slot_index ASC LIMIT 1",
            (user_id,),
        ).fetchone()
        if kit:
            conn.execute(
                "UPDATE users SET active_kit_index=? WHERE user_id=?",
                (kit["slot_index"], user_id),
            )
            conn.commit()
    conn.close()
    return kit


def get_all_kits(user_id):
    conn = get_connection()
    kits = conn.execute(
        "SELECT * FROM gear_kits WHERE user_id=? ORDER BY slot_index ASC", (user_id,)
    ).fetchall()
    conn.close()
    return kits


def update_active_kit(user_id, updates: dict):
    conn = get_connection()
    u = conn.execute(
        "SELECT active_kit_index FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    idx = u["active_kit_index"] if u else 1
    cols = ", ".join([f"{k} = ?" for k in updates.keys()])
    vals = list(updates.values())
    vals.append(user_id)
    vals.append(idx)
    conn.execute(
        f"UPDATE gear_kits SET {cols} WHERE user_id = ? AND slot_index = ?", vals
    )
    conn.commit()
    conn.close()


def delete_user_account(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM loadouts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM gear_kits WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_snapshots WHERE user_id = ?", (user_id,))
        conn.commit()


def get_user_data(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def update_user_stats(user_id, updates: dict):
    with get_connection() as conn:
        cols = ", ".join([f"{k} = ?" for k in updates.keys()])
        vals = list(updates.values())
        vals.append(user_id)
        conn.execute(f"UPDATE users SET {cols} WHERE user_id = ?", vals)
        conn.commit()


def get_user_inventory(user_id):
    conn = get_connection()
    items = conn.execute(
        "SELECT * FROM inventory WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return items


def get_item_instance(instance_id):
    conn = get_connection()
    item = conn.execute(
        "SELECT * FROM inventory WHERE instance_id = ?", (instance_id,)
    ).fetchone()
    conn.close()
    return item


def upgrade_item_level(instance_id, player_level, amount=1):
    with get_connection() as conn:
        item = conn.execute(
            "SELECT level FROM inventory WHERE instance_id = ?", (instance_id,)
        ).fetchone()
        if not item:
            return False
        if item["level"] >= 50:
            return False
        new_lvl = min(50, min(player_level, item["level"] + amount))
        if new_lvl <= item["level"]:
            return False
        conn.execute(
            "UPDATE inventory SET level = ? WHERE instance_id = ?",
            (new_lvl, instance_id),
        )
        conn.commit()
        return True


def add_item_to_inventory(user_id, item_id, modifier="Standard", level=1):
    level = min(50, level)
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, item_id, modifier, level) VALUES (?, ?, ?, ?)",
            (user_id, item_id, modifier, level),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return new_id


def toggle_item_lock(instance_id, lock_state):
    with get_connection() as conn:
        conn.execute(
            "UPDATE inventory SET locked = ? WHERE instance_id = ?",
            (1 if lock_state else 0, instance_id),
        )
        conn.commit()


def delete_inventory_item(instance_id):
    unequip_from_all_slots(None, instance_id, ignore_user_check=True)
    with get_connection() as conn:
        conn.execute("DELETE FROM inventory WHERE instance_id = ?", (instance_id,))
        conn.commit()


def remove_user_skin(user_id, skin_id):
    u = get_user_data(user_id)
    if not u:
        return
    try:
        owned = json.loads(u["owned_skins"])
        if skin_id in owned:
            owned.remove(skin_id)
            update_user_stats(user_id, {"owned_skins": json.dumps(owned)})
    except:
        pass


def unequip_from_all_slots(user_id, instance_id, ignore_user_check=False):
    with get_connection() as conn:
        id_slots = [
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
            "ride_id",
        ]
        for slot in id_slots:
            sql = f"UPDATE gear_kits SET {slot} = NULL WHERE {slot} = ?"
            if not ignore_user_check:
                sql += " AND user_id = ?"
                exec_params = (instance_id, user_id)
            else:
                exec_params = (instance_id,)
            conn.execute(sql, exec_params)
        if not ignore_user_check:
            for slot in id_slots:
                conn.execute(
                    f"UPDATE loadouts SET {slot} = NULL WHERE user_id = ? AND {slot} = ?",
                    (user_id, instance_id),
                )
        else:
            for slot in id_slots:
                conn.execute(
                    f"UPDATE loadouts SET {slot} = NULL WHERE {slot} = ?",
                    (instance_id,),
                )
        conn.commit()


def get_snapshot(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT data_json FROM user_snapshots WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["data_json"])
    return None


def backup_account(user_id):
    conn = get_connection()
    try:
        u = conn.execute(
            "SELECT account_state, * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not u:
            return False, "User not found."
        if u["account_state"] != "LEGIT":
            return False, "Can only backup from LEGIT state."

        inv = conn.execute(
            "SELECT * FROM inventory WHERE user_id = ?", (user_id,)
        ).fetchall()
        kits = conn.execute(
            "SELECT * FROM gear_kits WHERE user_id = ?", (user_id,)
        ).fetchall()

        user_dict = dict(u)
        inv_list = [dict(x) for x in inv]
        kits_list = [dict(x) for x in kits]

        full_data = {"user": user_dict, "inventory": inv_list, "kits": kits_list}

        json_str = json.dumps(full_data)
        conn.execute(
            "INSERT OR REPLACE INTO user_snapshots (user_id, data_json) VALUES (?, ?)",
            (user_id, json_str),
        )
        conn.commit()
        return True, "Backup successful."
    finally:
        conn.close()


def wipe_account_for_mode(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM gear_kits WHERE user_id = ?", (user_id,))
        conn.commit()


def restore_account(user_id):
    snap = get_snapshot(user_id)
    if not snap:
        return False, "No backup found."

    wipe_account_for_mode(user_id)

    with get_connection() as conn:
        u_data = snap["user"]
        keys = u_data.keys()
        u_data["account_state"] = "LEGIT"

        placeholders = ", ".join(["?"] * len(keys))
        columns = ", ".join(keys)
        values = list(u_data.values())

        conn.execute(
            f"INSERT OR REPLACE INTO users ({columns}) VALUES ({placeholders})", values
        )

        for item in snap["inventory"]:
            i_keys = item.keys()
            i_cols = ", ".join(i_keys)
            i_vals = list(item.values())
            i_ph = ", ".join(["?"] * len(i_keys))
            conn.execute(f"INSERT INTO inventory ({i_cols}) VALUES ({i_ph})", i_vals)

        for kit in snap["kits"]:
            k_keys = kit.keys()
            k_cols = ", ".join(k_keys)
            k_vals = list(kit.values())
            k_ph = ", ".join(["?"] * len(k_keys))
            conn.execute(f"INSERT INTO gear_kits ({k_cols}) VALUES ({k_ph})", k_vals)

        conn.execute("DELETE FROM user_snapshots WHERE user_id = ?", (user_id,))
        conn.commit()

    return True, "Account restored to LEGIT state."


def inject_god_mode(user_id):
    wipe_account_for_mode(user_id)
    update_user_stats(
        user_id,
        {
            "xp": 7002000,
            "elite_xp": 100000000,
            "is_elite": 1,
            "prestige_level": 3,
            "mo_gold": 9999999,
            "merch_tokens": 9999999,
            "chaos_cores": 9999,
            "chaos_kits": 9999,
            "chaos_shards": 99999,
            "elite_tokens": 99999,
            "account_state": "GOD",
            "current_title": "Game Master",
        },
    )

    modifiers = ["Standard", "Overcharged", "Megacharged", "Chaos", "Toxic"]
    all_skins = []
    all_titles = []

    with get_connection() as conn:
        for item_id, item_def in game_data.ALL_ITEMS.items():
            itype = item_def["type"]
            if itype in ["skin"]:
                all_skins.append(item_id)
            elif itype == "title":
                all_titles.append(item_def["name"])
            elif itype == "ride":
                conn.execute(
                    "INSERT INTO inventory (user_id, item_id, modifier, level) VALUES (?, ?, ?, ?)",
                    (user_id, item_id, "Standard", 1),
                )
            else:
                if itype in ["weapon", "gadget"]:
                    for mod in modifiers:
                        conn.execute(
                            "INSERT INTO inventory (user_id, item_id, modifier, level) VALUES (?, ?, ?, ?)",
                            (user_id, item_id, mod, 50),
                        )
                else:
                    conn.execute(
                        "INSERT INTO inventory (user_id, item_id, modifier, level) VALUES (?, ?, ?, ?)",
                        (user_id, item_id, "Standard", 50),
                    )

        conn.execute(
            "UPDATE users SET owned_skins = ?, owned_titles = ? WHERE user_id = ?",
            (json.dumps(all_skins), json.dumps(all_titles), user_id),
        )
        conn.execute(
            "INSERT INTO gear_kits (user_id, slot_index, name) VALUES (?, ?, ?)",
            (user_id, 1, "GOD KIT"),
        )
        conn.commit()


def inject_sandbox_mode(user_id):
    wipe_account_for_mode(user_id)
    register_user(user_id)
    update_user_stats(user_id, {"account_state": "SANDBOX"})


def get_promo_code(code_key):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM promo_codes WHERE code_key = ?", (code_key,)
    ).fetchone()
    conn.close()
    return row


def create_promo_code(code_key, rewards, desc, expires_at=None, crate_type="default"):
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO promo_codes 
            (code_key, rewards, description, active, expires_at, crate_type)
            VALUES (?, ?, ?, 1, ?, ?)""",
            (code_key, json.dumps(rewards), desc, expires_at, crate_type),
        )
        conn.commit()


def delete_promo_code(code_key):
    with get_connection() as conn:
        conn.execute("DELETE FROM promo_codes WHERE code_key = ?", (code_key,))
        conn.commit()


def get_shop_state():
    conn = get_connection()
    state = conn.execute("SELECT * FROM shop_state WHERE id=1").fetchone()
    if not state:
        now_ts = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO shop_state (id, last_refresh_date, daily_seed, elite_shop_item, elite_refreshes_at) VALUES (1, ?, ?, ?, ?)",
            (
                datetime.now().date().isoformat(),
                random.randint(1, 100000),
                None,
                now_ts,
            ),
        )
        conn.commit()
        state = conn.execute("SELECT * FROM shop_state WHERE id=1").fetchone()
    conn.close()
    return state


def update_shop_seed(new_seed, date_str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE shop_state SET daily_seed = ?, last_refresh_date = ? WHERE id=1",
            (new_seed, date_str),
        )
        conn.commit()


def get_elite_rotation(all_item_keys):
    state = get_shop_state()
    now = datetime.utcnow()
    current_item = state["elite_shop_item"]
    refresh_at = state["elite_refreshes_at"]
    needs_refresh = False
    if not current_item or not refresh_at:
        needs_refresh = True
    else:
        if now > datetime.fromisoformat(refresh_at):
            needs_refresh = True
    if needs_refresh:
        pool = [
            k
            for k in all_item_keys
            if "ring" not in k and "module" not in k and "skin" not in k
        ]
        new_item = random.choice(pool)
        next_refresh = (now + timedelta(hours=4)).isoformat()
        with get_connection() as conn:
            conn.execute(
                "UPDATE shop_state SET elite_shop_item = ?, elite_refreshes_at = ? WHERE id=1",
                (new_item, next_refresh),
            )
            conn.commit()
        return new_item, next_refresh
    return current_item, refresh_at


def get_active_deals():
    conn = get_connection()
    now_ts = datetime.utcnow().isoformat()
    deals = conn.execute(
        "SELECT * FROM active_deals WHERE is_active=1 AND (expiration_timestamp IS NULL OR expiration_timestamp > ?)",
        (now_ts,),
    ).fetchall()
    conn.close()
    return deals


def prune_expired_deals():
    with get_connection() as conn:
        now_ts = datetime.utcnow().isoformat()
        conn.execute(
            "DELETE FROM active_deals WHERE expiration_timestamp IS NOT NULL AND expiration_timestamp < ?",
            (now_ts,),
        )
        conn.commit()


def get_deal(deal_id):
    conn = get_connection()
    deal = conn.execute(
        "SELECT * FROM active_deals WHERE deal_id=?", (deal_id,)
    ).fetchone()
    conn.close()
    return deal


def add_deal(
    item_type, item_id, price_type, price_amount, offer_name, expiration_timestamp
):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO active_deals (item_type, item_id, price_type, price_amount, offer_name, expiration_timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (
                item_type,
                item_id,
                price_type,
                price_amount,
                offer_name,
                expiration_timestamp,
            ),
        )
        conn.commit()


def update_deal(deal_id, price, ptype, name, expiry):
    with get_connection() as conn:
        conn.execute(
            "UPDATE active_deals SET price_amount=?, price_type=?, offer_name=?, expiration_timestamp=? WHERE deal_id=?",
            (price, ptype, name, expiry, deal_id),
        )
        conn.commit()


def delete_deal(deal_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM active_deals WHERE deal_id = ?", (deal_id,))
        conn.commit()


def add_system_event(e_type, multiplier, guild_id, message, hours):
    end_dt = datetime.utcnow() + timedelta(hours=hours)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO active_system_events (event_type, multiplier, target_guild_id, display_message, end_timestamp) VALUES (?, ?, ?, ?, ?)",
            (e_type, multiplier, guild_id, message, end_dt.isoformat()),
        )
        conn.commit()


def get_active_system_events():
    conn = get_connection()
    now_ts = datetime.utcnow().isoformat()
    events = conn.execute(
        "SELECT * FROM active_system_events WHERE end_timestamp > ?", (now_ts,)
    ).fetchall()
    conn.close()
    return events


def get_config(key, default=None):
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM system_config WHERE key = ?", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else default


def set_config(key, value):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()


def has_claimed_promo(user_id, code_key):
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM promo_history WHERE user_id=? AND code_key=?",
        (user_id, code_key),
    ).fetchone()
    conn.close()
    return bool(row)


def mark_promo_claimed(user_id, code_key):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO promo_history (user_id, code_key, claimed_at) VALUES (?, ?, ?)",
            (user_id, code_key, datetime.utcnow().isoformat()),
        )
        conn.commit()


def send_inbox_message(user_id, sender, title, body, rewards_dict, days_to_expire=30):
    expiry = (datetime.utcnow() + timedelta(days=days_to_expire)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO inbox_messages (user_id, sender_text, title, body, rewards, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, sender, title, body, json.dumps(rewards_dict), expiry),
        )
        conn.commit()


def get_user_inbox(user_id, include_claimed=False):
    conn = get_connection()
    sql = "SELECT * FROM inbox_messages WHERE user_id = ? AND expires_at > datetime('now')"
    if not include_claimed:
        sql += " AND is_claimed = 0"
    sql += " ORDER BY sent_at DESC"

    msgs = conn.execute(sql, (user_id,)).fetchall()
    conn.close()
    return msgs


def get_inbox_message(message_id):
    conn = get_connection()
    msg = conn.execute(
        "SELECT * FROM inbox_messages WHERE message_id = ?", (message_id,)
    ).fetchone()
    conn.close()
    return msg


def mark_message_claimed(message_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE inbox_messages SET is_claimed = 1 WHERE message_id = ?",
            (message_id,),
        )
        conn.commit()


def log_gm_action(admin_id, target_id, action, details):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gm_logs (admin_id, target_id, action_type, details) VALUES (?, ?, ?, ?)",
            (admin_id, target_id, action, json.dumps(details)),
        )
        conn.commit()


def get_gm_logs(limit=20):
    conn = get_connection()
    logs = conn.execute(
        "SELECT * FROM gm_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return logs


def create_backup():
    if USE_TURSO:
        return "BACKUP_SKIPPED_TURSO"
    if not os.path.exists("backups"):
        os.makedirs("backups")
    ts = int(time.time())
    dest = f"backups/moco_backup_{ts}.db"
    src = get_connection()
    dst = sqlite3.connect(dest)
    src.backup(dst)
    dst.close()
    src.close()
    return dest


def blacklist_user(admin_id, user_id, reason, expires_at_iso):
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO user_blacklist (user_id, reason, expires_at, banned_by)
                        VALUES (?, ?, ?, ?)""",
            (user_id, reason, expires_at_iso, admin_id),
        )
        conn.commit()


def is_user_blacklisted(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM user_blacklist WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return False, None
    expires = row["expires_at"]
    if expires == "PERMANENT":
        return True, row
    try:
        if datetime.fromisoformat(expires) > datetime.utcnow():
            return True, row
        else:
            with get_connection() as c:
                c.execute("DELETE FROM user_blacklist WHERE user_id = ?", (user_id,))
                c.commit()
    except:
        pass
    return False, None


def blacklist_guild(admin_id, guild_id, public_reason, staff_reason):
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO guild_blacklist (guild_id, public_reason, staff_reason, banned_by)
                        VALUES (?, ?, ?, ?)""",
            (guild_id, public_reason, staff_reason, admin_id),
        )
        conn.commit()


def is_guild_blacklisted(guild_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM guild_blacklist WHERE guild_id = ?", (guild_id,)
    ).fetchone()
    conn.close()
    if row:
        return True, row
    return False, None


def unblacklist_user(user_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM user_blacklist WHERE user_id = ?", (user_id,))
        conn.commit()


def unblacklist_guild(guild_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM guild_blacklist WHERE guild_id = ?", (guild_id,))
        conn.commit()


def run_raw_sql(query):
    conn = get_connection()
    try:
        cursor = conn.execute(query)
        conn.commit()
        try:
            return cursor.fetchall(), cursor.rowcount
        except:
            return [], cursor.rowcount
    except Exception as e:
        raise e
    finally:
        conn.close()


def get_active_season():
    conn = get_connection()
    season = conn.execute(
        "SELECT * FROM season_config ORDER BY season_id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return season

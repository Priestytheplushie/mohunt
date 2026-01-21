import sqlite3
import os
import sys
import libsql_experimental as libsql               
from dotenv import load_dotenv


load_dotenv()

TURSO_URL = os.getenv("TURSO_DB_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
LOCAL_DB = "moco_v2.db"


TABLES = [
    "users",
    "inventory",
    "gear_kits",
    "loadouts",
    "inbox_messages",
    "season_config",
    "shop_state",
    "active_deals",
    "active_system_events",
    "promo_codes",
    "promo_history",
    "system_config",
    "user_blacklist",
    "guild_blacklist",
    "user_snapshots",
]


def migrate():
    print("--- STARTING MIGRATION TO TURSO ---")

    if not os.path.exists(LOCAL_DB):
        print(f"CRITICAL: {LOCAL_DB} not found in current directory.")
        return

    if not TURSO_URL or not TURSO_TOKEN:
        print("CRITICAL: TURSO credentials missing in env vars.")
        return

    local = sqlite3.connect(LOCAL_DB)
    local.row_factory = sqlite3.Row
    l_cur = local.cursor()

    remote = libsql.connect(database=TURSO_URL, auth_token=TURSO_TOKEN)

    for table in TABLES:
        print(f"Migrating table: {table}...")

        try:

            rows = l_cur.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                print(f"  -> Skipping {table} (Empty)")
                continue

            print(f"  -> Moving {len(rows)} rows...")

            keys = rows[0].keys()
            cols = ", ".join(keys)
            placeholders = ", ".join(["?" for _ in keys])
            query = f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders})"

            count = 0
            remote.execute("BEGIN TRANSACTION")
            for row in rows:
                try:
                    remote.execute(query, tuple(row))
                    count += 1
                except Exception as e:
                    print(f"  -> Error on row: {e}")

            remote.commit()
            print(f"  -> Success: {count} rows inserted.")

        except Exception as e:
            print(f"  -> FAILED to migrate table {table}: {e}")

    print("--- MIGRATION COMPLETE ---")


if __name__ == "__main__":
    migrate()

import os
import requests
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
APPLICATION_ID = os.getenv("APPLICATION_ID")

if not DISCORD_TOKEN or not APPLICATION_ID:
    raise RuntimeError("Missing DISCORD_TOKEN or APPLICATION_ID")

API_BASE = "https://discord.com/api/v10"

headers = {
    "Authorization": f"Bot {DISCORD_TOKEN}",
}

url = f"{API_BASE}/applications/{APPLICATION_ID}/emojis"

res = requests.get(url, headers=headers)
res.raise_for_status()

data = res.json()


emojis = data.get("items", [])

if not emojis:
    print("No application emojis found.")
    exit()

for emoji in emojis:
    emoji_id = emoji.get("id")
    name = emoji.get("name")
    animated = emoji.get("animated", False)

    prefix = "a" if animated else ""
    tag = f"<{prefix}:{name}:{emoji_id}>"

    print(f"Name : {name}")
    print(f"ID   : {emoji_id}")
    print(f"Tag  : {tag}")
    print("-" * 30)

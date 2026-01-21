import discord
from discord import app_commands
from discord.ext import commands
import random
from mo_co import database, config, utils

TIPS = [
    "Doing Daily Jobs regularly is the fastest way to level up.",
    "I give hunters tips, therefore I am.",
    "The right smart rings in the right kits can be DEVASTATING!",
    "The Vitamin Shot gives you a quick heal & attack speed boost.",
    "Your Emblem evolves as you level up!",
    "Overcharged monsters drop higher level Chaos Cores.",
    "Spitters spit. They really nailed the name!",
    "Being near a monster when it dies counts towards your Daily Jobs.",
    "Gadgets have a cooldown after being used.",
    "Blowers attract monsters with their horns.",
    "Complete Missions and level up, unlock new locations and Gear!",
    "Joining hunters in Worlds is a very effective way to grind loot and XP.",
    "Tough Chaos Rifts? Try tweaking your Gear Kit.",
    "Gear Level is capped by your XP Level.",
    "You can find new Smart Rings through Chaos Cores!",
    "Being near a monster gives you some loot.",
    "Make sure you beat all the rifts under 2 mins for best gains!",
    "Chaos Cores upgrade the power of your gear.",
    "Increasing your collector level improves your emblem.",
    "Maximize Gadget DPS! Try the Portable Portal!",
    "Monsters drop XP as loot.",
    "You should write these useful tips down.",
    "Chaos Cores contain pure unbridled CHAOS ENERGY",
    "Problems with large swarms? Try the Spinsickle!",
    "All level ups increase your max health.",
    "In Rifts, you respawn after 15s",
    "Daily Jobs are regularly added to the list.",
    "Have you maxed out any of your weapons yet?",
    "Don’t let the dashers overwhelm you!",
    "Low health Big Reds get berserk.",
    "Daily Jobs, Projects and hunting monsters all give XP!",
    "The Monster Taser is great at dealing with tough monsters.",
    "New Daily Jobs won’t spawn if your list is full.",
    "You can also upgrade your smart rings through Chaos Kits!",
    "Use Splash Heal to heal friendlies.",
    "All loot you see on the ground is yours.",
    "A well timed Dash goes a long way",
    "Check the shop, Manny restocks often!",
    "XP is multiplied by 3x for 30,000 XP each day",
    "You can bank up to 7 days worth of unclaimed XP",
    "Complete DOJO Challenges for more XP",
    "New Dojos, Rifts, and Worlds are added on level up",
    "You can trade items with other Hunters once you reach Level 12! Use /trade.",
    "Got too much junk? Use the Fusion menu in /inventory to recycle gear into Cores!",
    "Visit the Cool Zone to hang out, chat, and test your DPS on dummies.",
    "Certain weapons have special Combo attacks. Check /inspect to learn them!",
    "Equipping a matching skin for your weapon? Stylish AND intimidating.",
    "PvP Belts reset every season. Fight in the /versus arena to rank up!",
    "If you see a mo.co Crate in the wild, grab it fast! It contains Merch Tokens.",
    "The 'Death Ball' strategy involves grouping up to melt bosses instantly.",
    "Don't forget to claim your Project rewards in the /missions menu!",
    "Manny sometimes puts rare mods on items in the Daily Shop.",
    "Upgrading a Smart Ring increases its effect significantly.",
    "Passive items work automatically. You don't need to press a button!",
    "Dashing makes you invincible for a split second. Use it to dodge big hits.",
    "The Boom Box stuns enemies in a wide area. Great for crowd control!",
    "Luna, Jax, and Manny sometimes appear in worlds to help out. Follow them!",
    "Check your /profile to see how close you are to the next reward.",
    "Chaos monsters have random modifiers. Watch out for Toxic ones!",
    "You can have multiple Gear Kits. Use them to switch builds quickly.",
    "The Snow Globe slows down everything in its radius. Chill out!",
    "Some Projects require you to hunt in specific worlds. Check the list!",
]

ELITE_TIPS = [
    "Have you tried the Hard and Nightmare Rifts? They are pretty tough I’ve heard…",
    "HARD/NIGHTMARE Rifts = tougher monsters = more loot.",
    "Smart Rings gain insane power at higher elite levels.",
    "Elite Modules permanently boost your stats, even if you Prestige.",
    "Prestige resets your level but gives you a permanent XP boost and a shiny emblem.",
    "Megacharged World Bosses have shared HP. Call your friends!",
    "If you see a 'World Threat' alert, stop what you're doing and attack!",
    "Elite Projects grant Elite Tokens. Spend them wisely in the Elite Shop.",
    "The Overcharged Amulet helps you find more Elite monsters. Essential for farming.",
    "Nightmare Rifts have reduced stability. Clear them fast or fail!",
    "You can buy 'Rotation' items in the Elite Shop to get gear that isn't dropping.",
    "Insane Rings are... well, insane. They break the rules of physics.",
    "Fighting alongside an NPC like Jax gives you a massive damage boost.",
    "The Elite Conquerer title is only for those who have mastered the shop.",
    "Corrupted Worlds spawn much stronger enemies. Bring your best kit.",
    "Speedrun Projects require optimization. Every second counts.",
    "Your Elite Level determines the max level of your Smart Rings.",
    "Don't face a Megacharged Boss alone unless you have a death wish.",
]


class Ellie(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ellie", description="Get a tip from Ellie")
    async def ellie(self, interaction: discord.Interaction):
        u_data = database.get_user_data(interaction.user.id)
        if not u_data:
            return await interaction.response.send_message(
                "Please register first!", ephemeral=True
            )

        try:
            import json

            m_state = json.loads(u_data["mission_state"])
            if "basictraining" not in m_state.get("completed", []):
                return await interaction.response.send_message(
                    "🚫 **Ellie isn't ready to talk to you yet.** (Finish #basictraining)",
                    ephemeral=True,
                )
        except:
            return await interaction.response.send_message(
                "Error checking mission status.", ephemeral=True
            )

        pool = list(TIPS)
        if bool(u_data["is_elite"]):
            pool.extend(ELITE_TIPS)

        tip = random.choice(pool)

        embed = discord.Embed(description=f"**{tip}**", color=0x3498DB)
        embed.set_author(
            name="Ellie says:",
            icon_url="https://cdn.discordapp.com/emojis/1458981935207547082.png",
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Ellie(bot))

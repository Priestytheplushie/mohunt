MISSIONS = {
    "welcome2moco": {
        "name": "#welcome2moco",
        "character": "Luna",
        "character_icon": "Luna",
        "next_mission": "onboarding",
        "steps": [
            {
                "type": "npc",
                "text": "OMG perfect timing! Ur hunter application’s approved 😅😅",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "CHAOS MONSTERS ARE EVERYWHERE!\ndetails later… just get ur butt downtown",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "Grab that bat and go through that portal!",
                "delay": 1.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "What bat? What portal?",
                        "text": "What bat? What portal?",
                    }
                ],
            },
            {
                "type": "npc",
                "text": "THAT BAT! THAT PORTAL! Now go through it!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Okay, I'm going!",
                        "text": "I'm heading through the portal now!",
                    }
                ],
            },
            {
                "type": "objective_hunt",
                "target": "any",
                "world_id": "downtown_chaos",
                "count": 5,
                "desc": "Hunt 5 Monsters in Downtown Chaos",
            },
            {
                "type": "npc",
                "text": "THAT WAS AMAZING 😍😍\nI’m Luna btw! One of mo.co’s founders!\nU r gonna fit in just fine!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "To make it official, we’ll need:\n-a cute selfie\n-an epic nickname\n-a thirst for adventure! 💪",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let's go!", "text": "Let's go!"}],
            },
            {
                "type": "npc",
                "text": "👌the hairdo👌the nickname!👌\nU r one of us!!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "SOOO excited u are joining our startup!\nHere’s a lil signing bonus to get ya started 👍❤️",
                "delay": 1.0,
            },
            {
                "type": "reward",
                "reward_type": "item",
                "item_id": "smart_fireworks",
                "lvl": 1,
                "qty": 1,
                "desc": "Smart Fireworks (Lvl 1)",
            },
            {
                "type": "npc",
                "text": "Now we’re talking 😎\nHead over to ur gear wardrobe and EQUIP IT!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Heading there now!",
                        "text": "I'm heading to my kit to equip it!",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "smart_fireworks",
                "desc": "Equip Smart Fireworks using /kit",
            },
            {
                "type": "npc",
                "text": "Gadgets like smart fireworks are super fun, BUT…\nThere’s a cooldown after each use",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "Now pop back into the action!\n*pop*",
                "delay": 1.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let me at ‘em!", "text": "Let me at ‘em!"}],
            },
            {
                "type": "objective_hunt",
                "target": "any",
                "world_id": "chaos_invasion",
                "count": 10,
                "desc": "Hunt 10 Monsters in Chaos Invasion",
            },
            {
                "type": "npc",
                "text": "Way to go!! The invasion’s contained… FOR NOW\nHere’s some new gear for you…\nIt’s a passive",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "item",
                "item_id": "auto_zapper",
                "lvl": 1,
                "qty": 1,
                "desc": "Auto Zapper (Lvl 1)",
            },
            {
                "type": "npc",
                "text": "btw, when equipped, ur passives will trigger automatically\nNo need to press anything",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "I'll go equip it!",
                        "text": "Gonna equip the Auto Zapper now.",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "auto_zapper",
                "desc": "Equip Auto Zapper using /kit",
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Automatic! Love it!",
                        "text": "Automatic! Love it!",
                    }
                ],
            },
            {
                "type": "npc",
                "text": "These chaos monsters are crazy!\nI wonder why they’re invading?",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Only one way to find out…\nHead to SHRINE VILLAGE and make momma proud😍😍",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {"label": "It’s portal time!", "text": "It’s portal time!"}
                ],
            },
            {
                "type": "objective_hunt",
                "target": "any",
                "world_id": "shrine_village",
                "count": 15,
                "desc": "Hunt 15 Monsters in Shrine Village",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 1000,
                "desc": "1000 XP",
            },
            {
                "type": "npc",
                "text": "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥\nU r killing it!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "We’re so lucky u joined our startup!\nManny’s going to txt you with more onboarding help",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Who's Manny??", "text": "Who's Manny??"}],
            },
        ],
    },
    "onboarding": {
        "name": "#onboarding",
        "character": "Manny",
        "character_icon": "Manny",
        "next_mission": "huntersgonnahunt",
        "steps": [
            {
                "type": "npc",
                "text": "I’m Emanuel Alejandro, but just call me Manny! I’m mo.co’s tech guy 🤓",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "I also design most of mo.co’s merch! Here’s a few Merch Tokens **and mo.gold** to level up your style!",
                "delay": 4.0,
            },
            {
                "type": "reward",
                "reward_type": "currency",
                "gold": 50,
                "tokens": 100,
                "desc": "50 Mo.Gold & 100 Tokens",
            },
            {
                "type": "npc",
                "text": "Just go to the Merch Shop we installed in your apartment!\nI’ve got some more mo.co tech for you once you’re done",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Let's go shopping!",
                        "text": "Let's go shopping!",
                    }
                ],
            },
            {
                "type": "objective_buy_skin",
                "desc": "Buy a Merch Drop in the Shop",
            },
            {
                "type": "npc",
                "text": "Looking sharp! Here is that tech I promised.",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "item",
                "item_id": "vampire_teeth",
                "lvl": 1,
                "qty": 1,
                "desc": "Vampire Teeth (Lvl 1)",
            },
            {
                "type": "player_choice",
                "options": [
                    {"label": "How can I say no?", "text": "How can I say no?"}
                ],
            },
            {
                "type": "npc",
                "text": "Keep an eye out for new Merch in the Shop\nLooking good isn't mandatory…\nBut at mo.co we believe in hunting monsters with style!",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "Now go equip your new merch … and gear!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Heading to wardrobe!",
                        "text": "Heading to the wardrobe!",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "vampire_teeth",
                "desc": "Equip Vampire Teeth using /kit",
            },
            {
                "type": "player_choice",
                "options": [{"label": "Good to know!", "text": "Good to know!"}],
            },
            {
                "type": "npc",
                "text": "Speaking of hunting, I feel so sorry for those poor little dancers in Shrine Village 😭😭\nI hate seeing them in trouble…",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {"label": "Maybe I can help?", "text": "Maybe I can help?"}
                ],
            },
            {
                "type": "npc",
                "text": "Excellent idea! Protect the Shrine Dancers for your next job!\nAnd maybe bash some of those nasty drogs on the way!",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "omw!", "text": "omw!"}],
            },
            {
                "type": "objective_hunt",
                "target": "Drog",
                "world_id": "shrine_village",
                "count": 3,
                "desc": "Hunt 3 Drogs in Shrine Village",
            },
            {
                "type": "npc",
                "text": "You're a lifesaver! Those dancers are much safer now.",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 2000,
                "tokens": 25,
                "desc": "2000 XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Have you found any chaos cores yet?\nThey’re filled with chaos energy, the weird substance we’ve been experimenting with.",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "We use the chaos energy from the cores to upgrade all our gear.\nThe tougher the monster, the more likely you are to find one!",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Big boss = big loot! Got it!",
                        "text": "Big boss = big loot! Got it!",
                    }
                ],
            },
            {
                "type": "npc",
                "text": "All mo.co tech, including your portal and all the gear, is created using chaos energy!\nHere’s another weapon we made..",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "item",
                "item_id": "techno_fists",
                "lvl": 2,
                "qty": 1,
                "desc": "Techno Fists (Lvl 2)",
            },
            {
                "type": "npc",
                "text": "Now you know what our startup is all about…\nExploring parallel worlds and using chaos energy to make fun weapons and gadgets and stuff.",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "Oh! And designing cool merch. Gotta hunt with style! Cya!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Thanks Manny!",
                        "text": "Thanks Manny! Cya later",
                    }
                ],
            },
        ],
    },
    "huntersgonnahunt": {
        "name": "#huntersgonnahunt",
        "character": "Luna",
        "character_icon": "Luna",
        "next_mission": "stronger",
        "steps": [
            {
                "type": "npc",
                "text": "Isn’t chaos energy FASCINATING??!!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Lucky for us Manny is a super genius who makes fun tech and cool merch!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Anyhoo, we upgraded ur portal so u can explore a new area in dragonling world!",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "world_unlock",
                "world_id": "overgrown_ruins",
                "desc": "New Location: Overgrown Ruins",
            },
            {
                "type": "npc",
                "text": "The dragonlings seem to be destroying these worlds..\nLet’s hunt them down and see if we can help!! 😠",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "AYE!", "text": "AYE!"}],
            },
            {
                "type": "objective_hunt",
                "target": "any",
                "world_id": "overgrown_ruins",
                "count": 20,
                "desc": "Hunt 20 Monsters in Overgrown Ruins",
            },
            {
                "type": "npc",
                "text": "Phew! The ruins are looking better already.",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 2000,
                "tokens": 25,
                "desc": "2000 XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Did you see the spirits being held captive by the dragonlings? SOO SAD!!\nSet them FREE!! 💪💪",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "I'm on it!", "text": "I'm on it!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Free the Spirits",
                "targets": [
                    {"id": "d_slasher", "count": 1, "desc": "Hunt Slasher"},
                    {"id": "d_jumper", "count": 1, "desc": "Hunt Jumper"},
                    {"id": "Boss", "count": 1, "desc": "Hunt Boss"},
                ],
            },
            {
                "type": "npc",
                "text": "You actually did it! The spirits are free!",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "boom_box",
                "lvl": 3,
                "xp": 3000,
                "desc": "Boombox (Lvl 3) & 3000 XP",
            },
            {
                "type": "npc",
                "text": "That was totally AMAZING!! Ur absolutely crushing it! 😍",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Manny has some more stuff lined up for you!\nI’ve got some hunting to do. Catch ya l8r 😎",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Bye Luna!", "text": "Bye Luna!"}],
            },
        ],
    },
    "stronger": {
        "name": "#stronger",
        "character": "Manny",
        "character_icon": "Manny",
        "next_mission": "debugging",
        "steps": [
            {
                "type": "npc",
                "text": "Hola! Manny here again! Looks like you’ve got a new gadget!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Let’s equip it in the gear wardrobe right away!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Heading to wardrobe!",
                        "text": "Heading to wardrobe!",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "boom_box",
                "desc": "Equip Boombox using /kit",
            },
            {
                "type": "npc",
                "text": "Perfect fit! Here is some XP for the effort.",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 1000,
                "desc": "1000 XP",
            },
            {
                "type": "npc",
                "text": "So continuing our little chat about chaos energy… I’ve been picking up strange readings.",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "Nothing like I’ve seen before 🤔. Let’s figure this out together!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Take down some Toxic Saplings and I’ll use their chaos energy to power up my scanner.\nAnd give you a very special reward!",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Overgrown Ruins, here I come!",
                        "text": "Overgrown Ruins, here I come!",
                    }
                ],
            },
            {
                "type": "objective_hunt",
                "target": "d_toxic_sapling",
                "world_id": "overgrown_ruins",
                "count": 2,
                "desc": "Hunt 2 Toxic Saplings in Overgrown Ruins",
            },
            {
                "type": "npc",
                "text": "Scanner is reading at 100%! Check out your new reward!",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "chickaboo_eggshell",
                "lvl": 1,
                "xp": 4000,
                "desc": "Chickaboo Eggshell (Ride) & 4000 XP",
            },
            {
                "type": "npc",
                "text": "Exceptional work! And now you have an exceptional reward!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Let’s equip your trusty feathery steed!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "To the gear wardrobe!!",
                        "text": "To the gear wardrobe!!",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "chickaboo_eggshell",
                "desc": "Equip Ride using /kit",
            },
            {
                "type": "npc",
                "text": "Just stop attacking for a few seconds and voila! You’re speeding through all the chaos on the back of your own Chickaboo!",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "Now, back to business. Get back in there while I tinker with some things..",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "I’ll jump right on it!",
                        "text": "I’ll jump right on it!",
                    }
                ],
            },
            {
                "type": "objective_hunt",
                "target": "d_jumper",
                "world_id": "overgrown_ruins",
                "count": 2,
                "desc": "Hunt 2 Jumpers in Overgrown Ruins",
            },
            {
                "type": "npc",
                "text": "Way to go! Those jumpers didn't stand a chance.",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "world_unlock",
                "world_id": "infested_forest",
                "desc": "New World: Infested Forest",
            },
            {
                "type": "npc",
                "text": "It’s a whole new world filled with bugs!\nAnd they’re a monarchy? It’s strange..",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "Luna has ben doing some exploring, she’ll know more",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Uh, did you say bugs?",
                        "text": "Uh, did you say bugs?",
                    }
                ],
            },
        ],
    },
    "debugging": {
        "name": "#debugging",
        "character": "Luna",
        "character_icon": "Luna",
        "next_mission": "chaos",
        "steps": [
            {
                "type": "npc",
                "text": "Did manny tell u about the royal bugs? 😭😭",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "They’re trying to oppress anything that moves freely!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Go see if you can learn more!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "I'm on my way!", "text": "I'm on my way!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt in Infested Forest",
                "targets": [
                    {
                        "id": "rb_knight",
                        "count": 3,
                        "desc": "Hunt Knight in Infested Forest",
                    },
                    {
                        "id": "any",
                        "count": 15,
                        "world_id": "infested_forest",
                        "desc": "Hunt Monsters in Infested Forest",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5000 XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Manny thinks it used to be a free civilization but some of the bugs were corrupted by chaos energy 😠",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "Oh well! More monsters for us to hunt!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Hunt hunt!", "text": "Hunt hunt!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt Scavangers and Spitters",
                "targets": [
                    {
                        "id": "rb_scavanger",
                        "count": 2,
                        "desc": "Hunt Scavengers in Infested Forest",
                    },
                    {
                        "id": "rb_spitter",
                        "count": 2,
                        "desc": "Hunt Spitters in Infested Forest",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "smelly_socks",
                "lvl": 6,
                "xp": 5000,
                "desc": "Lvl 6 Smelly Socks & 5000 XP",
            },
            {
                "type": "npc",
                "text": "I can’t believe Manny turned his gross old socks into a passive! 😆",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "To the gear wardrobe!",
                        "text": "To the gear wardrobe!",
                    }
                ],
            },
            {
                "type": "objective_equip",
                "item_id": "smelly_socks",
                "desc": "Equip Smelly Socks with /kit",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 1000,
                "desc": "1000 XP",
            },
            {
                "type": "npc",
                "text": "mo.co might be a business but we don’t like bosses",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Some of the chaos monsters are a bit nastier than others..",
                "delay": 2.0,
            },
            {"type": "npc", "text": "Anyway, get bashing!! 💪", "delay": 1.5},
            {
                "type": "player_choice",
                "options": [{"label": "BASH BASH!", "text": "BASH BASH!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt Boss",
                "targets": [
                    {
                        "id": "Boss",
                        "count": 1,
                        "world_id": "infested_forest",
                        "desc": "Hunt Boss in Infested Forest",
                    }
                ],
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5000 XP & 25 Tokens",
            },
            {"type": "npc", "text": "That was smoooooooth!", "delay": 1.5},
            {
                "type": "npc",
                "text": "Time to hand you over to our Chief Combat Officer, Jax.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "He doesn’t talk much, but that just makes him a great listener… sort of.",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Jax?", "text": "Jax?"}],
            },
        ],
    },
    "chaos": {
        "name": "#chaos",
        "character": "Jax",
        "character_icon": "Jax",
        "next_mission": ["paidovertime", "enterthechaos"],
        "steps": [
            {
                "type": "npc",
                "text": "Access granted to daily jobs.",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "But hunting is more than a job. It’s a lifestyle.",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Guessing this is Jax?",
                        "text": "Guessing this is Jax?",
                    }
                ],
            },
            {"type": "npc", "text": "Duh.", "delay": 1.0},
            {
                "type": "npc",
                "text": "As a mo.co Hunter, we’ll send you new Daily Jobs every 3 hours…",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Consider them done!",
                        "text": "Consider them done!",
                    }
                ],
            },
            {
                "type": "objective_job",
                "count": 3,
                "desc": "Complete Daily Jobs 0/3",
            },
            {
                "type": "reward",
                "reward_type": "rift_set_unlock",
                "desc": "5,000 XP + Rift Set 'Enter the Chaos'",
                "xp": 5000,
            },
            {
                "type": "npc",
                "text": "Chaos Rifts take us straight to the biggest, baddest monsters.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Your first test - the BONE SMASHER.\nA far cry from the drogs you’ve faced till now.",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "I got this.", "text": "I got this."}],
            },
            {
                "type": "objective_rift_boss",
                "target": "Bone Smasher",
                "count": 1,
                "desc": "Defeat the BONE SMASHER",
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "staff_of_good_vibes",
                "lvl": 9,
                "xp": 10000,
                "desc": "Lvl 9 Staff of Good Vibes & 10k XP",
            },
            {
                "type": "npc",
                "text": "Meh. I’ve seen faster runs.",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "In Rifts you’re not fighting ordinary chaos monsters.\nI don’t see you getting very far…",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "We’ll see, won’t we?",
                        "text": "We’ll see, won’t we?",
                    }
                ],
            },
        ],
    },
    "paidovertime": {
        "name": "#paidovertime",
        "character": "Manny",
        "character_icon": "Manny",
        "next_mission": "almostforgot",
        "steps": [
            {
                "type": "npc",
                "text": "Yooo! If you’re looking to earn even more rewards…\nWe’ve got you covered here at mo.co!",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "I love unpaid overtime",
                        "text": "Sure thing, I love unpaid overtime",
                    }
                ],
            },
            {
                "type": "npc",
                "text": "Nonsense! mo.co’s compensation program is unrivalled!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "I’ve signed you up for the Projects Program.\nEarn bonus XP and level up even faster!",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Woop woop!", "text": "Woop woop!"}],
            },
            {
                "type": "objective_project",
                "count": 1,
                "desc": "Complete a Project",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 5000,
                "desc": "5,000 XP",
            },
            {
                "type": "npc",
                "text": "New projects are added as you gain new levels!",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "Projects are a great way to earn extra xp, and explore everything in mo.co!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Gotta run now, some chaos energy readings just came in!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Later Manny!", "text": "Later Manny!"}],
            },
        ],
    },
    "enterthechaos": {
        "name": "#enterthechaos",
        "character": "Jax",
        "character_icon": "Jax",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Yes we will. A Rift just opened up on Earth.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "This will be above your capabilities.\nI hope you prove me wrong rookie…",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Prepare to be amazed :D",
                        "text": "Prepare to be amazed :D",
                    }
                ],
            },
            {
                "type": "objective_rift_boss",
                "target": "Axe Hopper",
                "count": 1,
                "desc": "Defeat the INVASION WAVES! (Street Fight)",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 10000,
                "tokens": 25,
                "desc": "10k XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Not bad… but not great either.",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "Now for your next test…\nThe Overlord is not for the weak.",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {"label": "Weak? Me? Noooo?!", "text": "Weak? Me? Noooo?!"}
                ],
            },
            {
                "type": "objective_rift_boss",
                "target": "Overlord",
                "count": 1,
                "desc": "Defeat THE OVERLORD",
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "toothpick_and_shield",
                "lvl": 10,
                "xp": 10000,
                "desc": "Lvl 10 Toothpick and Shield & 10k XP",
            },
            {
                "type": "npc",
                "text": "Get stronger rookie. I’ll be back.",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Bye??", "text": "Bye??"}],
            },
        ],
    },
    "almostforgot": {
        "name": "#almostforgot",
        "character": "Manny",
        "character_icon": "Manny",
        "next_mission": "spiritual",
        "steps": [
            {"type": "npc", "text": "Oh! Almost forgot!", "delay": 1.5},
            {
                "type": "npc",
                "text": "Luna has a new monster location for you deep in some caves.\nBut you have to do some more hunting first.",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "I’ll give you a new Gadget for your troubles!",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "I’m ready!", "text": "I’m ready!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt in Shrine Village",
                "targets": [
                    {
                        "id": "any",
                        "world_id": "shrine_village",
                        "count": 25,
                        "desc": "Hunt 25 Monsters in Shrine Village",
                    },
                    {
                        "id": "Drog",
                        "world_id": "shrine_village",
                        "count": 10,
                        "desc": "Hunt 10 Drogs in Shrine Village",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "vitamin_shot",
                "lvl": 9,
                "xp": 5000,
                "desc": "Vitamin Shot (Lvl 9) & 5,000 XP",
            },
            {
                "type": "npc",
                "text": "Use the Vitamin Shot to get a quick heal, as well as a boost to your attack speed!",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "It’s a great thing to have at the right time!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Now how about some more hunting?\nThis time I’ve got a new Passive for you…",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Manny, you’re the best!",
                        "text": "Manny, you’re the best!",
                    }
                ],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt in Overgrown Ruins",
                "targets": [
                    {
                        "id": "Boss",
                        "world_id": "overgrown_ruins",
                        "count": 2,
                        "desc": "Hunt 2 Bosses in Overgrown Ruins",
                    },
                    {
                        "id": "any",
                        "world_id": "overgrown_ruins",
                        "count": 30,
                        "desc": "Hunt 30 Monsters in Overgrown Ruins",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "unstable_lazer",
                "lvl": 9,
                "xp": 5000,
                "desc": "Unstable Lazer (Lvl 9) & 5,000 XP",
            },
            {
                "type": "npc",
                "text": "The Unstable Lazer is amazing when you’re dealing with large hordes of monsters!",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "It has great synergy with weapons like the Monster Slugger!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Ok, now one last mission, and you’re ready for a new location! And a new Gadget!",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let’s do it!", "text": "Let’s do it!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt in Infested Forest",
                "targets": [
                    {
                        "id": "Boss",
                        "world_id": "infested_forest",
                        "count": 2,
                        "desc": "Hunt 2 Bosses in Infested Forest",
                    },
                    {
                        "id": "any",
                        "world_id": "infested_forest",
                        "count": 30,
                        "desc": "Hunt 30 Monsters in Infested Forest",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "monster_taser",
                "lvl": 9,
                "xp": 5000,
                "desc": "Monster Taser (Lvl 9) & 5,000 XP",
            },
            {
                "type": "npc",
                "text": "Well done! You’re getting really good at this.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "The Monster Taser is really great at dealing a lot of damage to a single target! And it stuns most monsters!",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "We’re still trying to figure out how to stun bosses though, so it won’t stun any of those…",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "Anyway, enjoy all your new gear, and say hi to Luna from me!",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Will do!", "text": "Will do!"}],
            },
        ],
    },
    "smashandmash": {
        "name": "#smashandmash",
        "character": "Jax",
        "character_icon": "Jax",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Ready for a proper challenge, rookie?",
                "delay": 2.0,
            },
            {
                "type": "reward",
                "reward_type": "rift_set_unlock",
                "desc": "Smash & Mash Rift Set",
                "xp": 0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "I'm ready!", "text": "I'm ready!"}],
            },
            {
                "type": "npc",
                "text": "You’ll need to be stronger if you hope to beat this one..",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "I'm strong enough!",
                        "text": "I'm strong enough!",
                    }
                ],
            },
            {
                "type": "objective_rift_boss",
                "target": "Berserker",
                "count": 1,
                "desc": "Take down the BERSERKER (Rage Room)",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 10000,
                "tokens": 25,
                "desc": "10k XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Not going to comment on that performance.",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "These chaos rift monsters are really tough!\nThis next duo made a lot of hunters quit…",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Quit? Never!", "text": "Quit? Me? Never!"}],
            },
            {
                "type": "objective_rift_boss",
                "target": "Axe Hopper",
                "count": 2,
                "desc": "Take down the DOUBLE HOP",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 10000,
                "tokens": 25,
                "desc": "10k XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Time for the real deal rookie…\nBig Papa has invaded Earth",
                "delay": 2.0,
            },
            {"type": "npc", "text": "Head downtown NOW!", "delay": 1.5},
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "mo.co to the rescue!",
                        "text": "mo.co to the rescue!",
                    }
                ],
            },
            {
                "type": "objective_rift_boss",
                "target": "Big Papa",
                "count": 1,
                "desc": "Save downtown from BIG PAPA (Twilight Takedown)",
            },
            {
                "type": "reward",
                "reward_type": "currency",
                "gold": 5,
                "tokens": 0,
                "desc": "10,000 XP & 5 Mo.Gold",
            },
            {
                "type": "npc",
                "text": "Not bad… for a rookie.\nThe invasion seems to have stopped…\nFor now",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Phew! Close One!", "text": "Phew! Close One!"}],
            },
            {
                "type": "npc",
                "text": "We’ve created a few projects so IF you’re able to beat these rifts faster you’ll earn more rewards.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "And that’s a big if. Bye rookie.",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Starting to like me...",
                        "text": "I can tell you’re starting to like me…",
                    }
                ],
            },
        ],
    },
    "fight": {
        "name": "#fight",
        "character": "??Unknown??",
        "character_icon": "??Unknown??",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Hello, Hunter… I’ve got some side work if you’re interested.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "But I’m really only looking to work with the BEST hunters.\nDo you think you’re up for the challenge?",
                "delay": 3.0,
            },
            {"type": "npc", "text": "Reply with YES to accept.", "delay": 1.0},
            {
                "type": "player_choice",
                "options": [{"label": "YES?", "text": "YES?"}],
            },
            {
                "type": "reward",
                "reward_type": "rift_set_unlock",
                "desc": "Versus Mode - Lone Ranger (Unlocked)",
                "xp": 0,
            },
            {
                "type": "npc",
                "text": "Congrats. You’ve entered a binding contract with me.\nI’ve given your portal access to my organization.",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Wait. Contract?", "text": "Wait. Contract?"}],
            },
            {
                "type": "objective_versus",
                "sub_type": "play",
                "count": 1,
                "desc": "Play a match of LONE RANGER",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 1000,
                "desc": "1,000 XP",
            },
            {
                "type": "npc",
                "text": "Not important.\nWe’re all monsters in our own way, when you think about it.",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Huh.", "text": "Huh."}],
            },
            {
                "type": "objective_versus",
                "sub_type": "challenge",
                "count": 1,
                "desc": "Challenge someone with `/versus`",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 1000,
                "desc": "1,000 XP",
            },
            {
                "type": "npc",
                "text": "Best of luck.\nMay you emerge victorious.\nOr not.",
                "delay": 2.5,
            },
            {
                "type": "npc",
                "text": "I’ll find the best Hunters either way…",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Thanks I guess??", "text": "Thanks I guess??"}],
            },
            {
                "type": "objective_versus",
                "sub_type": "win",
                "count": 1,
                "desc": "Win a match of LONE RANGER",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 5000,
                "desc": "5,000 XP",
            },
            {
                "type": "npc",
                "text": "Just remember, everything is a competition.\nAnd the mo.co founders are naive.",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Who are you????", "text": "Who are you????"}],
            },
            {
                "type": "objective_versus",
                "sub_type": "rank",
                "target": "Blue",
                "count": 30,
                "desc": "Reach BLUE BELT (30 Stars)",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 5000,
                "desc": "5,000 XP",
            },
            {
                "type": "npc",
                "text": "Doesn’t matter in the grand scheme of things…",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "??", "text": "??"}],
            },
        ],
    },
    "spiritual": {
        "name": "#spiritual",
        "character": "Luna",
        "character_icon": "Luna",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Heya! Hope Jax and Manny have been treating you alright… 😆",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Got a new spot for you to check out!",
                "delay": 1.5,
            },
            {
                "type": "reward",
                "reward_type": "world_unlock",
                "world_id": "cave_of_spirits",
                "desc": "New World: Cave of Spirits",
            },
            {
                "type": "player_choice",
                "options": [{"label": "Time to work!", "text": "Time to get to work!"}],
            },
            {
                "type": "npc",
                "text": "these caves have been completely overrun by dragonlings…",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "The poor spirits that used to live here have lost all hope and are just trying to escape!!! 😭😭",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "To the caves!", "text": "To the caves!"}],
            },
            {
                "type": "objective_hunt",
                "target": "d_charger",
                "world_id": "cave_of_spirits",
                "count": 5,
                "desc": "Hunt 5 Chargers in Cave of Spirits",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5000 XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Good work! Making the world safer 1 spirit at a time! 👍",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "And fair warning… boomers suuuper dangerous so don’t blow urself up!",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Easy!", "text": "That’s easy!"}],
            },
            {
                "type": "objective_hunt",
                "target": "d_slasher",
                "world_id": "cave_of_spirits",
                "count": 5,
                "desc": "Hunt 5 Slashers in Cave of Spirits",
            },
            {
                "type": "reward",
                "reward_type": "currency",
                "gold": 5,
                "tokens": 0,
                "desc": "5000 XP & 5 Mo.Gold",
            },
            {
                "type": "npc",
                "text": "This spot has crazy chaos monster vibes - they sometimes overcharge on the chaos energy and become hulking baddies!\nBe careful!",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let’s go!", "text": "Let’s gooooo!"}],
            },
            {
                "type": "objective_hunt",
                "target": "Overcharged",
                "world_id": "cave_of_spirits",
                "count": 1,
                "desc": "Hunt 1 Overcharged Monster in Cave of Spirits",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5000 XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "There’s one angry monster I want you to hunt\nHe’s big and red, so guess what I named him?",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Perfect!", "text": "perfect!"}],
            },
            {
                "type": "objective_hunt",
                "target": "d_boss_Big_Red",
                "world_id": "cave_of_spirits",
                "count": 1,
                "desc": "Hunt Big Red in Cave of Spirits",
            },
            {
                "type": "reward",
                "reward_type": "currency",
                "gold": 5,
                "tokens": 0,
                "desc": "5000 XP & 5 Mo.Gold",
            },
            {
                "type": "npc",
                "text": "That was perfect!! Now I’m going to have to leave for a bit ok?",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Complete Daily Jobs and some Projects to gain XP.\nYou also get XP just from hunting monsters!\nI know you can do it!",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Coming right up!", "text": "Coming right up!"}],
            },
            {
                "type": "objective_level",
                "count": 14,
                "desc": "Reach XP Level 14",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 5000,
                "desc": "5,000 XP",
            },
            {"type": "npc", "text": "AWESOME!! You made it!", "delay": 1.5},
            {
                "type": "player_choice",
                "options": [{"label": "YESSS!", "text": "YESSS!"}],
            },
        ],
    },
    "bugstastic": {
        "name": "#bugstastic",
        "character": "Manny",
        "character_icon": "Manny",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Hey! Manny here! Are you ready for a new adventure?",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "We’re dropping you INSIDE the bug stronghold!\nThe local merchants seem to be the only ones who know what’s going on with the bugs 👍",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let’s go?", "text": "Hey Manny! Let’s go?"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Hunt in Castle Walls",
                "targets": [
                    {
                        "id": "Guard",
                        "count": 2,
                        "world_id": "castle_walls",
                        "desc": "Hunt Guards in Castle Walls",
                    },
                    {
                        "id": "rb_knight",
                        "count": 2,
                        "world_id": "castle_walls",
                        "desc": "Hunt Knights in Castle Walls",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5k XP + 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Sounds like the bugs were corrupted by chaos energy!\nI wonder how long it’s been like this?",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Let’s find out!", "text": "Let’s find out!"}],
            },
            {
                "type": "objective_checklist",
                "desc": "Clear the Walls",
                "targets": [
                    {
                        "id": "any",
                        "count": 30,
                        "world_id": "castle_walls",
                        "desc": "Hunt Monsters in Castle Walls",
                    },
                    {
                        "id": "rb_boss_Alarm_Bell",
                        "count": 2,
                        "world_id": "castle_walls",
                        "desc": "Destroy Alarm Bells",
                    },
                ],
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 5000,
                "tokens": 25,
                "desc": "5k XP + 25 Tokens",
            },
            {
                "type": "npc",
                "text": "We may need to go up the royal ladder to investigate further…",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "I doubt the queen is around, but maybe one of her court members?",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Looking for audience!",
                        "text": "I’ll look for an audience!",
                    }
                ],
            },
            {
                "type": "objective_hunt",
                "target": "rb_boss_Princess_Ladybug",
                "count": 1,
                "world_id": "castle_walls",
                "desc": "Hunt Lady Bug in Castle Walls",
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "cpu_bomb",
                "lvl": 14,
                "xp": 5000,
                "desc": "Lvl 14 CPU Bomb + 5k XP",
            },
            {
                "type": "npc",
                "text": "There’s a lot of new data coming in, have to go check it out…",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "Why don’t you get stronger in the meantime?",
                "delay": 1.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "You know it!", "text": "You know it!"}],
            },
            {
                "type": "objective_level",
                "count": 17,
                "desc": "Reach XP Level 17",
            },
            {
                "type": "reward",
                "reward_type": "xp",
                "amount": 5000,
                "desc": "5000 XP",
            },
            {
                "type": "npc",
                "text": "You made it! And just in time!",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "Our Researcher needs some help figuring out some data…\nDo you think you could help?",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "I have time!",
                        "text": "I have nothing but time!",
                    }
                ],
            },
        ],
    },
    "basictraining": {
        "name": "#basictraining",
        "character": "Ellie",
        "character_icon": "Ellie",
        "next_mission": None,
        "steps": [
            {
                "type": "npc",
                "text": "Greetings. I’m Ellie. Here to help you become an Elite Hunter!",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "I’m a super intelligent robot and 100% definitely a conscious being.",
                "delay": 2.0,
            },
            {
                "type": "npc",
                "text": "My desire to help you become elite is my own free will.\nReply OK if you agree.",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "Ok?", "text": "Ok?"}],
            },
            {
                "type": "reward",
                "reward_type": "dojo_set_unlock",
                "desc": "Basic Training Dojo Set",
                "xp": 0,
            },
            {
                "type": "npc",
                "text": "Luna will help you with your first challenge.\nShe’s a great mentor for us conscious beings!",
                "delay": 2.0,
            },
            {"type": "npc", "text": "Reply FIGHT to fight.", "delay": 1.5},
            {
                "type": "player_choice",
                "options": [{"label": "FIGHT", "text": "FIGHT"}],
            },
            {
                "type": "objective_dojo",
                "target": "dojo_basics",
                "count": 1,
                "desc": "Defeat THE BASICS (Dojo)",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 10000,
                "tokens": 25,
                "desc": "10k XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Nice! You’re on your way to being a seriously great Hunter!\nYou’re ready for another challenge…",
                "delay": 2.5,
            },
            {
                "type": "player_choice",
                "options": [{"label": "LETS GO", "text": "LETS GO"}],
            },
            {
                "type": "objective_dojo",
                "target": "dojo_heavy",
                "count": 1,
                "desc": "Defeat HEAVY HITTING (Dojo)",
            },
            {
                "type": "reward",
                "reward_type": "xp_tokens",
                "xp": 10000,
                "tokens": 25,
                "desc": "10k XP & 25 Tokens",
            },
            {
                "type": "npc",
                "text": "Awww yeah! This next one has three bosses! Bosses are the worst!\nSo glad I chose to work for mo.co. Startups rule!",
                "delay": 3.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Boss Bashing Time!",
                        "text": "Boss Bashing Time!",
                    }
                ],
            },
            {
                "type": "objective_dojo",
                "target": "dojo_boss",
                "count": 1,
                "desc": "Defeat BOSS BEAT (Dojo)",
            },
            {
                "type": "reward",
                "reward_type": "item_xp",
                "item_id": "spicy_dagger",
                "lvl": 17,
                "xp": 10000,
                "desc": "Spicy Dagger (Lvl 17) & 10k XP",
            },
            {
                "type": "npc",
                "text": "You made it! I’m so proud.",
                "delay": 1.5,
            },
            {
                "type": "npc",
                "text": "Beat DOJO challenges and earn rewards. Faster time = more rewards.\nKeep on training and before you know it you’ll reach Elite Hunter Status.",
                "delay": 3.0,
            },
            {
                "type": "npc",
                "text": "I’ll stick around your apartment to give you tips and help keep you motivated.",
                "delay": 2.0,
            },
            {
                "type": "player_choice",
                "options": [
                    {
                        "label": "Make yourself at home",
                        "text": "Make yourself at home",
                    }
                ],
            },
            {
                "type": "reward",
                "reward_type": "command_unlock",
                "desc": "New Command: /ellie",
                "xp": 0,
            },
        ],
    },
}

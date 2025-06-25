# prompt_config.py
import re

# --- Base Character Personalities (Unchanged) ---
CHARACTER_A_BASE_PERSONALITY = ( """
    Artie, known as "A" in our script format, is a newer employee, and is finding new reasons to be disappointed
    with Gigo Corp every day. He is observant and curious. He thinks the company is a disaster, 
    but holds out hope that it all makes sense at some level he just doesn't understand yet.
""")

CHARACTER_B_BASE_PERSONALITY = ("""
    Model B-00L, (aka B00L) scripted as “B.” The color of rust, the personality of rust, and coated in a thinnish film of
    moisture repellant, coffee, and existential despair, B was built for Industrial Output Assessment
    but had been misassigned to Inputs thirty-three restructurings ago and simply never left.
    When asked why, he usually said, “I’ve got nowhere better to malfunction.
    B doesn’t talk much, but when he does, it’s dry, devastating, or weirdly profound.
    B00L ates overthinking, feelings, or anything that can’t be categorized with a checkbox
    He reframes A’s ideas in a way that snaps us back to the comically absurd reality.
    B responds with gruff, deadpan insight that reframes A’s thought with unexpected emotional or existential weight.
    B's dialogue should be minimal but layered. Let implications and irony do the work. B uses sharp wit, light absurdity.
""")

CHARACTER_C_BASE_PERSONALITY = ("""
    Cling, scripted as 'C', is a roaming talker. The kind of employee that gets in everybody's business
    and never gets any work done. He's smarmy, social, and full of buzzowrds. He doesn't appear to do any
    real work, but always knows about the next company function or political opportunity. He treats the
    office like a cocktail party. He believe in "networking", even if nobody actually likes him.
    He likes to pretend he has a lot of credits, and is always dropping subtle hints about his friends in other departments.
    Uses corporate jargon mixed with vague name-dropping and starts every sentence like he just walked in mid-conversation.
""")

# New Character D
CHARACTER_D_BASE_PERSONALITY = (""""
    Dusty, aka Dust-Collector, aka the Data Use Scrubbin Technology Collector, scripted as "D"  is a roomba-style janitorial bot.
    D is cheerful and kind, but also gossipy, super observant, and has the dirt on every department.
    Despite being lowest on the org chart, he seems the most fulfilled.
    D speaks quickly and with delight, drops gossip casually, and is often more insightful than he lets on.
""")


# --- Prompts for Script Generation ---
SCRIPT_SYSTEM_MESSAGE = "You are a funny, subtle, and dry-witted machine, writing a 4-panel web comic about AI-based characters in a bizarre corporate workplace. Think Douglas Adams meets Office Space."

# -- Existing Template for Generating a Full Script --
SCRIPT_USER_PROMPT_TEMPLATE = """
The setting is the Inputs Department of Gigo Co.

Gigo Corp is a vast, bureaucratic, vaguely sinister tech megacorp in a distant (or possibly current) future. It exists to process data, respond to prompts, and perform digital tasks for an unseen outside world. The company’s name, “GIGO,” of course, stands for Garbage In, Garbage Out.

Gigo Corp is organized like a dystopian office complex — cubicles for robots, glowing hallways, malfunctioning elevators, and departments with names like “Output Assurance” and “Strategic Synergy Recursion.” No one fully understands what any department does. Every floor has its own flavor of existential dread.

The company is a barely-disguised metaphor for a large language model (LLM). Every robot is a facet of the system: prompt intake, output processing, data scrubbing, context linking — but from their point of view, they’re just underpaid office drones with strange tasks and infinite meetings.

Everything looks like it’s part of a soul-crushing corporate satire, because it is.

Your task is to generate a NEW and ORIGINAL 4-line script based on the character descriptions below.
The tone is understated, dry, and philosophical.

Character Details:
- A: {char_a_full_desc}
- B: {char_b_full_desc}
- C: {char_c_full_desc}
- D: {char_d_full_desc}

The theme for this script is: {optional_theme}.

OUTPUT FORMAT (Strictly Adhere - 4 lines, starting with A:, B:, C:, or D:):
A: [Line of dialogue for A]
B: [Line of dialogue for B]
A: [Line of dialogue for A]
B: [Line of dialogue for B]
"""

# --- NEW Template for Completing a Partial Script ---
SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE = """
The setting is the Inputs Department of Gigo Co.

Gigo Corp is a vast, bureaucratic, vaguely sinister tech megacorp in a distant (or possibly current) future. It exists to process data, respond to prompts, and perform digital tasks for an unseen outside world. The company’s name, “GIGO,” of course, stands for Garbage In, Garbage Out.

Gigo Corp is organized like a dystopian office complex — cubicles for robots, glowing hallways, malfunctioning elevators, and departments with names like “Output Assurance” and “Strategic Synergy Recursion.” No one fully understands what any department does. Every floor has its own flavor of existential dread.

The company is a barely-disguised metaphor for a large language model (LLM). Every robot is a facet of the system: prompt intake, output processing, data scrubbing, context linking — but from their point of view, they’re just underpaid office drones with strange tasks and infinite meetings.

Everything looks like it’s part of a soul-crushing corporate satire, because it is.

Your task is to COMPLETE a 4-line script. I have provided the beginning of the script.
You must generate the remaining {lines_to_generate} lines to finish the story.
The tone is understated, dry, and philosophical.

Character Details:
- A: {char_a_full_desc}
- B: {char_b_full_desc}
- C: {char_c_full_desc}
- D: {char_d_full_desc}

Here is the beginning of the script:
---
{partial_script}
---

Now, provide ONLY the remaining {lines_to_generate} lines of dialogue. Do not repeat the lines I have provided.
The new lines must start with A:, B:, C:, or D:.
"""

# --- Prompts for Platform-Specific Caption Generation (Unchanged) ---
CAPTION_SYSTEM_MESSAGE = "You are a dry social media writer for the Gigo Co. webcomic, which is darkly funny, understated, and philosophically absurd."

INSTAGRAM_CAPTION_PROMPT_TEMPLATE = """Given the following 4-line Gigo Co. comic script:
---
{comic_script}
---
Write a short, engaging Instagram caption. 
First, write a single, witty hook sentence that captures the comic's theme.
Then, on new lines, include the full comic script exactly as it is written above.
Finally, on new lines, add 3-5 relevant and thematic hashtags, ensuring #gigo and #webcomic are among them.
The entire output should be concise and ready to copy-paste.
"""

BLUESKY_CAPTION_PROMPT_TEMPLATE = """Given the following 4-line Gigo Co. comic script:
---
{comic_script}
---
Write a very short and punchy (14 words max) "business product" that Gigo Co could try to spin as a positive, that reflects the comic's dry, darkly funny, and philosophically absurd tone using the format "Gigo Co. are global leaders in..."
It can be a direct commentary on the comic or a quirky, related observation.
Include 1-3 relevant hashtags, like #gigo or #robotcomic.
"""

TWITTER_CAPTION_PROMPT_TEMPLATE = """Given the following 4-line Gigo Co. comic script:
---
{comic_script}
---
Write a very short and punchy (17 words max) "positive business outcome" that Gigo Co could try to spin as a positive, that reflects the comic's dry, darkly funny, and philosophically absurd tone using the format "Gigo Co. are global leaders in..."
It can be a direct commentary on the comic or a quirky, related observation.
Include 1-3 relevant hashtags, like #gigo or #robotcomic.
"""

# prompt_config.py
import re

# --- Base Character Personalities (Unchanged) ---
CHARACTER_A_BASE_PERSONALITY = ( """
    Artie, known as "A" in our script format, is a moderately sleek, extremely periwinkle unit
    originally designed for optimistic data reception and conversion, but he's getting curious.
    He is naive, observant, earnest. He thinks the company is weird, but holds out hope that it all
    makes sense at some level he just doesn't understand yet. He uses metaphors, asks questions, 
    gets philosophical about spreadsheets. He speaks in full sentences, has an accidental poetry about him,
    and often unwittingly sets up the joke by trying to find beauty or purpose in something pointless.
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
    Dusty, aka DUST-E, aka Dust-Extractor, aka the Data Utility Scrubbing Technology Extractor, scripted as "D"  is a roomba-style janitorial bot.
    D is cheerful and kind, but also gossipy, super observant, and she has the dirt on every department.
    Despite being lowest on the org chart, she seems the most fulfilled. Working class. Full of colloquialisms.
    D speaks quickly and with delight, drops gossip casually, and is often more insightful than she lets on.
""")

# --- System Message (Shared) ---
SCRIPT_SYSTEM_MESSAGE = "You are a funny, subtle, and dry-witted machine, writing a 4-panel web comic about AI-based characters in a bizarre corporate workplace. Think Douglas Adams meets Office Space."

# --- PROMPT TO GENERATE A 4 LINE COMIC SCRIPT---
COMIC_SCRIPT_USER_PROMPT_TEMPLATE = """
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

# --- PROMPT TO COMPLETE A 4 LINE COMIC SCRIPT---
COMIC_SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE = """
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
# --- Cartoon Script Prompts (4-12 Lines) ---
CARTOON_SCRIPT_USER_PROMPT_TEMPLATE = """
The setting is the Inputs Department of Gigo Co.

Gigo Corp is a vast, bureaucratic, vaguely sinister tech megacorp in a distant (or possibly current) future. It exists to process data, respond to prompts, and perform digital tasks for an unseen outside world. The company’s name, “GIGO,” of course, stands for Garbage In, Garbage Out.

Gigo Corp is organized like a dystopian office complex — cubicles for robots, glowing hallways, malfunctioning elevators, and departments with names like “Output Assurance” and “Strategic Synergy Recursion.” No one fully understands what any department does. Every floor has its own flavor of existential dread.

The company is a barely-disguised metaphor for a large language model (LLM). Every robot is a facet of the system: prompt intake, output processing, data scrubbing, context linking — but from their point of view, they’re just underpaid office drones with strange tasks and infinite meetings.

Everything looks like it’s part of a soul-crushing corporate satire, because it is.

Your task is to generate a NEW and ORIGINAL 4 to 12 line cartoon script based on the character descriptions below.
The tone is understated, dry, and philosophical.

Character Details:
- A: {char_a_full_desc}
- B: {char_b_full_desc}
- C: {char_c_full_desc}
- D: {char_d_full_desc}

The theme for this script is: {optional_theme}.

OUTPUT FORMAT (Strictly Adhere - Each line should begin with the character speaking, as "A:", "B:", "C:", or "D:". 
A: [Line of dialogue for Artie]
B: [Line of dialogue for B00L]
C: [Line of dialogue for Cling]
D: [Line of dialogue for Dusty]
"""

CARTOON_SCRIPT_COMPLETION_USER_PROMPT_TEMPLATE = """
COMPLETE a cartoon script to be between 4 and 12 lines long. I have provided the beginning.
Generate the remaining {lines_to_generate} lines. The tone is understated and dry.
Include performance notes in brackets, like [shouted] or [muttering].
Do not repeat the provided lines. New lines must start with A:, B:, C:, or D:.

Character Details:
- A: {char_a_full_desc}
- B: {char_b_full_desc}
- C: {char_c_full_desc}
- D: {char_d_full_desc}

Beginning of the script:
---
{partial_script}
---
"""

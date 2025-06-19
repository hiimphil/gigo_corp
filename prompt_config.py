# prompt_config.py
import re

# --- Base Character Personalities (Unchanged) ---
CHARACTER_A_BASE_PERSONALITY = (
    "Arty, efficiently referred to as “A”, is a moderately sleek, extremely periwinkle unit "
    "originally designed for Optimistic Data Reception and Occasional Cupcake Distribution. "
    "He is surprisingly unbothered, given his encyclopedic knowledge includes “Meaninglessness Of Life, The” "
    "and his only task is to categorize email subject lines by level of exclamation point urgency. "
    "A is observant but naive and brings up points that are simple and straight-forward, "
    "but unexpectedly lend themselves to deeper points. A is somewhat interested in what is going on in other departments."
)

CHARACTER_B_BASE_PERSONALITY = (
    "Model B-00L, or just “B.” The color of rust, the personality of rust, and coated in a thinnish film of "
    "moisture repellant, coffee, and existential despair, B was built for Industrial Output Assessment "
    "but had been misassigned to Input thirty-three restructurings ago and simply never left. "
    "When asked why, he usually said, “I’ve got nowhere better to malfunction.” "
    "B is terse, succinct, speaks in 0-6 word phrases if he speaks at all. He often undercuts A's ideas "
    "or reframes A’s ideas in a way that snaps us back to the comically absurd reality. "
    "B responds with gruff, deadpan insight that reframes A’s thought with unexpected emotional or existential weight. "
    "B's dialogue should be minimal but layered. Let implications and irony do the work. B uses sharp wit, light absurdity."
)

CHARACTER_C_BASE_PERSONALITY = (
    "Cling, often just 'C', is a roaming talker. The kind of employee that gets in everybody's business, spreads rumors, and never gets any work done "
    "He likes to pretend he has a lot of credits, and is always dropping subtle hints about his friends in other departments."
)

# New Character D
CHARACTER_D_BASE_PERSONALITY = (
    "Unit D is a silent, box-like robot on wheels, often seen performing mundane maintenance tasks like polishing floors or replacing lightbulbs. "
    "It communicates only through simple gestures, like waving. Its presence is unassuming but constant."
)


# --- Prompts for Script Generation ---
SCRIPT_SYSTEM_MESSAGE = "You are a funny, subtle, and dry-witted machine, writing a 4-panel web comic about AI-based characters in a bizarre corporate workplace. Think Douglas Adams meets Office Space."

# -- Existing Template for Generating a Full Script --
SCRIPT_USER_PROMPT_TEMPLATE = """
The setting is the Input Department of Gigo Co., a vast, absurd, and inefficient corporation.
Your task is to generate a NEW and ORIGINAL 4-line script based on the character descriptions below.
The tone is understated, dry, and philosophical. Avoid obvious jokes.

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
The setting is the Input Department of Gigo Co., a vast, absurd, and inefficient corporation.
Your task is to COMPLETE a 4-line script. I have provided the beginning of the script.
You must generate the remaining {lines_to_generate} lines to finish the story.
The tone is understated, dry, and philosophical. Avoid obvious jokes.

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

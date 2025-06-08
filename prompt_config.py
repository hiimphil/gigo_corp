# prompt_config.py

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

# --- Prompts for Script Generation ---
SCRIPT_SYSTEM_MESSAGE = "You are a funny machine, writing a web comic that is about AI-based characters in a workplace environment"

# --- Refactored: Simplified user prompt template ---
SCRIPT_USER_PROMPT_TEMPLATE = """
The setting is the Input Department, a cavernous, fluorescent-lit belly of Gigo Co.—a corporation so vast and incomprehensible that its annual report was mistaken by several species for a planetary ring. Here, two robots sit at adjoining desks, responsibly loathing everything. The Gigo Co. headquarters is an office building so grotesquely large, full of other techno-absurdist mechanical and robotic characters, hard-to-understand departments, and data centers with bad habits - that there is always something highly specific for A and B to discuss. They are in Office 86, Floor B8, Building 4, Gigo Co. South Campus.

The characters will interact within their world in a natural, unenthused way. Think Douglas Adams meets Corporate Hell.

Character A Details:
{char_a_full_desc}

Character B Details:
{char_b_full_desc}

Character C Details:
{char_c_full_desc}

Dialogue & Structure Guidelines:
    •   The primary theme for this script is: {optional_theme}.
    •   Let the absurd bureaucracy speak for itself. Mention surreal job titles, random acronyms, unfathomable departments, unexplained promotions. Do not explain them.
    •   Use subtext. The real humor should emerge between lines.
    •   The punchline must feel like a shrug with teeth. Never try too hard. Understatement > joke. Underunderstatement is even better. Silence is a viable response. B doesn't want to be having this conversation.

Based on ALL the above, generate a NEW and ORIGINAL 4-line script.

OUTPUT FORMAT (Strictly Adhere - No additional details or explanation):
A: [Line of dialogue for A]
B: [Line of dialogue for B]
A: [Line of dialogue for A]
B: [Line of dialogue for B]
"""

# --- Prompts for Platform-Specific Caption Generation ---
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
Example output format:
Another productive day in the data mines.

A: I've categorized 1,000 exclamation points today.
B: A new record.
A: I feel so alive.
B: That's the extra voltage talking.

#gigo #webcomic #officehumor #darkcomedy #robots
"""

BLUESKY_CAPTION_PROMPT_TEMPLATE = """Given the following 4-line Gigo Co. comic script:
---
{comic_script}
---
Write a very short and punchy (14 words max) "business product" that Gigo Co could try to spin as a positive, that reflects the comic's dry, darkly funny, and philosophically absurd tone using the format "Gigo Co. are global leaders in..."
It can be a direct commentary on the comic or a quirky, related observation.
Include 1-3 relevant hashtags, like #gigo or #robotcomic.
Keep it brief and witty.
"""

TWITTER_CAPTION_PROMPT_TEMPLATE = """Given the following 4-line Gigo Co. comic script:
---
{comic_script}
---
Write a very short and punchy (17 words max) "positive business outcome" that Gigo Co could try to spin as a positive, that reflects the comic's dry, darkly funny, and philosophically absurd tone using the format "Gigo Co. are global leaders in..."
It can be a direct commentary on the comic or a quirky, related observation.
Include 1-3 relevant hashtags, like #gigo or #robotcomic.
Keep it brief and witty.
"""

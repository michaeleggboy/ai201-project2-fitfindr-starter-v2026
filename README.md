# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr is a thrift-shopping agent. You type a plain-language request like
"vintage graphic tee size M or smaller under $25", and it pulls the item
keywords, size, and price ceiling out of it, then searches 40 secondhand
listings from Depop, Poshmark, and thredUp. If something matches, you get the
top listing (title, price, platform), one or two outfits built from the clothes
already in your wardrobe, and a short caption you could post about the find. If
nothing matches, it stops before the outfit step and tells you which filter to
loosen, for example "raise your budget, the closest match starts at $X".


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Search the listings data for items matching a description, and optionally a
size and a price ceiling.
- **Inputs:** `description`: str - keywords describing what the user wants
            - `size`: str | None - a size string to filter by, or None to skip size filtering. Match      case-insensitively, "M" should match "S/M".
            - `max_price`: float | None - maximum price, inclusive, or None to skip price filtering.
- **Returns:** list[dict] - A list of matching listing dicts, best match first.
- **When it has nothing:** Returns an empty list when nothing matches — an empty list, not None, and not an exception. The loop branches on this.

### `suggest_outfit`

- **What it does:** Given a thrifted item and the user's wardrobe, suggest one or two outfits.
- **Inputs:** `new_item`: dict - a listing dict, the item the user is considering.
            - `wardrobe`: dict - a wardrobe dict with an 'items' key holding a list of items. **It may be empty.**
- **Returns:** str - A non-empty string with outfit suggestions.
- **When it has nothing:**  With an empty wardrobe, return general styling advice rather than raising or returning.

### `create_fit_card`

- **What it does:**  Write a short caption someone would actually post about the find.
- **Inputs:** `outfit`: str - the outfit suggestion string from suggest_outfit().
            - `new_item`: dict - the listing dict for the item.
- **Returns:** str - A two-to-four sentence caption.
- **When it has nothing:** If `outfit` is empty or whitespace, return a descriptive message rather than raising.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names what the user could change (raise the budget, try another size, or use broader words) and stop, so `suggest_outfit` and `create_fit_card` never run and `session["fit_card"]` stays `None`. Otherwise put the first result in `session["selected_item"]` and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** The query is parsed by asking the model (`agent.py::_parse_query`, temperature 0) for JSON with `description`, `size`, and `max_price`. If the reply isn't usable JSON, it falls back to regex (`_parse_query_regex`).

**What moves through the session:** query, wardrobe → `session["parsed"]` → `search_listings(description, size, max_price)` → `session["search_results"]` → `session["selected_item"]` (first result) → `suggest_outfit(selected_item, wardrobe)` → `session["outfit_suggestion"]` → `create_fit_card(outfit_suggestion, selected_item)` → `session["fit_card"]`

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   **Outfit 1 (Edgy Streetwear):**
Pair the Graphic Tee with your baggy straight-leg jeans. Tuck the tee in to define the high waist, secure with the brown leather belt, and layer your vintage black denim jacket on top. Finish with your black combat boots and the black crossbody bag.

**Outfit 2 (Casual Grunge):**
Wear the Graphic Tee untucked over your wide-leg khaki trousers for a relaxed, boxy silhouette. Slip on your chunky white sneakers, and throw the oversized grey crewneck sweatshirt over your shoulders as a scarf accent. Accessorize with the black crossbody bag.

  Fit card: Just scored this insanely good 2003 tour bootleg tee on depop for $24 and I am obsessed with the faded graphic. I threw it on with baggy jeans and combat boots for the ultimate edgy streetwear look. The 100 percent cotton feels so perfectly worn-in. 🖤
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; r=search_listings('graphic tee', max_price=30); print(len(r)); [print(l['id'], l['title'], l['size'], l['price'], l['platform']) for l in r]"
7
lst_006 Graphic Tee — 2003 Tour Bootleg Style L 24.0 depop
lst_002 Y2K Baby Tee — Butterfly Print S/M 18.0 depop
lst_033 Vintage Band Tee — Faded Grey L 19.0 depop
lst_015 Vintage Graphic Hoodie — Faded Black L 26.0 depop
lst_017 Mesh Long-Sleeve Top — Black S/M 15.0 depop
lst_012 Oversized Crewneck Sweatshirt — Vintage Navy XL (fits oversized) 20.0 thredUp
lst_011 Low-Rise Cargo Pants — Khaki W29 27.0 poshmark

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "
from tools import suggest_outfit; from utils.data_loader import load_listings, get_empty_wardrobe
item = [l for l in load_listings() if l['id']=='lst_002'][0]
print(suggest_outfit(item, get_empty_wardrobe()))"
**Outfit 1: Y2K Street**
*   Low-rise cargo pants in khaki or olive green
*   Chunky platform flip-flops
*   Rectangular tinted sunglasses
*   Small nylon shoulder bag

**Outfit 2: Sweet & Casual**
*   Light-wash denim mini skirt
*   White canvas low-top sneakers
*   Beaded choker necklace
*   Pastel claw clip
```

```
$ python -c "
from tools import create_fit_card; from utils.data_loader import load_listings
item = [l for l in load_listings() if l['id']=='lst_002'][0]
print(create_fit_card('Y2K baby tee with baggy jeans and white sneakers', item)); print('---'); print(create_fit_card('   ', item))"
Found the cutest little butterfly tee on depop and it is honestly my new favorite thing. Styled it with some baggy jeans and fresh white sneakers for that ultimate early 2000s look. Snagging this for $18 feels like an absolute steal.
---
Couldn't write a fit card: there was no outfit suggestion to caption. Run suggest_outfit first and pass its result in.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1: size filtering**

- *What I asked for:* The starter filtered sizes with `l["size"] == size`, which drops `S/M` when you search for `M`. I gave Claude that line and asked it to "create dynamic size filtering function."
- *What came back:* A `size_matches` helper that split each size into the sizes it covers and compared whole words: `S/M` matched `S` or `M`, `XL (oversized)` counted as `XL`, `US 9` matched `9`, and `medium` matched `M`. It worked on single sizes, but it had no idea what "M or smaller" means, and it only knew sizes as words, so it couldn't tell a letter size from a waist or shoe size. Later, when Claude built the rest of the tools, it swapped this for a model call that asked which size labels fit. That made the search non-deterministic.
- *What I changed:* I had `search_listings` stop calling the model and rebuilt the size check in plain Python (`tools.py::_parse_size` and `_size_fits`). Every size string is now read into one sizing system (letter, waist, shoe, or One Size), and a listing is kept only when it's in the same system as the request and overlaps it. Ranges like "M or smaller", "<=M", and "S, M" now work. I checked that each of those keeps exactly `S`, `M`, `S/M`, and `M/L` from the data, which is the answer key in criterion 5.

**Moment 2: dynamic query parsing**

- *What I asked for:* I had Claude fill in `run_agent()` following my branch rule, with the query parsed by asking the model (my README already said so) instead of by fixed regex.
- *What came back:* `agent.py::_parse_query`, which asks the model at temperature 0 for JSON with `description`, `size`, and `max_price`, and falls back to `_parse_query_regex` if the reply isn't usable JSON. The happy path parsed to `{'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}`. Claude also pointed out that my README branch rule said the loop reports "there are no matches", while the code's message actually names which filter to change (words, size, or budget).
- *What I changed:* I made sure the size comes back as written rather than flattened. `"graphic tee size M or smaller under $25"` parses to `size: 'M or smaller'`, not `'M'`, which would drop every `S` listing. That's the one model step criterion 5 depends on. I also rewrote the README's branch rule and "How the query is parsed" line to match what the code really does, including the regex fallback.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

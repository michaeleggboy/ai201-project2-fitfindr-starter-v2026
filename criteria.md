# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
This is the longest path through the agent, and a model is involved at several
points along it: parsing the query, writing the outfit suggestion, and writing
the fit card. Any one of those can occasionally return a malformed or incomplete
answer, such as a parse that leaves out a field or turns the size into something
the search can't read, and the loop then stops early even though the query was
fine. So I allow one miss in 5 rather than demanding 5 of 5. I don't go lower
than 4 because this is the main thing the agent exists to do. If a valid query
fails twice in five runs, the handoffs between tools are broken, and that isn't
just model randomness.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path has only one decision point, and it is plain Python: if
`session["search_results"]` is empty, the loop returns before calling
`suggest_outfit`. No model chooses whether to continue, so no randomness can
push it past the check, and anything below 5 of 5 is a bug in the loop

---

## 3. Something about state

On a matching query, the listing `id` passed into `suggest_outfit` and the
listing `id` passed into `create_fit_card` (both logged in the trace) are equal
to `session["selected_item"]["id"]`, which is equal to
`session["search_results"][0]["id"]` — in 5 of 5 tries.

**Why this target:**
Picking the item and passing it along is plain Python with no model involved, so
nothing random can get in the way and anything below 5 of 5 is a bug. If the
loop hands over the wrong variable, such as a stale item or the whole results
list, `suggest_outfit` still returns a reasonable outfit for *something*. It
looks like a tool problem when it is really a state problem. Comparing `id`s at
each handoff catches it, and titles would not, since two listings can have
similar titles.

---

## 4. Something about the fit card

Running the same matching query 5 times, a fit card passes when it states the
selected item's exact price (`$18` or `$18.00` both count) and its platform, and
is 2–4 sentences long. At least 4 of 5 cards pass.

**Why this target:**
The wording can change between runs, but the facts can't. The price and platform
are in the listing, so a card that leaves them out or gets them wrong has failed
at its job. I allow 4 of 5 rather than 5 of 5 because the model will sometimes
write a fifth sentence or round a price.

---

## 5. Your choice

For the query `"graphic tee size M or smaller under $25"`, `session["parsed"]`
has `max_price == 25.0` and a `size` that keeps the "M or smaller" meaning
(`"M or smaller"`, `"<=M"`, or `"S, M"` all count; plain `"M"` does not). The
size check is plain Python inside `search_listings`, with no model call. It reads
each listing's `size` string into a sizing system (letter, waist, shoe, or One
Size) and keeps it only if it shares a size with the request.

Scored against this answer key built from the sizes in `data/listings.json`:

- **Must keep:** `S`, `M`, `S/M`, `M/L` (`M/L` still covers M)
- **Must drop:** `L`, `L/XL`, `XL`, `XL (oversized)`, `XL (fits oversized)`,
  any `One Size…`, any waist size (`W28`, `W30 L30`, …), any shoe size (`US 8`, …)

A run passes when every listing in `session["search_results"]` costs $25.00 or
less, no listing breaks the answer key, and the list includes `lst_002` (S/M
graphic tee, $18), the one listing that should match. At least 4 of 5 runs pass.

**Why this target:**
The sizes in the data are messy: letter sizes, ranges like `S/M`, notes like
`XL (fits oversized)`, waist sizes, and shoe sizes. Keeping the size check in
plain Python makes `search_listings` deterministic and safe to expose over MCP:
given the same parsed size, it always returns the same listings. The one place
the model can still go wrong is the parse. It sometimes flattens "M or smaller"
to plain `"M"`, which drops `S`, so I allow one miss in 5. I don't allow two,
because the search side can't vary, so two misses would mean the parse prompt
is unclear, not just random. Requiring `lst_002` keeps the agent from passing
by dropping everything.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

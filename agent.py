"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import json
import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import generate, ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    next_step = "parse"
    count = 0
    while next_step != "done":
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = _parse_query(session["query"])
            next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], parsed["size"], parsed["max_price"],
            )
            # THE BRANCH: nothing matched → explain what to change, and stop.
            if not session["search_results"]:
                session["error"] = _no_results_message(session["parsed"])
                next_step = "done"
            else:
                session["selected_item"] = session["search_results"][0]
                next_step = "suggest"

        elif next_step == "suggest":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"],
            )
            next_step = "card"

        elif next_step == "card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"],
            )
            next_step = "done"

    return session


# ── query parsing ─────────────────────────────────────────────────────────────

_PARSE_SYSTEM = (
    "You extract shopping filters from a thrift-shopping request. "
    "Reply with a single JSON object and nothing else."
)


def _parse_query(query: str) -> dict:
    """
    Pull description / size / max_price out of the query by asking the model.

    Falls back to regex if the model's reply isn't usable JSON, so a parse
    hiccup never sinks the run.
    """
    prompt = (
        f"Request: {query}\n\n"
        'Return JSON with exactly these keys:\n'
        '  "description": the item keywords only (style, item type, color), '
        'without size or price words\n'
        '  "size": the size asked for as written (e.g. "M", "S/M", '
        '"M or smaller", "W32", "US 9"), or null if none\n'
        '  "max_price": the price ceiling as a number, or null if none'
    )
    reply = generate(prompt, system=_PARSE_SYSTEM, temperature=0.0)
    match = re.search(r"\{.*\}", reply, re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
        description = str(data.get("description") or "").strip()
        size = data.get("size") or None
        max_price = data.get("max_price")
        max_price = float(max_price) if max_price not in (None, "") else None
        if description:
            return {"description": description,
                    "size": str(size).strip() if size else None,
                    "max_price": max_price}
    except (ValueError, TypeError, AttributeError):
        pass
    return _parse_query_regex(query)


def _parse_query_regex(query: str) -> dict:
    price = re.search(r"(?:under|below|less than|max|<)\s*\$?\s*(\d+(?:\.\d+)?)", query, re.I)
    size = re.search(r"\bsize\s+([A-Za-z0-9/.]+(?:\s+or\s+(?:smaller|bigger|larger))?)", query, re.I)
    description = query
    for m in (price, size):
        if m:
            description = description.replace(m.group(0), " ")
    return {
        "description": " ".join(description.replace(",", " ").split()),
        "size": size.group(1) if size else None,
        "max_price": float(price.group(1)) if price else None,
    }


def _no_results_message(parsed: dict) -> str:
    """
    Say what the user could change. Re-runs the search with one filter
    dropped at a time to find out which filter is the one ruling things out.
    """
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f'"{desc}"'
    if size:
        asked += f", size {size}"
    if max_price is not None:
        asked += f", under ${max_price:g}"

    hints = []
    if max_price is not None:
        found = search_listings(desc, size, None)
        if found:
            cheapest = min(l["price"] for l in found)
            hints.append(f"raise your budget — the closest match starts at ${cheapest:g}")
    if size:
        found = search_listings(desc, None, max_price)
        if found:
            sizes = sorted({str(l["size"]) for l in found})[:4]
            hints.append(f"try a different size — matches come in {', '.join(sizes)}")
    if not hints:
        hints.append(
            f'use broader or different words than "{desc}" '
            f"(e.g. the item type alone, like \"jacket\" or \"tee\")"
        )
        if size or max_price is not None:
            hints.append("drop the size or price limit")

    return f"Nothing matched {asked}. You could " + ", or ".join(hints) + "."


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )

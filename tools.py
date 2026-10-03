"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Keyword scoring ───────────────────────────────────────────────────────────

_STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "in", "on", "of", "to", "or",
    "i", "im", "i'm", "me", "my", "looking", "want", "need", "some", "something",
    "size", "under", "below", "less", "than", "max", "around", "about", "cheap",
}

# How much a keyword hit counts, by the field it landed in. A hit in the title
# or tags says more about what the item *is* than a passing word in the
# seller's description.
_FIELD_WEIGHTS = {
    "title": 3,
    "style_tags": 3,
    "category": 2,
    "colors": 2,
    "brand": 2,
    "description": 1,
}


def _tokens(text: str) -> set[str]:
    """Lowercase words, with a trailing plural 's' dropped ("tees" → "tee")."""
    words = re.findall(r"[a-z0-9']+", text.lower())
    out = set()
    for w in words:
        if w in _STOPWORDS or len(w) < 2:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.add(w)
    return out


def _score(keywords: set[str], listing: dict) -> int:
    """Weighted count of query keywords that appear in the listing's fields."""
    score = 0
    for field, weight in _FIELD_WEIGHTS.items():
        value = listing.get(field)
        if value is None:                    # brand is None for most listings
            continue
        if isinstance(value, list):
            value = " ".join(value)
        score += weight * len(keywords & _tokens(str(value)))
    return score


# ── Size matching (plain Python, no model call) ───────────────────────────────
#
# A size is read into (system, values): letter sizes become ranks on
# XXS < XS < S < M < L < XL < XXL, waist sizes ("W30 L30") become the waist
# number, shoe sizes ("US 8.5") become the shoe number, and "One Size…" is its
# own system. A label fits a request only when both are in the same system and
# share at least one value — so "S/M" fits "M", but "US 9" never fits "S" and
# "XL (oversized)" never fits "M or smaller".

_LETTER_SIZES = ["XXS", "XS", "S", "M", "L", "XL", "XXL"]
_LETTER_RANK = {s: i for i, s in enumerate(_LETTER_SIZES)}
_LETTER_ALIASES = {
    "XXSMALL": "XXS", "XSMALL": "XS", "EXTRASMALL": "XS", "SMALL": "S",
    "MEDIUM": "M", "MED": "M", "LARGE": "L", "XLARGE": "XL",
    "EXTRALARGE": "XL", "XXLARGE": "XXL", "2XL": "XXL",
}

_SMALLER_WORDS = re.compile(r"or smaller|or less|or under|and under|and below|or below|<=?|max", re.I)
_BIGGER_WORDS = re.compile(r"or bigger|or larger|or more|or above|and up|and above|>=?|min", re.I)


def _letter(word: str) -> str | None:
    word = word.upper().replace("-", "").replace(" ", "")
    word = _LETTER_ALIASES.get(word, word)
    return word if word in _LETTER_RANK else None


def _parse_size(text: str) -> tuple[str, set] | None:
    """
    Read a size label or request into (system, values), or None if unreadable.

    Requests can be open-ended ("M or smaller", "<=M", "L and up") or a list
    ("S, M", "S/M"); labels use the same reader.
    """
    text = re.sub(r"\(.*?\)", "", text).strip()      # "(oversized)" doesn't change size
    if not text:
        return None
    if re.search(r"one\s*size|\bos\b", text, re.I):
        return ("one_size", {"one size"})

    waist = re.findall(r"\bW\s*(\d{2})\b", text, re.I)
    if waist:
        return ("waist", {int(w) for w in waist})
    shoe = re.findall(r"\bUS\s*(\d{1,2}(?:\.5)?)\b", text, re.I)
    if shoe:
        return ("shoe", {float(s) for s in shoe})

    words = re.findall(r"[A-Za-z0-9]+", text)
    ranks = {_LETTER_RANK[l] for w in words if (l := _letter(w))}
    if ranks:
        if _SMALLER_WORDS.search(text):
            ranks = set(range(0, max(ranks) + 1))
        elif _BIGGER_WORDS.search(text):
            ranks = set(range(min(ranks), len(_LETTER_SIZES)))
        return ("letter", ranks)

    # A bare number: shoe sizes are small, waist sizes are 20+.
    nums = [float(n) for n in re.findall(r"\d{1,2}(?:\.5)?", text)]
    if nums:
        if all(n >= 20 for n in nums):
            return ("waist", {int(n) for n in nums})
        return ("shoe", set(nums))
    return None


def _size_fits(requested: tuple[str, set], label: str) -> bool:
    """True when the listing's size label shares a size with the request."""
    parsed = _parse_size(label)
    if parsed is None:
        return False
    system, values = parsed
    return system == requested[0] and bool(values & requested[1])


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    Everything here is plain Python — price, keywords, and size. The model is
    never called. A size request like "M or smaller" or "S, M" is read into a
    set of letter sizes, and a listing fits when its label (ranges like "S/M"
    included) shares one of them. Waist, shoe, and "One Size" labels only fit
    a request in that same system.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    listings = load_listings()

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    keywords = _tokens(description or "")
    scored = [(_score(keywords, l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]

    # An unreadable size request filters out everything rather than being
    # silently ignored — the loop handles an empty search.
    if size and size.strip():
        requested = _parse_size(size)
        scored = [
            (s, l) for s, l in scored
            if requested and _size_fits(requested, str(l["size"]))
        ]

    # Ties keep the cheaper listing first.
    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [l for _, l in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            "They haven't told us what's in their wardrobe. Suggest two outfits "
            "built around this piece, naming the kinds of items to pair it with "
            "(e.g. 'straight-leg dark jeans', 'white low-top sneakers'). "
            "Keep it under 120 words. No preamble."
        )
    else:
        closet = "\n".join(f"- {_describe_wardrobe_item(w)}" for w in items)
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item_text}\n\n"
            f"Here is what they already own:\n{closet}\n\n"
            "Suggest one or two outfits that pair the new piece with specific "
            "items from their wardrobe, naming those items as written above. "
            "Only use pieces from the list plus the new item. "
            "Keep it under 120 words. No preamble."
        )

    reply = generate(prompt, system=_STYLIST_SYSTEM)
    if reply.strip():
        return reply
    # The model can come back empty; the tool promises a non-empty string.
    return (
        f"Style the {new_item.get('title', 'piece')} with simple basics in "
        f"neutral colors so it stays the focus of the outfit."
    )


# ── Shared prompt helpers ─────────────────────────────────────────────────────

_STYLIST_SYSTEM = (
    "You are a thrift-savvy personal stylist. Be concrete and brief. "
    "Never invent clothing the user owns."
)


def _describe_item(item: dict) -> str:
    """One listing as a few labelled lines. Skips brand when there isn't one."""
    lines = [
        f"Title: {item.get('title', 'unknown')}",
        f"Category: {item.get('category', 'unknown')}",
        f"Colors: {', '.join(item.get('colors') or []) or 'unknown'}",
        f"Style: {', '.join(item.get('style_tags') or []) or 'unknown'}",
        f"Size: {item.get('size', 'unknown')}",
        f"Condition: {item.get('condition', 'unknown')}",
    ]
    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")
    if item.get("description"):
        lines.append(f"Seller notes: {item['description']}")
    return "\n".join(lines)


def _describe_wardrobe_item(w: dict) -> str:
    parts = [w.get("name", "item"), f"({w.get('category', '?')})"]
    if w.get("colors"):
        parts.append(f"colors: {', '.join(w['colors'])}")
    if w.get("notes"):
        parts.append(f"note: {w['notes']}")
    return " — ".join(parts)


def _format_price(price) -> str:
    """$18.00 → "$18", $18.50 → "$18.50" — matches what criterion 4 accepts."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return str(price)
    return f"${p:.0f}" if p == int(p) else f"${p:.2f}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "Couldn't write a fit card: there was no outfit suggestion to "
            "caption. Run suggest_outfit first and pass its result in."
        )

    price = _format_price(new_item.get("price"))
    platform = new_item.get("platform", "a thrift app")
    prompt = (
        f"The find:\n{_describe_item(new_item)}\n"
        f"Price: {price}\nPlatform: {platform}\n\n"
        f"How they're styling it:\n{outfit}\n\n"
        "Write a 2 to 4 sentence caption for a social post about this find. "
        "It should sound like a real person posting their thrift haul, not a "
        f"product listing. Mention the item, the exact price written as {price}, "
        f"and the platform {platform} once each. Be specific about the vibe "
        "of the outfit. Up to two emoji, no hashtags, no quotation marks."
    )
    return generate(prompt, system=_CAPTION_SYSTEM)


_CAPTION_SYSTEM = (
    "You write short, casual social captions about thrift finds. "
    "Always use the exact price and platform you are given, never round or "
    "rename them. Stay between 2 and 4 sentences."
)

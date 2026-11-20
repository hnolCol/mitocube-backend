import re


SPECIAL_TAG_CHAR_REPLACEMENTS = {
    "%": "perc",
    "+": "plus",
    "-": "minus",
    "&": "and",
    ">": "gt",
    "<": "lt",
    "=": "eq",
    "~": "approx",
    "*": "star",
    "#": "hash",
    "@": "at",
    "°": "deg",
    "€": "eur",
    "$": "usd",
}


MICRO_SIGN_REPLACEMENTS = {
    "µ": "u",
    "μ": "u",
}


def normalize_tag_text(text: str) -> str:
    """Normalizes a free-text label into a tag-safe token.

    Replaces spaces with underscores, lowercases the text, and replaces
    characters that are problematic in tags (e.g. '%', '+', '>') with
    word equivalents ('perc', 'plus', 'gt'). Any remaining characters
    outside [a-z0-9_] are removed, and repeated/leading/trailing
    underscores are collapsed.
    """
    for special, replacement in SPECIAL_TAG_CHAR_REPLACEMENTS.items():
        text = text.replace(special, " " + replacement + " ")
    for special, replacement in MICRO_SIGN_REPLACEMENTS.items():
        text = text.replace(special, replacement)
    text = text.replace(" ", "_").lower().encode("utf-8", "ignore").decode("utf-8")
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_{2,}", "_", text)
    return text.strip("_")

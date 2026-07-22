"""Lexicalization — the ONLY place an LLM appears, and it is never trusted.

Contract:
  1. The LLM receives the filled fact sheet and may only phrase its slots.
  2. Output is verified mechanically: every chess token (SAN move, square)
     in the prose must appear in the fact sheet's witnesses. A claim with no
     backing slot is a hallucination by construction.
  3. On verification failure (or no API key), fall back to the deterministic
     template — always correct, merely less fluent.

Provider: Gemini (GEMINI_API_KEY). Swappable by design — the model is the
least-trusted component in the system.
"""
from __future__ import annotations

import os
import re

from .factsheet import FactSheet

GEMINI_MODEL = os.environ.get("EXPLAINER_GEMINI_MODEL", "gemini-2.5-flash")

_SAN_RE = re.compile(
    r"\b(?:O-O(?:-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)\b"
)


def _strength(cp: int) -> str:
    """Margin-scaled language: the adjective must match the eval."""
    if cp >= 500: return "a decisive advantage"
    if cp >= 250: return "a winning advantage"
    if cp >= 120: return "a clear advantage"
    return "the better position"


# ---------------------------------------------------------------- templates
def template_prose(fs: FactSheet) -> str:
    """Deterministic fallback — every sentence maps 1:1 to a slot."""
    if fs.status == "not_a_mistake":
        return (f"Your move {fs.played} is actually fine here ({fs.delta.value}). "
                f"The intended solution {fs.solution} is stronger, but you haven't "
                f"thrown the position away.")
    if fs.status != "ok":
        return f"Cannot explain this position reliably: {fs.status} ({fs.note})."

    parts: list[str] = []
    f, e = fs.forfeit, fs.error
    if f.value.startswith("mate_in"):
        n = f.value.split("_")[-1]
        parts.append(f"{fs.solution} forces mate in {n} "
                     f"({' '.join(f.witness['line'])}).")
    elif f.value == "forced_mate":
        parts.append(f"{fs.solution} forces checkmate — the main line runs "
                     f"{' '.join(f.witness['line'])}.")
    elif f.value.startswith("wins_"):
        parts.append(f"{fs.solution} wins a {f.value[5:]} "
                     f"({' '.join(f.witness['line'])}).")
    elif f.value == "winning_attack":
        parts.append(f"{fs.solution} breaks through — the attack is decisive "
                     f"({' '.join(f.witness['line'])}, {f.witness['win_pct']}% winning).")
    elif f.value == "promotion":
        parts.append(f"{fs.solution} wins through the passed pawn "
                     f"({' '.join(f.witness['line'])}).")
    elif f.value == "decisive_threat":
        parts.append(f"{fs.solution} creates an unstoppable threat "
                     f"({' '.join(f.witness['threat_pv'])}).")
    else:
        cp = int(f.witness.get("eval_cp", 300))
        parts.append(f"{fs.solution} keeps {_strength(cp)} "
                     f"({' '.join(f.witness.get('line', []))}).")

    mech = f.witness.get("mechanism")
    if mech:
        kind = mech["mechanism"]
        if kind in ("deflection", "overload"):
            parts.append(f"The point is a {kind}: the {mech['deflected_defender']} on "
                         f"{mech['deflected_from']} is the only defender of the "
                         f"{mech['target_piece']} on {mech['target']} — {mech['forcing_move']} "
                         f"drags it to {mech['lured_to']}, and {mech['follow_up']} collects.")
        elif kind == "defender_removal":
            parts.append(f"The point: {mech['forcing_move']} removes the {mech['removed_defender']} "
                         f"on {mech['removed_on']} — the only defender of the "
                         f"{mech['target_piece']} on {mech['target']} — and {mech['follow_up']} collects.")
        elif kind in ("mating_net", "back_rank_mate", "smothered_mate"):
            esc = "; ".join(f"{sq} {why}" for sq, why in list(mech["escapes"].items())[:4])
            name = {"back_rank_mate": "a back-rank mate", "smothered_mate": "a smothered mate",
                    "mating_net": "a mating net"}[kind]
            parts.append(f"It ends in {name}: after {mech['mate_move']} the king on "
                         f"{mech['king']} has nowhere to go ({esc}).")
        elif kind == "fork":
            parts.append(f"The point is a fork: {mech['fork_move']} attacks "
                         f"{' and '.join(mech['targets'])} at once — only one can be "
                         f"saved, and {mech['collected_with']} collects the other.")
        elif kind == "attraction":
            if "deflected_defender" in mech:   # composed lure: arrival exploited
                parts.append(f"The point is an attraction: {mech['forcing_move']} drags the "
                             f"{mech['deflected_defender']} from {mech['deflected_from']} to "
                             f"{mech['lured_to']}, where {mech.get('arrival_exploited_by', mech['follow_up'])} "
                             f"hits it — and {mech['target']} falls with it.")
                if "overload" in mech.get("also", []):
                    parts.append(f"The {mech['deflected_defender']} was overloaded: it could "
                                 f"not hold both {mech['second_duty']} and {mech['target']}.")
            else:
                parts.append(f"The point is an attraction: {mech['forcing_move']} forces the "
                             f"{mech['lured_piece']} from {mech['lured_from']} onto "
                             f"{mech['lured_to']}, where {mech['follow_up']} wins it.")

    if e.value == "bad_trade":
        parts.append(f"Your move {fs.played} starts an exchange that doesn't work: "
                     f"{e.witness['they_retook']} takes back on {e.witness['square']} "
                     f"and the trade nets you nothing.")
    elif e.value == "hung":
        parts.append(f"Your move {fs.played} also loses material outright: "
                     f"{e.witness['capture']} simply takes on {e.witness['square']}.")
    elif e.value == "wrong_piece":
        parts.append(f"Your move {fs.played} had the right idea — the same square "
                     f"({e.witness['square']}) — but the wrong piece; "
                     f"the difference shows after {fs.refutation.value}.")
    elif e.value == "move_order":
        parts.append(f"{fs.played} belongs in the winning line, but not yet — "
                     f"the order matters: {' '.join(e.witness['solution_line'])}.")
    elif e.value == "allowed_forcing_reply":
        parts.append(f"Your move {fs.played} allows the forcing reply "
                     f"{' '.join(e.witness['reply'])}.")
    else:
        parts.append(f"Your move {fs.played} isn't actively bad — it just isn't "
                     f"the win; after {fs.refutation.value} the moment is gone.")

    if fs.salvage.value == "position_lost":
        parts.append(f"After this the game is lost ({fs.delta.value}).")
    elif fs.salvage.value == "advantage_gone":
        parts.append(f"The win is gone — the position is roughly equal now "
                     f"({fs.delta.value}).")
    else:
        parts.append(f"You are still winning, but gave back part of the "
                     f"advantage ({fs.delta.value}).")

    from .takeaways import takeaway
    tip = takeaway(fs)
    if tip:
        parts.append(f"Habit: {tip}")
    return " ".join(parts)


# ---------------------------------------------------------------- LLM path
def _harvest(v, toks: set[str]) -> None:
    if isinstance(v, dict):
        for x in v.values():
            _harvest(x, toks)
    elif isinstance(v, list):
        for x in v:
            _harvest(x, toks)
    elif isinstance(v, str):
        toks.update(v.split())


def _allowed_tokens(fs: FactSheet) -> set[str]:
    toks: set[str] = {fs.solution, fs.played}
    for slot in (fs.forfeit, fs.error, fs.refutation, fs.delta, fs.salvage):
        if slot is not None:
            _harvest(slot.witness, toks)
    return {t.rstrip("+#") for t in toks}


# Doctrine vocabulary: mechanism words may enter prose ONLY from the mechanism
# layer's witnessed slots — an LLM reaching for them on its own is fabricating
# analysis (observed: "overloaded ... can't recapture" against a witness line
# that contained the recapture).
_MECHANISM_WORDS = {
    "fork": "fork", "forked": "fork", "forking": "fork",
    "deflect": "deflection", "deflected": "deflection", "deflection": "deflection",
    "lure": "attraction", "lured": "attraction", "attraction": "attraction",
    "overload": "overload", "overloaded": "overload", "overloading": "overload",
    "skewer": "skewer", "skewered": "skewer",
    "pin": "pin", "pinned": "pin", "pinning": "pin",
    "zwischenzug": "intermezzo", "intermezzo": "intermezzo",
    "smothered": "smothered_mate", "decoy": "attraction",
    "x-ray": "xray", "xray": "xray", "discovered": "discovered",
    "battery": "battery",
    "sacrifice": "sacrifice", "sacrificed": "sacrifice", "sacrifices": "sacrifice",
    "trapped": "trapped", "hanging": "hanging_piece", "hangs": "hanging_piece",
    "back-rank": "back_rank_mate", "back rank": "back_rank_mate",
}


def _allowed_concepts(fs: FactSheet) -> set[str]:
    """Concept families the sheet actually asserts (slot values + mechanism)."""
    out: set[str] = set()
    for slot in (fs.forfeit, fs.error, fs.refutation, fs.delta, fs.salvage):
        if slot is None:
            continue
        out.add(slot.value)
        mech = slot.witness.get("mechanism")
        if isinstance(mech, dict):
            out.add(mech.get("mechanism", ""))
            out.update(mech.get("also", []))
    if fs.error is not None and fs.error.value == "hung":
        out.add("hanging_piece")
    return out


def verify(prose: str, fs: FactSheet) -> tuple[bool, list[str]]:
    """Two checks: every SAN token AND every mechanism word must trace to
    the fact sheet. Vocabulary discipline is claim discipline."""
    allowed = _allowed_tokens(fs)
    unsupported = [t for t in _SAN_RE.findall(prose)
                   if t.rstrip("+#") not in allowed]
    concepts = _allowed_concepts(fs)
    low = prose.lower()
    for word, family in _MECHANISM_WORDS.items():
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            if not any(family in c or c.startswith(family) for c in concepts):
                unsupported.append(f"concept:{word}")
    # COVERAGE (symmetry of the blocklist): when the sheet asserts a mechanism,
    # the prose must speak it — an explanation that drops the point is not an
    # explanation. Weak models don't fabricate; they omit. Both fail.
    for slot in (fs.forfeit, fs.error):
        if slot is None:
            continue
        mech = slot.witness.get("mechanism")
        if isinstance(mech, dict):
            fam = mech.get("mechanism", "")
            words = [w for w, f in _MECHANISM_WORDS.items() if f == fam or fam.startswith(f)]
            words += [fam.replace("_", " "), fam.replace("_", "-")]
            if not any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words if w):
                unsupported.append(f"missing_mechanism:{fam}")
    return (not unsupported), unsupported


_PROMPT = """You are a chess coach explaining why a puzzle move failed.

You will receive a FACT SHEET. Every chess claim you make MUST come from it.
Rules — violating any of them makes your output unusable:
- Mention ONLY moves and squares that appear in the fact sheet.
- Do NOT add chess analysis, motifs, or evaluations of your own.
- Do NOT hedge or speculate. The facts are engine-verified; state them plainly.
- 2 to 4 sentences, warm but direct coaching tone, second person.
- Lead with the most important fact (the forfeit), then the error if any.
- If the fact sheet contains a "mechanism", you MUST explain it by name using
  its witness fields (defender, squares, forcing move) — it is the point.

FACT SHEET:
{sheet}
"""


def _redact(obj):
    """Strip everything the LLM is not allowed to speak — above all
    ungraduated mechanism candidates. Never show the model what it can't say."""
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items()
                if k not in ("mechanism_candidate", "secondary", "execution",
                             "geometry_candidate")}
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def llm_prose(fs: FactSheet) -> str | None:
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        return None
    try:
        from google import genai
        client = genai.Client()
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=_PROMPT.format(sheet=_redact(fs.to_dict())),
        )
        return (resp.text or "").strip() or None
    except Exception:
        return None


# ---------------------------------------------------------------- entry
def explain(fs: FactSheet) -> dict:
    """Fact sheet -> prose, with provenance of how the prose was produced."""
    fallback = template_prose(fs)
    if fs.status != "ok":
        return {"prose": fallback, "source": "template", "verified": True}

    prose = llm_prose(fs)
    if prose is None:
        return {"prose": fallback, "source": "template", "verified": True}

    ok, unsupported = verify(prose, fs)
    if ok:
        return {"prose": prose, "source": "llm", "verified": True}
    return {"prose": fallback, "source": "template_after_llm_rejected",
            "verified": True, "rejected_tokens": unsupported}

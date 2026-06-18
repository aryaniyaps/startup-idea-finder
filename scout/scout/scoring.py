"""
Multi-axis startup idea scoring engine.

Dimensions:
  1. Problem Quality (40%)    — 8 criteria via LLM (Hale + Friedman)
  2. Market Viability (25%)   — 6 criteria via LLM (Friedman)
  3. Sentiment Signal (15%)   — keyword-based with source-tier multiplier
  4. Founder-Market Fit (20%) — 5 criteria via LLM, personalised to UserProfile

Verdict thresholds: STRONG ≥ 75, PROMISING ≥ 60, WEAK ≥ 40, else REJECT.
Tarpit detection overrides verdict to TARPIT.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & tier constants
# ---------------------------------------------------------------------------


class SourceTier(IntEnum):
    TIER_1 = 1  # Reddit, HN, Indie Hackers, X/Twitter, WorldMonitor
    TIER_2 = 2  # Professional communities, review sites
    TIER_3 = 3  # Job boards
    TIER_4 = 4  # GitHub Issues, app store reviews
    TIER_5 = 5  # Product Hunt, founder communities


SOURCE_TIER_MAP: dict[str, int] = {
    # Tier 1 — public pain points, unsolicited complaints
    "reddit": 1,
    "hn": 1,
    "indiehackers": 1,
    "twitter": 1,
    "x": 1,
    "worldmonitor": 1,
    # Tier 2 — people evaluating alternatives, writing detailed complaints
    "review": 2,
    "g2": 2,
    "capterra": 2,
    "trustpilot": 2,
    "support_forum": 2,
    "discord": 2,
    "slack": 2,
    # Tier 3 — market proof: people already paying
    "job_board": 3,
    "upwork": 3,
    "fiverr": 3,
    "linkedin": 3,
    # Tier 4 — developer pain documented in detail
    "github_issue": 4,
    "app_store": 4,
    "youtube": 4,
    "extension_review": 4,
    # Tier 5 — useful for feedback, weaker for novel discovery
    "producthunt": 5,
    "founder_community": 5,
}

TIER_MULTIPLIERS: dict[int, float] = {
    1: 1.0,
    2: 1.3,
    3: 1.2,
    4: 1.1,
    5: 0.8,
}


def _resolve_tier(source_type: str) -> int:
    """Map a source-type string to its tier, defaulting to tier 3."""
    return SOURCE_TIER_MAP.get(source_type.lower(), 3)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Idea:
    id: str
    title: str
    description: str
    source_url: str
    source_type: str
    source_tier: int
    discovered_at: datetime
    embedding: list[float] | None = None


@dataclass
class ScoreReport:
    idea_id: str
    composite: float
    problem_quality: float
    market_viability: float
    sentiment_signal: float
    founder_fit: float
    sentiment_flags: list[str]
    risks: list[str]
    tarpit: dict | None
    failure_matches: list[str]
    verdict: str  # STRONG | PROMISING | WEAK | TARPIT | REJECT
    justification: str


# ---------------------------------------------------------------------------
# Sentiment keyword detection (Dimension 3)
# ---------------------------------------------------------------------------

# Each tier: (keywords, points_per_match, max_points)
_FRUSTRATION_TERMS: list[str] = [
    "hate",
    "frustrated",
    "nightmare",
    "killing me",
    "can't stand",
    "ruining",
    "infuriating",
    "garbage",
    "useless",
    "terrible",
    "driving me crazy",
    "drives me insane",
]
_FRUSTRATION_POINTS: int = 12
_FRUSTRATION_MAX: int = 36

_WORKAROUND_TERMS: list[str] = [
    "manual",
    "spreadsheet",
    "workaround",
    "duct tape",
    "hacky",
    "janky",
    "copy-paste",
    "copy paste",
    "excel",
    "emailing back and forth",
    "email back and forth",
    "manually",
]
_WORKAROUND_POINTS: int = 10
_WORKAROUND_MAX: int = 30

_ACTIVE_SEARCH_TERMS: list[str] = [
    "any tool for",
    "does anyone else",
    "why is there no",
    "someone should build",
    "wish there was",
    "looking for a",
    "recommend a tool",
    "alternative to",
    "is there a way to",
    "anyone know of",
    "has anyone built",
    "where can i find",
    "need something that",
    "i wish",
]
_ACTIVE_SEARCH_POINTS: int = 15
_ACTIVE_SEARCH_MAX: int = 45

_DESPERATION_TERMS: list[str] = [
    "desperate",
    "please someone",
    "i would pay anything",
    "life depends on",
    "this is costing us",
    "at my wit's end",
    "about to give up",
    "losing my mind",
    "out of options",
    "last resort",
    "begging",
]
_DESPERATION_POINTS: int = 20
_DESPERATION_MAX: int = 40

# Revenue signal regex: dollar amount near a payment word
_REVENUE_PATTERN: re.Pattern[str] = re.compile(
    r"\$[\d,]+(?:\.\d+)?\s*(?:k|m|b|thousand|million|billion)?",
    re.IGNORECASE,
)
_REVENUE_CONTEXT: list[str] = [
    "month",
    "paying",
    "spent",
    "costs",
    "costing",
    "billed",
    "charge",
    "invoice",
    "subscription",
]
_REVENUE_BONUS: int = 30
_REPETITION_BONUS: int = 25
_REPETITION_THRESHOLD: int = 3

# Synthetic / AI-generated text heuristics
_MARKETING_SPEAK: list[str] = [
    "revolutionary",
    "game-changing",
    "game changing",
    "disruptive",
    "unprecedented",
    "cutting-edge",
    "cutting edge",
    "best-in-class",
    "best in class",
    "world-class",
    "world class",
    "next-gen",
    "next gen",
    "state-of-the-art",
    "state of the art",
    "paradigm shift",
    "bleeding edge",
    "industry-leading",
    "industry leading",
    "groundbreaking",
    "ground breaking",
]


def _count_phrase_matches(text: str, phrases: list[str]) -> int:
    """Count how many *unique* phrases appear in *text* (case-insensitive)."""
    lower = text.lower()
    return sum(1 for p in phrases if p.lower() in lower)


def _count_exclamation_bursts(text: str, window: int = 500) -> int:
    """Return the maximum exclamation-mark count in any *window*-char span."""
    if len(text) <= window:
        return text.count("!")
    best = 0
    lower = text.lower()
    # Slide window in 100-char steps for performance
    for start in range(0, len(lower) - window, 100):
        best = max(best, lower[start : start + window].count("!"))
    return best


def _detect_synthetic_text(text: str) -> tuple[bool, list[str]]:
    """Return (is_synthetic, reasons)."""
    reasons: list[str] = []
    lower = text.lower()

    # Excessive exclamation marks
    excl = _count_exclamation_bursts(text)
    if excl >= 5:
        reasons.append(f"excessive_exclamations({excl})")

    # Marketing-speak keywords
    hits = [w for w in _MARKETING_SPEAK if w.lower() in lower]
    if len(hits) >= 3:
        reasons.append(f"marketing_speak({','.join(hits[:5])})")

    return bool(reasons), reasons


def _score_sentiment(
    text: str,
    source_tier: int,
    cross_community_count: int = 0,
) -> tuple[float, list[str]]:
    """Compute raw sentiment score (0-100) and collect flags.

    Returns (final_sentiment_score, flags) where the score already
    incorporates the tier multiplier and is capped at 100.
    """
    flags: list[str] = []
    lower = text.lower()
    raw: int = 0

    # 1. Explicit frustration
    frustration_hits = [p for p in _FRUSTRATION_TERMS if p.lower() in lower]
    if frustration_hits:
        pts = min(len(frustration_hits) * _FRUSTRATION_POINTS, _FRUSTRATION_MAX)
        raw += pts
        flags.append(f"frustration({len(frustration_hits)})")

    # 2. Workaround signal
    workaround_hits = [p for p in _WORKAROUND_TERMS if p.lower() in lower]
    if workaround_hits:
        pts = min(len(workaround_hits) * _WORKAROUND_POINTS, _WORKAROUND_MAX)
        raw += pts
        flags.append(f"workaround({len(workaround_hits)})")

    # 3. Active search
    search_hits = [p for p in _ACTIVE_SEARCH_TERMS if p.lower() in lower]
    if search_hits:
        pts = min(len(search_hits) * _ACTIVE_SEARCH_POINTS, _ACTIVE_SEARCH_MAX)
        raw += pts
        flags.append(f"active_search({len(search_hits)})")

    # 4. Desperation
    desperation_hits = [p for p in _DESPERATION_TERMS if p.lower() in lower]
    if desperation_hits:
        pts = min(len(desperation_hits) * _DESPERATION_POINTS, _DESPERATION_MAX)
        raw += pts
        flags.append(f"desperation({len(desperation_hits)})")

    # 5. Revenue signal — one-time bonus if $X found near payment context
    if _REVENUE_PATTERN.search(lower):
        ctx_window = 200
        for ctx_term in _REVENUE_CONTEXT:
            idx = lower.find(ctx_term.lower())
            if idx >= 0:
                # Look for dollar amounts within ctx_window chars
                snippet = lower[max(0, idx - ctx_window) : idx + ctx_window]
                if _REVENUE_PATTERN.search(snippet):
                    raw += _REVENUE_BONUS
                    flags.append("revenue_signal")
                    break

    # 6. Repetition signal (external, cross-community)
    if cross_community_count >= _REPETITION_THRESHOLD:
        raw += _REPETITION_BONUS
        flags.append(f"repetition({cross_community_count})")

    # Cap raw at 100, then apply tier multiplier, then cap again
    raw = min(raw, 100)
    multiplier = TIER_MULTIPLIERS.get(source_tier, 1.0)
    final = round(raw * multiplier, 1)
    final = min(final, 100.0)

    return final, flags


# ---------------------------------------------------------------------------
# LLM prompt builders
# ---------------------------------------------------------------------------

_PQ_MV_SYSTEM_PROMPT = """\
You are a rigorous startup idea evaluator. You rate ideas on two dimensions:
Problem Quality (8 criteria) and Market Viability (6 criteria).

Rate each sub-criterion 0-10. Provide a short justification for each rating (1 sentence).

Return ONLY valid JSON — no preamble, no markdown fences, no trailing text.\
"""


def _build_pq_mv_prompt(idea_title: str, description: str, supplementary: list[dict] | None = None) -> str:
    extra = ""
    if supplementary:
        extra = "\n\nSupplementary extracted problems:\n" + json.dumps(supplementary, indent=2)

    return f"""Evaluate this startup idea:

Title: {idea_title}
Description: {description}{extra}

## Problem Quality (8 criteria, each 0-10)
1. urgency — Does the user NEED this solved now?
2. pervasiveness — How many people share this problem?
3. frequency — How often does the problem occur (daily, weekly)?
4. cost_of_inaction — What is the cost of NOT solving it?
5. growth — Is the problem trending up?
6. mandatory — Is regulatory/compliance pressure forcing action?
7. underserved — Are existing solutions inadequate?
8. acuteness — Does it cause emotional distress or acute pain?

## Market Viability (6 criteria, each 0-10)
1. buyer_budget — Is there a clear buyer with budget?
2. market_size — Is the market large and growing?
3. reach — Can customers be reached efficiently?
4. competition — Is the competitive landscape favorable (fragmented, weak incumbents)?
5. business_model — Is the business model obvious (can you charge for this)?
6. timing — Why now? Is the timing right?

Return JSON with this exact structure:
{{
  "problem_quality": {{
    "urgency": <0-10>,
    "pervasiveness": <0-10>,
    "frequency": <0-10>,
    "cost_of_inaction": <0-10>,
    "growth": <0-10>,
    "mandatory": <0-10>,
    "underserved": <0-10>,
    "acuteness": <0-10>,
    "justification": "<summary sentence>"
  }},
  "market_viability": {{
    "buyer_budget": <0-10>,
    "market_size": <0-10>,
    "reach": <0-10>,
    "competition": <0-10>,
    "business_model": <0-10>,
    "timing": <0-10>,
    "justification": "<summary sentence>"
  }},
  "risks": ["<risk 1>", "<risk 2>", ...]
}}
"""


def _build_founder_fit_prompt(idea_title: str, description: str, profile: Any) -> str:
    return f"""Evaluate founder-market fit for this idea given the founder's profile.

Idea: {idea_title}
Description: {description}

## Founder Profile
- Skills: {', '.join(profile.skills) if profile.skills else 'unspecified'}
- Industries: {', '.join(profile.industries) if profile.industries else 'unspecified'}
- Years of experience: {profile.years_experience}
- Technical depth (0-1): {profile.technical_depth}
- Capital available ($): {profile.capital_available:,.0f}
- Problems personally experienced: {', '.join(profile.problems_experienced) if profile.problems_experienced else 'none specified'}
- Anti-preferences (domains to avoid): {', '.join(profile.anti_preferences) if profile.anti_preferences else 'none'}

## Founder-Market Fit (5 criteria, each 0-10)
1. domain_expertise — Does the founder know this space well?
2. technical_fit — Can the founder build this (or hire for it)?
3. network_advantage — Does the founder have useful connections in this domain?
4. passion_persistence — Will the founder stick with this for 5-10 years?
5. unique_insight — Does the founder see something others miss?

Return JSON with this exact structure:
{{
  "domain_expertise": <0-10>,
  "technical_fit": <0-10>,
  "network_advantage": <0-10>,
  "passion_persistence": <0-10>,
  "unique_insight": <0-10>,
  "justification": "<summary sentence>"
}}
"""

_EXTRACT_PROBLEMS_SYSTEM = """\
You extract distinct, well-formed problem statements from user-generated text.
Each problem must be a genuine pain point someone is experiencing — not a feature request or vague complaint.

Return ONLY valid JSON — no preamble, no markdown fences, no trailing text.\
"""


def _build_extract_problems_prompt(text: str, source_type: str) -> str:
    context_hint: dict[str, str] = {
        "review": "This is a product review describing what the reviewer dislikes. "
        "Extract the underlying problems the user is experiencing.",
        "github_issue": "This is a GitHub issue describing a feature gap or bug. "
        "Extract the underlying problem this feature or fix would address.",
        "job_board": "This job listing describes tasks people are paid to perform. "
        "Identify problems these tasks hint at — could software partially or fully automate this?",
        "reddit": "This is a Reddit post. Extract the pain points the poster is experiencing.",
        "hn": "This is a Hacker News post or comment. Extract the problems being discussed.",
        "twitter": "This is a tweet or thread. Extract the problems or frustrations expressed.",
        "x": "This is a tweet or thread. Extract the problems or frustrations expressed.",
        "worldmonitor": "This is a news/trend brief. Extract the emerging problems being reported.",
        "news": "This is a news article. Extract the problems being reported on.",
    }
    hint = context_hint.get(source_type.lower(), "Extract distinct problem statements from this text.")

    return f"""{hint}

Text:
{text[:8000]}

Return a JSON list of problem objects:
[
  {{
    "title": "<short problem title>",
    "description": "<1-2 sentence description of the problem>",
    "severity": <1-5>
  }}
]

If no clear problem is found, return an empty list [].
"""


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------


async def _llm_json(
    client: AsyncOpenAI,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Make a single JSON-mode LLM call with retries."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                max_tokens=max_tokens,
                temperature=temperature,
            )
            raw = response.choices[0].message.content
            if raw is None:
                raise ValueError("LLM returned empty response")
            # Strip any markdown code fences the model may still emit
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            logger.warning("LLM JSON parse attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(0.5 * (attempt + 1))
        except Exception:
            raise  # Don't retry auth / network errors the same way

    raise ValueError(f"LLM JSON parsing failed after 3 attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Knowledge-graph lookups
# ---------------------------------------------------------------------------


def _keyword_overlap(a: str, b: str) -> float:
    """Jaccard-like overlap of words (case-insensitive)."""
    words_a = set(re.findall(r"[a-z]{3,}", a.lower()))
    words_b = set(re.findall(r"[a-z]{3,}", b.lower()))
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / min(len(words_a), len(words_b))


def _check_tarpit(idea: Idea, kg: Any, threshold: float = 0.7) -> tuple[dict | None, list[str]]:
    """Check knowledge-graph tarpit examples against the idea.

    Returns (best_match_dict | None, match_reasons).
    """
    try:
        tarpits = kg.get_tarpit_examples()
    except Exception:
        logger.warning("Failed to query KG tarpits", exc_info=True)
        return None, []

    if not tarpits:
        return None, []

    combined_text = f"{idea.title}\n{idea.description}"
    matches: list[tuple[float, dict]] = []

    for tp in tarpits:
        tp_text = tp.get("description", "") + " " + tp.get("title", "")
        overlap = _keyword_overlap(combined_text, tp_text)
        if overlap >= threshold:
            matches.append((overlap, tp))

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        best_score, best_tp = matches[0]
        reasons = [f"tarpit:{best_tp.get('title', 'unknown')}({best_score:.2f})"]
        return best_tp, reasons

    return None, []


def _check_failure_modes(idea: Idea, kg: Any, threshold: float = 0.7) -> list[str]:
    """Check knowledge-graph pre-launch failure modes."""
    try:
        modes = kg.get_pre_launch_failure_modes()
    except Exception:
        logger.warning("Failed to query KG failure modes", exc_info=True)
        return []

    if not modes:
        return []

    combined_text = f"{idea.title}\n{idea.description}"
    matches: list[str] = []

    for mode in modes:
        mode_text = mode.get("description", "") + " " + mode.get("title", "")
        overlap = _keyword_overlap(combined_text, mode_text)
        if overlap >= threshold:
            label = mode.get("title", "unknown")
            matches.append(f"{label}({overlap:.2f})")

    return matches


# ---------------------------------------------------------------------------
# Verdict computation
# ---------------------------------------------------------------------------

_VERDICT_LEVELS: list[str] = ["STRONG", "PROMISING", "WEAK", "REJECT"]


def _base_verdict(composite: float) -> str:
    if composite >= 75:
        return "STRONG"
    if composite >= 60:
        return "PROMISING"
    if composite >= 40:
        return "WEAK"
    return "REJECT"


def _downgrade_verdict(base: str, steps: int) -> str:
    """Downgrade *base* verdict by *steps* levels, floor at REJECT."""
    try:
        idx = _VERDICT_LEVELS.index(base)
    except ValueError:
        return "REJECT"
    new_idx = min(idx + steps, len(_VERDICT_LEVELS) - 1)
    return _VERDICT_LEVELS[new_idx]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def extract_problems(
    text: str,
    source_type: str,
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> list[dict[str, Any]]:
    """Extract distinct problem statements from *text* using an LLM.

    Returns a list of dicts with keys `title`, `description`, `severity`.
    """
    if not text.strip():
        return []

    prompt = _build_extract_problems_prompt(text, source_type)
    try:
        result = await _llm_json(client, model, _EXTRACT_PROBLEMS_SYSTEM, prompt, max_tokens=1500)
    except Exception:
        logger.warning("extract_problems LLM call failed", exc_info=True)
        return []

    if isinstance(result, list):
        return [p for p in result if isinstance(p, dict)]
    if isinstance(result, dict) and "problems" in result:
        return result["problems"]
    return []


async def score_idea(
    idea: Idea,
    profile: Any,  # UserProfile
    kg: Any,  # KnowledgeGraph
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
    cross_community_count: int = 0,
) -> ScoreReport:
    """Full multi-axis scoring pipeline.

    Parameters
    ----------
    cross_community_count:
        Number of distinct communities where semantically similar complaints
        have been detected.  Used for the repetition bonus in sentiment scoring.
    """
    idea_text = f"{idea.title}\n{idea.description}"
    justification_parts: list[str] = []
    risks: list[str] = []

    # ── Step 1: Extract supplementary problems ──────────────────────────
    supplementary = await extract_problems(idea.description, idea.source_type, client, model)

    # ── Step 2: Problem Quality + Market Viability (LLM, concurrent with FF) ──
    pq_mv_prompt = _build_pq_mv_prompt(idea.title, idea.description, supplementary)

    async def _call_pq_mv() -> dict[str, Any]:
        try:
            return await _llm_json(client, model, _PQ_MV_SYSTEM_PROMPT, pq_mv_prompt, max_tokens=2000)
        except Exception:
            logger.warning("PQ+MV LLM call failed", exc_info=True)
            return {}

    # ── Step 3: Founder-Market Fit (LLM) ────────────────────────────────
    ff_prompt = _build_founder_fit_prompt(idea.title, idea.description, profile)

    async def _call_ff() -> dict[str, Any]:
        try:
            return await _llm_json(
                client, model, "", ff_prompt, max_tokens=1000, temperature=0.4
            )
        except Exception:
            logger.warning("Founder-fit LLM call failed", exc_info=True)
            return {}

    # Run PQ+MV and FF concurrently
    pq_mv_result, ff_result = await asyncio.gather(_call_pq_mv(), _call_ff())

    # ── Parse PQ+MV scores ──────────────────────────────────────────────
    pq_scores = pq_mv_result.get("problem_quality", {}) if pq_mv_result else {}
    mv_scores = pq_mv_result.get("market_viability", {}) if pq_mv_result else {}
    llm_risks = pq_mv_result.get("risks", []) if pq_mv_result else []

    PQ_KEYS = [
        "urgency", "pervasiveness", "frequency", "cost_of_inaction",
        "growth", "mandatory", "underserved", "acuteness",
    ]
    MV_KEYS = [
        "buyer_budget", "market_size", "reach", "competition",
        "business_model", "timing",
    ]

    # Default to 5 (midpoint) on parse / LLM failure
    pq_sum = sum(int(pq_scores.get(k, 5)) for k in PQ_KEYS)
    mv_sum = sum(int(mv_scores.get(k, 5)) for k in MV_KEYS)

    problem_quality = round((pq_sum / 80) * 100, 1)
    market_viability = round((mv_sum / 60) * 100, 1)

    if pq_mv_result:
        pq_j = pq_scores.get("justification", "")
        mv_j = mv_scores.get("justification", "")
        if pq_j:
            justification_parts.append(f"Problem Quality: {pq_j}")
        if mv_j:
            justification_parts.append(f"Market Viability: {mv_j}")
    else:
        justification_parts.append("PQ+MV scores defaulted (LLM call failed).")

    if isinstance(llm_risks, list):
        risks.extend(str(r) for r in llm_risks)

    # ── Parse Founder-Fit scores ────────────────────────────────────────
    FF_KEYS = [
        "domain_expertise", "technical_fit", "network_advantage",
        "passion_persistence", "unique_insight",
    ]
    ff_sum = sum(int(ff_result.get(k, 5)) for k in FF_KEYS) if ff_result else 25
    founder_fit = round((ff_sum / 50) * 100, 1)

    if ff_result and ff_result.get("justification"):
        justification_parts.append(f"Founder-Market Fit: {ff_result['justification']}")
    elif not ff_result:
        justification_parts.append("Founder-fit scores defaulted (LLM call failed).")

    # ── Step 4: Sentiment signal (keyword-based, no LLM) ────────────────
    sentiment_signal, sentiment_flags = _score_sentiment(
        idea_text, idea.source_tier, cross_community_count
    )

    # ── Step 5: Check KG for tarpits ────────────────────────────────────
    tarpit_match, tarpit_reasons = _check_tarpit(idea, kg)
    if tarpit_reasons:
        sentiment_flags.extend(tarpit_reasons)

    # ── Step 6: Check KG for pre-launch failure modes ───────────────────
    failure_matches = _check_failure_modes(idea, kg)
    if failure_matches:
        sentiment_flags.extend(f"failure_mode:{f}" for f in failure_matches)

    # ── Step 7: Compute composite ───────────────────────────────────────
    composite = round(
        problem_quality * 0.40
        + market_viability * 0.25
        + sentiment_signal * 0.15
        + founder_fit * 0.20,
        1,
    )

    # ── Step 8: Determine verdict ───────────────────────────────────────
    base = _base_verdict(composite)
    downgrade_steps = 0

    # Tarpit detection → explicit TARPIT verdict (overrides downgrade logic)
    if tarpit_match is not None:
        verdict = "TARPIT"
        justification_parts.append(
            f"Tarpit detected: {tarpit_match.get('title', 'unknown')}. "
            "This idea resembles known tarpit patterns — high failure rate."
        )
    else:
        # Pre-launch failure mode downgrade
        if failure_matches:
            downgrade_steps += 1
            justification_parts.append(
                f"Pre-launch failure mode(s) matched: {', '.join(failure_matches)}. Downgrading 1 level."
            )
            risks.append("Matches known pre-launch failure patterns.")

        # Synthetic / AI-generated text downgrade
        synthetic, synth_reasons = _detect_synthetic_text(idea.description)
        if synthetic:
            downgrade_steps += 1
            sentiment_flags.extend(f"synthetic:{r}" for r in synth_reasons)
            justification_parts.append(
                "Text appears AI-generated (marketing-speak, excessive exclamation marks). Downgrading 1 level."
            )
            risks.append("Source text may be AI-generated — weaker signal.")

        verdict = _downgrade_verdict(base, downgrade_steps)

        if downgrade_steps > 0:
            justification_parts.append(f"Base verdict: {base}. Final after downgrades: {verdict}.")
        else:
            justification_parts.append(f"Verdict: {verdict} (composite={composite}).")

    if sentiment_flags:
        justification_parts.insert(
            0, f"Sentiment flags: {', '.join(sentiment_flags)}."
        )

    return ScoreReport(
        idea_id=idea.id,
        composite=composite,
        problem_quality=problem_quality,
        market_viability=market_viability,
        sentiment_signal=sentiment_signal,
        founder_fit=founder_fit,
        sentiment_flags=sentiment_flags,
        risks=risks,
        tarpit=tarpit_match,
        failure_matches=failure_matches,
        verdict=verdict,
        justification=" ".join(justification_parts),
    )

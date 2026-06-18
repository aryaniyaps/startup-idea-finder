"""
Mass signal analysis engine.

Takes raw signals, clusters them by underlying problem domain, applies
knowledge-graph frameworks, and derives problem statements with structured
evaluations.

Flow:
  1. Batch cluster signals via LLM → problem clusters
  2. Score each cluster using Hale/Friedman framework criteria
  3. Cross-reference with KG for tarpit/failure-mode detection
  4. Store derived problems with framework evaluation
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from scout.kg import KnowledgeGraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Batch clustering prompt
# ---------------------------------------------------------------------------

_CLUSTER_SYSTEM = """\
You are a startup idea analyst. Your job is to read raw signals (user complaints,
feature requests, discussion threads) and cluster them by the UNDERLYING PROBLEM
they point to.

A problem cluster represents a real pain point many people share. It should be:
- Specific: not "people want better software" but "SMB owners waste 4h/week on manual invoice reconciliation"
- Evidenced: grounded in the signals provided
- Actionable: something a startup could actually solve

Group signals that point to the SAME underlying problem. If a signal is noise or
doesn't point to a real problem, exclude it.

Return ONLY valid JSON — no preamble, no markdown fences."""


def _build_cluster_prompt(signals: list[dict]) -> str:
    """Build a clustering prompt for a batch of signals."""
    items = []
    for i, sig in enumerate(signals):
        text = sig.get("text", "") or sig.get("title", "")
        source = sig.get("source_type", "unknown")
        items.append(
            f"Signal {i + 1} (source: {source}):\n{text[:1500]}\n"
        )
    signal_block = "\n---\n".join(items)

    return f"""Analyze the following {len(signals)} signals and group them into
problem clusters.

{signal_block}

Return a JSON object with:
- "clusters": list of problem clusters, each with:
  - "problem_title": short title for the underlying problem
  - "problem_description": 2-3 sentence description
  - "signal_indices": list of 1-based indices of signals in this cluster
  - "severity": estimated severity 1-5 (1=minor, 5=critical/massive)
  - "category": one of ["workflow", "data", "integration", "compliance", "consumer", "developer_tool", "marketplace", "other"]
  - "affected_demographic": who suffers from this problem
- "excluded_indices": list of signal indices that don't point to real problems
"""


# ---------------------------------------------------------------------------
# Framework evaluation prompt (Hale + Friedman)
# ---------------------------------------------------------------------------

_FRAMEWORK_SYSTEM = """\
You evaluate startup problem statements using frameworks from leading startup
thinkers (Kevin Hale, Jared Friedman, Paul Graham, Marc Andreessen).

Evaluate each problem across multiple dimensions and return structured scores.
Be honest — not every problem is a good startup idea. Flag weaknesses aggressively.

Return ONLY valid JSON — no preamble, no markdown fences."""


def _build_framework_prompt(problems: list[dict], supplementary: list[dict] | None = None) -> str:
    """Build a framework evaluation prompt for batched problems."""
    problem_items = []
    for i, p in enumerate(problems):
        title = p.get("problem_title", p.get("title", ""))
        desc = p.get("problem_description", p.get("description", ""))
        problem_items.append(f"Problem {i + 1}: {title}\n{desc}")

    problem_block = "\n\n".join(problem_items)

    extra = ""
    if supplementary:
        frameworks = []
        for s in supplementary[:5]:
            label = s.get("title", s.get("label", ""))
            text = s.get("description", "")[:500]
            frameworks.append(f"- {label}: {text}")
        if frameworks:
            extra = "\n\nRelevant frameworks from startup literature:\n" + "\n".join(frameworks)

    return f"""Evaluate the following {len(problems)} problem statements using
these startup evaluation frameworks:{extra}

{problem_block}

For EACH problem, return:
1. problem_quality (Hale framework — 8 criteria, each 0-10):
   - urgency: how urgent is this problem?
   - pervasiveness: how many people have it?
   - frequency: how often does it occur?
   - cost_of_inaction: what happens if unsolved?
   - growth: is the affected population growing?
   - mandatory: must people solve this (legal/compliance)?
   - underserved: are existing solutions inadequate?
   - acuteness: how painful is it right now?

2. market_viability (Friedman framework — 6 criteria, each 0-10):
   - buyer_budget: can/will target users pay?
   - market_size: how large is the addressable market?
   - reach: how easy to reach these customers?
   - competition: how crowded is the space? (10 = no competition, 0 = dominated)
   - business_model: how clear is the path to revenue?
   - timing: is now the right time for this?

3. risks: list of specific risks for this problem/domain

4. tarpit_check: is this a known startup tarpit? (common but hard to solve,
   e.g. "social network for X", "marketplace", "AI wrapper with no moat")
   Return true/false and a brief explanation.

Return JSON:
{{
  "problem_1": {{
    "problem_quality": {{ "urgency": 7, ... }},
    "market_viability": {{ "buyer_budget": 5, ... }},
    "risks": ["risk 1", "risk 2"],
    "tarpit_check": {{ "is_tarpit": false, "reason": "..." }}
  }},
  "problem_2": {{ ... }}
}}
"""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DerivedProblem:
    """A problem derived from clustered signal analysis."""

    id: str
    title: str
    description: str
    category: str
    affected_demographic: str
    signal_count: int
    source_tiers: list[int]
    severity: float
    problem_quality: float
    market_viability: float
    composite_score: float
    framework_scores: dict  # raw LLM output per dimension
    risks: list[str]
    tarpit_check: dict | None
    failure_matches: list[str]
    innovative_solutions: list[dict] = field(default_factory=list)
    created_at: str = ""

    def to_row(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "affected_demographic": self.affected_demographic,
            "signal_count": self.signal_count,
            "source_tiers": json.dumps(self.source_tiers),
            "severity": self.severity,
            "problem_quality": self.problem_quality,
            "market_viability": self.market_viability,
            "composite_score": self.composite_score,
            "framework_scores": json.dumps(self.framework_scores),
            "risks": json.dumps(self.risks),
            "tarpit_check": json.dumps(self.tarpit_check) if self.tarpit_check else None,
            "failure_matches": json.dumps(self.failure_matches),
            "innovative_solutions": json.dumps(self.innovative_solutions),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# LLM helper (shared with scoring.py pattern, duplicated to avoid circular imports)
# ---------------------------------------------------------------------------

import re as _re


async def _llm_json(
    client: AsyncOpenAI,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4000,
    temperature: float = 0.3,
) -> dict[str, Any]:
    """Single JSON-mode LLM call with retries."""
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
            raw = raw.strip()
            if raw.startswith("```"):
                raw = _re.sub(r"^```(?:json)?\s*", "", raw)
                raw = _re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            last_exc = exc
            logger.warning("LLM JSON parse attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(0.5 * (attempt + 1))
        except Exception:
            raise

    raise ValueError(f"LLM JSON parsing failed after 3 attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def cluster_signals(
    signals: list[dict],
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
    batch_size: int = 15,
) -> list[dict]:
    """Cluster raw signals into problem groups.

    Args:
        signals: List of signal dicts with 'text', 'source_type', 'id'
        client: OpenAI async client
        model: Model to use
        batch_size: Max signals per clustering call

    Returns:
        List of problem cluster dicts with 'problem_title', 'problem_description',
        'signal_indices', 'severity', 'category', 'affected_demographic'
    """
    if not signals:
        return []

    all_clusters: list[dict] = []

    # Process in batches
    for batch_start in range(0, len(signals), batch_size):
        batch = signals[batch_start:batch_start + batch_size]
        offset = batch_start  # for translating indices

        prompt = _build_cluster_prompt(batch)
        try:
            result = await _llm_json(client, model, _CLUSTER_SYSTEM, prompt, max_tokens=4000)
        except Exception:
            logger.warning("Signal clustering failed for batch %d", batch_start, exc_info=True)
            continue

        clusters = result.get("clusters", [])
        for c in clusters:
            # Translate 1-based indices to original signal IDs
            indices = c.get("signal_indices", [])
            c["signal_ids"] = []
            for idx in indices:
                sig_idx = idx - 1 + offset
                if 0 <= sig_idx < len(signals):
                    c["signal_ids"].append(signals[sig_idx].get("id"))
            c["signal_count"] = len(c["signal_ids"])
            all_clusters.append(c)

    return all_clusters


async def evaluate_problems(
    problems: list[dict],
    kg: KnowledgeGraph,
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> list[DerivedProblem]:
    """Evaluate problem clusters using startup frameworks.

    Args:
        problems: List of problem cluster dicts from cluster_signals()
        kg: Knowledge graph for tarpit/failure-mode lookups
        client: OpenAI async client
        model: Model to use

    Returns:
        List of DerivedProblem objects with full framework evaluation
    """
    if not problems:
        return []

    # Get supplementary framework nodes from KG
    supplementary = kg.get_deep_dive_frameworks("problem evaluation")

    prompt = _build_framework_prompt(problems, supplementary)
    try:
        result = await _llm_json(client, model, _FRAMEWORK_SYSTEM, prompt, max_tokens=8000)
    except Exception:
        logger.warning("Framework evaluation failed", exc_info=True)
        return []

    import hashlib

    derived: list[DerivedProblem] = []
    now = datetime.now(timezone.utc).isoformat()

    for i, problem in enumerate(problems):
        key = f"problem_{i + 1}"
        scores = result.get(key, {})
        if not scores:
            continue

        pq = scores.get("problem_quality", {})
        mv = scores.get("market_viability", {})

        PQ_KEYS = [
            "urgency", "pervasiveness", "frequency", "cost_of_inaction",
            "growth", "mandatory", "underserved", "acuteness",
        ]
        MV_KEYS = [
            "buyer_budget", "market_size", "reach", "competition",
            "business_model", "timing",
        ]

        pq_sum = sum(float(pq.get(k, 5)) for k in PQ_KEYS)
        mv_sum = sum(float(mv.get(k, 5)) for k in MV_KEYS)

        problem_quality = round((pq_sum / 80) * 100, 1)
        market_viability = round((mv_sum / 60) * 100, 1)
        composite = round(problem_quality * 0.6 + market_viability * 0.4, 1)

        risks = scores.get("risks", [])
        tarpit_check = scores.get("tarpit_check")

        # KG lookups
        combined_text = (
            problem.get("problem_title", "")
            + " "
            + problem.get("problem_description", "")
        )
        failure_matches = _check_failure_modes_kg(combined_text, kg)

        problem_id = hashlib.sha256(
            problem.get("problem_title", "").encode()
        ).hexdigest()[:12]

        dp = DerivedProblem(
            id=f"dp-{problem_id}",
            title=problem.get("problem_title", "Untitled"),
            description=problem.get("problem_description", ""),
            category=problem.get("category", "other"),
            affected_demographic=problem.get("affected_demographic", "unknown"),
            signal_count=problem.get("signal_count", 0),
            source_tiers=problem.get("source_tiers", []),
            severity=float(problem.get("severity", 3)),
            problem_quality=problem_quality,
            market_viability=market_viability,
            composite_score=composite,
            framework_scores=scores,
            risks=risks if isinstance(risks, list) else [],
            tarpit_check=tarpit_check,
            failure_matches=failure_matches,
            created_at=now,
        )
        derived.append(dp)

    return derived


def _check_failure_modes_kg(text: str, kg: KnowledgeGraph, threshold: float = 0.3) -> list[str]:
    """Check knowledge-graph pre-launch failure modes against problem text."""
    import re as _re2

    modes = kg.get_pre_launch_failure_modes()
    matches: list[str] = []
    text_lower = text.lower()

    for mode in modes:
        mode_text = (mode.get("description", "") + " " + mode.get("label", "")).lower()
        # Simple keyword overlap
        words_a = set(_re2.findall(r"[a-z]{4,}", text_lower))
        words_b = set(_re2.findall(r"[a-z]{4,}", mode_text))
        if not words_a or not words_b:
            continue
        overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
        if overlap >= threshold:
            label = mode.get("label", mode.get("title", "unknown"))
            matches.append(f"{label}({overlap:.2f})")

    return matches[:5]

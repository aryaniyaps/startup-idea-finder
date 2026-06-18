"""
First Principles + Inversion innovation layer.

Takes derived problem statements and applies two complementary
thinking frameworks to generate novel, out-of-box solutions:

1. First Principles Thinking
   - Deconstruct the problem to fundamental truths
   - Question every assumption
   - Rebuild solutions from the ground up
   - Used by: Elon Musk, Aristotle, Johannes Gutenberg

2. Inversion Thinking
   - "What would make this problem worse?"
   - "What's the opposite of the conventional solution?"
   - "What if we deliberately failed?"
   - Used by: Charlie Munger, Carl Jacobi ("invert, always invert")

The output is a set of innovative solution directions with
rationale grounded in the original problem analysis.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

from scout.kg import KnowledgeGraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# First Principles system prompt
# ---------------------------------------------------------------------------

_FIRST_PRINCIPLES_SYSTEM = """\
You are an innovation strategist specializing in First Principles thinking.

First Principles Thinking means breaking down a complex problem into its most
basic, fundamental elements — truths that cannot be deduced further — and then
reassembling them from the ground up to create novel solutions.

Your task:
1. Identify the FUNDAMENTAL TRUTHS of this problem domain (not assumptions, not conventions)
2. Question EVERY assumption the industry takes for granted
3. Deconstruct to atomic components
4. Rebuild solutions from these fundamentals, ignoring existing solutions entirely
5. Generate 3-5 innovative solution directions

Key principle: If everyone is solving the problem the same way, the assumptions
they share are where the opportunity lies.

Return ONLY valid JSON — no preamble, no markdown fences."""


_INVERSION_SYSTEM = """\
You are an innovation strategist specializing in Inversion Thinking.

Inversion Thinking (from Carl Jacobi: "invert, always invert") means approaching
a problem backward — instead of asking "how do I solve this?", ask:
- "What would guarantee failure?"
- "What's the opposite of what everyone does?"
- "How could I make this problem 10x worse?"
- "What assumptions, if reversed, create opportunity?"

Your task:
1. Identify the DOMINANT APPROACH everyone uses for this problem
2. Invert each assumption to find counter-intuitive angles
3. Ask "what if the opposite were true?" for each constraint
4. Generate 3-5 innovative solution directions from inversions

Key principle: The best solutions often come from doing the opposite of
what conventional wisdom says. If everyone is going left, look right.

Return ONLY valid JSON — no preamble, no markdown fences."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class InnovationDirection:
    """A single innovative solution direction."""

    title: str
    description: str
    approach: str  # "first_principles" or "inversion"
    fundamental_insight: str  # What truth or inversion led here
    feasibility: float  # 0-1
    novelty: float  # 0-1
    impact: float  # 0-1


@dataclass
class InnovationReport:
    """Complete innovation analysis for a problem."""

    problem_id: str
    first_principles_analysis: str  # Narrative
    inversion_analysis: str  # Narrative
    assumptions_challenged: list[str]
    fundamental_truths: list[str]
    inverted_constraints: list[str]
    solutions: list[InnovationDirection]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def _build_first_principles_prompt(problem: dict) -> str:
    title = problem.get("problem_title", problem.get("title", ""))
    desc = problem.get("problem_description", problem.get("description", ""))
    category = problem.get("category", "unknown")
    demographic = problem.get("affected_demographic", "unknown users")

    return f"""Apply First Principles Thinking to this problem.

## Problem
Title: {title}
Description: {desc}
Category: {category}
Affected: {demographic}

## Process

### Step 1: Deconstruct to Fundamentals
What are the IRREDUCIBLE truths about this problem domain?
(Not conventions, not "how it's done" — fundamental physics/psychology/economics truths)

### Step 2: Question Assumptions
List 5-10 assumptions the industry makes about this problem.
Then mark which ones are actually testable vs. just conventional wisdom.

### Step 3: Rebuild from Fundamentals
If you knew nothing about existing solutions and started only from
the fundamental truths, what would you build?

### Step 4: Generate Solutions
Create 3-5 innovative solution directions. For each:
- What fundamental truth does it leverage?
- How is it different from existing approaches?
- What would need to be true for it to work?

Return JSON:
{{
  "analysis": "<2-3 paragraph first principles analysis>",
  "assumptions_challenged": ["<assumption>", ...],
  "fundamental_truths": ["<irreducible truth>", ...],
  "solutions": [
    {{
      "title": "<solution name>",
      "description": "<1-2 sentence description>",
      "fundamental_insight": "<what truth this leverages>",
      "feasibility": <0.0-1.0>,
      "novelty": <0.0-1.0>,
      "impact": <0.0-1.0>
    }},
    ...
  ]
}}"""


def _build_inversion_prompt(problem: dict) -> str:
    title = problem.get("problem_title", problem.get("title", ""))
    desc = problem.get("problem_description", problem.get("description", ""))
    category = problem.get("category", "unknown")

    return f"""Apply Inversion Thinking to this problem.

## Problem
Title: {title}
Description: {desc}
Category: {category}

## Inversion Process

### Step 1: The Dominant Approach
What's the CONVENTIONAL way everyone tries to solve this?
Describe the standard playbook.

### Step 2: How To Guarantee Failure
List 5-10 specific actions that would guarantee this solution fails.
Be brutally honest — these reveal what actually matters.

### Step 3: Invert the Assumptions
For each industry assumption, ask: "What if the opposite were true?"
- What if the problem is actually a feature?
- What if the customer doesn't want a solution?
- What if the constraint everyone accepts is artificial?
- What if you should make it MORE expensive, not cheaper?
- What if the "wrong" customer is actually right?

### Step 4: Generate Inverted Solutions
Create 3-5 solution directions by inverting conventional wisdom.
For each:
- What assumption did you invert?
- What counter-intuitive approach does this unlock?
- What evidence suggests this could work?

Return JSON:
{{
  "analysis": "<2-3 paragraph inversion analysis>",
  "dominant_approach": "<summary of conventional solution>",
  "inverted_constraints": ["<inverted assumption>", ...],
  "solutions": [
    {{
      "title": "<solution name>",
      "description": "<1-2 sentence description>",
      "fundamental_insight": "<what inversion unlocked this>",
      "feasibility": <0.0-1.0>,
      "novelty": <0.0-1.0>,
      "impact": <0.0-1.0>
    }},
    ...
  ]
}}"""


# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------


async def _llm_json(
    client: AsyncOpenAI,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4000,
    temperature: float = 0.5,  # Slightly higher for creativity
) -> dict[str, Any]:
    import re as _re
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
            logger.warning("Innovation LLM parse attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(0.5 * (attempt + 1))
        except Exception:
            raise
    raise ValueError(f"Innovation LLM parsing failed after 3 attempts: {last_exc}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_innovations(
    problem: dict,
    kg: KnowledgeGraph,
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> InnovationReport:
    """Generate innovative solutions using First Principles + Inversion thinking.

    Runs both analyses concurrently, then merges results.

    Args:
        problem: Problem dict with problem_title, problem_description, category, etc.
        kg: Knowledge graph for supplementary framework context
        client: OpenAI async client
        model: Model to use

    Returns:
        InnovationReport with combined analysis and solution directions
    """
    fp_prompt = _build_first_principles_prompt(problem)
    inv_prompt = _build_inversion_prompt(problem)

    fp_result, inv_result = await asyncio.gather(
        _llm_json(client, model, _FIRST_PRINCIPLES_SYSTEM, fp_prompt, temperature=0.6),
        _llm_json(client, model, _INVERSION_SYSTEM, inv_prompt, temperature=0.6),
        return_exceptions=True,
    )

    # Handle failures gracefully
    if isinstance(fp_result, Exception):
        logger.warning("First principles analysis failed: %s", fp_result)
        fp_result = {
            "analysis": "Analysis failed.",
            "assumptions_challenged": [],
            "fundamental_truths": [],
            "solutions": [],
        }

    if isinstance(inv_result, Exception):
        logger.warning("Inversion analysis failed: %s", inv_result)
        inv_result = {
            "analysis": "Analysis failed.",
            "dominant_approach": "Unknown",
            "inverted_constraints": [],
            "solutions": [],
        }

    # Parse solutions from both analyses
    all_solutions: list[InnovationDirection] = []

    for sol in fp_result.get("solutions", []):
        if isinstance(sol, dict):
            all_solutions.append(InnovationDirection(
                title=sol.get("title", "Untitled"),
                description=sol.get("description", ""),
                approach="first_principles",
                fundamental_insight=sol.get("fundamental_insight", ""),
                feasibility=float(sol.get("feasibility", 0.5)),
                novelty=float(sol.get("novelty", 0.5)),
                impact=float(sol.get("impact", 0.5)),
            ))

    for sol in inv_result.get("solutions", []):
        if isinstance(sol, dict):
            all_solutions.append(InnovationDirection(
                title=sol.get("title", "Untitled"),
                description=sol.get("description", ""),
                approach="inversion",
                fundamental_insight=sol.get("fundamental_insight", ""),
                feasibility=float(sol.get("feasibility", 0.5)),
                novelty=float(sol.get("novelty", 0.5)),
                impact=float(sol.get("impact", 0.5)),
            ))

    # Sort by impact * novelty (most innovative + impactful first)
    all_solutions.sort(key=lambda s: s.impact * s.novelty, reverse=True)

    problem_id = problem.get("id", "unknown")

    return InnovationReport(
        problem_id=problem_id,
        first_principles_analysis=fp_result.get("analysis", ""),
        inversion_analysis=inv_result.get("analysis", ""),
        assumptions_challenged=fp_result.get("assumptions_challenged", []),
        fundamental_truths=fp_result.get("fundamental_truths", []),
        inverted_constraints=inv_result.get("inverted_constraints", []),
        solutions=all_solutions,
    )


def innovation_solutions_to_dicts(report: InnovationReport) -> list[dict]:
    """Convert InnovationReport solutions to dicts for storage."""
    return [
        {
            "title": s.title,
            "description": s.description,
            "approach": s.approach,
            "fundamental_insight": s.fundamental_insight,
            "feasibility": s.feasibility,
            "novelty": s.novelty,
            "impact": s.impact,
            "composite": round(s.impact * s.novelty * 100, 1),
        }
        for s in report.solutions
    ]

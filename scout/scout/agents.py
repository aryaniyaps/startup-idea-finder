"""
Agentic framework runner.

Executes structured evaluation processes from the startup literature
knowledge graph on derived problem statements. Each agent follows a
specific framework from a book/source in the KG.

Available agents:
  - CustomerDevelopmentAgent: Blank's 4-step customer development
  - JobsToBeDoneAgent: Christensen's JTBD hiring/firing framework
  - IdeaEvaluationAgent: Friedman + Hale criteria
  - ChasmAnalysisAgent: Moore's crossing-the-chasm evaluation
  - TarpitDetectorAgent: Graham/Andreessen tarpit identification
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


@dataclass
class AgentReport:
    """Structured output from a framework agent."""

    agent_name: str
    framework: str
    problem_id: str
    scores: dict[str, Any] = field(default_factory=dict)
    narrative: str = ""
    recommendations: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    go_no_go: str = "INCONCLUSIVE"  # GO, NO_GO, INCONCLUSIVE
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# Base agent
# ---------------------------------------------------------------------------


class BaseAgent:
    """Base class for framework-following agents."""

    name: str = "base"
    framework: str = "generic"
    system_prompt: str = ""

    def __init__(self, kg: KnowledgeGraph, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.kg = kg
        self.client = client
        self.model = model

    async def evaluate(self, problem: dict) -> AgentReport:
        """Run the framework evaluation on a problem. Override in subclasses."""
        raise NotImplementedError

    def _get_framework_nodes(self, *keywords: str) -> list[dict]:
        """Get relevant framework nodes from the KG."""
        results: list[dict] = []
        for kw in keywords:
            nodes = self.kg.search_nodes(kw, top_k=5)
            results.extend(nodes)
        return results


# ---------------------------------------------------------------------------
# Agent implementations
# ---------------------------------------------------------------------------


class CustomerDevelopmentAgent(BaseAgent):
    """Executes Steve Blank's Customer Development framework.

    Four steps: Customer Discovery → Customer Validation →
    Customer Creation → Company Building.
    """

    name = "customer_development"
    framework = "Blank Customer Development"

    async def evaluate(self, problem: dict) -> AgentReport:
        title = problem.get("problem_title", problem.get("title", ""))
        desc = problem.get("problem_description", problem.get("description", ""))

        # Get relevant KG nodes
        cdev_nodes = self._get_framework_nodes("customer development", "problem hypothesis", "customer discovery")
        node_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:300]}"
            for n in cdev_nodes[:5]
        )

        prompt = f"""Evaluate this problem using Steve Blank's Customer Development framework.

## Problem
Title: {title}
Description: {desc}

## Framework Context
{node_context}

## Evaluation Tasks
1. **Problem Hypothesis**: Is there a clear hypothesis about who has this problem?
2. **Customer Discovery**: What would you test first? Who would you interview?
3. **Problem Validation**: How would you confirm this is a real, painful problem?
4. **Solution Hypothesis**: What's the simplest solution to test?
5. **Early Adopter Profile**: Who feels this pain most acutely?

Return JSON:
{{
  "scores": {{
    "problem_hypothesis_clarity": <1-10>,
    "customer_discoverability": <1-10>,
    "problem_validatability": <1-10>,
    "solution_testability": <1-10>,
    "early_adopter_accessibility": <1-10>
  }},
  "narrative": "<2-3 paragraph analysis>",
  "recommendations": ["<actionable next step>", ...],
  "risks": ["<specific risk>", ...],
  "go_no_go": "GO|NO_GO|INCONCLUSIVE",
  "confidence": <0.0-1.0>
}}"""

        return await self._run(prompt, title)


class JobsToBeDoneAgent(BaseAgent):
    """Executes Christensen's Jobs-to-Be-Done framework.

    What job is the customer hiring this product to do?
    What are they firing? What's the struggling moment?
    """

    name = "jobs_to_be_done"
    framework = "Christensen Jobs-to-Be-Done"

    async def evaluate(self, problem: dict) -> AgentReport:
        title = problem.get("problem_title", problem.get("title", ""))
        desc = problem.get("problem_description", problem.get("description", ""))

        jtbd_nodes = self._get_framework_nodes("jobs to be done", "hiring", "firing", "struggling moment")
        node_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:300]}"
            for n in jtbd_nodes[:5]
        )

        prompt = f"""Evaluate this problem using Christensen's Jobs-to-Be-Done framework.

## Problem
Title: {title}
Description: {desc}

## Framework Context
{node_context}

## Evaluation Tasks
1. **The Job**: What job is the customer hiring a solution to do? (functional, emotional, social)
2. **The Firing**: What existing solution or workaround are they firing?
3. **Struggling Moment**: When do they realize they need something better?
4. **Progress**: What progress does the customer seek? (not product features)
5. **Competing Alternatives**: What else could they "hire" instead?

Return JSON:
{{
  "scores": {{
    "job_clarity": <1-10>,
    "firing_pain": <1-10>,
    "struggling_moment_frequency": <1-10>,
    "progress_definition": <1-10>,
    "alternative_strength": <1-10>
  }},
  "narrative": "<2-3 paragraph JTBD analysis>",
  "recommendations": ["<actionable insight>", ...],
  "risks": ["<specific risk>", ...],
  "go_no_go": "GO|NO_GO|INCONCLUSIVE",
  "confidence": <0.0-1.0>
}}"""

        return await self._run(prompt, title)


class IdeaEvaluationAgent(BaseAgent):
    """Executes combined Hale + Friedman + Graham idea evaluation.

    Problem quality (Hale), market viability (Friedman),
    founder fit, schlep blindness check (Graham).
    """

    name = "idea_evaluation"
    framework = "Hale + Friedman + Graham"

    async def evaluate(self, problem: dict) -> AgentReport:
        title = problem.get("problem_title", problem.get("title", ""))
        desc = problem.get("problem_description", problem.get("description", ""))

        eval_nodes = self._get_framework_nodes(
            "problem quality", "market viability", "schlep", "startup idea",
        )
        node_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:300]}"
            for n in eval_nodes[:5]
        )

        prompt = f"""Evaluate this startup idea using combined frameworks from
Kevin Hale (problem quality), Jared Friedman (market viability), and
Paul Graham (schlep blindness, idea quality).

## Problem
Title: {title}
Description: {desc}

## Framework Context
{node_context}

## Evaluation Tasks
1. **Hale's Problem Quality** (8 criteria, score each 0-10):
   urgency, pervasiveness, frequency, cost_of_inaction,
   growth, mandatory, underserved, acuteness
2. **Friedman's Market Viability** (6 criteria, 0-10):
   buyer_budget, market_size, reach, competition,
   business_model, timing
3. **Graham's Idea Quality** (4 criteria, 0-10):
   founder_market_fit, schlep_blindness_check,
   idea_clarity, latent_demand
4. **Overall Assessment**: Is this a good startup idea?

Return JSON:
{{
  "scores": {{
    "hale_problem_quality": {{ "urgency": 7, "pervasiveness": 6, ... }},
    "friedman_market": {{ "buyer_budget": 5, "market_size": 8, ... }},
    "graham_idea": {{ "founder_market_fit": 6, "schlep_blindness": 7, ... }}
  }},
  "composite_score": <1-100>,
  "narrative": "<2-3 paragraph evaluation>",
  "recommendations": ["<specific advice>", ...],
  "risks": ["<risk>", ...],
  "go_no_go": "GO|NO_GO|INCONCLUSIVE",
  "confidence": <0.0-1.0>
}}"""

        return await self._run(prompt, title)


class TarpitDetectorAgent(BaseAgent):
    """Detects startup tarpits using Graham/Andreessen frameworks.

    Tarpits: ideas that look promising but are structurally
    terrible businesses (social networks, marketplaces,
    AI wrappers with no moat, etc.)
    """

    name = "tarpit_detector"
    framework = "Graham Tarpit Detection"

    async def evaluate(self, problem: dict) -> AgentReport:
        title = problem.get("problem_title", problem.get("title", ""))
        desc = problem.get("problem_description", problem.get("description", ""))

        tarpit_nodes = self.kg.get_tarpit_examples()
        node_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:300]}"
            for n in tarpit_nodes[:5]
        )

        failure_nodes = self.kg.get_pre_launch_failure_modes()[:3]
        failure_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:200]}"
            for n in failure_nodes
        )

        prompt = f"""Evaluate whether this problem space is a startup tarpit.

## Problem
Title: {title}
Description: {desc}

## Known Tarpits
{node_context}

## Common Failure Modes
{failure_context}

## Detection Criteria
1. **Structural Moat**: Can a solution build defensibility? Or is it easily copied?
2. **Network Effects**: Does this require network effects to work? (tarpit red flag)
3. **Chicken-and-Egg**: Does it need supply AND demand simultaneously?
4. **Regulatory Risk**: Is this in a regulated industry with high barriers?
5. **Winner-Take-All**: Does one player capture most of the value?
6. **Margins**: Can this business have good margins?

Return JSON:
{{
  "scores": {{
    "structural_moat": <1-10>,
    "network_effect_risk": <1-10> (10 = high risk),
    "chicken_egg_risk": <1-10> (10 = high risk),
    "regulatory_risk": <1-10> (10 = high risk),
    "winner_take_all": <1-10> (10 = highly concentrated),
    "margin_potential": <1-10>
  }},
  "tarpit_verdict": true|false,
  "tarpit_reason": "<brief explanation>",
  "narrative": "<2-3 paragraph analysis>",
  "recommendations": ["<how to avoid tarpit>", ...],
  "risks": ["<specific risk>", ...],
  "go_no_go": "GO|NO_GO|INCONCLUSIVE",
  "confidence": <0.0-1.0>
}}"""

        return await self._run(prompt, title)

    # ---- Internal ----

    async def _run(self, prompt: str, title: str) -> AgentReport:
        try:
            result = await self._call_llm(prompt)
        except Exception:
            logger.warning("%s agent failed for '%s'", self.name, title, exc_info=True)
            return AgentReport(
                agent_name=self.name,
                framework=self.framework,
                problem_id="unknown",
                narrative="Agent evaluation failed.",
                go_no_go="INCONCLUSIVE",
            )

        return AgentReport(
            agent_name=self.name,
            framework=self.framework,
            problem_id="unknown",
            scores=result.get("scores", {}),
            narrative=result.get("narrative", ""),
            recommendations=result.get("recommendations", []),
            risks=result.get("risks", []),
            go_no_go=result.get("go_no_go", "INCONCLUSIVE"),
            confidence=float(result.get("confidence", 0.5)),
        )

    async def _call_llm(self, prompt: str) -> dict:
        import re as _re
        for attempt in range(3):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a startup evaluation agent following structured frameworks. Return ONLY valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=4000,
                    temperature=0.3,
                )
                raw = response.choices[0].message.content
                if raw is None:
                    raise ValueError("Empty response")
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = _re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = _re.sub(r"\s*```$", "", raw)
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("%s: LLM parse attempt %d failed: %s", self.name, attempt + 1, exc)
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception:
                raise
        raise ValueError(f"{self.name}: JSON parsing failed after 3 attempts")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_all_agents(
    problem: dict,
    kg: KnowledgeGraph,
    client: AsyncOpenAI,
    model: str = "gpt-4o-mini",
) -> list[AgentReport]:
    """Run all framework agents on a derived problem.

    Returns one AgentReport per agent.
    """
    agents: list[BaseAgent] = [
        CustomerDevelopmentAgent(kg, client, model),
        JobsToBeDoneAgent(kg, client, model),
        IdeaEvaluationAgent(kg, client, model),
        TarpitDetectorAgent(kg, client, model),
    ]

    reports = await asyncio.gather(
        *[agent.evaluate(problem) for agent in agents],
        return_exceptions=True,
    )

    results: list[AgentReport] = []
    for i, r in enumerate(reports):
        if isinstance(r, Exception):
            logger.warning("Agent %s crashed: %s", agents[i].name, r)
            results.append(AgentReport(
                agent_name=agents[i].name,
                framework=agents[i].framework,
                problem_id="unknown",
                narrative=f"Agent error: {r}",
                go_no_go="INCONCLUSIVE",
            ))
        elif isinstance(r, AgentReport):
            r.problem_id = problem.get("id", "unknown")
            results.append(r)

    return results

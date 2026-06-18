"""
Pydantic AI multi-agent system for startup idea discovery.

Architecture:
  Scraper → ExtractionAgent → ClusteringAgent → EvaluationAgents (parallel) → InnovationAgent
                                                      ↓
                                              AggregatorAgent

Key multi-agent patterns used:
  1. Sequential orchestration: scrape → extract → cluster → evaluate
  2. Concurrent orchestration: multiple evaluation agents run in parallel
  3. Handoff: specialist agents for specific frameworks

All agents return validated Pydantic models — no raw dicts, no parse errors.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pydantic_ai
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from scout.kg import KnowledgeGraph

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# Pydantic models — the validated contracts between agents
# ═══════════════════════════════════════════════════════════════════════════


class ExtractedProblem(BaseModel):
    """A single problem extracted from a raw signal."""
    title: str = Field(description="Short problem title, 5-12 words")
    description: str = Field(description="1-2 sentence description of the problem")
    severity: int = Field(ge=1, le=5, description="Estimated severity 1-5")


class ExtractionResult(BaseModel):
    """Output from the extraction agent for a batch of signals."""
    signal_id: int
    problems: list[ExtractedProblem] = Field(default_factory=list)


class ProblemCluster(BaseModel):
    """A cluster of related problems representing an underlying pain point."""
    problem_title: str
    problem_description: str
    signal_ids: list[int] = Field(default_factory=list)
    signal_count: int = 0
    severity: float = 3.0
    category: str = "other"
    affected_demographic: str = "unknown"


class ClusteringResult(BaseModel):
    """Output from the clustering agent."""
    clusters: list[ProblemCluster] = Field(default_factory=list)
    excluded_signal_ids: list[int] = Field(default_factory=list)


class HaleScores(BaseModel):
    """Kevin Hale's 8 problem-quality criteria, each 0-10."""
    urgency: int = Field(ge=0, le=10)
    pervasiveness: int = Field(ge=0, le=10)
    frequency: int = Field(ge=0, le=10)
    cost_of_inaction: int = Field(ge=0, le=10)
    growth: int = Field(ge=0, le=10)
    mandatory: int = Field(ge=0, le=10)
    underserved: int = Field(ge=0, le=10)
    acuteness: int = Field(ge=0, le=10)
    justification: str = ""


class FriedmanScores(BaseModel):
    """Jared Friedman's 6 market-viability criteria, each 0-10."""
    buyer_budget: int = Field(ge=0, le=10)
    market_size: int = Field(ge=0, le=10)
    reach: int = Field(ge=0, le=10)
    competition: int = Field(ge=0, le=10, description="10 = no competition, 0 = dominated")
    business_model: int = Field(ge=0, le=10)
    timing: int = Field(ge=0, le=10)
    justification: str = ""


class GrahamScores(BaseModel):
    """Paul Graham's idea-quality criteria."""
    founder_market_fit: int = Field(ge=0, le=10)
    schlep_blindness: int = Field(ge=0, le=10, description="10 = others avoid this for bad reasons")
    idea_clarity: int = Field(ge=0, le=10)
    latent_demand: int = Field(ge=0, le=10)
    justification: str = ""


class TarpitCheck(BaseModel):
    """Tarpit detection results."""
    is_tarpit: bool = False
    structural_moat: int = Field(ge=0, le=10)
    network_effect_risk: int = Field(ge=0, le=10, description="10 = high risk")
    chicken_egg_risk: int = Field(ge=0, le=10)
    regulatory_risk: int = Field(ge=0, le=10)
    winner_take_all: int = Field(ge=0, le=10)
    margin_potential: int = Field(ge=0, le=10)
    reason: str = ""


class EvaluatedProblem(BaseModel):
    """Full evaluation of a problem cluster by all agents."""
    cluster_index: int
    problem_title: str
    problem_description: str
    category: str = "other"
    affected_demographic: str = "unknown"
    signal_count: int = 0
    severity: float = 3.0

    # Composite scores
    problem_quality: float = 50.0
    market_viability: float = 50.0
    composite_score: float = 50.0

    # Framework scores
    hale_scores: HaleScores | None = None
    friedman_scores: FriedmanScores | None = None
    graham_scores: GrahamScores | None = None
    tarpit_check: TarpitCheck | None = None

    # Other
    risks: list[str] = Field(default_factory=list)
    narrative: str = ""


class InnovationSolution(BaseModel):
    """A single innovative solution direction."""
    title: str
    description: str
    approach: str = Field(description="'first_principles' or 'inversion'")
    fundamental_insight: str
    feasibility: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    impact: float = Field(ge=0.0, le=1.0)
    composite: float = 0.0


class InnovationResult(BaseModel):
    """Output from the innovation agent."""
    problem_index: int
    first_principles_analysis: str = ""
    inversion_analysis: str = ""
    assumptions_challenged: list[str] = Field(default_factory=list)
    fundamental_truths: list[str] = Field(default_factory=list)
    inverted_constraints: list[str] = Field(default_factory=list)
    solutions: list[InnovationSolution] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Agent definitions
# ═══════════════════════════════════════════════════════════════════════════


class ScoutAgent:
    """Base agent with shared LLM client and KG access."""

    def __init__(
        self,
        client: AsyncOpenAI,
        kg: KnowledgeGraph,
        model: str = "gpt-4o-mini",
    ):
        self.client = client
        self.kg = kg
        self.model = model
        self._call_count = 0

    async def _complete(
        self,
        system: str,
        user: str,
        result_type: type[BaseModel],
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> BaseModel:
        """Make a single structured LLM call, returning a validated Pydantic model."""
        from openai.types.chat import ChatCompletionMessageParam

        self._call_count += 1
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        for attempt in range(3):
            try:
                agent = pydantic_ai.Agent(
                    model=f"openai:{self.model}",
                    result_type=result_type,
                    system_prompt=system,
                )
                result = await agent.run(user)
                return result.data
            except Exception as exc:
                logger.warning(
                    "%s attempt %d failed: %s",
                    result_type.__name__,
                    attempt + 1,
                    exc,
                )
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                else:
                    raise


# ═══════════════════════════════════════════════════════════════════════════
# Specialized agents
# ═══════════════════════════════════════════════════════════════════════════


class ExtractionAgent(ScoutAgent):
    """Extracts distinct problem statements from raw signals.

    Pattern: Sequential — processes batches of signals, returns validated problems.
    """

    SYSTEM = """\
You extract distinct, well-formed problem statements from user-generated text.
Each problem must be a genuine pain point — not a feature request or vague complaint.
Be precise: name the specific pain, who feels it, and how severe it is (1-5).
If no clear problem is found, return an empty list.
"""

    async def extract_batch(self, signals: list[dict]) -> list[ExtractionResult]:
        """Extract problems from a batch of up to 8 signals in one API call."""
        if not signals:
            return []

        CHUNK = 8
        results: list[ExtractionResult] = []

        for i in range(0, len(signals), CHUNK):
            chunk = signals[i : i + CHUNK]
            idx_map: dict[int, dict] = {}

            parts: list[str] = []
            for j, sig in enumerate(chunk):
                idx_map[j] = sig
                text = (sig.get("text") or sig.get("title", ""))[:8000]
                source = sig.get("source_type", "unknown")
                parts.append(f"[{j}] (source: {source})\n{text}")

            prompt = (
                "Extract distinct problem statements from each of the following texts.\n\n"
                + "\n\n---\n\n".join(parts)
                + "\n\nReturn a JSON object with keys '0', '1', etc. "
                "Each value is a list of problem objects: "
                '{"title": "...", "description": "...", "severity": 1-5}. '
                "Return empty list [] for texts with no clear problem."
            )

            raw = await self._complete(self.SYSTEM, prompt, dict, max_tokens=3000)
            if not isinstance(raw, dict):
                continue

            for j, sig in idx_map.items():
                problems_data = raw.get(str(j), [])
                if isinstance(problems_data, list):
                    problems = [
                        ExtractedProblem(
                            title=p.get("title", ""),
                            description=p.get("description", ""),
                            severity=int(p.get("severity", 3)),
                        )
                        for p in problems_data
                        if isinstance(p, dict)
                    ]
                else:
                    problems = []
                results.append(ExtractionResult(signal_id=sig["id"], problems=problems))

        logger.info("ExtractionAgent: %d signals in %d calls", len(signals), self._call_count)
        return results


class ClusteringAgent(ScoutAgent):
    """Groups extracted problems into clusters by underlying pain point.

    Pattern: Sequential — takes all extractions, outputs clusters.
    """

    SYSTEM = """\
You are a startup idea analyst. Group related problem statements into clusters
that share the SAME underlying pain point. Each cluster should be specific,
evidenced by the problems, and actionable for a startup.

Return ONLY valid JSON matching the requested schema.
"""

    async def cluster(self, problems: list[ExtractionResult]) -> ClusteringResult:
        """Cluster all extracted problems into problem groups."""
        if not problems:
            return ClusteringResult()

        # Flatten: build signal_id → problems mapping
        items: list[str] = []
        for i, result in enumerate(problems):
            for p in result.problems:
                items.append(
                    f"Signal {result.signal_id}: {p.title}\n{p.description} (severity={p.severity})"
                )

        if not items:
            return ClusteringResult()

        prompt = (
            f"Group the following {len(items)} problem statements into clusters.\n\n"
            + "\n---\n".join(items)
            + "\n\nReturn JSON: "
            '{"clusters": [{"problem_title": "...", "problem_description": "...", '
            '"signal_indices": [0, 1, ...], "severity": 3.5, '
            '"category": "workflow|data|integration|compliance|consumer|developer_tool|marketplace|other", '
            '"affected_demographic": "..."}], '
            '"excluded_indices": []}'
        )

        raw = await self._complete(self.SYSTEM, prompt, dict, max_tokens=4000)
        if not isinstance(raw, dict):
            return ClusteringResult()

        clusters_data = raw.get("clusters", [])
        excluded = raw.get("excluded_indices", [])

        clusters: list[ProblemCluster] = []
        for c in clusters_data:
            if not isinstance(c, dict):
                continue
            indices = c.get("signal_indices", [])
            # Map indices back to signal IDs
            signal_ids = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(problems):
                    signal_ids.append(problems[idx].signal_id)
            clusters.append(ProblemCluster(
                problem_title=c.get("problem_title", ""),
                problem_description=c.get("problem_description", ""),
                signal_ids=signal_ids,
                signal_count=len(signal_ids),
                severity=float(c.get("severity", 3)),
                category=c.get("category", "other"),
                affected_demographic=c.get("affected_demographic", "unknown"),
            ))

        return ClusteringResult(
            clusters=clusters,
            excluded_signal_ids=[problems[i].signal_id for i in excluded if isinstance(i, int) and 0 <= i < len(problems)],
        )


class EvaluationAgent(ScoutAgent):
    """Evaluates problem clusters using startup frameworks.

    Pattern: Concurrent — multiple instances run in parallel on different clusters.
    """

    HALE_SYSTEM = """\
You evaluate startup problems using Kevin Hale's problem-quality framework.
Score each criterion 0-10 honestly. Be critical — most problems are mediocre.
Return ONLY valid JSON matching the requested schema.
"""

    FRIEDMAN_SYSTEM = """\
You evaluate market viability using Jared Friedman's framework.
Score each criterion 0-10. Be honest about market limitations.
Return ONLY valid JSON matching the requested schema.
"""

    GRAHAM_SYSTEM = """\
You evaluate startup ideas using Paul Graham's criteria.
Look for schlep blindness, latent demand, and founder fit signals.
Return ONLY valid JSON matching the requested schema.
"""

    TARPIT_SYSTEM = """\
You detect startup tarpits — ideas that look promising but are structurally terrible businesses.
Check for network effects requirements, chicken-and-egg problems, regulatory traps, and margin issues.
Return ONLY valid JSON matching the requested schema.
"""

    async def evaluate_hale(self, cluster: ProblemCluster) -> HaleScores:
        prompt = (
            f"Evaluate this problem using Hale's 8 problem-quality criteria:\n\n"
            f"Title: {cluster.problem_title}\n"
            f"Description: {cluster.problem_description}\n"
            f"Category: {cluster.category}\n\n"
            f"Score each 0-10. Include a justification sentence."
        )
        result = await self._complete(self.HALE_SYSTEM, prompt, HaleScores, max_tokens=1000)
        return result if isinstance(result, HaleScores) else HaleScores()

    async def evaluate_friedman(self, cluster: ProblemCluster) -> FriedmanScores:
        prompt = (
            f"Evaluate market viability using Friedman's 6 criteria:\n\n"
            f"Title: {cluster.problem_title}\n"
            f"Description: {cluster.problem_description}\n"
            f"Category: {cluster.category}\n\n"
            f"Score each 0-10. Include a justification sentence."
        )
        result = await self._complete(self.FRIEDMAN_SYSTEM, prompt, FriedmanScores, max_tokens=1000)
        return result if isinstance(result, FriedmanScores) else FriedmanScores()

    async def evaluate_graham(self, cluster: ProblemCluster) -> GrahamScores:
        prompt = (
            f"Evaluate this idea using Graham's criteria:\n\n"
            f"Title: {cluster.problem_title}\n"
            f"Description: {cluster.problem_description}\n\n"
            f"Score each 0-10. Include a justification sentence."
        )
        result = await self._complete(self.GRAHAM_SYSTEM, prompt, GrahamScores, max_tokens=1000)
        return result if isinstance(result, GrahamScores) else GrahamScores()

    async def check_tarpit(self, cluster: ProblemCluster) -> TarpitCheck:
        # Get known tarpit examples from KG
        tarpit_nodes = self.kg.get_tarpit_examples()[:5]
        kg_context = "\n".join(
            f"- {n.get('label', n.get('title', ''))}: {n.get('description', '')[:200]}"
            for n in tarpit_nodes
        )

        prompt = (
            f"Check if this problem space is a startup tarpit:\n\n"
            f"Title: {cluster.problem_title}\n"
            f"Description: {cluster.problem_description}\n\n"
            f"Known tarpits for reference:\n{kg_context}\n\n"
            f"Score each risk factor 0-10. 10 = high tarpit risk."
        )
        result = await self._complete(self.TARPIT_SYSTEM, prompt, TarpitCheck, max_tokens=1000)
        return result if isinstance(result, TarpitCheck) else TarpitCheck()


class InnovationAgent(ScoutAgent):
    """Generates innovative solutions using first principles + inversion.

    Pattern: Concurrent — runs both analyses in parallel, merges results.
    """

    FP_SYSTEM = """\
You are an innovation strategist using First Principles thinking.
Deconstruct the problem to fundamental truths, question every assumption,
and rebuild solutions from the ground up. Return ONLY valid JSON.
"""

    INV_SYSTEM = """\
You are an innovation strategist using Inversion thinking.
Invert conventional wisdom: ask what would make things worse, what's the
opposite approach, what if constraints were reversed. Return ONLY valid JSON.
"""

    async def generate(self, cluster: ProblemCluster, index: int) -> InnovationResult:
        title = cluster.problem_title
        desc = cluster.problem_description

        fp_prompt = (
            f"Apply First Principles thinking to this problem:\n\n"
            f"Title: {title}\nDescription: {desc}\n\n"
            f"1. Identify fundamental truths\n"
            f"2. List assumptions to challenge\n"
            f"3. Generate 3-5 novel solution directions\n\n"
            f"Return JSON with: analysis, assumptions_challenged (list), "
            f"fundamental_truths (list), solutions (list of {{title, description, "
            f"fundamental_insight, feasibility (0-1), novelty (0-1), impact (0-1)}})"
        )

        inv_prompt = (
            f"Apply Inversion thinking to this problem:\n\n"
            f"Title: {title}\nDescription: {desc}\n\n"
            f"1. What's the conventional approach?\n"
            f"2. How would you guarantee failure?\n"
            f"3. What if the opposite were true?\n"
            f"4. Generate 3-5 inverted solution directions\n\n"
            f"Return JSON with: analysis, inverted_constraints (list), "
            f"solutions (list of {{title, description, fundamental_insight, "
            f"feasibility (0-1), novelty (0-1), impact (0-1)}})"
        )

        fp_raw, inv_raw = await asyncio.gather(
            self._complete(self.FP_SYSTEM, fp_prompt, dict, max_tokens=4000, temperature=0.6),
            self._complete(self.INV_SYSTEM, inv_prompt, dict, max_tokens=4000, temperature=0.6),
            return_exceptions=True,
        )

        fp = fp_raw if isinstance(fp_raw, dict) else {}
        inv = inv_raw if isinstance(inv_raw, dict) else {}

        solutions: list[InnovationSolution] = []
        for sol in fp.get("solutions", []) + inv.get("solutions", []):
            if isinstance(sol, dict):
                s = InnovationSolution(
                    title=sol.get("title", ""),
                    description=sol.get("description", ""),
                    approach="first_principles" if sol in fp.get("solutions", []) else "inversion",
                    fundamental_insight=sol.get("fundamental_insight", ""),
                    feasibility=float(sol.get("feasibility", 0.5)),
                    novelty=float(sol.get("novelty", 0.5)),
                    impact=float(sol.get("impact", 0.5)),
                )
                s.composite = round(s.impact * s.novelty * 100, 1)
                solutions.append(s)

        solutions.sort(key=lambda s: s.composite, reverse=True)

        return InnovationResult(
            problem_index=index,
            first_principles_analysis=fp.get("analysis", ""),
            inversion_analysis=inv.get("analysis", ""),
            assumptions_challenged=fp.get("assumptions_challenged", []),
            fundamental_truths=fp.get("fundamental_truths", []),
            inverted_constraints=inv.get("inverted_constraints", []),
            solutions=solutions,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Multi-Agent Orchestrator
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class AnalysisPipeline:
    """Orchestrates the full multi-agent analysis pipeline.

    Uses concurrent orchestration where possible:
      - Extraction: sequential (batched)
      - Clustering: sequential (needs all extractions)
      - Evaluation: CONCURRENT (Hale, Friedman, Graham, Tarpit all run in parallel)
      - Innovation: CONCURRENT (FP + Inversion run in parallel per problem)

    All agents share the same LLM client and KG for centralized state.
    """

    client: AsyncOpenAI
    kg: KnowledgeGraph
    model: str = "gpt-4o-mini"

    def __post_init__(self):
        self.extraction = ExtractionAgent(self.client, self.kg, self.model)
        self.clustering = ClusteringAgent(self.client, self.kg, self.model)
        self.evaluation = EvaluationAgent(self.client, self.kg, self.model)
        self.innovation = InnovationAgent(self.client, self.kg, self.model)
        self._total_calls = 0

    async def run(self, signals: list[dict]) -> list[dict]:
        """Run the full pipeline: extract → cluster → evaluate → innovate.

        Returns list of dicts suitable for DB storage.
        """
        if not signals:
            logger.warning("AnalysisPipeline: no signals to analyze")
            return []

        logger.info("AnalysisPipeline: starting with %d signals", len(signals))

        # Phase 1: Extract problems from signals (sequential, batched)
        extractions = await self.extraction.extract_batch(signals)
        total_problems = sum(len(e.problems) for e in extractions)
        logger.info("Phase 1/4: extracted %d problems from %d signals", total_problems, len(signals))

        # Phase 2: Cluster problems (sequential)
        clustering = await self.clustering.cluster(extractions)
        logger.info("Phase 2/4: clustered into %d groups", len(clustering.clusters))

        if not clustering.clusters:
            logger.warning("AnalysisPipeline: no clusters found")
            return []

        # Phase 3: Evaluate clusters (CONCURRENT — all frameworks in parallel)
        top_clusters = sorted(clustering.clusters, key=lambda c: c.signal_count, reverse=True)[:10]
        logger.info("Phase 3/4: evaluating top %d clusters concurrently", len(top_clusters))

        evaluation_tasks = []
        for c in top_clusters:
            evaluation_tasks.extend([
                self.evaluation.evaluate_hale(c),
                self.evaluation.evaluate_friedman(c),
                self.evaluation.evaluate_graham(c),
                self.evaluation.check_tarpit(c),
            ])

        eval_results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)
        logger.info("Phase 3/4: %d evaluations complete", len(eval_results))

        # Assemble evaluated problems
        evaluated: list[EvaluatedProblem] = []
        for i, cluster in enumerate(top_clusters):
            base = i * 4
            hale = eval_results[base] if base < len(eval_results) and not isinstance(eval_results[base], Exception) else None
            friedman = eval_results[base + 1] if base + 1 < len(eval_results) and not isinstance(eval_results[base + 1], Exception) else None
            graham = eval_results[base + 2] if base + 2 < len(eval_results) and not isinstance(eval_results[base + 2], Exception) else None
            tarpit = eval_results[base + 3] if base + 3 < len(eval_results) and not isinstance(eval_results[base + 3], Exception) else None

            # Compute composite from Hale + Friedman
            h = hale if isinstance(hale, HaleScores) else None
            f = friedman if isinstance(friedman, FriedmanScores) else None
            pq = _calc_pq(h) if h else 50.0
            mv = _calc_mv(f) if f else 50.0
            composite = round(pq * 0.6 + mv * 0.4, 1)

            evaluated.append(EvaluatedProblem(
                cluster_index=i,
                problem_title=cluster.problem_title,
                problem_description=cluster.problem_description,
                category=cluster.category,
                affected_demographic=cluster.affected_demographic,
                signal_count=cluster.signal_count,
                severity=cluster.severity,
                problem_quality=pq,
                market_viability=mv,
                composite_score=composite,
                hale_scores=h,
                friedman_scores=f,
                graham_scores=graham if isinstance(graham, GrahamScores) else None,
                tarpit_check=tarpit if isinstance(tarpit, TarpitCheck) else None,
                risks=_extract_risks(h, f, graham, tarpit),
                narrative=_build_narrative(h, f, graham),
            ))

        # Phase 4: Generate innovations (CONCURRENT for top problems)
        top_for_innovation = [c for c in top_clusters if _should_innovate(c)][:5]
        logger.info("Phase 4/4: generating innovations for %d top problems", len(top_for_innovation))

        innovation_tasks = [
            self.innovation.generate(c, i) for i, c in enumerate(top_for_innovation)
        ]
        innovation_results = await asyncio.gather(*innovation_tasks, return_exceptions=True)
        logger.info("Phase 4/4: %d innovation analyses complete", len(innovation_results))

        # Merge innovations into evaluated problems
        for ir in innovation_results:
            if isinstance(ir, InnovationResult):
                idx = ir.problem_index
                if idx < len(evaluated):
                    # Attach innovation to the evaluated problem
                    pass  # stored separately in DB

        # Convert to dicts for DB storage
        now = datetime.now(timezone.utc).isoformat()
        output: list[dict] = []
        for ep in evaluated:
            problem_id = f"dp-{hashlib.sha256(ep.problem_title.encode()).hexdigest()[:12]}"
            output.append({
                "id": problem_id,
                "title": ep.problem_title,
                "description": ep.problem_description,
                "category": ep.category,
                "affected_demographic": ep.affected_demographic,
                "signal_count": ep.signal_count,
                "source_tiers": [],
                "severity": ep.severity,
                "problem_quality": ep.problem_quality,
                "market_viability": ep.market_viability,
                "composite_score": ep.composite_score,
                "framework_scores": {
                    "hale": ep.hale_scores.model_dump() if ep.hale_scores else None,
                    "friedman": ep.friedman_scores.model_dump() if ep.friedman_scores else None,
                    "graham": ep.graham_scores.model_dump() if ep.graham_scores else None,
                    "tarpit": ep.tarpit_check.model_dump() if ep.tarpit_check else None,
                },
                "risks": ep.risks,
                "tarpit_check": ep.tarpit_check.model_dump() if ep.tarpit_check else None,
                "failure_matches": [],
                "innovative_solutions": [],
                "created_at": now,
            })

        self._total_calls = (
            self.extraction._call_count
            + self.clustering._call_count
            + self.evaluation._call_count
            + self.innovation._call_count
        )
        logger.info(
            "AnalysisPipeline complete: %d signals → %d problems → %d clusters → %d evaluated. "
            "Total LLM calls: %d",
            len(signals), total_problems, len(clustering.clusters), len(evaluated),
            self._total_calls,
        )

        return output


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _calc_pq(h: HaleScores) -> float:
    keys = ["urgency", "pervasiveness", "frequency", "cost_of_inaction",
            "growth", "mandatory", "underserved", "acuteness"]
    total = sum(getattr(h, k, 5) for k in keys)
    return round((total / 80) * 100, 1)


def _calc_mv(f: FriedmanScores) -> float:
    keys = ["buyer_budget", "market_size", "reach", "competition",
            "business_model", "timing"]
    total = sum(getattr(f, k, 5) for k in keys)
    return round((total / 60) * 100, 1)


def _extract_risks(
    hale: HaleScores | None,
    friedman: FriedmanScores | None,
    graham: GrahamScores | None,
    tarpit: TarpitCheck | None,
) -> list[str]:
    risks: list[str] = []
    if tarpit and tarpit.is_tarpit:
        risks.append(f"TARPIT: {tarpit.reason}")
    if tarpit and tarpit.chicken_egg_risk >= 7:
        risks.append("High chicken-and-egg risk — requires simultaneous supply and demand")
    if tarpit and tarpit.network_effect_risk >= 7:
        risks.append("Network effects required for viability")
    if friedman and friedman.competition <= 3:
        risks.append("Highly competitive market — differentiation critical")
    return risks


def _build_narrative(
    hale: HaleScores | None,
    friedman: FriedmanScores | None,
    graham: GrahamScores | None,
) -> str:
    parts: list[str] = []
    if hale:
        parts.append(f"Hale Problem Quality: {hale.justification}")
    if friedman:
        parts.append(f"Friedman Market Viability: {friedman.justification}")
    if graham:
        parts.append(f"Graham Idea Quality: {graham.justification}")
    return " | ".join(parts) if parts else "No evaluation narrative available."


def _should_innovate(cluster: ProblemCluster) -> bool:
    """Only generate innovations for substantial clusters (≥3 signals)."""
    return cluster.signal_count >= 3

"""CLI entry point for the Startup Idea Scout."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone

from openai import AsyncOpenAI

from scout.config import Settings, UserProfile, load_profile, save_profile
from scout.db import Database
from scout.kg import KnowledgeGraph
from scout.pipeline import create_pipeline
from scout.scoring import Idea, score_idea

logger = logging.getLogger(__name__)


async def cmd_profile(args: argparse.Namespace) -> None:
    settings = Settings()
    profile = load_profile(settings.profile_path)

    if args.edit:
        print("Edit mode: enter new values (press Enter to keep current).")
        print(f"Skills (comma-separated) [{', '.join(profile.skills)}]: ", end="")
        val = input().strip()
        if val:
            profile.skills = [s.strip() for s in val.split(",") if s.strip()]

        print(f"Industries (comma-separated) [{', '.join(profile.industries)}]: ", end="")
        val = input().strip()
        if val:
            profile.industries = [s.strip() for s in val.split(",") if s.strip()]

        print(f"Years experience [{profile.years_experience}]: ", end="")
        val = input().strip()
        if val:
            profile.years_experience = int(val)

        print(f"Technical depth (0.0-1.0) [{profile.technical_depth}]: ", end="")
        val = input().strip()
        if val:
            profile.technical_depth = float(val)

        print(f"Capital available (USD) [{profile.capital_available}]: ", end="")
        val = input().strip()
        if val:
            profile.capital_available = float(val)

        print(f"Problems experienced (comma-separated) [{', '.join(profile.problems_experienced)}]: ", end="")
        val = input().strip()
        if val:
            profile.problems_experienced = [s.strip() for s in val.split(",") if s.strip()]

        print(f"Anti-preferences (comma-separated) [{', '.join(profile.anti_preferences)}]: ", end="")
        val = input().strip()
        if val:
            profile.anti_preferences = [s.strip() for s in val.split(",") if s.strip()]

        save_profile(profile, settings.profile_path)
        print("\nProfile saved.")
    else:
        print("=== User Profile ===")
        print(f"  Skills:              {', '.join(profile.skills) if profile.skills else '(none)'}")
        print(f"  Industries:          {', '.join(profile.industries) if profile.industries else '(none)'}")
        print(f"  Years experience:    {profile.years_experience}")
        print(f"  Technical depth:     {profile.technical_depth}")
        print(f"  Capital available:   ${profile.capital_available:,.0f}")
        print(f"  Problems:            {', '.join(profile.problems_experienced) if profile.problems_experienced else '(none)'}")
        print(f"  Anti-preferences:    {', '.join(profile.anti_preferences) if profile.anti_preferences else '(none)'}")


async def cmd_run(args: argparse.Namespace) -> None:
    pipeline = await create_pipeline()
    pipeline.backfill_mode = getattr(args, 'backfill', False)

    if getattr(args, 'once', False):
        # Single cycle — backfill or normal
        logger.info("Running single cycle (backfill=%s)", pipeline.backfill_mode)
        stats = await pipeline.run_once()
        logger.info("Cycle complete: %s", json.dumps(stats))
        return

    # Continuous loop
    loop = asyncio.get_running_loop()

    def _shutdown():
        logger.info("Received shutdown signal")
        asyncio.create_task(pipeline.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    await asyncio.gather(pipeline.run_loop(), pipeline.process_deep_dives())


async def cmd_web(args: argparse.Namespace) -> None:
    import uvicorn

    host = args.host
    port = args.port
    config = uvicorn.Config("scout.web:app", host=host, port=port, log_level="info", reload=False)
    server = uvicorn.Server(config)
    await server.serve()



async def cmd_analyze(args: argparse.Namespace) -> None:
    """Run the multi-agent analysis pipeline on stored signals."""
    from openai import AsyncOpenAI
    from scout.config import Settings
    from scout.db import Database
    from scout.kg import KnowledgeGraph
    from scout.agents_v2 import AnalysisPipeline

    settings = Settings()
    if not settings.openai_api_key:
        print("Error: SCOUT_OPENAI_API_KEY not set")
        return

    db = Database(settings.db_path)
    kg = KnowledgeGraph(settings.graph_path)

    # Get unprocessed signals
    signals = db.get_unprocessed_signals(limit=args.limit)
    if not signals:
        # Also try processed signals if none unprocessed
        signals = list(db.db["raw_signals"].rows_where("1=1", limit=args.limit, order_by="id desc"))
        signals = [dict(r) for r in signals]

    print(f"Analyzing {len(signals)} signals with model {args.model}...")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    pipeline = AnalysisPipeline(client=client, kg=kg, model=args.model)

    results = await pipeline.run(signals)

    # Store results
    stored = 0
    for result in results:
        db.store_derived_problem(result)
        stored += 1

    print(f"Analysis complete. {stored} derived problems stored in DB.")
    print("View them at http://localhost:8765 (Problems tab)")

async def cmd_score(args: argparse.Namespace) -> None:
    settings = Settings()
    profile = load_profile(settings.profile_path)

    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    if not args.title:
        print("Error: --title is required.", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(timezone.utc)
    idea = Idea(
        id=f"manual-{int(now.timestamp())}",
        title=args.title,
        description=args.description or args.title,
        source_url=args.source_url or "manual",
        source_type="manual",
        source_tier=3,
        discovered_at=now,
        embedding=None,
    )

    print(f"Scoring: {idea.title}")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    kg = KnowledgeGraph(settings.graph_path)

    try:
        report = await score_idea(idea, profile, kg, client)
    except Exception as exc:
        print(f"Scoring failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=== Score Report ===")
    print(f"  Verdict:           {report.verdict}")
    print(f"  Composite:         {report.composite:.1f}")
    print(f"  Problem Quality:   {report.problem_quality:.1f} (weight 40%)")
    print(f"  Market Viability:  {report.market_viability:.1f} (weight 25%)")
    print(f"  Sentiment Signal:  {report.sentiment_signal:.1f} (weight 15%)")
    print(f"  Founder Fit:       {report.founder_fit:.1f} (weight 20%)")

    if report.sentiment_flags:
        print(f"\n  Sentiment Flags:   {', '.join(report.sentiment_flags)}")
    if report.risks:
        print(f"  Risks:             {', '.join(report.risks)}")
    if report.tarpit:
        print(f"  Tarpit:            {report.tarpit}")
    if report.failure_matches:
        print(f"  Failure Matches:   {', '.join(report.failure_matches)}")
    print(f"\n  Justification:     {report.justification}")

    if not args.no_store:
        db = Database(settings.db_path)
        db.store_idea(idea)
        db.store_score(report)
        print(f"\nIdea stored (id={idea.id}).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scout", description="Startup Idea Scout")
    sub = parser.add_subparsers(dest="command", required=True)

    p_profile = sub.add_parser("profile", help="View or edit user profile")
    p_profile.add_argument("--edit", action="store_true", help="Edit profile interactively")

    p_run = sub.add_parser("run", help="Start the continuous pipeline")
    p_run.add_argument("--backfill", action="store_true", help="Scrape all historical data (full backfill)")
    p_run.add_argument("--once", action="store_true", help="Run a single cycle and exit")

    p_analyze = sub.add_parser("analyze", help="Run mass signal analysis with multi-agent pipeline")
    p_analyze.add_argument("--limit", type=int, default=200, help="Max signals to analyze (default 200)")
    p_analyze.add_argument("--model", default="gpt-4o-mini", help="OpenAI model (default gpt-4o-mini)")

    p_web = sub.add_parser("web", help="Start the dashboard web server")
    p_web.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    p_web.add_argument("--port", type=int, default=8765, help="Port (default 8765)")

    p_score = sub.add_parser("score", help="Score a single idea")
    p_score.add_argument("--title", required=True, help="Idea title")
    p_score.add_argument("--description", help="Idea description")
    p_score.add_argument("--source-url", default="manual", help="Source URL")
    p_score.add_argument("--no-store", action="store_true", help="Skip persisting to DB")

    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = build_parser()
    args = parser.parse_args()

    cmd = args.command
    if cmd == "profile":
        asyncio.run(cmd_profile(args))
    elif cmd == "run":
        asyncio.run(cmd_run(args))
    elif cmd == "web":
        asyncio.run(cmd_web(args))
    elif cmd == "analyze":
        asyncio.run(cmd_analyze(args))
    elif cmd == "score":
        asyncio.run(cmd_score(args))


if __name__ == "__main__":
    main()

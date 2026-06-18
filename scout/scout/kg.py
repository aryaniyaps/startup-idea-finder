"""Knowledge Graph loader for the 909-node startup-ideas graph."""

import json
from pathlib import Path

import networkx as nx


class KnowledgeGraph:
    """Wraps the graphify-out/graph.json knowledge graph with query methods."""

    def __init__(self, graph_path: str | None = None):
        """Load the graph from graph_path. Defaults to ~/research/startup-idea-finder/graphify-out/graph.json."""
        if graph_path is None:
            graph_path = str(
                Path.home() / "research" / "startup-idea-finder" / "graphify-out" / "graph.json"
            )
        self._graph = nx.Graph()
        self._node_index: dict[str, dict] = {}
        self._community_index: dict[int, list[dict]] = {}
        self._load(graph_path)

    def _load(self, path: str) -> None:
        """Load graph from JSON file into NetworkX graph and in-memory indices."""
        with open(path) as f:
            data = json.load(f)

        for node in data.get("nodes", []):
            nid = node["id"]
            self._graph.add_node(nid, **node)
            self._node_index[nid] = node
            community = node.get("community")
            if community is not None:
                self._community_index.setdefault(community, []).append(node)

        for link in data.get("links", []):
            self._graph.add_edge(
                link["source"],
                link["target"],
                relation=link.get("relation", ""),
                confidence=link.get("confidence", ""),
                confidence_score=link.get("confidence_score", 0.0),
            )

    def query_node(self, node_id: str) -> dict | None:
        """Look up a node by its id. Returns dict with label, properties, community, or None."""
        return self._node_index.get(node_id)

    def query_community(self, community_id: int) -> list[dict]:
        """Return all nodes with the given community id."""
        return self._community_index.get(community_id, [])

    def search_nodes(self, query: str, top_k: int = 10) -> list[dict]:
        """Case-insensitive substring match on node labels. Returns top_k results."""
        q = query.lower()
        matches = []
        for node in self._node_index.values():
            label = node.get("label", "")
            norm = node.get("norm_label", "")
            rationale = node.get("rationale", "")
            if q in label.lower() or q in norm.lower() or q in rationale.lower():
                matches.append(node)
            if len(matches) >= top_k:
                break
        return matches[:top_k]

    def get_pre_launch_failure_modes(self) -> list[dict]:
        """Return nodes matching failure/pitfall/mistake/trap/pre-launch keywords."""
        keywords = ["failure", "fail", "pitfall", "mistake", "why startups fail", "pre-launch", "trap"]
        seen: set[str] = set()
        results: list[dict] = []
        for kw in keywords:
            for node in self._node_index.values():
                nid = node["id"]
                if nid in seen:
                    continue
                label = node.get("label", "")
                norm = node.get("norm_label", "")
                rationale = node.get("rationale", "")
                q = kw.lower()
                if q in label.lower() or q in norm.lower() or q in rationale.lower():
                    seen.add(nid)
                    results.append(node)
        return results

    def get_tarpit_examples(self) -> list[dict]:
        """Return nodes matching tarpit/crowded/saturated/commodity keywords."""
        keywords = ["tarpit", "crowded", "saturated", "commodity"]
        seen: set[str] = set()
        results: list[dict] = []
        for kw in keywords:
            for node in self._node_index.values():
                nid = node["id"]
                if nid in seen:
                    continue
                label = node.get("label", "")
                norm = node.get("norm_label", "")
                rationale = node.get("rationale", "")
                q = kw.lower()
                if q in label.lower() or q in norm.lower() or q in rationale.lower():
                    seen.add(nid)
                    results.append(node)
        return results

    def get_deep_dive_frameworks(self, domain: str) -> list[dict]:
        """Return nodes matching framework-related terms + domain keyword."""
        framework_terms = [
            "framework",
            "checklist",
            "methodology",
            "process",
            "template",
            "guide",
            "strategy",
            "model",
            "canvas",
            "toolkit",
            "playbook",
            "heuristic",
        ]
        domain_lower = domain.lower()
        seen: set[str] = set()
        results: list[dict] = []

        for node in self._node_index.values():
            nid = node["id"]
            if nid in seen:
                continue
            label = node.get("label", "")
            norm = node.get("norm_label", "")
            rationale = node.get("rationale", "")
            combined = f"{label} {norm} {rationale}".lower()

            # Must match domain AND at least one framework term
            if domain_lower not in combined:
                continue
            if not any(term in combined for term in framework_terms):
                continue
            seen.add(nid)
            results.append(node)

        return results

    def get_signal_source_tiers(self) -> dict:
        """Return the 5-tier signal source hierarchy from the ChatGPT framework.

        Each tier maps to a dict with sources list, multiplier, and description.
        This is a hardcoded reference mirroring sources/chatgpt-sources-of-customer-problems.md.
        """
        return {
            "tier_1": {
                "label": "Public Unsolicited Complaints",
                "sources": ["reddit", "hn", "indie_hackers", "twitter", "worldmonitor"],
                "multiplier": 1.0,
                "description": "Raw, unfiltered pain points expressed publicly without prompting — the purest signal.",
            },
            "tier_2": {
                "label": "Professional Communities & Review Sites",
                "sources": [
                    "slack",
                    "discord",
                    "facebook_groups",
                    "support_forums",
                    "g2",
                    "capterra",
                    "trustpilot",
                ],
                "multiplier": 1.3,
                "description": "People evaluating alternatives and writing detailed complaints — high-intent, high-signal.",
            },
            "tier_3": {
                "label": "Job Boards & Consulting Marketplaces",
                "sources": ["upwork", "fiverr", "linkedin", "consulting_marketplaces"],
                "multiplier": 1.2,
                "description": "Market proof — money is already being spent to solve this problem manually.",
            },
            "tier_4": {
                "label": "Developer & User Pain Documented in Detail",
                "sources": [
                    "github_issues",
                    "browser_extension_reviews",
                    "youtube_comments",
                    "app_store_reviews",
                ],
                "multiplier": 1.1,
                "description": "Detailed technical pain documented with reproduction steps and feature gap analysis.",
            },
            "tier_5": {
                "label": "Founder Communities & Build-in-Public",
                "sources": ["product_hunt", "founder_communities", "build_in_public"],
                "multiplier": 0.8,
                "description": "What builders think is important — echo chamber risk, but useful for competitive awareness.",
            },
        }

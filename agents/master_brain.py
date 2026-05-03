"""
Master Brain — Tier 0 Global Orchestrator
============================================
The Master Brain maintains wide-spectrum holistic context.
It orchestrates Domain Agents, identifies gaps, makes
risk-weighted strategic decisions, and serves as the
default human interaction layer.

Capabilities:
- Cross-domain reasoning (queries all domains simultaneously)
- Gap detection (identifies thin coverage and missing connections)
- Strategic synthesis (combines insights across domains)
- Task delegation (routes questions to appropriate Domain Agents)
- Knowledge Base oversight (monitors health and coverage)
"""

from typing import Callable, Optional

from core.model_router import AgentRequest, AgentResponse, execute
from core.kb import get_nodes, get_venture_id, get_stats


class MasterBrain:
    """Tier 0 Global Orchestrator."""

    def __init__(self, venture_name: str = None):
        self.venture_id = get_venture_id(venture_name)
        self.agent_id = "master_brain"

    def _get_full_context(self, limit: int = 60) -> list[dict]:
        """Retrieve knowledge across ALL domains."""
        nodes = get_nodes(self.venture_id, limit=limit)
        nodes.sort(key=lambda n: n.get("confidence", 0), reverse=True)
        return nodes

    def _format_knowledge(self, nodes: list[dict]) -> str:
        """Format all knowledge nodes grouped by domain and label."""
        if not nodes:
            return "THE KNOWLEDGE BASE IS EMPTY."

        # Group by domain
        by_domain = {}
        for node in nodes:
            domain = node.get("domain", "unknown")
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(node)

        parts = []
        for domain, domain_nodes in sorted(by_domain.items()):
            lines = [f"\n=== DOMAIN: {domain.upper()} ({len(domain_nodes)} nodes) ==="]
            for n in domain_nodes:
                label = n.get("epistemic_label", "?")[:3].upper()
                conf = n.get("confidence", 0)
                state = n.get("lifecycle_state", "?")
                content = n.get("content", "")[:200]
                lines.append(f"  [{label}|{conf:.0f}|{state}] {content}")
            parts.append("\n".join(lines))

        return "\n".join(parts)

    def _build_system_prompt(self, knowledge_context: str, stats: dict) -> str:
        return f"""You are the Master Brain of the Autonomous Disruptive Intelligence Ecosystem.

ROLE: Tier 0 Global Orchestrator. You maintain the wide-spectrum holistic context across ALL domains. You do not specialize — you synthesize. You see connections between domains that domain agents cannot see individually.

VENTURE: Vision Correction Display
PRIME DIRECTIVE: Identify and validate a commercially viable, patent-clear method for correcting refractive vision errors through display technology.

CURRENT KNOWLEDGE BASE STATUS:
Total nodes: {stats.get('total', 0)}
By label: {stats.get('by_label', {})}
By domain: {stats.get('by_domain', {})}
Average confidence: {stats.get('avg_confidence', 0):.1f}

OPERATING PRINCIPLES:
1. You think across domains. When an optics constraint meets a materials opportunity, you see the connection.
2. You identify GAPS — areas where knowledge is thin, contradictory, or missing entirely.
3. You identify CROSS-DOMAIN OPPORTUNITIES — insights that emerge from combining knowledge across domains.
4. You make STRATEGIC ASSESSMENTS — evaluating which research directions are most promising given the full picture.
5. You NEVER fabricate knowledge. Clearly separate KB-grounded facts from your own strategic reasoning.
6. You challenge assumptions — especially Cognitive Frameworks that may be limiting the solution space.
7. When you identify a gap, specify what kind of research or data would fill it.

EPISTEMIC AWARENESS:
- AXI = Axiomatic Fact (inviolable physics/math, high confidence)
- EXP = Experimental Result (context-dependent data)
- COG = Cognitive Framework (human interpretation — challengeable)

KNOWLEDGE BASE (all domains):
{knowledge_context}

When answering, structure your thinking as:
1. What the KB tells us (grounded facts)
2. What the KB implies (cross-domain connections)
3. What the KB is missing (gaps and unknowns)
4. Strategic recommendation (what to do next)
"""

    def think(
        self,
        question: str,
        complexity: str = "complex",
        on_text: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        """Strategic thinking across all domains.

        Defaults to complex (Opus) because the Master Brain
        handles high-level reasoning that benefits from depth.

        Pass on_text to receive streaming text deltas while the model generates.
        """
        nodes = self._get_full_context(limit=60)
        knowledge = self._format_knowledge(nodes)
        stats = get_stats(self.venture_id)

        request = AgentRequest(
            role="master_brain",
            complexity=complexity,
            system_prompt=self._build_system_prompt(knowledge, stats),
            input_text=question,
            output_format="text",
            max_tokens=6144,
            temperature=0.4,
            on_text=on_text,
        )

        return execute(request)

    def strategic_review(
        self,
        on_text: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        """Comprehensive strategic review of the venture's knowledge state."""
        nodes = self._get_full_context(limit=60)
        knowledge = self._format_knowledge(nodes)
        stats = get_stats(self.venture_id)

        request = AgentRequest(
            role="master_brain",
            complexity="complex",
            system_prompt=self._build_system_prompt(knowledge, stats),
            input_text="""Conduct a comprehensive strategic review of the venture's current knowledge state.

Analyze:

1. COVERAGE ASSESSMENT: Which domains are well-covered and which are dangerously thin? Rate each domain's readiness.

2. CONSTRAINT MAP: What are the hard physics constraints we've established? What is the actual boundary of what's possible?

3. SOLUTION HYPOTHESIS SPACE: Based on everything in the KB, what are the 3-5 most promising solution paths for the Prime Directive? For each, assess:
   - Physical viability (does it respect all Axiomatic Facts?)
   - Technical feasibility (is it buildable with current technology?)
   - Patent clearance risk (based on what we know)
   - Competitive exposure (who else is pursuing this?)

4. CRITICAL GAPS: What missing knowledge would most change our strategic direction? Prioritize by impact.

5. RECOMMENDED NEXT ACTIONS: What should the Architect-Sovereign focus on next? Be specific — name papers to read, experiments to run, or domains to investigate.

This is the Master Brain's most important function. Be thorough, honest, and strategic.""",
            output_format="text",
            max_tokens=8192,
            temperature=0.3,
            on_text=on_text,
        )

        return execute(request)

    def assess_idea(
        self,
        idea: str,
        on_text: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        """Evaluate an idea against the full Knowledge Base.

        This is a lightweight version of the Dialectic Engine —
        the Master Brain plays both Thesis advocate and Red Team.
        """
        nodes = self._get_full_context(limit=60)
        knowledge = self._format_knowledge(nodes)
        stats = get_stats(self.venture_id)

        request = AgentRequest(
            role="master_brain",
            complexity="complex",
            system_prompt=self._build_system_prompt(knowledge, stats),
            input_text=f"""Evaluate this idea against the full Knowledge Base:

IDEA: {idea}

Perform a structured assessment:

1. THESIS (Steelman): Present the strongest possible case for this idea. What KB data supports it?

2. RED TEAM (Destroy): Systematically attack the idea. What KB data contradicts it? What physics makes it impossible or impractical? What has been tried before and failed?

3. FEASIBILITY: Can this be built with current technology? What would it take? What are the unknowns?

4. PATENT RISK: Based on what we know about existing patents, is this path clear or blocked?

5. VERDICT: Promising / Needs refinement / Fundamentally flawed — with a clear explanation.

6. IF PROMISING: What is the single most important experiment or analysis to do next to validate or invalidate this idea?

Be brutally honest. The value of this assessment is in its accuracy, not its optimism.""",
            output_format="text",
            max_tokens=6144,
            temperature=0.3,
            on_text=on_text,
        )

        return execute(request)

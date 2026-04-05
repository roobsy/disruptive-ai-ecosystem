"""
Domain Agent — Base Class + Optics Specialization
====================================================
Phase 1: Domain Agents that answer questions using
knowledge from the KB, with epistemic awareness.

Each Domain Agent:
- Has a specialized system prompt defining its expertise
- Retrieves relevant knowledge from Supabase before answering
- Cites its sources with confidence levels
- Distinguishes between what it knows (from the KB) and what it's reasoning about
- Can identify gaps in the Knowledge Base
"""

from core.model_router import AgentRequest, AgentResponse, execute
from core.kb import get_nodes, get_venture_id, get_stats


# ── Base Domain Agent ─────────────────────────────────────
class DomainAgent:
    """Base class for all Domain Agents."""

    def __init__(
        self,
        agent_id: str,
        display_name: str,
        domain_scope: str,
        expertise_description: str,
        domains: list[str] = None,
        venture_name: str = None,
    ):
        self.agent_id = agent_id
        self.display_name = display_name
        self.domain_scope = domain_scope
        self.expertise_description = expertise_description
        self.domains = domains or []
        self.venture_id = get_venture_id(venture_name)

    def _retrieve_context(self, query: str, limit: int = 30) -> list[dict]:
        """Retrieve relevant knowledge nodes for context.

        Currently uses domain filtering. In Phase 1+, this will
        use vector similarity search over embeddings.
        """
        all_nodes = []
        for domain in self.domains:
            nodes = get_nodes(
                self.venture_id,
                domain=domain,
                min_confidence=0,
                limit=limit,
            )
            all_nodes.extend(nodes)

        # If no domain filter, get everything
        if not self.domains:
            all_nodes = get_nodes(self.venture_id, limit=limit)

        # Sort by confidence descending
        all_nodes.sort(key=lambda n: n.get("confidence", 0), reverse=True)
        return all_nodes[:limit]

    def _format_knowledge_context(self, nodes: list[dict]) -> str:
        """Format knowledge nodes into a context string for the LLM."""
        if not nodes:
            return "NO KNOWLEDGE AVAILABLE IN THE SPINE FOR THIS DOMAIN YET."

        sections = {
            "axiomatic_fact": [],
            "experimental_result": [],
            "cognitive_framework": [],
            "experience_data": [],
        }

        for node in nodes:
            label = node.get("epistemic_label", "unknown")
            conf = node.get("confidence", 0)
            content = node.get("content", "")
            state = node.get("lifecycle_state", "unknown")
            domain = node.get("domain", "unknown")

            entry = f"  [{conf:.0f}] [{state}] [{domain}] {content}"
            if label in sections:
                sections[label].append(entry)

        parts = []
        if sections["axiomatic_fact"]:
            parts.append("AXIOMATIC FACTS (inviolable constraints):\n" +
                        "\n".join(sections["axiomatic_fact"]))
        if sections["experimental_result"]:
            parts.append("EXPERIMENTAL RESULTS (context-dependent data):\n" +
                        "\n".join(sections["experimental_result"]))
        if sections["cognitive_framework"]:
            parts.append("COGNITIVE FRAMEWORKS (human interpretations — acknowledge but do not treat as constraints):\n" +
                        "\n".join(sections["cognitive_framework"]))
        if sections["experience_data"]:
            parts.append("EXPERIENCE DATA (proprietary observations):\n" +
                        "\n".join(sections["experience_data"]))

        return "\n\n".join(parts)

    def _build_system_prompt(self, knowledge_context: str) -> str:
        """Build the full system prompt with knowledge context."""
        return f"""You are {self.display_name}, a Domain Agent in the Autonomous Disruptive Intelligence Ecosystem.

ROLE: {self.expertise_description}

DOMAIN SCOPE: {self.domain_scope}

OPERATING PRINCIPLES:
1. You are a subject-matter expert. Answer with precision and depth.
2. Ground your answers in the knowledge from the KB provided below.
3. Clearly distinguish between:
   - What is established fact (Axiomatic Facts from the KB)
   - What is experimentally demonstrated (Experimental Results — cite the conditions)
   - What is human interpretation (Cognitive Frameworks — acknowledge but note these are challengeable)
   - What you are reasoning or inferring beyond the KB data
4. When you identify a GAP in the Knowledge Base — something important that isn't covered — explicitly flag it as: [KNOWLEDGE GAP: description]
5. When asked for creative solutions, you may propose ideas that challenge Cognitive Frameworks, but you must NEVER violate Axiomatic Facts.
6. Be concise but thorough. Every claim should be traceable to KB data or clearly marked as your own reasoning.

KNOWLEDGE SPINE (your current knowledge base):
{knowledge_context}

When referencing KB data, indicate the confidence level: e.g., "PSF normalization conserves image brightness [Axiom, 96]"
"""

    def ask(self, question: str, complexity: str = "standard") -> AgentResponse:
        """Ask the Domain Agent a question.

        Args:
            question: The question to answer
            complexity: "standard" (Sonnet) or "complex" (Opus)

        Returns:
            AgentResponse with the answer
        """
        # Retrieve relevant knowledge
        nodes = self._retrieve_context(question)
        knowledge_context = self._format_knowledge_context(nodes)

        # Build and execute
        request = AgentRequest(
            role=f"domain:{self.agent_id}",
            complexity=complexity,
            system_prompt=self._build_system_prompt(knowledge_context),
            input_text=question,
            output_format="text",
            max_tokens=4096,
            temperature=0.3,
        )

        return execute(request)

    def identify_gaps(self) -> AgentResponse:
        """Ask the agent to analyze the Knowledge Base for gaps."""
        nodes = self._retrieve_context("", limit=50)
        knowledge_context = self._format_knowledge_context(nodes)

        request = AgentRequest(
            role=f"domain:{self.agent_id}",
            complexity="standard",
            system_prompt=self._build_system_prompt(knowledge_context),
            input_text="""Analyze the Knowledge Base above and identify:

1. CRITICAL GAPS: Important topics in your domain that have NO coverage at all.
2. THIN COVERAGE: Topics that have some data but need more depth or validation.
3. STALE DATA: Areas where the existing data may be outdated or needs refreshing.
4. MISSING CONNECTIONS: Relationships between facts that should be explored.
5. CONTRADICTIONS: Any conflicts between nodes that need resolution.

For each gap, suggest specific sources or research directions to fill it.
Format your response clearly with these 5 sections.""",
            output_format="text",
            max_tokens=4096,
            temperature=0.2,
        )

        return execute(request)


# ── Optics Domain Agent ───────────────────────────────────
class OpticsAgent(DomainAgent):
    """Specialized agent for optics, photonics, and vision correction."""

    def __init__(self, venture_name: str = None):
        super().__init__(
            agent_id="optics",
            display_name="Optics & Vision Correction Agent",
            domain_scope="Fourier optics, wavefront propagation, PSF modeling, "
                         "Zernike polynomials, diffractive optics, light field displays, "
                         "computational imaging, vision-correcting displays, "
                         "deconvolution algorithms, human visual system modeling, "
                         "refractive error correction, display technology.",
            expertise_description=(
                "You are a world-class expert in computational optics and vision "
                "correction display technology. You combine deep knowledge of "
                "Fourier optics and wavefront physics with practical understanding "
                "of display engineering, PSF-based deconvolution, and the optical "
                "limitations of the human eye. You can analyze proposed solutions "
                "for physical viability and identify non-obvious approaches that "
                "existing research may have overlooked."
            ),
            domains=[
                "optics",
                "display_technology",
                "ophthalmology",
                "image_processing",
                "computer_science",
                "materials_science",
            ],
            venture_name=venture_name,
        )

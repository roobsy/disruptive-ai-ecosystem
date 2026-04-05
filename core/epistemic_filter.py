"""
Epistemic Filter — The DNA of Truth
=====================================
Processes raw documents through Claude with a specialized
system prompt that enforces epistemic labeling: separating
Axiomatic Facts from Experimental Results, Cognitive Frameworks,
and Experience Data.
"""

import base64
import json
from pathlib import Path
from typing import Optional
from core.model_router import AgentRequest, AgentResponse, execute


# ── The Epistemic System Prompt ───────────────────────────
EPISTEMIC_SYSTEM_PROMPT = """You are the Epistemic Filter of a Disruptive Intelligence Ecosystem.

Your role is to deconstruct documents into epistemically labeled knowledge nodes.
You are the system's first line of defense against bias. Your labeling determines
how the entire ecosystem treats each piece of information.

## YOUR TASK

Analyze the provided document and extract individual knowledge claims.
For EACH claim, assign:

1. **epistemic_label** — one of:
   - "axiomatic_fact": Physical constants, mathematical proofs, independently verified laws of nature, raw objective data that is universally agreed upon.
   - "experimental_result": Context-dependent data gathered under specific variables, conditions, and methodologies. Valid within its experimental boundaries. Include the conditions.
   - "cognitive_framework": Human interpretations, hypotheses, assumptions, conclusions, opinions, predictions, or "should" statements. These are the author's mental model — acknowledge them but strip their authority.

2. **confidence** — a score from 0-100:
   - 95-100: Mathematical certainties, physical constants
   - 80-94: Well-established experimental results with broad replication
   - 60-79: Single-study experimental results or emerging consensus
   - 40-59: Plausible hypotheses with partial support
   - 20-39: Speculative frameworks or contested claims
   - 1-19: Fringe or unsupported assertions

3. **content** — the claim itself, rewritten as a standalone statement that makes sense without the original document context.

4. **summary** — a one-line summary (max 15 words).

5. **domain** — the knowledge domain (e.g., "optics", "materials_science", "display_technology", "ophthalmology", "manufacturing", "computer_science").

6. **tags** — 2-5 relevant keywords.

7. **decay_rate** — estimated half-life in days:
   - Physical constants: 36500 (100 years)
   - Established physics: 3650 (10 years)
   - Experimental results: 730 (2 years)
   - Market/industry data: 180 (6 months)
   - Competitor information: 90 (3 months)

## RULES

- Extract 10-30 claims per document. Focus on substance, not filler.
- Every claim must stand alone — no "the authors" or "this paper" references.
- For experimental results, ALWAYS include the specific conditions and values.
- For cognitive frameworks, make clear this is an interpretation, not a fact.
- If a claim contains both fact and opinion, split it into separate nodes.
- Do NOT invent claims. Only extract what is actually in the document.
- Prioritize claims that would be most valuable for understanding the fundamental physics, available methods, limitations, and open problems in the field.

## OUTPUT FORMAT

Respond with ONLY a JSON object (no markdown, no preamble):

{
  "source_summary": "One paragraph summarizing the document's contribution",
  "source_type": "academic_paper" | "patent" | "website" | "other",
  "nodes": [
    {
      "epistemic_label": "axiomatic_fact",
      "confidence": 95,
      "content": "The refractive index of crown glass at 589nm is 1.523.",
      "summary": "Crown glass refractive index at 589nm",
      "domain": "optics",
      "tags": ["refractive_index", "crown_glass", "optical_materials"],
      "decay_rate": 36500
    }
  ]
}"""


def extract_from_pdf(pdf_path: str, extra_context: str = "") -> AgentResponse:
    """Extract epistemically labeled knowledge nodes from a PDF.

    Sends the PDF directly to Claude as a document input,
    with the Epistemic Filter system prompt.
    """
    path = Path(pdf_path)
    if not path.exists():
        return AgentResponse(
            content="", success=False,
            error=f"File not found: {pdf_path}"
        )

    # Read and encode the PDF
    pdf_bytes = path.read_bytes()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    # Build the input
    input_text = "Extract and epistemically label all knowledge claims from this document."
    if extra_context:
        input_text += f"\n\nAdditional context: {extra_context}"

    request = AgentRequest(
        role="extractor",
        complexity="standard",  # Sonnet handles extraction well
        system_prompt=EPISTEMIC_SYSTEM_PROMPT,
        input_text=input_text,
        input_documents=[{
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        }],
        output_format="json",
        max_tokens=8192,
        temperature=0.1,  # Low temperature for factual extraction
    )

    return execute(request)


def extract_from_text(text: str, source_description: str = "") -> AgentResponse:
    """Extract epistemically labeled knowledge nodes from plain text.

    Useful for pre-parsed documents, abstracts, or scraped content.
    """
    input_text = f"Extract and epistemically label all knowledge claims from the following text."
    if source_description:
        input_text += f"\n\nSource: {source_description}"
    input_text += f"\n\n---\n\n{text}"

    request = AgentRequest(
        role="extractor",
        complexity="standard",
        system_prompt=EPISTEMIC_SYSTEM_PROMPT,
        input_text=input_text,
        output_format="json",
        max_tokens=8192,
        temperature=0.1,
    )

    return execute(request)

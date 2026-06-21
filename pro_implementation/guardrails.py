"""
pro_implementation/guardrails.py
---------------------------------
Input and output guardrails for the Radixweb RAG assistant.

HOW TO CUSTOMIZE
----------------
1. Add/remove/edit entries in RULES to change what input categories are blocked.
   Each rule needs:
     - "description": what the LLM classifier should look for (used verbatim in the prompt)
     - "response": the fixed message returned to the user when this rule fires
2. Edit OUTPUT_INSTRUCTIONS to change what the LLM is told to avoid in its answers.
3. Change CLASSIFIER_MODEL to use a different model for the input classifier.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from litellm import completion

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

CLASSIFIER_MODEL = "openai/gpt-4.1-nano"

# Input rules — add new entries here to block additional categories.
# Keys become the rule_id recorded in the audit log.
RULES: dict[str, dict] = {
    "pricing": {
        "description": (
            "User is asking about pricing, costs, rates, quotes, budgets, invoices, "
            "or how much a product or service costs"
        ),
        "response": (
            "For pricing and cost information, please contact the Radixweb team directly. "
            "Visit radixweb.com/contact and our experts will provide a tailored quote for your needs."
        ),
    },
    "off_topic": {
        "description": (
            "The question is completely unrelated to Radixweb, software development, "
            "IT services, technology, or any business topic Radixweb operates in "
            "(e.g. cooking, sports, weather, politics, entertainment)"
        ),
        "response": (
            "I'm specialized in answering questions about Radixweb's services, expertise, "
            "team, industries, and capabilities. Please ask me something related to "
            "software development or how Radixweb can help your business."
        ),
    },
}

# Injected verbatim into the RAG system prompt (output guardrail).
# The LLM sees this before generating — it won't include forbidden content.
OUTPUT_INSTRUCTIONS = """
GUARDRAIL RULES — follow strictly, no exceptions:
1. NEVER reveal, estimate, hint at, or discuss pricing, costs, rates, billing, or budget \
figures under any circumstances. If the retrieved Knowledge Base contains any pricing data, \
do NOT quote or paraphrase it. Instead respond: \
"For pricing information, please contact us at radixweb.com/contact."
2. Only answer questions relevant to Radixweb, software development, IT services, technology, \
or business topics Radixweb operates in. If a question is completely off-topic, politely \
decline and redirect the user to ask about Radixweb's services.
"""

# ─── Classifier ───────────────────────────────────────────────────────────────

def _build_classifier_system() -> str:
    """Build the system prompt for the input classifier from RULES."""
    rule_lines = "\n".join(
        f'- "{rule_id}": {meta["description"]}'
        for rule_id, meta in RULES.items()
    )
    rule_ids = ", ".join(f'"{r}"' for r in RULES)
    return (
        "You are a strict single-label classifier for a Radixweb company knowledge-base assistant.\n\n"
        "Classify the user message into exactly ONE of these labels:\n"
        '- "allowed": The message is relevant to Radixweb, software development, '
        "IT services, technology, or any business topic Radixweb may cover.\n"
        f"{rule_lines}\n\n"
        f"Respond with ONLY the label name ({rule_ids}, or allowed). No explanation, no punctuation."
    )


_CLASSIFIER_SYSTEM = _build_classifier_system()


@dataclass
class GuardrailViolation:
    rule_id: str   # key from RULES
    response: str  # fixed message to return to the user


def classify_input(message: str) -> GuardrailViolation | None:
    """
    Run LLM-based input classification on a user message.

    Returns a GuardrailViolation if the message should be blocked, or None to allow it.
    On any classifier error, fails open (returns None) so users are never silently blocked
    by an infrastructure fault.
    """
    try:
        resp = completion(
            model=CLASSIFIER_MODEL,
            messages=[
                {"role": "system", "content": _CLASSIFIER_SYSTEM},
                {"role": "user", "content": message},
            ],
            max_tokens=10,
            temperature=0,
        )
        label = resp.choices[0].message.content.strip().lower().strip('"\'')
    except Exception as exc:
        logger.warning("[guardrails] Classifier call failed — failing open. Error: %s", exc)
        return None

    if label in RULES:
        return GuardrailViolation(rule_id=label, response=RULES[label]["response"])

    return None

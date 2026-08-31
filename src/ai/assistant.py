"""
AI Assistant (layer sopra il Compatibility Engine).

NON sostituisce il motore: riceve dati strutturati e produce spiegazioni.
Le risposte sono basate su regole deterministiche. Una futura integrazione AI
potra' usare questa stessa interfaccia, ma non potra' inventare compatibilita'.
"""

from __future__ import annotations

from typing import Dict, List

from compatibility import CompatibilityResult
from .explanation import (
    answer_recommended_macos,
    answer_why_incompatible,
    explain_results,
)


class Assistant:
    def explain(self, result: CompatibilityResult) -> List[str]:
        return explain_results(result)

    def why_incompatible(self, result: CompatibilityResult, component: str) -> str:
        return answer_why_incompatible(result, component)

    def recommended_macos(self, result: CompatibilityResult) -> str:
        return answer_recommended_macos(result)

    def answer(self, question: str, result: CompatibilityResult) -> str:
        q = question.lower()
        if "perché" in q or "perche" in q or "why" in q:
            for comp in result.components:
                if comp.name.lower() in q:
                    return self.why_incompatible(result, comp.name)
            return ("Non ho abbastanza dati per rispondere con certezza. "
                    "Il Compatibility Engine non ha identificato un problema specifico.")
        if "macos" in q or "consigli" in q.lower():
            return self.recommended_macos(result)
        return "\n".join(explain_results(result))

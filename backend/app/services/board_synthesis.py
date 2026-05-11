"""Cross-interview synthesis — produces the project research board."""

import json
import logging
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

BOARD_PROMPT = """\
You are a senior UX researcher synthesizing findings across multiple customer interviews.

Given a set of interviews (each with its extracted insights and participant profile), produce a structured research board.

Return valid JSON with exactly these keys:

{
  "recurring_themes": [
    {
      "name": "Theme name",
      "description": "1-2 sentence summary",
      "count": <number of interviews mentioning this>,
      "strength": "strong" | "moderate" | "weak",
      "interviews": [
        {
          "title": "exact interview title",
          "insight": "the specific insight text from this interview that supports the theme",
          "quote": "the exact verbatim quote from the transcript that evidences this"
        }
      ]
    }
  ],
  "pain_points": [
    {
      "text": "Pain point description",
      "count": <frequency across interviews>,
      "interviews": [
        {
          "title": "exact interview title",
          "insight": "the specific pain point insight from this interview",
          "quote": "the exact verbatim quote that captures this pain"
        }
      ]
    }
  ],
  "unique_insights": [
    {
      "text": "Insight that only appeared once but is worth noting",
      "interview": "exact interview title",
      "quote": "supporting verbatim quote",
      "why_notable": "brief reason this stands out"
    }
  ],
  "patterns": [
    {
      "title": "Pattern name",
      "description": "Non-obvious correlation or pattern across interviews",
      "evidence": "How you detected this — specific references",
      "type": "behavioral" | "demographic" | "contextual" | "emotional"
    }
  ],
  "demographic_summary": {
    "age_ranges": {"26-35": 2, "36-45": 1},
    "roles": ["PM", "Founder", ...],
    "industries": ["SaaS", "E-commerce", ...],
    "tech_levels": {"technical": 2, "non-technical": 1},
    "locations": ["India", "US", ...]
  },
  "data_gaps": [
    {
      "question": "What question is left unanswered?",
      "context": "Why this matters",
      "missing_in": <number of interviews where this was unclear>
    }
  ]
}

Be rigorous. Only report patterns that have genuine evidence across multiple interviews.
Flag single-interview observations as unique_insights, not patterns.
For every interview entry in recurring_themes and pain_points, include the most relevant verbatim quote — do not paraphrase.
Return ONLY the JSON, no explanation.
"""


class BoardSynthesisService:
    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def synthesize(
        self,
        interviews: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        interviews: list of dicts each with keys:
          - title
          - analysis (dict of pain_points, goals, etc.)
          - profile (dict of name, role, age_range, etc.)
          - report_summary (executive_summary string)
        """
        if not interviews:
            return self._empty_board()

        context = self._build_context(interviews)
        logger.info("Running board synthesis across %d interviews", len(interviews))

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8192,
                system=BOARD_PROMPT,
                messages=[{"role": "user", "content": context}],
            )
            text = response.content[0].text.strip()

            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            result = json.loads(text)
        except Exception as exc:
            logger.error("Board synthesis failed: %s", exc)
            raise

        return result

    def _build_context(self, interviews: list[dict[str, Any]]) -> str:
        parts = [f"# Research Board Synthesis\n\nTotal interviews: {len(interviews)}\n"]

        for i, iv in enumerate(interviews, 1):
            parts.append(f"\n---\n## Interview {i}: {iv['title']}")

            profile = iv.get("profile") or {}
            if any(profile.get(f) for f in ["role", "age_range", "industry"]):
                parts.append("### Participant Profile")
                for field in ["name", "role", "age_range", "industry", "tech_level", "location", "financial_context"]:
                    val = profile.get(field)
                    if val:
                        parts.append(f"- {field}: {val}")

            summary = iv.get("report_summary")
            if summary:
                parts.append(f"### Executive Summary\n{summary[:1000]}")

            analysis = iv.get("analysis") or {}
            for cat in ["pain_points", "goals", "objections", "feature_requests", "workarounds", "emotional_moments", "strong_quotes"]:
                items = analysis.get(cat) or []
                if items:
                    parts.append(f"### {cat.replace('_', ' ').title()}")
                    for item in items[:8]:
                        if isinstance(item, dict):
                            text_val = item.get("text", "")
                            quote = item.get("quote", "")
                            parts.append(f"- {text_val}" + (f' ("{quote}")' if quote else ""))

        return "\n".join(parts)

    def _empty_board(self) -> dict[str, Any]:
        return {
            "recurring_themes": [],
            "pain_points": [],
            "unique_insights": [],
            "patterns": [],
            "demographic_summary": {},
            "data_gaps": [],
        }

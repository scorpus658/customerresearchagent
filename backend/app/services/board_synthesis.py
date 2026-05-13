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

OUTPUT SIZE RULES (critical — output must fit in one response):
- recurring_themes: max 8 themes total
- pain_points: max 8 pain points total
- For each theme/pain point, include at most 5 representative interviews (pick the most illustrative ones)
- Each "insight" field: max 20 words
- Each "quote" field: max 25 words — truncate with "…" if needed, keep the most impactful fragment
- unique_insights: max 5 items; "why_notable" max 15 words
- patterns: max 5 items; "evidence" max 25 words
- data_gaps: max 4 items

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
          "insight": "≤20 words: specific insight from this interview supporting the theme",
          "quote": "≤25 words verbatim quote evidencing this (truncate with … if needed)"
        }
      ]
    }
  ],
  "pain_points": [
    {
      "text": "Pain point description (1 sentence)",
      "count": <frequency across interviews>,
      "interviews": [
        {
          "title": "exact interview title",
          "insight": "≤20 words: specific pain point insight from this interview",
          "quote": "≤25 words verbatim quote capturing this pain (truncate with … if needed)"
        }
      ]
    }
  ],
  "unique_insights": [
    {
      "text": "Insight that only appeared once but is worth noting",
      "interview": "exact interview title",
      "quote": "≤25 words supporting verbatim quote",
      "why_notable": "≤15 words: why this stands out"
    }
  ],
  "patterns": [
    {
      "title": "Pattern name",
      "description": "1 sentence: non-obvious correlation across interviews",
      "evidence": "≤25 words: how you detected this",
      "type": "behavioral" | "demographic" | "contextual" | "emotional"
    }
  ],
  "demographic_summary": {
    "age_ranges": {"26-35": 2, "36-45": 1},
    "roles": ["PM", "Founder"],
    "industries": ["SaaS", "E-commerce"],
    "tech_levels": {"technical": 2, "non-technical": 1},
    "locations": ["India", "US"]
  },
  "data_gaps": [
    {
      "question": "What question is left unanswered?",
      "context": "Why this matters (1 sentence)",
      "missing_in": <number of interviews where this was unclear>
    }
  ]
}

Be rigorous. Only report patterns with genuine evidence across multiple interviews.
Flag single-interview observations as unique_insights, not patterns.
Strictly respect the word limits above — the entire JSON must be complete and valid.
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
                max_tokens=32000,
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

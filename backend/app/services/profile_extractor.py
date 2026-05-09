"""Extract a structured interviewee profile from a transcript using Claude."""

import json
import logging
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

PROFILE_FIELDS = [
    "name",
    "age_range",
    "role",

    "industry",
    "tech_level",
    "financial_context",
    "location",
]

FIELD_LABELS = {
    "name": "Name or pseudonym",
    "age_range": "Age range (e.g. 26-35, 36-45)",
    "role": "Job title / role",

    "industry": "Industry or sector",
    "tech_level": "Technical expertise (non-technical, somewhat-technical, technical, very-technical)",
    "financial_context": "Any mentions of budget, pricing, spending, or financial constraints (direct quotes preferred)",
    "location": "Location or region",
}

EXTRACT_PROMPT = """\
You are extracting a structured profile of the interview participant from a transcript.

Extract ONLY what is clearly stated or strongly implied. Do NOT infer or guess.
If a field cannot be determined from the transcript, return null for that field.

Return valid JSON with exactly these keys:
{
  "name": string | null,
  "age_range": string | null,          // e.g. "26-35", "46-55"
  "role": string | null,               // job title as stated

  "industry": string | null,
  "tech_level": string | null,         // "non-technical" | "somewhat-technical" | "technical" | "very-technical"
  "financial_context": string | null,  // relevant quotes about budget/spend/pricing
  "location": string | null,
  "notes": string | null               // any other useful context about this person
}

Return ONLY the JSON object, no explanation.
"""


class ProfileExtractorService:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def extract(self, raw_text: str) -> dict[str, Any]:
        """
        Extract structured profile from transcript text.
        Returns the profile dict plus a `missing_fields` list of field names
        that could not be determined.
        """
        truncated = raw_text[:40000] if len(raw_text) > 40000 else raw_text

        try:
            response = self._client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=EXTRACT_PROMPT,
                messages=[{"role": "user", "content": f"Transcript:\n\n{truncated}"}],
            )
            text = response.content[0].text.strip()

            # Strip markdown fences if present
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            profile = json.loads(text)
        except Exception as exc:
            logger.error("Profile extraction failed: %s", exc)
            profile = {f: None for f in PROFILE_FIELDS}
            profile["notes"] = None

        missing = [f for f in PROFILE_FIELDS if not profile.get(f)]
        profile["missing_fields"] = missing
        return profile

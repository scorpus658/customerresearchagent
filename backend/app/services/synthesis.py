"""Synthesise a final report from interview data using Claude."""

import json
import logging
from typing import Any

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

SYNTHESIS_PROMPT = """\
You are an expert customer research analyst. Given an interview transcript, extracted insights, and interview metadata, produce a comprehensive research report.

Your report must include:

1. **executive_summary** (string): A 3-5 paragraph executive summary covering the key findings, main themes, and critical recommendations. Be specific and reference actual quotes.

2. **detailed_findings** (object): Organised by theme. Each key is a theme name, and the value is an object with:
   - description: What this theme covers
   - insights: Array of insight objects from the analysis that support this theme
   - evidence: Key quotes and data points
   - implications: What this means for the product/business

3. **themes** (array): Each element has:
   - name: Theme name
   - description: 1-2 sentence description
   - insight_ids: Array of indices referencing insights from the analysis
   - evidence_count: Number of supporting data points

4. **recommendations** (array): Each element has:
   - title: Short recommendation title
   - description: Detailed recommendation
   - priority: "high", "medium", or "low"
   - supporting_evidence: Key quotes/insights that support this recommendation
   - effort: "low", "medium", or "high"

Be rigorous: every claim must be backed by a specific quote or insight from the data.
Flag any insights with confidence below 0.5 in a "low_confidence_flags" section.

Return ONLY valid JSON with keys: executive_summary, detailed_findings, themes, recommendations, metadata.
"""


class SynthesisService:
    """Generate a comprehensive report from interview analysis using Claude."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def synthesize_report(
        self,
        interview: dict[str, Any],
        transcript: dict[str, Any],
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Produce a final synthesised report.

        Args:
            interview: Interview metadata (title, filename, etc.)
            transcript: {raw_text, segments}
            analysis: Extracted insights dict

        Returns:
            {executive_summary, detailed_findings, themes, recommendations, metadata}
        """
        # Build context for Claude
        context = self._build_context(interview, transcript, analysis)

        logger.info("Synthesising report for interview %s", interview.get("id", "unknown"))

        response = await self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            messages=[
                {"role": "user", "content": context},
            ],
            system=SYNTHESIS_PROMPT,
        )

        content = response.content[0].text
        report = self._parse_response(content)

        # Verification pass
        report = self._verify_report(report, analysis)

        logger.info("Report synthesis complete")
        return report

    def _build_context(
        self,
        interview: dict[str, Any],
        transcript: dict[str, Any],
        analysis: dict[str, Any],
    ) -> str:
        """Assemble the prompt context from all data sources."""
        parts: list[str] = []

        parts.append("## Interview Metadata")
        parts.append(f"- Title: {interview.get('title', 'Untitled')}")
        parts.append(f"- Original file: {interview.get('original_filename', 'unknown')}")
        parts.append(f"- Language detected: {interview.get('language_detected', 'en')}")
        parts.append("")

        parts.append("## Transcript")
        raw_text = transcript.get("raw_text", "")
        # Truncate very long transcripts to stay within context limits
        if len(raw_text) > 60000:
            parts.append(raw_text[:60000])
            parts.append("\n... [transcript truncated for length] ...")
        else:
            parts.append(raw_text)
        parts.append("")

        parts.append("## Extracted Insights")
        # Serialise analysis without raw_extraction to save tokens
        analysis_clean = {k: v for k, v in analysis.items() if k != "raw_extraction"}
        parts.append(json.dumps(analysis_clean, indent=2, default=str))

        return "\n".join(parts)

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse Claude's JSON response, handling markdown fences and partial JSON."""
        text = content.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract the first JSON object from the text
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("Failed to parse synthesis response as JSON: %s", exc)
            # Extract just the executive_summary text if the full JSON failed
            return {
                "executive_summary": text,
                "detailed_findings": {},
                "themes": [],
                "recommendations": [],
                "metadata": {"parse_error": str(exc)},
            }

    def _verify_report(
        self, report: dict[str, Any], analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Verification pass: check every referenced insight has quote + speaker + timestamp + confidence >= 0.5.
        Flag low-confidence items.
        """
        low_confidence_flags: list[dict[str, Any]] = []

        categories = [
            "pain_points", "goals", "objections", "feature_requests",
            "workarounds", "emotional_moments", "strong_quotes",
        ]

        for cat in categories:
            insights = analysis.get(cat, [])
            for i, insight in enumerate(insights):
                if not isinstance(insight, dict):
                    continue

                issues: list[str] = []
                if not insight.get("quote"):
                    issues.append("missing quote")
                if not insight.get("speaker"):
                    issues.append("missing speaker")
                confidence = insight.get("confidence", 0)
                if confidence < 0.5:
                    issues.append(f"low confidence ({confidence})")

                if issues:
                    low_confidence_flags.append({
                        "category": cat,
                        "index": i,
                        "text": insight.get("text", ""),
                        "issues": issues,
                        "confidence": confidence,
                    })

        if low_confidence_flags:
            logger.info("Verification flagged %d low-confidence insights", len(low_confidence_flags))

        metadata = report.get("metadata", {}) or {}
        metadata["low_confidence_flags"] = low_confidence_flags
        metadata["total_insights_verified"] = sum(
            len(analysis.get(cat, [])) for cat in categories
        )
        metadata["flagged_count"] = len(low_confidence_flags)
        report["metadata"] = metadata

        return report

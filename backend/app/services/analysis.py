"""Extract structured insights from transcript segments using OpenAI gpt-4o-mini."""

import hashlib
import json
import logging
from typing import Any

import openai

from app.config import settings

logger = logging.getLogger(__name__)

INSIGHT_CATEGORIES = [
    "pain_points",
    "goals",
    "objections",
    "feature_requests",
    "workarounds",
    "emotional_moments",
    "strong_quotes",
]

EXTRACTION_PROMPT = """\
You are an expert qualitative research analyst. Analyse the following interview transcript chunk and extract structured insights.

For each category below, extract relevant items. Each item MUST include:
- text: A short summary of the insight (1-2 sentences)
- quote: The exact verbatim quote from the transcript that supports this insight
- speaker: Who said it
- timestamp: The start_time from the segment (or null if unavailable)
- confidence: A float 0-1 indicating how confident you are this is a genuine insight of this category
- category: A sub-category label you choose (e.g. "pricing", "onboarding", "performance")

Categories to extract:
1. pain_points — problems, frustrations, complaints
2. goals — desired outcomes, objectives, aspirations
3. objections — resistance, concerns, pushback about a product/service
4. feature_requests — desired features, improvements, capabilities
5. workarounds — hacks, manual processes, alternative tools used
6. emotional_moments — strong emotional reactions (positive or negative)
7. strong_quotes — particularly insightful, memorable, or quotable statements

Return a JSON object with these seven keys, each containing an array of insight objects.
If a category has no insights in this chunk, return an empty array for it.
Return ONLY valid JSON, no markdown fences or commentary.
"""

CHUNK_TOKEN_LIMIT = 3000
OVERLAP_TOKENS = 300


class AnalysisService:
    """Extract structured insights from transcript segments."""

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    async def extract_insights(self, transcript_segments: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Process transcript segments and extract insights across all categories.

        Returns a dict with keys for each insight category plus raw_extraction.
        """
        chunks = self._build_chunks(transcript_segments)
        logger.info("Split transcript into %d chunks for analysis", len(chunks))

        all_results: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            logger.info("Analysing chunk %d/%d", i + 1, len(chunks))
            result = await self._extract_from_chunk(chunk)
            if result:
                all_results.append(result)

        merged = self._merge_results(all_results)
        merged["raw_extraction"] = all_results

        logger.info(
            "Analysis complete: %s",
            {cat: len(merged.get(cat, [])) for cat in INSIGHT_CATEGORIES},
        )
        return merged

    def _build_chunks(self, segments: list[dict[str, Any]]) -> list[str]:
        """Split segments into text chunks of roughly CHUNK_TOKEN_LIMIT tokens with overlap."""
        chunks: list[str] = []
        current_lines: list[str] = []
        current_token_est = 0

        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("translated_text") or seg.get("text", "")
            start = seg.get("start_time")
            ts_str = f" [{start:.1f}s]" if start is not None else ""
            line = f"{speaker}{ts_str}: {text}"

            # Rough token estimate: ~4 chars per token
            line_tokens = len(line) // 4

            if current_token_est + line_tokens > CHUNK_TOKEN_LIMIT and current_lines:
                chunks.append("\n".join(current_lines))
                # Keep last few lines for overlap
                overlap_lines: list[str] = []
                overlap_tokens = 0
                for prev_line in reversed(current_lines):
                    t = len(prev_line) // 4
                    if overlap_tokens + t > OVERLAP_TOKENS:
                        break
                    overlap_lines.insert(0, prev_line)
                    overlap_tokens += t
                current_lines = overlap_lines
                current_token_est = overlap_tokens

            current_lines.append(line)
            current_token_est += line_tokens

        if current_lines:
            chunks.append("\n".join(current_lines))

        return chunks if chunks else ["(empty transcript)"]

    async def _extract_from_chunk(self, chunk_text: str) -> dict[str, Any] | None:
        """Send a single chunk to gpt-4o-mini for insight extraction."""
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": chunk_text},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            return json.loads(content)

        except (openai.OpenAIError, json.JSONDecodeError) as exc:
            logger.error("Chunk extraction failed: %s", exc)
            return None

    def _merge_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        """Merge and deduplicate insights across chunks."""
        merged: dict[str, list[dict[str, Any]]] = {cat: [] for cat in INSIGHT_CATEGORIES}

        for result in results:
            for cat in INSIGHT_CATEGORIES:
                items = result.get(cat, [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    # Ensure required fields exist
                    item.setdefault("text", "")
                    item.setdefault("quote", "")
                    item.setdefault("speaker", "Unknown")
                    item.setdefault("timestamp", None)
                    item.setdefault("confidence", 0.5)
                    item.setdefault("category", "general")
                    item.setdefault("translated_quote", None)
                    merged[cat].append(item)

        # Deduplicate by quote similarity
        for cat in INSIGHT_CATEGORIES:
            merged[cat] = self._dedup_insights(merged[cat])

        return merged

    def _dedup_insights(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove near-duplicate insights based on quote fingerprinting."""
        if not insights:
            return insights

        seen_hashes: set[str] = set()
        deduped: list[dict[str, Any]] = []

        for insight in insights:
            quote = insight.get("quote", "").strip().lower()
            # Normalise whitespace for fingerprint
            normalised = " ".join(quote.split())
            # Use first 100 chars as fingerprint to catch near-dupes
            fingerprint = hashlib.md5(normalised[:100].encode()).hexdigest()

            if fingerprint not in seen_hashes:
                seen_hashes.add(fingerprint)
                deduped.append(insight)
            else:
                logger.debug("Deduped insight: %s", insight.get("text", "")[:60])

        return deduped

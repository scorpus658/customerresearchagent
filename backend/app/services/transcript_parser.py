"""Parse uploaded transcript files (.txt, .srt, .vtt, .json) into a normalised format."""

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Common speaker patterns: "Speaker 1:", "John:", "INTERVIEWER:", "[Speaker 1]"
_SPEAKER_PATTERN = re.compile(
    r"^(?:\[?(?P<speaker>[A-Za-z0-9 _-]+)\]?\s*:\s*)(?P<text>.+)$"
)

# SRT timestamp: 00:01:23,456 --> 00:01:26,789
_SRT_TS = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)

# VTT timestamp (same pattern, sometimes without hours)
_VTT_TS = re.compile(
    r"(?:(\d{2}):)?(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(?:(\d{2}):)?(\d{2}):(\d{2})[,.](\d{3})"
)


def _ts_to_seconds(h: int, m: int, s: int, ms: int) -> float:
    return h * 3600 + m * 60 + s + ms / 1000.0


Segment = dict[str, Any]


def _make_segment(
    text: str,
    speaker: str = "Unknown",
    start_time: float | None = None,
    end_time: float | None = None,
) -> Segment:
    return {
        "speaker": speaker,
        "text": text.strip(),
        "start_time": start_time,
        "end_time": end_time,
        "language": None,
        "translated_text": None,
    }


def _parse_txt(content: str) -> list[Segment]:
    """Best-effort parsing of plain text, detecting speaker labels."""
    segments: list[Segment] = []
    current_speaker = "Unknown"
    buffer: list[str] = []

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        match = _SPEAKER_PATTERN.match(line)
        if match:
            # Flush previous buffer
            if buffer:
                segments.append(_make_segment(" ".join(buffer), speaker=current_speaker))
                buffer = []
            current_speaker = match.group("speaker").strip()
            text = match.group("text").strip()
            if text:
                buffer.append(text)
        else:
            buffer.append(line)

    if buffer:
        segments.append(_make_segment(" ".join(buffer), speaker=current_speaker))

    return segments


def _parse_srt(content: str) -> list[Segment]:
    """Parse SRT subtitle format."""
    segments: list[Segment] = []
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue

        # Find the timestamp line
        ts_line_idx = None
        for i, line in enumerate(lines):
            if _SRT_TS.search(line):
                ts_line_idx = i
                break

        if ts_line_idx is None:
            continue

        ts_match = _SRT_TS.search(lines[ts_line_idx])
        if not ts_match:
            continue

        g = [int(x) for x in ts_match.groups()]
        start = _ts_to_seconds(g[0], g[1], g[2], g[3])
        end = _ts_to_seconds(g[4], g[5], g[6], g[7])

        text_lines = lines[ts_line_idx + 1 :]
        text = " ".join(l.strip() for l in text_lines if l.strip())
        # Strip HTML tags commonly found in SRT
        text = re.sub(r"<[^>]+>", "", text)

        # Try to detect speaker from text
        speaker = "Unknown"
        sp_match = _SPEAKER_PATTERN.match(text)
        if sp_match:
            speaker = sp_match.group("speaker").strip()
            text = sp_match.group("text").strip()

        if text:
            segments.append(_make_segment(text, speaker=speaker, start_time=start, end_time=end))

    return segments


def _parse_vtt(content: str) -> list[Segment]:
    """Parse WebVTT format."""
    segments: list[Segment] = []
    # Remove WEBVTT header and metadata
    lines_raw = content.strip().splitlines()
    start_idx = 0
    for i, line in enumerate(lines_raw):
        if line.strip().upper().startswith("WEBVTT"):
            start_idx = i + 1
            break

    # Skip any header lines until first blank line after WEBVTT
    while start_idx < len(lines_raw) and lines_raw[start_idx].strip():
        start_idx += 1

    body = "\n".join(lines_raw[start_idx:])
    blocks = re.split(r"\n\s*\n", body.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        ts_line_idx = None
        for i, line in enumerate(lines):
            if _VTT_TS.search(line):
                ts_line_idx = i
                break

        if ts_line_idx is None:
            continue

        ts_match = _VTT_TS.search(lines[ts_line_idx])
        if not ts_match:
            continue

        g = ts_match.groups()
        h1 = int(g[0]) if g[0] else 0
        m1, s1, ms1 = int(g[1]), int(g[2]), int(g[3])
        h2 = int(g[4]) if g[4] else 0
        m2, s2, ms2 = int(g[5]), int(g[6]), int(g[7])
        start = _ts_to_seconds(h1, m1, s1, ms1)
        end = _ts_to_seconds(h2, m2, s2, ms2)

        text_lines = lines[ts_line_idx + 1 :]
        text = " ".join(l.strip() for l in text_lines if l.strip())
        text = re.sub(r"<[^>]+>", "", text)

        speaker = "Unknown"
        sp_match = _SPEAKER_PATTERN.match(text)
        if sp_match:
            speaker = sp_match.group("speaker").strip()
            text = sp_match.group("text").strip()

        if text:
            segments.append(_make_segment(text, speaker=speaker, start_time=start, end_time=end))

    return segments


def _parse_json_transcript(content: str) -> list[Segment]:
    """Parse JSON transcript. Expects an array of objects or {segments: [...]}."""
    data = json.loads(content)

    if isinstance(data, dict):
        # Try common keys
        for key in ("segments", "transcript", "results", "data"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            raise ValueError("JSON object does not contain a recognisable segments array")

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of segments")

    segments: list[Segment] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = item.get("text", item.get("content", "")).strip()
        if not text:
            continue
        speaker = item.get("speaker", item.get("name", "Unknown"))
        start = item.get("start_time", item.get("start", item.get("startTime")))
        end = item.get("end_time", item.get("end", item.get("endTime")))
        segments.append(
            _make_segment(
                text,
                speaker=str(speaker),
                start_time=float(start) if start is not None else None,
                end_time=float(end) if end is not None else None,
            )
        )

    return segments


def parse_transcript(file_path: str, file_type: str) -> dict[str, Any]:
    """
    Parse an uploaded transcript file.

    Returns {"raw_text": str, "segments": list[Segment]}
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()

    logger.info("Parsing transcript file %s (type=%s, ext=%s)", path.name, file_type, ext)

    if ext == ".json":
        segments = _parse_json_transcript(content)
    elif ext == ".srt":
        segments = _parse_srt(content)
    elif ext == ".vtt":
        segments = _parse_vtt(content)
    else:
        # Default: plain text
        segments = _parse_txt(content)

    raw_text = "\n".join(
        f"{seg['speaker']}: {seg['text']}" if seg["speaker"] != "Unknown" else seg["text"]
        for seg in segments
    )

    logger.info("Parsed %d segments from %s", len(segments), path.name)
    return {"raw_text": raw_text, "segments": segments}

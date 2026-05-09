"""Audio/video transcription using OpenAI gpt-4o-mini-transcribe."""

import logging
import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import openai

from app.config import settings

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}

MAX_FILE_SIZE_MB = 24  # stay safely under OpenAI's 25MB limit
CHUNK_DURATION_SECS = 600  # 10-minute chunks


class TranscriptionService:
    """Transcribe audio/video files via OpenAI and optionally translate non-English segments."""

    def __init__(self) -> None:
        self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, file_path: str, file_type: str) -> dict[str, Any]:
        """
        Transcribe an audio or video file.

        Pipeline:
          1. Extract audio from video if needed
          2. Compress to mono 16kHz mp3 to reduce size
          3. If still > MAX_FILE_SIZE_MB, split into chunks and transcribe each
          4. Stitch segments together
          5. Translate non-English segments
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        audio_path = file_path
        temps: list[str] = []

        try:
            # Step 1: extract audio from video
            if ext in VIDEO_EXTENSIONS:
                audio_path = self._ffmpeg_extract_audio(file_path)
                temps.append(audio_path)

            # Step 2: compress
            compressed_path = self._ffmpeg_compress(audio_path)
            temps.append(compressed_path)

            # Step 3: transcribe (chunked if file is large or audio is long)
            size_mb = Path(compressed_path).stat().st_size / (1024 * 1024)
            duration = self._get_duration(compressed_path)
            if size_mb > MAX_FILE_SIZE_MB or duration > CHUNK_DURATION_SECS:
                logger.info("File is %.1fMB, %.0fs — transcribing in chunks", size_mb, duration)
                segments = self._transcribe_chunked(compressed_path, temps)
            else:
                segments = self._transcribe_file(compressed_path)

            # Step 4: translate non-English
            non_english = [s for s in segments if s.get("language") and s["language"] != "en"]
            if non_english:
                await self._translate_segments(non_english)

            raw_text = "\n".join(f"{seg['speaker']}: {seg['text']}" for seg in segments)
            return {"raw_text": raw_text, "segments": segments}

        finally:
            for t in temps:
                try:
                    Path(t).unlink(missing_ok=True)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # ffmpeg helpers
    # ------------------------------------------------------------------

    def _ffmpeg_compress(self, audio_path: str) -> str:
        """Convert audio to mono 16kHz mp3 at 32kbps — good enough for STT, ~8x smaller."""
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        out = tmp.name

        cmd = [
            "ffmpeg", "-i", audio_path,
            "-ac", "1",          # mono
            "-ar", "16000",      # 16kHz sample rate
            "-b:a", "32k",       # 32kbps bitrate
            "-y", out,
        ]
        logger.info("Compressing audio to mono 16kHz mp3")
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg compression failed: {proc.stderr[:500]}")

        original_mb = Path(audio_path).stat().st_size / (1024 * 1024)
        compressed_mb = Path(out).stat().st_size / (1024 * 1024)
        logger.info("Compressed %.1fMB → %.1fMB", original_mb, compressed_mb)
        return out

    def _ffmpeg_extract_audio(self, video_path: str) -> str:
        """Extract audio track from video."""
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        out = tmp.name

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
            "-y", out,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg extraction failed: {proc.stderr[:500]}")
        return out

    def _get_duration(self, audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def _ffmpeg_split_chunk(self, audio_path: str, start: float, duration: float) -> str:
        """Extract a time slice from the audio file."""
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        out = tmp.name

        cmd = [
            "ffmpeg", "-i", audio_path,
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",
            "-y", out,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg split failed: {proc.stderr[:500]}")
        return out

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def _transcribe_file(self, audio_path: str) -> list[dict[str, Any]]:
        """Send a single file to OpenAI and parse response into segments."""
        logger.info("Transcribing %s", audio_path)
        with open(audio_path, "rb") as f:
            response = self._client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                response_format="json",
            )

        detected_language = getattr(response, "language", "en") or "en"
        full_text = response.text.strip() if hasattr(response, "text") else str(response)

        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if s.strip()]
        if not sentences:
            sentences = [full_text]

        return [
            {
                "speaker": "Speaker 1",
                "text": sentence,
                "start_time": None,
                "end_time": None,
                "language": detected_language,
                "translated_text": None,
            }
            for sentence in sentences
        ]

    def _transcribe_chunked(self, audio_path: str, temps: list[str]) -> list[dict[str, Any]]:
        """Split audio into chunks and transcribe each, then stitch together."""
        duration = self._get_duration(audio_path)
        if duration == 0:
            return self._transcribe_file(audio_path)

        num_chunks = math.ceil(duration / CHUNK_DURATION_SECS)
        logger.info("Splitting into %d chunks of %ds each", num_chunks, CHUNK_DURATION_SECS)

        all_segments: list[dict[str, Any]] = []

        for i in range(num_chunks):
            start = i * CHUNK_DURATION_SECS
            chunk_path = self._ffmpeg_split_chunk(audio_path, start, CHUNK_DURATION_SECS)
            temps.append(chunk_path)

            logger.info("Transcribing chunk %d/%d (start=%.0fs)", i + 1, num_chunks, start)
            chunk_segments = self._transcribe_file(chunk_path)
            all_segments.extend(chunk_segments)

        return all_segments

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    async def _translate_segments(self, segments: list[dict[str, Any]]) -> None:
        """Batch-translate non-English segments using gpt-4o-mini."""
        texts = [seg["text"] for seg in segments]
        batch_size = 20

        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
            numbered = "\n".join(f"{j + 1}. {t}" for j, t in enumerate(batch))

            try:
                response = self._client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Translate each numbered line to English. "
                                "Preserve the numbering. Output only the translations, "
                                "one per line, with the same numbering."
                            ),
                        },
                        {"role": "user", "content": numbered},
                    ],
                    temperature=0.2,
                )

                result_text = response.choices[0].message.content or ""
                for j, line in enumerate(result_text.strip().splitlines()):
                    idx = i + j
                    if idx < len(segments):
                        clean = line.strip().lstrip("0123456789").lstrip(".):- ").strip()
                        segments[idx]["translated_text"] = clean or line.strip()

            except openai.OpenAIError as exc:
                logger.error("Translation batch failed: %s", exc)

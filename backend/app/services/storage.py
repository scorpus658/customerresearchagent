import logging
import os
from pathlib import Path

import aiofiles
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Handles local file storage and optional S3 uploads."""

    def __init__(self) -> None:
        self._upload_dir = Path(settings.UPLOAD_DIR)
        self._upload_dir.mkdir(parents=True, exist_ok=True)

        self._s3_client = None
        if settings.S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
            try:
                self._s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_REGION,
                )
                logger.info("S3 client initialised for bucket %s", settings.S3_BUCKET)
            except (BotoCoreError, ClientError) as exc:
                logger.warning("Failed to initialise S3 client: %s", exc)

    async def save_file(self, file_bytes: bytes, filename: str) -> str:
        """Save bytes to the local upload directory. Returns the absolute path."""
        dest = self._upload_dir / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(dest, "wb") as f:
            await f.write(file_bytes)
        logger.info("Saved file locally: %s", dest)
        return str(dest.resolve())

    async def upload_to_s3(self, file_path: str, key: str) -> str | None:
        """Upload a local file to S3. Returns the S3 URL or None if S3 is not configured."""
        if self._s3_client is None:
            logger.debug("S3 not configured; skipping upload for %s", key)
            return None
        try:
            self._s3_client.upload_file(file_path, settings.S3_BUCKET, key)
            url = f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            logger.info("Uploaded to S3: %s", url)
            return url
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3 upload failed for %s: %s", key, exc)
            return None

    async def get_file(self, path: str) -> bytes:
        """Read a file from the local filesystem."""
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> None:
        """Delete a local file if it exists."""
        try:
            os.remove(path)
            logger.info("Deleted local file: %s", path)
        except FileNotFoundError:
            logger.debug("File already absent: %s", path)

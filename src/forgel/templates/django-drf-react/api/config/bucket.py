"""Create the S3 bucket the API stores files in, when it does not exist yet.

Run by ``docker/entrypoint.sh`` on container startup. Without ``S3_BUCKET``
the project uses the file-system storage, so there is nothing to create and
this command exits successfully. Credentials and the endpoint come from the
environment only; nothing is committed.
"""
from __future__ import annotations

import os
import sys
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

ATTEMPTS = 30
DELAY = 2.0


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("S3_ENDPOINT") or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY") or None,
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY") or None,
        region_name=os.environ.get("S3_REGION", "us-east-1"),
    )


def ensure_bucket(bucket: str, attempts: int = ATTEMPTS) -> bool:
    """Return True once ``bucket`` exists, retrying while storage starts."""

    client = s3_client()
    for attempt in range(1, attempts + 1):
        try:
            client.head_bucket(Bucket=bucket)
            return True
        except (ClientError, BotoCoreError):
            try:
                client.create_bucket(Bucket=bucket)
                return True
            except (ClientError, BotoCoreError):
                pass
        if attempt < attempts:
            time.sleep(DELAY)
    return False


def main() -> int:
    bucket = os.environ.get("S3_BUCKET", "")
    if not bucket:
        print("S3_BUCKET is not set, keeping the file-system storage")
        return 0
    if ensure_bucket(bucket):
        print(f"bucket {bucket!r} is ready")
        return 0
    print(f"object storage bucket {bucket!r} is not available", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

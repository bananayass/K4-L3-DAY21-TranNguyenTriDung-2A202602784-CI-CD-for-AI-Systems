"""Shared S3 client setup for CI release helpers."""

import json
import os

import boto3


def create_s3_client():
    """Create an S3 client from the STORAGE_CREDENTIALS GitHub secret."""
    try:
        credentials = json.loads(os.environ["STORAGE_CREDENTIALS"])
    except (KeyError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "STORAGE_CREDENTIALS must contain valid AWS credentials JSON"
        ) from error

    access_key = credentials.get("aws_access_key_id")
    secret_key = credentials.get("aws_secret_access_key")
    if not access_key or not secret_key:
        raise RuntimeError(
            "STORAGE_CREDENTIALS needs aws_access_key_id and "
            "aws_secret_access_key"
        )

    client_options = {
        "region_name": credentials.get("region")
        or os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2"),
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
    }
    session_token = credentials.get("aws_session_token")
    if session_token:
        client_options["aws_session_token"] = session_token

    return boto3.client("s3", **client_options)

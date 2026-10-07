"""Publish a gate-approved model bundle and its report to S3."""

import os
from pathlib import Path

from botocore.exceptions import ClientError

from scripts.s3_client import create_s3_client


def _read_current_object(s3, bucket, object_key):
    try:
        response = s3.get_object(Bucket=bucket, Key=object_key)
    except ClientError as error:
        details = error.response.get("Error", {})
        status = error.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if (
            status == 404
            and details.get("Code") in {"NoSuchKey", "404", "NotFound"}
        ):
            return None
        raise
    return response["Body"].read()


def main():
    bucket = os.environ["ARTIFACT_BUCKET"]
    artifact_root = Path(os.environ.get("ARTIFACT_ROOT", "."))
    s3 = create_s3_client()
    artifacts = [
        (
            artifact_root / "models/model.joblib",
            "artifacts/current/model.joblib",
        ),
        (
            artifact_root / "outputs/report.json",
            "artifacts/current/report.json",
        ),
    ]

    previous_objects = {
        object_key: _read_current_object(s3, bucket, object_key)
        for _, object_key in artifacts
    }
    try:
        for local_path, object_key in artifacts:
            s3.upload_file(str(local_path), bucket, object_key)
            print(f"Uploaded s3://{bucket}/{object_key}")
    except Exception as publish_error:
        try:
            for object_key, previous_body in previous_objects.items():
                if previous_body is None:
                    s3.delete_object(Bucket=bucket, Key=object_key)
                else:
                    s3.put_object(
                        Bucket=bucket,
                        Key=object_key,
                        Body=previous_body,
                    )
        except Exception as rollback_error:
            raise RuntimeError(
                "S3 release upload failed and restoring prior artifacts also "
                "failed; inspect artifacts/current/model.joblib and "
                "artifacts/current/report.json."
            ) from rollback_error
        raise


if __name__ == "__main__":
    main()

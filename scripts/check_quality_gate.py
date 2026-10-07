"""Enforce the minimum F1 and no-regression release gates."""

import json
import math
import os

from botocore.exceptions import ClientError

from scripts.s3_client import create_s3_client


CURRENT_REPORT_KEY = "artifacts/current/report.json"
MINIMUM_F1 = 0.65


def read_f1(report, label):
    try:
        score = float(report["f1_score"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError(f"{label} report has no valid f1_score") from error

    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise RuntimeError(f"{label} f1_score must be finite and in [0, 1]")
    return score


def previous_f1(s3, bucket):
    try:
        response = s3.get_object(Bucket=bucket, Key=CURRENT_REPORT_KEY)
    except ClientError as error:
        details = error.response.get("Error", {})
        status = error.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        code = details.get("Code")
        if status == 404 and code in {"NoSuchKey", "404", "NotFound"}:
            print("No previous report found; rollback comparison is skipped.")
            return None
        raise

    try:
        report = json.loads(response["Body"].read())
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Previous S3 report is not valid JSON") from error
    return read_f1(report, "Previous S3")


def main():
    bucket = os.environ["ARTIFACT_BUCKET"]
    report_path = os.environ.get("REPORT_PATH", "outputs/report.json")
    with open(report_path, encoding="utf-8") as report_file:
        current_report = json.load(report_file)
    current_score = read_f1(current_report, "Candidate")

    if current_score < MINIMUM_F1:
        raise SystemExit(
            f"FAILED: candidate f1_score {current_score:.4f} < "
            f"{MINIMUM_F1:.2f}; release blocked."
        )
    print(
        f"Minimum quality passed: {current_score:.4f} >= "
        f"{MINIMUM_F1:.2f}."
    )

    old_score = previous_f1(create_s3_client(), bucket)
    if old_score is not None and current_score < old_score:
        raise SystemExit(
            f"FAILED: candidate f1_score {current_score:.4f} < "
            f"current f1_score {old_score:.4f}; release blocked."
        )
    if old_score is not None:
        print(
            f"No-regression gate passed: {current_score:.4f} >= "
            f"{old_score:.4f}."
        )


if __name__ == "__main__":
    main()

"""Nightly Reports - writes a daily sales summary to S3. Runs on an EventBridge schedule."""
import datetime
import json
import os

REPORT_BUCKET = os.environ.get("REPORT_BUCKET", "")
APP_VERSION = os.environ.get("APP_VERSION", "dev")

SAMPLE_SALES = [
    {"store": "north", "amount": 1200.50},
    {"store": "south", "amount": 980.00},
    {"store": "east", "amount": 1543.25},
]

_s3 = None


def s3():
    global _s3
    if _s3 is None:
        import boto3

        _s3 = boto3.client("s3")
    return _s3


def build_report(day, sales):
    return {
        "date": day,
        "stores": len(sales),
        "revenue": round(sum(s["amount"] for s in sales), 2),
        "generated_by": APP_VERSION,
    }


def lambda_handler(event, context):
    if event.get("simulate_failure"):
        raise RuntimeError("simulated failure requested")
    day = event.get("date") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    report = build_report(day, SAMPLE_SALES)
    key = f"reports/{day}.json"
    s3().put_object(
        Bucket=REPORT_BUCKET,
        Key=key,
        Body=json.dumps(report).encode("utf-8"),
        ContentType="application/json",
    )
    return {"status": "ok", "key": key}

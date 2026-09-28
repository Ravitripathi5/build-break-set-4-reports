#!/usr/bin/env python3
"""Build & Break - Part A build verifier.

Participants:  python3 tools/check_build.py --id p07
Organizers:    imported by organizer/grade.py (same checks, organizer credentials).

Checks the local work folder and the live resources in the AWS sandbox (read-only,
except for the functional test that sends one test request, message, or file).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

REGION = "ap-south-1"
SETS = {1: "quicklink", 2: "receipts", 3: "orders", 4: "reports", 5: "pricing"}
POLL_SECONDS = 90


class Report:
    def __init__(self):
        self.items = []

    def add(self, section, cid, label, pts, ok, detail=""):
        self.items.append(
            {"section": section, "id": cid, "label": label, "max": pts,
             "points": pts if ok else 0, "ok": bool(ok), "detail": str(detail)[:300]}
        )

    def total(self, section=None):
        rows = [i for i in self.items if section is None or i["section"] == section]
        return sum(i["points"] for i in rows), sum(i["max"] for i in rows)


def run(cmd, cwd=None, timeout=600, env=None):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def aws(*args, timeout=60):
    rc, out, err = run(["aws", *args, "--region", REGION, "--output", "json"], timeout=timeout)
    data = None
    if rc == 0 and out.strip():
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = out
    return rc == 0, data, err.strip()


def invoke(function, payload, qualifier=None):
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    args = ["lambda", "invoke", "--function-name", function, "--cli-binary-format",
            "raw-in-base64-out", "--payload", json.dumps(payload)]
    if qualifier:
        args += ["--qualifier", qualifier]
    ok, meta, err = aws(*args, out)
    try:
        body = open(out).read()
    finally:
        os.remove(out)
    if not ok:
        return None, err
    if isinstance(meta, dict) and meta.get("FunctionError"):
        return None, body
    try:
        return json.loads(body), ""
    except json.JSONDecodeError:
        return None, body


def s3_get_json(bucket, key):
    fd, out = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    ok, _, err = aws("s3api", "get-object", "--bucket", bucket, "--key", key, out)
    try:
        return (json.load(open(out)), "") if ok else (None, err)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    finally:
        os.remove(out)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ---------------------------------------------------------------- local checks

def check_package(rep, work):
    rc, out, err = run([sys.executable, "-m", "unittest", "discover", "-s", "app"], cwd=work, timeout=120)
    rep.add("A", "A1.tests", "Unit tests pass", 3, rc == 0, (err or out).strip().splitlines()[-1:] if rc else "ok")
    df = read(os.path.join(work, "Dockerfile"))
    base = re.search(r"(?im)^FROM\s+public\.ecr\.aws/lambda/python:3\.12", df)
    cmd = "handler.lambda_handler" in df
    ver = re.search(r"APP_VERSION", df)
    rep.add("A", "A1.dockerfile", "Dockerfile: Lambda Python 3.12 base, handler CMD, APP_VERSION", 2,
            bool(base and cmd and ver), f"base={bool(base)} cmd={cmd} version={bool(ver)}")


def check_iac_static(rep, work):
    infra = os.path.join(work, "infra")
    rc, out, err = run(["terraform", "fmt", "-check", "-recursive"], cwd=infra, timeout=60)
    rep.add("A", "A3.fmt", "terraform fmt -check", 2, rc == 0, out.strip() or err.strip() or "ok")

    tmp = tempfile.mkdtemp(prefix="bb-validate-")
    try:
        for name in os.listdir(infra):
            if name.endswith(".tf"):
                shutil.copy(os.path.join(infra, name), tmp)
        env = dict(os.environ)
        cache = os.path.expanduser("~/.terraform.d/plugin-cache")
        os.makedirs(cache, exist_ok=True)
        env["TF_PLUGIN_CACHE_DIR"] = cache
        rc, out, err = run(["terraform", "init", "-backend=false", "-input=false", "-no-color"], cwd=tmp, env=env)
        if rc == 0:
            rc, out, err = run(["terraform", "validate", "-no-color"], cwd=tmp, env=env)
        rep.add("A", "A3.validate", "terraform validate", 2, rc == 0, (err or out).strip()[-300:] or "ok")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tf = "\n".join(read(os.path.join(infra, n)) for n in os.listdir(infra) if n.endswith(".tf"))
    bad = []
    if re.search(r"\b\d{12}\b", tf):
        bad.append("12-digit account id")
    if re.search(r"AKIA[0-9A-Z]{16}", tf):
        bad.append("access key id")
    if re.search(r"(?m)^\s*(access_key|secret_key|token)\s*=", tf):
        bad.append("provider credentials")
    rep.add("A", "A3.nohardcode", "No hardcoded account ID or credentials in infra/", 2, not bad, ", ".join(bad) or "ok")


def check_ci(rep, work):
    wf = ""
    for n in ("deploy.yml", "deploy.yaml"):
        wf = wf or read(os.path.join(work, ".github", "workflows", n))
    present = bool(wf.strip())
    rep.add("A", "A6.tests", "CI runs unit tests", 1, present and re.search(r"unittest|pytest", wf), "" if present else "missing .github/workflows/deploy.yml")
    oidc = present and "configure-aws-credentials" in wf and "role-to-assume" in wf and re.search(r"id-token:\s*write", wf)
    rep.add("A", "A6.oidc", "CI uses OIDC (role-to-assume + id-token: write)", 1, oidc)
    static = re.search(r"aws-access-key-id|aws-secret-access-key|AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID", wf)
    rep.add("A", "A6.nokeys", "CI has no stored AWS access keys", 1, bool(oidc) and not static)
    build = present and re.search(r"docker (buildx )?build|build-push-action", wf) and re.search(r"amazon-ecr-login|ecr get-login-password", wf)
    rep.add("A", "A6.image", "CI builds image and logs in / pushes to ECR", 1, build)
    tfc = present and re.search(r"terraform\s+fmt\s+-check", wf) and "terraform validate" in wf and "terraform plan" in wf
    rep.add("A", "A6.terraform", "CI runs terraform fmt -check, validate, plan", 1, tfc)


# ---------------------------------------------------------------- live checks

def check_registry(rep, prefix, app):
    repo = f"{prefix}-{app}"
    ok, data, err = aws("ecr", "describe-repositories", "--repository-names", repo)
    r = data["repositories"][0] if ok else {}
    rep.add("A", "A2.repo", f"ECR repository {repo} exists", 2, ok, err or "ok")
    rep.add("A", "A2.scan", "Scan on push enabled", 2, r.get("imageScanningConfiguration", {}).get("scanOnPush") is True)
    rep.add("A", "A2.immutable", "Tag mutability IMMUTABLE", 2, r.get("imageTagMutability") == "IMMUTABLE")
    ok, _, err = aws("ecr", "describe-images", "--repository-name", repo, "--image-ids", "imageTag=v1")
    rep.add("A", "A1.image", f"Image {repo}:v1 pushed", 3, ok, err or "ok")


def check_boundary(rep, prefix, app, pid):
    ok, data, err = aws("iam", "get-role", "--role-name", f"{prefix}-{app}-role")
    arn = (data or {}).get("Role", {}).get("PermissionsBoundary", {}).get("PermissionsBoundaryArn", "") if ok else ""
    rep.add("A", "A3.boundary", f"Role {prefix}-{app}-role uses the permissions boundary", 2,
            arn.endswith(f":policy/hk-{pid}-boundary"), arn or err)


def check_function(rep, fn):
    ok, data, err = aws("lambda", "get-function", "--function-name", fn)
    cfg = (data or {}).get("Configuration", {}) if ok else {}
    good = cfg.get("PackageType") == "Image" and cfg.get("State") == "Active" and cfg.get("LastUpdateStatus") == "Successful"
    rep.add("A", "A4.function", f"Lambda {fn} is an Image function and Active", 3, good,
            err or f"package={cfg.get('PackageType')} state={cfg.get('State')}")
    return cfg


def check_retention(rep, fn, pts=2):
    ok, data, err = aws("logs", "describe-log-groups", "--log-group-name-prefix", f"/aws/lambda/{fn}")
    groups = [g for g in (data or {}).get("logGroups", []) if g["logGroupName"] == f"/aws/lambda/{fn}"] if ok else []
    days = groups[0].get("retentionInDays") if groups else None
    rep.add("A", "A5.retention", "Log group retention is 14 days", pts, days == 14, f"retention={days}")


def check_public_block(rep, bucket, pts):
    ok, data, err = aws("s3api", "get-public-access-block", "--bucket", bucket)
    cfg = (data or {}).get("PublicAccessBlockConfiguration", {}) if ok else {}
    keys = ["BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets"]
    rep.add("A", "A5.publicblock", "All four S3 Block Public Access settings on", pts, all(cfg.get(k) for k in keys), err or cfg)


def check_tags(rep, pid, fn, repo):
    ok, data, err = aws("resourcegroupstaggingapi", "get-resources", "--tag-filters",
                        f"Key=Participant,Values={pid}", "Key=Hackathon,Values=build-and-break")
    arns = [r["ResourceARN"] for r in (data or {}).get("ResourceTagMappingList", [])] if ok else []
    good = any(a.endswith(f":function:{fn}") for a in arns) and any(a.endswith(f":repository/{repo}") for a in arns)
    rep.add("C", "C.tags", "Resources carry Hackathon/Participant tags", 2, good, err or f"{len(arns)} tagged resources")


def live_set1(rep, prefix, stamp):
    fn = f"{prefix}-quicklink"
    check_function(rep, fn)

    def call(method, path, body=None):
        ev = {"rawPath": path, "requestContext": {"http": {"method": method}}}
        if body is not None:
            ev["body"] = json.dumps(body)
        res, err = invoke(fn, ev)
        if not res:
            return None, {}, err
        try:
            return res.get("statusCode"), json.loads(res.get("body") or "{}"), res
        except (json.JSONDecodeError, AttributeError):
            return res.get("statusCode"), {}, res

    status, body, raw = call("GET", "/health")
    rep.add("A", "A4.health", "GET /health returns version v1", 4, status == 200 and body.get("version") == "v1", raw)
    target = f"https://example.com/verify-{stamp}"
    status, body, raw = call("POST", "/shorten", {"url": target})
    code = body.get("code")
    rep.add("A", "A4.shorten", "POST /shorten returns 201 + code", 4, status == 201 and bool(code), raw)
    status, body, raw = call("GET", f"/{code}") if code else (None, {}, "no code")
    loc = (raw.get("headers", {}) if isinstance(raw, dict) else {}).get("Location")
    rep.add("A", "A4.redirect", "GET /<code> redirects 301 to stored URL", 4, status == 301 and loc == target, raw)

    ok, data, err = aws("lambda", "get-function-url-config", "--function-name", fn)
    auth, url = (data or {}).get("AuthType"), (data or {}).get("FunctionUrl")
    denied = False
    if ok and url:
        try:
            urllib.request.urlopen(url.rstrip("/") + "/health", timeout=15)
        except urllib.error.HTTPError as exc:
            denied = exc.code == 403
        except OSError:
            denied = False
    rep.add("A", "A4.url", "Function URL uses AWS_IAM and rejects unsigned requests (403)", 3,
            auth == "AWS_IAM" and denied, err or f"auth={auth} unsigned_denied={denied}")

    ok, data, err = aws("dynamodb", "describe-continuous-backups", "--table-name", f"{prefix}-links")
    pitr = (data or {}).get("ContinuousBackupsDescription", {}).get("PointInTimeRecoveryDescription", {}).get("PointInTimeRecoveryStatus")
    rep.add("A", "A5.pitr", "DynamoDB point-in-time recovery enabled", 3, pitr == "ENABLED", err or pitr)
    check_retention(rep, fn)
    return fn


def live_set2(rep, prefix, stamp, account):
    fn, bucket = f"{prefix}-receipts", f"{prefix}-receipts-{account}"
    check_function(rep, fn)
    ok, data, err = aws("s3api", "get-bucket-notification-configuration", "--bucket", bucket)
    good = False
    for c in (data or {}).get("LambdaFunctionConfigurations", []) if ok else []:
        rules = {r["Name"].lower(): r["Value"] for r in c.get("Filter", {}).get("Key", {}).get("FilterRules", [])}
        if c["LambdaFunctionArn"].endswith(f":function:{fn}") and any(e.startswith("s3:ObjectCreated") for e in c["Events"]) \
                and rules.get("prefix") == "incoming/" and rules.get("suffix") == ".json":
            good = True
    rep.add("A", "A4.trigger", "S3 notification incoming/*.json -> function", 3, good, err or "ok")

    name = f"verify-{stamp}.json"
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as fh:
        json.dump({"receipt_id": f"verify-{stamp}", "items": [{"name": "tea", "qty": 2, "price": 1.25}]}, fh)
    ok, _, err = aws("s3api", "put-object", "--bucket", bucket, "--key", f"incoming/{name}", "--body", path)
    os.remove(path)
    out, deadline = None, time.time() + POLL_SECONDS
    while ok and out is None and time.time() < deadline:
        time.sleep(5)
        out, _ = s3_get_json(bucket, f"processed/{name}")
    rep.add("A", "A4.pipeline", "Upload to incoming/ produces processed/ output", 8, out is not None, err or ("ok" if out else "no output"))
    rep.add("A", "A4.output", "Output total 2.5 and processed_by v1", 4,
            bool(out) and out.get("total") == 2.5 and out.get("processed_by") == "v1", out)

    ok, data, _ = aws("s3api", "get-bucket-versioning", "--bucket", bucket)
    rep.add("A", "A5.versioning", "Bucket versioning enabled", 1, (data or {}).get("Status") == "Enabled")
    ok, _, err = aws("s3api", "get-bucket-encryption", "--bucket", bucket)
    rep.add("A", "A5.encryption", "Default encryption configured", 1, ok, err or "ok")
    check_public_block(rep, bucket, 3)
    return fn


def live_set3(rep, prefix, stamp):
    fn, qname = f"{prefix}-orders", f"{prefix}-orders"
    check_function(rep, fn)
    ok, data, err = aws("lambda", "list-event-source-mappings", "--function-name", fn)
    esm = [m for m in (data or {}).get("EventSourceMappings", []) if m.get("EventSourceArn", "").endswith(f":{qname}")] if ok else []
    rep.add("A", "A4.esm", "Event source mapping from queue is Enabled", 3,
            any(m.get("State") == "Enabled" for m in esm), err or [m.get("State") for m in esm])

    oid = f"verify-{stamp}"
    ok, data, err = aws("sqs", "get-queue-url", "--queue-name", qname)
    qurl = (data or {}).get("QueueUrl")
    item = None
    if qurl:
        ok, _, err = aws("sqs", "send-message", "--queue-url", qurl, "--message-body",
                         json.dumps({"order_id": oid, "sku": "HAMMER", "qty": 2}))
        deadline = time.time() + POLL_SECONDS
        while ok and item is None and time.time() < deadline:
            time.sleep(5)
            _, got, _ = aws("dynamodb", "get-item", "--table-name", f"{prefix}-orders",
                            "--key", json.dumps({"order_id": {"S": oid}}))
            item = (got or {}).get("Item")
    rep.add("A", "A4.pipeline", "Message on queue creates DynamoDB item", 8, item is not None, err or ("ok" if item else "no item"))
    rep.add("A", "A4.output", "Item status ACCEPTED and version v1", 4,
            bool(item) and item.get("status", {}).get("S") == "ACCEPTED" and item.get("version", {}).get("S") == "v1", item)

    attrs = {}
    if qurl:
        _, data, _ = aws("sqs", "get-queue-attributes", "--queue-url", qurl, "--attribute-names", "All")
        attrs = (data or {}).get("Attributes", {})
    try:
        redrive = json.loads(attrs.get("RedrivePolicy", "{}"))
    except json.JSONDecodeError:
        redrive = {}
    rep.add("A", "A5.redrive", "Redrive to -orders-dlq after 3 receives", 3,
            str(redrive.get("deadLetterTargetArn", "")).endswith(f":{qname}-dlq") and int(redrive.get("maxReceiveCount", 0)) == 3, redrive)
    _, data, _ = aws("sqs", "get-queue-url", "--queue-name", f"{qname}-dlq")
    dlq_attrs = {}
    if data:
        _, d2, _ = aws("sqs", "get-queue-attributes", "--queue-url", data["QueueUrl"], "--attribute-names", "All")
        dlq_attrs = (d2 or {}).get("Attributes", {})
    sse = lambda a: a.get("SqsManagedSseEnabled") == "true" or bool(a.get("KmsMasterKeyId"))
    rep.add("A", "A5.sse", "Server-side encryption on both queues", 2, sse(attrs) and sse(dlq_attrs))
    return fn


def live_set4(rep, prefix, stamp, account):
    fn, bucket = f"{prefix}-reports", f"{prefix}-reports-{account}"
    check_function(rep, fn)
    day = f"verify-{stamp}"
    res, err = invoke(fn, {"date": day})
    report = None
    if res and res.get("key"):
        report, err = s3_get_json(bucket, res["key"])
    rep.add("A", "A4.report", "Invoke writes reports/<date>.json to the bucket", 6, report is not None, err or res)
    rep.add("A", "A4.output", "Report generated_by v1", 3, bool(report) and report.get("generated_by") == "v1", report)

    rule = f"{prefix}-nightly"
    ok, data, err = aws("events", "describe-rule", "--name", rule)
    enabled = ok and data.get("State") == "ENABLED" and "cron(0 1 * * ? *)" == data.get("ScheduleExpression")
    _, tgt, _ = aws("events", "list-targets-by-rule", "--rule", rule)
    targeted = any(t["Arn"].split(":")[6:7] == [fn] for t in (tgt or {}).get("Targets", []))
    _, pol, _ = aws("lambda", "get-policy", "--function-name", fn)
    allowed = "events.amazonaws.com" in json.dumps(pol or {})
    rep.add("A", "A4.schedule", "Schedule rule enabled, targets function, invoke permission", 3,
            enabled and targeted and allowed, err or f"enabled={enabled} target={targeted} permission={allowed}")

    ok, data, err = aws("cloudwatch", "describe-alarms", "--alarm-names", f"{prefix}-reports-errors")
    alarms = (data or {}).get("MetricAlarms", []) if ok else []
    a = alarms[0] if alarms else {}
    dims = {d["Name"]: d["Value"] for d in a.get("Dimensions", [])}
    threshold_ok = (a.get("ComparisonOperator") == "GreaterThanOrEqualToThreshold" and a.get("Threshold") == 1.0) or \
                   (a.get("ComparisonOperator") == "GreaterThanThreshold" and a.get("Threshold") == 0.0)
    good = a.get("Namespace") == "AWS/Lambda" and a.get("MetricName") == "Errors" and dims.get("FunctionName") == fn \
        and threshold_ok and any(x.endswith(f":{prefix}-alerts") for x in a.get("AlarmActions", []))
    rep.add("A", "A4.alarm", "Errors alarm on the function notifies the SNS topic", 3, good, err or ("ok" if good else a or "no alarm"))

    check_public_block(rep, bucket, 3)
    check_retention(rep, fn)
    return fn


def live_set5(rep, prefix, stamp):
    fn = f"{prefix}-pricing"
    check_function(rep, fn)
    ok, data, err = aws("lambda", "get-alias", "--function-name", fn, "--name", "live")
    ver = (data or {}).get("FunctionVersion", "") if ok else ""
    rep.add("A", "A4.alias", "Alias live points at a published version", 4, ver.isdigit(), err or f"version={ver}")
    res, err = invoke(fn, {"amount": 100}, qualifier="live")
    rep.add("A", "A4.total", "live: amount 100 -> total 118.0", 5, bool(res) and res.get("total") == 118.0, err or res)
    res, err = invoke(fn, {"amount": 100, "code": "HACK10"}, qualifier="live")
    rep.add("A", "A4.discount", "live: discount code -> total 106.2", 3,
            bool(res) and res.get("total") == 106.2 and res.get("discount_applied") is True, err or res)
    rep.add("A", "A4.version", "live reports version v1", 3, bool(res) and res.get("version") == "v1", err or res)
    ok, data, err = aws("ssm", "get-parameter", "--name", f"/{prefix}/pricing/discount_code")
    ptype = (data or {}).get("Parameter", {}).get("Type")
    rep.add("A", "A5.securestring", "discount_code stored as SecureString", 3, ptype == "SecureString", err or ptype)
    check_retention(rep, fn)
    return fn


def verify(set_no, pid, work, live=True):
    rep = Report()
    app = SETS[set_no]
    prefix = f"hk-{pid}"
    check_package(rep, work)
    check_iac_static(rep, work)
    check_ci(rep, work)
    if not live:
        return rep
    ok, ident, err = aws("sts", "get-caller-identity")
    if not ok:
        rep.add("A", "A0.aws", "AWS credentials work", 0, False, err)
        return rep
    account = ident["Account"]
    stamp = time.strftime("%Y%m%d%H%M%S")
    check_registry(rep, prefix, app)
    check_boundary(rep, prefix, app, pid)
    if set_no == 1:
        fn = live_set1(rep, prefix, stamp)
    elif set_no == 2:
        fn = live_set2(rep, prefix, stamp, account)
    elif set_no == 3:
        fn = live_set3(rep, prefix, stamp)
    elif set_no == 4:
        fn = live_set4(rep, prefix, stamp, account)
    else:
        fn = live_set5(rep, prefix, stamp)
    check_tags(rep, pid, fn, f"{prefix}-{app}")
    return rep


def print_report(rep, title):
    print(f"\n{title}\n" + "-" * len(title))
    for i in rep.items:
        mark = "PASS" if i["ok"] else "FAIL"
        line = f"[{mark}] {i['id']:<16} {i['points']:>2}/{i['max']:<2} {i['label']}"
        print(line)
        if not i["ok"] and i["detail"]:
            print(f"        -> {i['detail']}")
    got, mx = rep.total("A")
    print(f"\nPart A build score: {got}/{mx}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="participant id, e.g. p07")
    ap.add_argument("--set", type=int, choices=sorted(SETS), help="set number (default: read from set.json)")
    ap.add_argument("--workdir", default=".", help="work folder (default: current folder)")
    ap.add_argument("--no-live", action="store_true", help="only run local checks")
    args = ap.parse_args()
    if not re.fullmatch(r"p\d{2}", args.id):
        sys.exit("--id must look like p07")
    set_no = args.set
    if set_no is None:
        try:
            set_no = json.load(open(os.path.join(args.workdir, "set.json")))["set"]
        except (OSError, KeyError, json.JSONDecodeError):
            sys.exit("cannot read set.json; pass --set")
    rep = verify(set_no, args.id, os.path.abspath(args.workdir), live=not args.no_live)
    print_report(rep, f"Set {set_no} ({SETS[set_no]}) build check for {args.id}")


if __name__ == "__main__":
    main()

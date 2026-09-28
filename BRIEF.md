# Set 4 - Nightly Reports (scheduled job with alerting)

**Scenario.** Management wants a sales summary written to S3 every night. Operations wants an alert if the job ever fails. The job code in `app/` works and has unit tests. Your job is to containerize it, then provision the bucket, function, schedule, and alarm with Terraform in the AWS sandbox. A teammate also opened a pull request, `crack-files/`, that adds a BI dashboard export. Review it.

Read `RULES.md` first. `<id>` below is your participant ID, for example `p07`.

---

## Part A - Build and deploy (50 points, verified live)

| What | Exact name or setting |
|---|---|
| ECR repository | `hk-<id>-reports`, scan on push **on**, tag mutability **IMMUTABLE** |
| Image | `hk-<id>-reports:v1`, built from `app/`, with env `APP_VERSION=v1` baked in |
| S3 bucket | `hk-<id>-reports-<account-id>` (use `local.account_id`) |
| IAM role for Lambda | `hk-<id>-reports-role` with `permissions_boundary = var.permissions_boundary_arn`. Allow only writes under `reports/*` |
| Log group | `/aws/lambda/hk-<id>-reports` |
| Lambda function | `hk-<id>-reports`, `package_type = "Image"`, env `REPORT_BUCKET` = the bucket name |
| EventBridge rule | `hk-<id>-nightly`, schedule `cron(0 1 * * ? *)`, target is the function (EventBridge must be allowed to invoke it) |
| SNS topic | `hk-<id>-alerts` |
| CloudWatch alarm | `hk-<id>-reports-errors`: metric `AWS/Lambda` `Errors` for this function, threshold `>= 1`, alarm action is the SNS topic |

**Tasks**
1. **A1 Package (8).** Write `Dockerfile` in the work folder root. Use the AWS Lambda Python 3.12 base image, copy `app/handler.py`, and set the handler command to `handler.lambda_handler`. Bake in `APP_VERSION=v1`. Unit tests must pass: `python3 -m unittest discover -s app`.
2. **A2 Registry (6).** Create the ECR repository with Terraform and push tag `v1`.
3. **A3 Infrastructure as Code (8).** Put all resources in `infra/*.tf`. The code must pass `terraform fmt -check` and `terraform validate`. Do not hardcode the account ID or credentials.
4. **A4 Working deployment (18).** Invoking the function writes `reports/<today>.json` with `"generated_by": "v1"`. The schedule targets the function and has permission to invoke it. The alarm points at the topic.
5. **A5 Hardening (5).** Turn on **all four** Block Public Access settings on the bucket. Set log retention to 14 days.
6. **A6 CI pipeline (5).** Write `.github/workflows/deploy.yml`, which is checked statically and not run. On push to `main` it should: run the unit tests, use **OIDC** to AWS (`role-to-assume`, `id-token: write`, no stored keys), build the image and push it to ECR, and run `terraform fmt -check`, `validate`, and `plan`.

**Test it yourself**
```bash
aws lambda invoke --function-name hk-<id>-reports --cli-binary-format raw-in-base64-out --payload '{}' out.json && cat out.json
aws s3 ls s3://hk-<id>-reports-$(aws sts get-caller-identity --query Account --output text)/reports/
python3 tools/check_build.py --id <id>
```

**Known gotchas (not a trick)**
- The EventBridge target alone is not enough. The function also needs an `aws_lambda_permission` for `events.amazonaws.com`.
- Lambda needs the image to exist first. `-target` the ECR repository, push the image, then run the full apply.
- Match `--platform` to `architectures`. With BuildKit, add `--provenance=false`.

---

## Part B - Break: review `crack-files/` (40 points)
`crack-files/` is a pull request, "BI dashboard export". It has **at least 6** real security problems across secrets, public exposure, IAM trust, container hardening, the CI pipeline, and application code. Fix each one **in place**, keeping the file meaningful, and document it in `FINDINGS.md`.

## Part C - Operate (10 points)
Submit on time. Keep keys and state out of the zip. Keep the default tags on every resource. Answer the questions in `FINDINGS.md`.

## Submit
```bash
python3 tools/submit.py --id <id>
```
Do **not** run `terraform destroy`.

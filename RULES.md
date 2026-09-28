# Build & Break - Rules (read first, 3 minutes)

## Format
- Individual work. 90 minutes. One set per person.
- Part A, **Build** (DevOps, 50 points): package, provision, and deploy a small service to the AWS sandbox. A script verifies it live.
- Part B, **Break** (DevSecOps, 40 points): the `crack-files/` folder is a teammate's pull request. It contains planted security problems. Find them, fix them in place, and explain them in `FINDINGS.md`.
- Part C, **Operate** (10 points): submit on time, keep credentials out of your submission, tag resources, and write short operations notes.

## Suggested timeline
| Minutes | Do this |
|---|---|
| 0-5 | Read BRIEF.md, load your credentials, run `aws sts get-caller-identity` |
| 5-55 | Part A: build, deploy, and run `python3 tools/check_build.py --id <your-id>` |
| 55-85 | Part B: review and fix `crack-files/`, fill in `FINDINGS.md` |
| 85-90 | Run `python3 tools/submit.py --id <your-id>` and upload the zip |

You may switch between parts at any time. For example, you can review the crack files while `terraform apply` runs.

## Allowed
- Official documentation (AWS, Terraform, Docker, GitHub Actions, Python), man pages, and `--help`.
- Your own notes. Web search for documentation pages.
- Local tools: terminal, editor, Docker (or Colima or Podman), Terraform, AWS CLI, Python 3.

## Not allowed
- AI assistants of any kind: ChatGPT, Copilot, Cursor AI, Claude, Gemini, IDE AI completion, and AI answers in search engines. Turn off AI completion in your editor before you start.
- Help from other people during the 90 minutes, apart from organizers answering setup problems.
- Using any AWS account other than the sandbox credentials you were given.

Breaking a rule scores 0 for the set.

## AWS sandbox rules
- Region **ap-south-1** only. Every resource name starts with `hk-<your-id>-`. Your credentials cannot create anything else.
- Every IAM role you create must set `permissions_boundary = var.permissions_boundary_arn`. Without it, role creation is denied.
- **Do NOT destroy your resources at the end.** Organizers verify them live after submission and then clean up.
- Never put your access keys in any file inside the work folder.

## Setup (organizer gives you `hk-<id>.env`)
```bash
set -a; source ~/Downloads/hk-p07.env; set +a    # replace with your file
aws sts get-caller-identity                      # must show user hk-p07
cp infra/terraform.tfvars.example infra/terraform.tfvars   # then fill in participant_id and boundary ARN
```

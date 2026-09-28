# Build & Break — Set 4: Reports

This is the participant repository for one 90-minute DevOps and DevSecOps challenge.

## Start

1. Clone this repository.
2. Read `RULES.md`.
3. Read `BRIEF.md`.
4. Load the private `hk-pXX.env` credential file supplied separately by the organizer.
5. Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars` and replace its placeholders.
6. Run the supplied unit tests, build/deploy the service, review `crack-files/`, and submit with `tools/submit.py`.

The repository intentionally contains insecure **fake** examples under `crack-files/`. Do not deploy those files.

Do not commit AWS credentials, Terraform state, or your completed solution. Do not run `terraform destroy`; the organizer grades the live resources and performs cleanup.

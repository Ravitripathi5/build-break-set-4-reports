# PR #311 - BI dashboard export

Author: r.chen - "Dashboard team needs this by Friday. Infra is copy-paste from my side project."

Publishes the nightly report as a small static dashboard. Store managers can filter it by store.

Files:
- `dashboard/provider.tf` - AWS provider for the dashboard stack
- `dashboard/site.tf` - dashboard hosting bucket
- `dashboard/scheduler-role.tf` - role the BI scheduler assumes
- `dashboard/Dockerfile` - container for the dashboard API
- `dashboard/export.py` - store filter API
- `.github/workflows/dashboard.yml` - deploy pipeline

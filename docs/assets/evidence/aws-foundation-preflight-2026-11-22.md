# AWS foundation preflight — November 22, 2026

This is preparation evidence, not deployment success.

- AWS Budgets console: APICompass-25USD, monthly account-wide US$25. Actual thresholds US$10/20/25; forecast US$25. Recipient registration verified in console as 1/1. No actual threshold email receipt has been tested.
- IAM dashboard: root MFA enabled, no active root access keys. User completed private authenticator setup. Routine individual operator access remains pending.
- Singapore EC2 launch wizard: Linux t3.small, 2 vCPU/2 GiB, US$0.0264/hour. Six days (144 hours) computes to US$3.8016 for instance time alone. EBS, public IPv4, metrics, logs, backups, requests, data transfer and possible CPU-credit charges are additional. Use standard CPU-credit mode at launch to avoid surplus-credit charges; verify enough capacity under workload. No instance was launched; the wizard was cancelled.
- An existing unrelated running ShopSmart demo instance was observed. It was not changed. Account-wide cost readings/budget alerts include unrelated usage and must not be presented as APICompass-only costs.
- Prepared infra/foundation.json: private versioned SSE-S3 bucket, scoped EC2 runtime role/profile, three log groups with 14-day retention. It contains no live account number, notification address, credentials or public endpoint.
- cfn-lint 1.61.0 validated the template for ap-southeast-1: exit code 0, no findings. Installed into ignored [private local path omitted]; application dependencies were not changed. Initial invocation via `python -m cfnlint` was invalid because the package has no __main__; the documented installed entry point was used successfully.
- Independent reviewer: no Critical/Important findings. Clarified the two separate S3 lifecycle clocks in infra/README.md (current 14 days, then noncurrent 14 days). No deployed IAM/S3 allow/deny tests have run.

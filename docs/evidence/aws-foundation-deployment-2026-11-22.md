# AWS foundation deployment — November 22, 2026

## Verified outcome

CloudFormation stack `apicompass-foundation` in Singapore (`ap-southeast-1`) reached **CREATE_COMPLETE at 15:28:49 +08:00**. User explicitly approved the reviewed template upload and runtime IAM role creation before execution. All seven resource additions succeeded; no EC2 instance was launched and no public endpoint was created.

| Logical resource | Verified CloudFormation outcome |
| --- | --- |
| ProjectBucket | CREATE_COMPLETE |
| BucketTransportPolicy | CREATE_COMPLETE |
| RuntimeLogs | CREATE_COMPLETE |
| QuestionLogs | CREATE_COMPLETE |
| JobLogs | CREATE_COMPLETE |
| RuntimeRole | CREATE_COMPLETE |
| RuntimeInstanceProfile | CREATE_COMPLETE |

Source: `infra/foundation.json` from commit `0df2812`; source file SHA-256 `B39FCFC5FCB687EE5B08DDB9EAEC79C900BB8FF8C9ABC934E763A010054D40D8`. Change set `foundation-initial-20261122` listed exactly seven Adds, was CREATE_COMPLETE/AVAILABLE, then was executed with rollback enabled. No existing stack was replaced or deleted.

The browser file picker failed to open through both supported upload APIs and native fallback. Used AWS Template Studio instead: replaced its default placeholder through the editor, compared the entire visible JSON to the minified source (exact match, 4,513 characters), received AWS validation status `Valid`, saved it and continued. The first editor attempt left placeholder lines behind; AWS rejected it before deployment. Replacing the whole document corrected this, and only the matching validated version was deployed.

CloudFormation created its small regional `cf-templates-*` bucket to store the template. This is additional template storage, not a second database or application dataset bucket. Include it in cost/teardown inventory. No secrets are in that template.

## Additional AWS console checks

- S3 project bucket: versioning **Enabled**, SSE-S3 default encryption, Block Public Access **On**, bucket owner enforced with ACLs disabled, and explicit DenyInsecureTransport bucket policy.
- S3 lifecycle: `BackupRetention14Days` and `AbortIncompleteUploads` both **Enabled**. See infra/README.md for the separate current/noncurrent retention clocks.
- CloudFormation Outputs returned the project bucket, runtime role ARN, instance profile name and `/apicompass/prod/` secret path. Concrete account/resource identifiers are kept in ignored [private local path omitted] for local handoff, not this public evidence record.
- Three log groups were provisioned from the reviewed template with 14-day retention. The CloudWatch console's linked log view remained blank; independent CloudWatch UI retention readback is pending. Do not label empty log groups as populated monitoring or question logging.

No permanent screenshot artifact was saved. The S3 screens were inspected in the browser, and stack events/outputs were read from the accessibility tree. Capture sanitized screenshots for the final website separately; this text is an observation record, not a substitute for required visual evidence.

## Still pending

Individual operator access; compute/network/HTTPS; authenticated MongoDB; runtime SecureString creation/loading; release/dataset upload; actual instance-role allow/deny tests and S3-backed tool answer; CloudTrail; dashboard/alarms/email delivery; question instrumentation; two scheduled jobs with two unattended runs each; backup/restore/RPO/RTO; incident/evaluation and final submission package. The bucket currently contains no application dataset objects. APICompass is still local.

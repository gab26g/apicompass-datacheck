# Monitoring and audit — deployed baseline, integration pending

The baseline stack reached CREATE_COMPLETE on 23 November 2026 at 13:19:57 Asia/Manila. The email subscription was confirmed and independently checked. Actual alarm-email evidence is still pending. The current source additionally includes question request-volume and observed-duration widgets, which are not yet deployed at this checkpoint. Do not treat empty graphs as verified telemetry.

`python scripts/render_observability.py` renders `infra/observability.json`. It creates six relevant alarms, one email SNS route, a dashboard and a private S3 audit bucket with a single-region CloudTrail trail. Parameters are the actual project instance ID and the user's authorized alert email. Email is NoEcho; do not put the address in repository files or public screenshots.

Every alarm has both ALARM and OK actions to the same SNS topic. The topic permits publication only from this account's regional `apicompass-*` CloudWatch alarms. The user must confirm the new SNS email subscription; AWS Budgets recipient verification does not confirm SNS subscriptions. Actually trigger and receive one alert before claiming delivery.

| Signal | Threshold/window | Missing data |
| --- | --- | --- |
| EC2 CPU | Average >85%, two 5-minute periods | Not breaching |
| EC2 instance/system status | Maximum >0, one minute | Not breaching |
| Root disk | Maximum >85%, two 5-minute periods | Breaching |
| Synthetic health | HealthFailure >0, one 5-minute period | Breaching |
| Backup failure | BackupFailure >0, one 6-hour period | Breaching |
| Failed/aborted answer attempts | AnswerFailure sum >0, one 5-minute period | Breaching |

Custom metrics use namespace `APICompass`, dimension `Project=APICompass`, matching ops_jobs.py and ship_questions.py. Backup age remains graphed; health fails after backup age >8 hours. Its separate alarm was replaced by AnswerFailure to retain exactly six alarms. The first health checks without any successful backup deliberately fail and omit BackupAgeHours; HealthFailure therefore alarms for missing/stale backups. Start question telemetry and establish the first backup promptly after installing the stack. Expect initial ALARM/INSUFFICIENT_DATA states while startup is incomplete. Do not suppress missing-data failures just to produce a green screenshot.

The dashboard uses the same real series and preserves the BackupAgeHours graph. Its latency widget is **synthetic API check duration, not full chat response latency**. The reviewed question adapter and host shipper are included in the explicit application release allowlist, along with their service/timer and the host enrollment helper. The local SSM secret-preparation helper is excluded. The one-minute question shipper publishes AnswerSuccess/AnswerFailure, including zero counts when healthy and idle, and sends allowlisted metadata to `/apicompass/prod/questions`. Its metric counts are at least once across partial API/state failures; see [shipping contract](QUESTION-TELEMETRY-SHIPPING.md). AnswerFailure covers failed and aborted observed attempts, including provider errors under HTTP 200; a terminal success is not a factual-accuracy score. Empty log groups and API HTTP 200 do not prove a successful model answer. Real event shipping, idle heartbeats, alarms/email and source/image route coverage remain acceptance gates. General runtime/job log shipping beyond question events is still pending.

The audit bucket blocks public access, enforces TLS, disables ACLs and uses SSE-S3/versioning. Only the exact regional assessment trail can write its account prefix. Management reads/writes and log-file validation are enabled; costly S3 data-event selectors are not enabled. Current audit objects expire after 30 days, then persist as noncurrent versions for another 30 days (roughly 60 total plus lifecycle scheduling). Tiny expired delete markers can remain. Bucket retention on stack deletion protects evidence but can continue storage charges.

This Singapore **single-region trail does not establish global IAM-event coverage**. IncludeGlobalServiceEvents is set, but AWS delivers global service events to single-region trails only in us-east-1. Record this limitation honestly; do not claim complete account/global audit coverage. Any future change to global or multi-region audit coverage needs an explicit course-scope review.

Acceptance: validate/lint, inspect change set, confirm subscription, publish actual custom metrics, inspect populated graphs, exercise alarm delivery, inspect actual audit objects/digests and finite retention. None of those deployment outcomes is established by this template alone. Keep gross total usage within the authorized US$25 allowance and inventory retained audit storage at teardown.

Sources: [CloudTrail bucket policy](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/create-s3-bucket-policy-for-cloudtrail.html), [CloudWatch notification policies](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Notify_Users_Alarm_Changes.html), [global-event trail behavior](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-create-and-update-a-trail-by-using-the-aws-cli-update-trail.html).

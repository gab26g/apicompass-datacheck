# Consolidated integration handoff — refreshed 24 November 2026

Provenance: sanitized integration-owner handoffs to the submission-site author, consolidated with the dated public records linked below. The site author did not independently access AWS or inspect secret values. This record is an observation handoff, not a substitute for screenshots or a claim of final submission acceptance. The filename is retained for stable report links.

## Deployment and runtime

The Singapore t3.small host completed provisioning at 23:55:39 Philippine time on 22 November, with encrypted 24 GiB EBS, a scoped runtime role, IMDSv2 and public HTTPS through Caddy. MongoDB and DataCheck are private container services. Initial bootstrap encountered a curl/curl-minimal conflict; the corrected operational bootstrap subsequently reached READY. The deployed UserData remains distinct from that corrected rerun.

The runtime role retrieved the privately created SecureString with all eight required fields present, without exposing values. The original uploaded release and 25 file hashes were checked before operational corrections. This dated checkpoint preceded the final source-parity acceptance below.

Normal application login, one owned private action with four read operations, real Gemini/DataCheck/S3 answers and source version/hash correlation passed. See [cloud integration](cloud-integration-2026-11-23.md). The public hostname awaits publication review.

## Operational acceptance

- The dashboard, six alarms, SNS route and regional CloudTrail are deployed. A genuine [dashboard screenshot](cloud-dashboard-2026-11-24.jpg) shows selected populated widgets. It does not show every widget. Regional CloudTrail does not establish global IAM-event coverage.
- The actual health alarm entered ALARM at 11:41:51 UTC and OK at 11:51:51 UTC on 23 November. Both notification actions succeeded; the student separately confirmed receipt of both emails. This is inbox attestation, not an inspected email screenshot.
- Real question events and two-week retention were independently read in CloudWatch. The initial saved-agent route instrumentation gap was reproduced and fixed before those fresh monitored questions. The database service subsequently reported 730 sanitized events delivered; independent database destination readback subsequently passed on 24 November: the individual MFA operator loaded 202 events in runtime stream database-2026-11-23, including fixed NETWORK/database_connection and ACCESS/database_authentication classifications at 16:38:29 UTC on 23 November. The [actual console capture](cloud-database-logs-2026-11-24.jpg) preserves this view. Loaded view count is not the full delivered total. All three project group listings showed two-week retention; jobs destination events were subsequently independently read back in the 24 November acceptance below.
- [Scheduled journal observations](automation-runs-2026-11-23.json) preserve two genuine unattended backup runs and two health runs. The temporary fifteen-minute backup assessment calendar was disclosed and the six-hour calendar restored. A timer-reactivation run and the later operator-triggered drill backup are excluded from those scheduled proofs.
- [Fresh-volume recovery](recovery-incident-2026-11-23.md) passed normal login, saved conversation/action checks and a new correct 60/7/7 tool-backed answer. Whole-drill observed duration was 1438 seconds, including failed attempts, fixes and human interaction. Backup-age exposure was 572 seconds, not proven data loss or a guaranteed RPO. Scoped cleanup returned zero assessment resources and production health passed.
- The inherited Compose production-label fault was reproduced, corrected with explicit label overrides, regression-tested and checked live. The earlier login rejection has no confirmed root cause and is not attributed to this label fault.
- On 24 November the individual operator apicompass-student completed password/MFA setup, signed in and opened the permitted CloudWatch dashboard. No access keys were created. A complete sanitized IAM inventory and scoped allow/deny tests remain distinct evidence boundaries.

## Measurement and submission limits

The historical local assistant evaluation remains 10/13 executed cases. Four local v3 targeted passes and three targeted cloud cases do not create a fresh full-suite score. Focused test counts overlap and must not be added into a new suite total. Matched capacity, latency percentile and project-only cost improvements remain unmeasured.

The report remains unpublished. Recording/embed, student review/signature, final package/history inspection and signed-out hosting checks remain final hand-in work. No grade, instructor acceptance or submission receipt is claimed.

## Later acceptance — 24 November Manila

The integration owner independently verified all 40 release files against the clean source 6b12aeb manifest. The immutable new bundle is local; its upload to S3 is not claimed. Source checks passed 123 Python and 47 Node tests before installation. See [logging and parity acceptance](logging-acceptance-2026-11-24.md).

Bounded literal synthetic-question capture reached CloudWatch with runtime-v3, question status captured, failed/missing_final and 91718.898 ms. The underlying DataCheck tool returned correct S3-backed 60/7/7 facts, but the external model stream ended without a complete final answer. A second fresh concise attempt also failed after partial output. The recurring stream EOF condition is under investigation; neither a complete answer nor a new quality score or provider fix is claimed. The older full-width question screenshot was excluded from publication because its account header contains private details; the linked report uses only the reviewed replacement.

The jobs destination independently showed terminal health events, including two scheduled successes after the update. This supplements earlier unattended job evidence without manufacturing a new post-update backup success. The matched ten-probe thirty-second comparison returned 10/10 correct deterministic results both times: mean435.586ms before and440.767ms after. Docker/S3 overhead and background jobs limit interpretation; no performance improvement or savings are claimed. Exact samples remain in [the comparison JSON](runtime-comparison-2026-11-24.json).

A real-history checkpoint ZIP was extracted and verified, but later site/source edits require a new final archive. The public repository exists with an initial README; report publication, video and personal declaration remain pending.

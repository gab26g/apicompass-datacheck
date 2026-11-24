# Logging and source-parity acceptance — 24 November 2026, Manila

Source commit `6b12aebaac0a4a7f54cc224a01675c07d7a55f06` passed 123 Python and 47 Node tests before installation. Four public application/configuration files were installed only after all old/new SHA-256 checks passed. Rollback copies contain public source only. The normal runtime loader reused the existing SecureString and volumes and reported startup success. Independent host verification compared all 40 release files against the locally built clean release manifest and returned `all_release_files_match`.

Local immutable deployment bundle: `apicompass-43210eaa6487867feadf.zip`, SHA-256 `43210eaa6487867feadf600cd12b315478e2b5e79124e1ac4eb0c4013248872b`. This bundle is built locally; no upload of this new bundle to S3 is claimed. Its exact application bytes were installed and verified in place. The runtime manifest records the committed source.

## Literal question logging now reaches its destination

Production explicitly opts into bounded question capture. The visible footer says invented data only, and that sanitized questions and request outcomes are logged for 14 days. This does not promise universal personal-data detection: suspected sensitive input is omitted with an explicit status; real personal records and keys remain prohibited.

The normal student IAM console independently read this actual CloudWatch event:

| Field | Observed value |
| --- | --- |
| Timestamp UTC | 2026-11-23T17:05:04.276Z |
| Version | apicompass-runtime-v3; LibreChat 0.8.8 |
| Question | Inspect shipments. Give row count, issue count, affected-row count and all findings. |
| Question status | captured |
| Question request ID | fbd4ebf5-2b9e-40e2-9da7-8eda50243140 |
| Outcome/reason | failed / missing_final |
| HTTP status | 200 |
| Observed full-attempt duration | 91718.898 ms |

Screenshot: [actual question log destination](cloud-question-logs-2026-11-24.jpg). The partial account prefix in the narrow console header is not a complete account number. The earlier full-width screenshot is retained privately and is excluded from public publication because its header contains the account number.

The request failed honestly: DataCheck returned the known S3-backed 60/7/7 facts, request `b83a8fde-e70f-46d6-9533-50c94dd83727`, at 2026-11-23T17:03:47.050792Z, but the external model stream ended with `[GoogleGenerativeAI Error]: Failed to parse stream`. No complete assistant answer is claimed. A second concise question also stopped after a partial answer. This error previously occurred in the historical v1 evaluation, before the new logging code. Its recurring cause is under investigation; the pinned Google SDK throws this error when unparsed nonempty text remains at stream EOF. That condition alone does not identify the content or upstream cause.

Screenshot: [actual failed cloud answer](cloud-provider-stream-failure-2026-11-24.jpg). A failed answer is not a passing quality case merely because its API/tool facts were correct.

## Actual automation events delivered

The existing jobs group now receives strict metadata-only terminal events. The console independently showed:

| UTC | Trigger | Request ID | Duration | Outcome |
| --- | --- | --- | --- | --- |
| 2026-11-23T17:03:23.192Z | Operator-started health service | de9bd27c-ba8e-4380-9f97-6678cfefab2c | 1227.26 ms | succeeded |
| 2026-11-23T17:05:23.878Z | Scheduled health run | 0647c326-c2bb-400c-9af1-9f043c048003 | 1573.4 ms | succeeded |
| 2026-11-23T17:10:31.357Z | Scheduled health run | d32f6c07-0762-4840-bbfe-5b0b2dd86dda | 1434.27 ms | succeeded |

Screenshot: [actual jobs log destination](cloud-job-logs-2026-11-24.jpg). These later health events supplement, and do not replace or relabel, the earlier two unattended backup and health proofs. No new scheduled backup success after this logging update is claimed here.

## Matched short measurement

The same ten known-answer readiness-plus-shipments probes ran over thirty-second monotonic windows before and after the update. Both returned ten correct results. Mean probe duration was 435.586 ms before and 440.767 ms after; maximum 780.166 and 829.910 ms; observed host CPU 11.816% and 12.961%; disk 37.049% and 37.055%. Each probe includes Docker-exec overhead and four S3-backed dataset checks, so this is not user-answer latency or an availability/capacity study. UTC start stamps also precede configuration setup; setup is outside probe/window timing. Background jobs were not disabled. No performance improvement, cost savings or long-term conclusion is claimed. Exact samples and request IDs: [comparison record](runtime-comparison-2026-11-24.json).

## Submission artifact checkpoint

A clean local clone preserving the real ten-commit history was packaged with its actual `.git` and extracted separately. A dangling remote-HEAD symbolic reference left after removing the clone's local origin was removed from the disposable clone only; source history was unchanged. `git fsck --full --no-reflogs` then passed. The verified checkpoint ZIP is `apicompass-source-6b12aeb-verified.zip`, SHA-256 `5da4aa5b1d4e9cca0f286fe12b1b60ac6ea01dd3e29390994e7d38964d02adb9`, 185 files. It excludes ignored runtime state and retains authentic source/author history for private instructor submission. Later changes require a new final immutable archive; this checkpoint is not represented as the final submitted ZIP.

The public GitHub repository was created with an initial README; source/report publication and GitHub Pages deployment are still pending at this checkpoint. Video and student signature remain personal actions.

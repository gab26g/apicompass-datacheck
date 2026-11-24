# Final engineering acceptance observations — 24 November 2026

These are dated observations, not a submission certificate or an uptime guarantee. Student review, the actual 5–8-minute video, its public embed, declaration signature and course hand-in remain personal delivery actions.

## Public report and source

The report is live at https://gab26g.github.io/apicompass-datacheck/ and the reviewed source at https://github.com/gab26g/apicompass-datacheck. Public snapshot commit `62efc307eac405a7597a8ad625f7d4b978f3524d` was explicitly approved before publication. GitHub Pages deployed successfully from main/docs. An unauthenticated HTTP client received 200 responses for the report and all 31 linked local resources at this checkpoint. Later edits require another link check. The public snapshot excludes original private Git metadata; the instructor ZIP retains authentic development history.

## Fresh complete answer after restoring the original SDK

Prompt: “Inspect shipments. Give row count, issue count, affected-row count and all findings.” The normal production interface returned 60 rows, 7 findings and 7 affected rows; shipments-v2 / shipments-rules-v2; request `18fd5a9c-2225-4212-ba36-02710bb658a7`. It listed both duplicate rows, weight 0, non-integer heavy, missing shipment ID, unsupported category lost and weight 1001. The screenshot is `cloud-complete-answer-2026-11-24.jpg`.

Two preceding cloud attempts failed during provider stream parsing after correct tool facts. Temporary metadata-only SDK diagnostics captured no failure because two subsequent attempts succeeded. The original SDK bytes were restored, then the complete answer above passed. The cause remains unknown; this is an intermittent dependency limitation, not a proven parser fix. Retain the genuine failure screenshot and failed telemetry outcome. This targeted pass does not replace the historical 10/13 evaluation denominator. Rehearse shortly before recording; if a stream fails, identify it honestly and retry once in a fresh chat rather than claiming a missing answer succeeded.

## Live security boundaries

`live-boundaries-2026-11-24.json` records the 03:03 UTC read-only probes: IAM-role credential source, allowed versioned S3 read with matching raw SHA-256, AccessDenied for a deliberately nonexistent key outside allowed prefixes, and API statuses 401 without a token, 401 with an invalid token, 200 with the valid runtime token, 404 for an unknown dataset and 422 for invalid limit zero. No secret values were printed. Host-loopback ports 8000 and 27017 were not listening; this is not an external port scan. Original SDK SHA-256 and chat health 200 were independently observed.

The IAM console showed apicompass-student enabled with MFA, exactly one MFA device, zero access keys and exactly one directly attached customer-managed policy, APICompassStudentOperator. The MFA and policy screenshots have opaque rectangles over account identifiers and the administrator header; the unedited originals remain private. No measurements or policy results were changed. The administrator session was used for this read-only inventory and billing/audit inspection; routine project operations use the individual MFA identity. These captures do not establish every possible effective-permission path.

CloudTrail showed apicompass-assessment Logging, all management API activity, last log delivery 24 November 10:47:33 UTC+08 and last validation 10:34:02 UTC+08. Log-file validation was enabled. This is a single Singapore-region management trail, not global IAM coverage. No data events, Insights or trail-to-CloudWatch delivery are claimed.

## Genuine original/reskinned comparison

`librechat-original-2026-11-24.jpg` is an actual original LibreChat login UI, captured from the same pinned v0.8.8 container image used by the project. Its upstream identity/client assets were unchanged. A fresh empty MongoDB and isolated localhost-only port 3082 were used; no production database, account, provider key or model call was involved. The capture viewport was requested at 715 × 803 to match the branded cloud login. Backend assessment settings allowed this isolated UI reference; it is not claimed to duplicate the production configuration. Credit remains with LibreChat and its contributors under its MIT notice.

The two comparison containers, five labelled volumes and one network were removed by ownership-checked cleanup. Final scoped counts were zero containers, zero volumes and zero networks. Production resources were untouched. The project login retains “Welcome back”; visible changes are the compass identity, APICompass title and navy/teal palette. Domain instructions, invented data, private S3 tools and AWS operations are documented separately rather than inferred from a login screenshot.

## Operational proof and limitations

Literal sanitized-question text, duration, outcome and runtime version were read back from CloudWatch; one actual 91718.898 ms incomplete answer is correctly recorded as failed despite HTTP 200. Jobs and sanitized database streams were also read back; all three groups showed two-week retention. The deployed 40-file release matched the reviewed runtime manifest. The combined source validation passed 123 Python tests and 54 Node tests (47 telemetry plus 7 diagnostic tests).

Recovery, two unattended runs per job and the resolved isolation-label incident remain the dated 23 November records. Both ALARM and OK emails were confirmed received by the student; an inbox screenshot has not been inspected. Matched ten-probe thirty-second before/after results are in runtime-comparison-2026-11-24.json; no user-answer speed, capacity, savings or improvement is inferred. Project-attributed matched actual cost is not available. The US$25 allowance and budget notifications are not a hard spending cap; arrange reviewed teardown after assessment.

# APICompass recording script — seven-minute presentation

Updated 24 November 2026 against SAM10 v3.5 D2. Aim for 7:00; the exported video must be 5:00–8:00. This is a ready-to-rehearse script, not proof of a recording. The public website, hosted video/embed, signed declaration and final source ZIP remain unfinished. Replace the student's name, verified provider tier and eventual public URL before narration. Keep unresolved limitations honest.

## 0:00–0:40 — purpose and original contribution

Show the website summary, APICompass logo and signed-in application; stage authentic original/reskinned comparison captures when available.

“I am [student name]. APICompass checks invented inventory, shipment and equipment records. It adapts LibreChat version 0.8.8, by the LibreChat project and contributors, under the MIT licence. My project adds DataCheck, three synthetic datasets, explicit validation rules, domain prompts, branding and AWS operations. Codex assisted with implementation and documentation; my contribution record explains that assistance. DataCheck computes the facts and Gemini explains them. It cannot edit records, establish causes absent from the data, or make consequential decisions about people.”

## 0:40–1:50 — live AWS application and a limitation

Show the actual AWS HTTPS app, already authenticated, and expand its tool result. Submit:

> Inspect shipments. Give the total rows, issue_count and affected_row_count, list each finding, and include dataset_version, ruleset_version and request_id.

“This is the deployed application, using private DataCheck and versioned S3 source data. I compare its response with a frozen expected result: 60 rows, seven findings across seven rows, shipments-v2 and shipments-rules-v2. Both duplicate-ID rows count separately. The other findings are zero weight, nonnumeric weight, a missing ID, invalid status, and weight above the allowed range. The response includes a fresh request identifier and source version.”

Read the actual result before claiming it matches. If it fails, explain that failure and show the clearly dated 23 November evidence, without presenting it as the live response. Do not cut a wait while claiming full response latency. Preserve the source recording.

Show `docs/evidence/cloud-limitation-answer-2026-11-23.jpg`.

“When asked why shipments were delayed and which supplier caused it, the assistant explained that the available columns are shipment ID, weight and status. Supplier and delay-cause information is absent. This is an appropriate boundary. The website also preserves a real failed local evaluation answer.”

## 1:50–2:25 — deployed architecture and system card

Show the website architecture and system-card chapters. Use the final actual service diagram.

“The workload uses one EC2 host and one authenticated MongoDB database in Singapore, ap-southeast-1. HTTPS enters Caddy, then the branded chat application. Gemini runs outside AWS. One saved action exposes four read operations to private DataCheck. DataCheck validates the S3 object version and SHA-256 before returning findings. The instance role reads scoped S3 content and a runtime SecureString. MongoDB and DataCheck have no public service ports. CloudWatch and SNS support monitoring. One host keeps cost and complexity low but remains a single point of failure.”

Name the actual model shown in the app and the student's verified free/paid tier. If unknown, say “I have not verified the provider account tier.” Do not invent a model version or claim final source/runtime parity until reviewed.

## 2:25–3:20 — dashboard, alarms and real notification

Show the Singapore dashboard under the individual AWS account, with its actual time window readable. Reference capture: `docs/evidence/cloud-dashboard-2026-11-24.jpg`. Then show actual alarm configuration/history and the sanitized question-log screenshot.

“This dashboard separates host health from application attempts. Its required signals are request count, errors, response time, CPU, disk used, and database or request volume. The six configured alarm names use the apicompass prefix: cpu, instancestatus, disk, health, backupfailure and answerfailure. Here are their actual thresholds and notification settings. HealthFailure greater than zero for one five-minute maximum datapoint detects failed scheduled checks; missing data is breaching.”

“During the isolation fault, health changed from OK to ALARM at 11:41:51 UTC on 23 November and back to OK at 11:51:51. Both notification actions succeeded, and I confirmed both emails arrived. Inbox receipt is my confirmation; the evidence does not include an inspected inbox screenshot.”

“After fixing the saved-agent telemetry route, actual CloudWatch attempt durations included 3479.704 and 1834.423 milliseconds. These are complete attempt observations, not tool duration or accuracy. The first two pre-fix answers had no attempt events. Telemetry intentionally omits raw prompts; reviewed synthetic questions are recorded separately. That remains a limitation against the brief's literal per-request question-log requirement.”

## 3:20–4:20 — a real restored account and tool answer

Show `docs/evidence/recovery-backup-2026-11-23.json` and `cloud-restored-tool-2026-11-23.jpg`, with date visible. The assessment copy was removed afterward; do not suggest it is still running.

“Recovery needs MongoDB state, exact versioned dataset and rule bytes, deployment configuration, and access to preserved runtime secrets. S3 versioning and the fourteen-day backup lifecycle protect saved objects. I restored a real dump into five fresh volumes, without attaching production volumes. Counts matched: one user, two conversations, eight messages, one agent and one action. Normal login succeeded, the six-message saved conversation and action were recovered, and a fresh model/tool question returned 60 rows, seven findings and seven affected rows.”

“The conservative whole drill lasted 1438 seconds, or 23 minutes 58 seconds, from 11:36:41 to verification at 12:00:39 UTC. This includes failed attempts, fixes, cleanup and my private-login handoff; it is not automated restore speed. The backup was 572 seconds old at drill start. That nine-minute-32-second exposure is not measured production data loss. The production backup schedule is six-hourly, subject to successful runs. Assessment resources were removed and production health passed.”

## 4:20–5:00 — security and unattended automations

Show security controls, metadata-only secret evidence and automation timestamps. Never show passwords, MFA QR/codes, provider keys or decrypted SecureString.

“Root has MFA. My individual student IAM account has console password and MFA configured, zero access keys, and a scoped operator policy. On 24 November I viewed this dashboard under my own account. This proves individual sign-in and dashboard access; it does not prove every allowed or denied action. Private database ports and a scoped instance role reduce exposure, and runtime secrets stay outside source.”

“Two backup jobs succeeded unattended at 05:30:33 and 05:45:14 UTC on 23 November. They used a disclosed temporary fifteen-minute assessment schedule; the six-hour production calendar was restored afterward. Health jobs succeeded at 05:40:30 and 05:50:31 UTC. The timer-reactivation run is excluded. These prove scheduler execution separately from restore and assistant quality.”

Only claim a final Git-history/archive secret review or active CloudTrail delivery after that evidence exists; otherwise retain the open gates on the website.

## 5:00–5:50 — real fault, root cause and prevention

Show the dated incident/runbook and restore proof. Do not induce a new outage just to record it.

“A restored DataCheck container inherited the production Compose project label from its image. The production health selector found two matching containers and failed closed; cleanup guards also rejected the scope. Label inheritance was the demonstrated root cause. An earlier login rejection had an unknown cause, so I do not attribute it to a password.”

“The fix clears inherited Compose project and service labels while retaining assessment ownership labels. A regression failed before the change; all fourteen recovery tests passed afterward. Live verification found exactly four real production containers and three separate assessment containers. Restored login and a fresh tool answer succeeded, scoped cleanup returned zero resources, and production health passed. The runbook requires verified installation, disjoint volumes and exact scope checks before login or cleanup. Dependent actions stop if installation verification fails.”

## 5:50–7:00 — results, six pillars and next work

Show evaluation, before/after results, graph, cost table and six-pillar review. Show gaps visibly; unmatched numbers cannot establish improvement.

“The initial fixed local assistant evaluation passed ten of thirteen executed cases, about 76.9 percent. Fifteen were planned; two were unrun. Four targeted retests investigated known failures and do not replace that denominator. The scoring script totals reviewed verdicts; it does not independently establish truth. Later cloud cases prove selected integration behavior rather than a new complete quality score.”

“Across the six pillars, operations gained alarms, jobs and a tested incident runbook. Security gained runtime secrets, private services and individual MFA. Reliability gained versioned backups and a verified restore. Performance has actual attempt durations but no matched load benchmark. Cost optimization and sustainability benefit from a small single-host design; project-only before-and-after billing remains a measurement gap unless the final table supplies matched evidence.”

“My priorities are to close the question-log and audit-evidence gaps, improve measurement with a complete reviewed evaluation and matched cost windows, and then reduce single-host recovery risk. The website contains evidence beside claims and records limitations. The final hand-in includes this embedded video, the reviewed declaration and a source ZIP with the actual hidden dot-git history. The public project URL is [published website URL].”

Do not read the last sentence until the URL exists. Time a real rehearsal and trim narration to stay below 8:00 while retaining required demonstrations. If any final hand-in item is still unfinished, say so instead of narrating it as complete. This guide cannot establish D1/D2/D3 acceptance by itself.

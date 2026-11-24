# Final submission handoff

Updated 24 November 2026. The report is live at https://gab26g.github.io/apicompass-datacheck/ and reviewed source is public at https://github.com/gab26g/apicompass-datacheck . The initial source/report snapshot is `62efc307eac405a7597a8ad625f7d4b978f3524d`; the first anonymous HTTP check passed for the report and 31 linked resources. Later report changes need their own publication/link check.

The application, cloud integration, original/reskin capture, logs, monitoring, unattended jobs, fresh restore and actual fault recovery have evidence. The remaining personal deliverables are the student's actual 5–8-minute recording, review/signature, video hosting choice and course submission. Final evidence integration and final ZIP preparation are still in progress; this document is not a completion certificate.

## 1. Freeze the final evidence and source

Use `docs/SUBMISSION-EVIDENCE-MAP.md` and `docs/RECORDING-CHECKLIST.md`.

- Preserve real failures and dates. Fresh normal-SDK shipments request `18fd5a9c-2225-4212-ba36-02710bb658a7` returned 60/7/7 and all seven findings. Intermittent provider stream EOF failures remain unexplained; temporary diagnostics were removed and the original SDK restored. Do not call the failure permanently fixed.
- All 40 deployed release files matched `6b12aebaac0a4a7f54cc224a01675c07d7a55f06`. Source `9d11d9e` adds documentation/diagnostic helpers; it is not a new production SDK fix. Recorded checks passed: 123 Python and 54 Node tests. Keep application parity separate from later report commits.
- Literal sanitized question, duration/outcome/version, database events and jobs were read back in CloudWatch; finite retention is fourteen days. The original metadata-only question-log gap is resolved by explicitly enabled bounded capture with sensitive-input omission statuses.
- Original LibreChat login was captured from the pinned unmodified frontend in a fresh loopback-only local deployment. Its two containers, five volumes and network were removed. Keep the original image attribution and dates.
- Student IAM MFA count one, access keys zero and exactly one directly attached scoped operator policy were observed. Live role/S3/API/private-port probes are recorded in `live-boundaries-2026-11-24.json`.
- CloudTrail is Logging, single Singapore region, all management read/write activity, validation enabled; observed log delivery 24 November 10:47:33 UTC+08 and validation 10:34:02. This is not evidence of global IAM-event coverage.
- Both health ALARM/OK emails arrived by student confirmation. **Still obtain an authentic received-email screenshot with date/time**, redacted for public use, to meet WS-B5's screenshot wording. Do not repeat the fault merely to generate mail.
- Preserve initial 10/13 executed quality result and separate targeted retests. Matched ten-probe/thirty-second API windows both passed 10/10; mean 435.586 ms before and 440.767 ms after. These include Docker/S3 overhead and do not prove improvement or user-answer latency.
- Account month-to-date US$2.42 is account-wide and includes unrelated usage/delayed charges. Project-only matched cost is unmeasured; US$25 alert allowance is not a hard spending cap.
- Finish current-facing report statements, security comparison and six-pillar priorities. Optional thirty-case evaluation or future certificate-renewal observation must not be represented as already completed or made an invented prerequisite for recording.
- Review final source, history, screenshots, archive and eventual video for credentials/private identifiers. Preserve originals privately; deterministic redaction must not change outcomes or measurements. No agent signs the declaration.

| Final source field | Actual state / remaining entry |
| --- | --- |
| Working branch | `codex/datacheck-mvp`; final commit pending final evidence/report edits. |
| Installed application parity | Forty files matched source `6b12aebaac0a4a7f54cc224a01675c07d7a55f06`; later documentation/helper changes identified separately. |
| Public source/report checkpoint | `62efc307eac405a7597a8ad625f7d4b978f3524d`; later publication revision pending. |
| History review | 158 reachable blobs / 23 scanner findings manually resolved in dated review; final new files and actual ZIP still reviewed separately. |

## 2. Finish the private instructor ZIP

D3 requires **actual hidden `.git` history plus README**, not the normal GitHub ZIP or `git archive`.

1. Finish real reviewed source commits. Preserve upstream LibreChat source/author/MIT notice, synthetic-data provenance and honest original/borrowed/AI-assisted contribution statements.
2. Create a fresh local clone preserving authentic history, with no hard links. Remove only the clone's local origin/private metadata as appropriate; do not rewrite the original development history. Review actual copied Git objects/configuration as well as working files.
3. Exclude ignored `.local`, secrets/environment/DPAPI caches, virtual environments, databases/dumps/volumes, unrelated upstream working copies, private assignment text and unrelated project files. An ignore file alone is not archive validation.
4. Run Git integrity checks in the clone, build a new immutable ZIP, extract it separately and verify `.git`, README, expected source and readable real `git log`. Record exact filename/bytes/SHA-256 only after that artifact exists.
5. Keep this archive private for the course channel: real author/committer metadata is retained. The separately reviewed public snapshot excludes original private Git history. Never publish the instructor ZIP by default.

| Instructor archive | State |
| --- | --- |
| Verified earlier checkpoint | `apicompass-source-6b12aeb-verified.zip`; 185 files, ten authentic commits, extracted Git integrity/history and README checked. |
| Checkpoint SHA-256 | `5da4aa5b1d4e9cca0f286fe12b1b60ac6ea01dd3e29390994e7d38964d02adb9` |
| **Final** ZIP filename / bytes / SHA-256 | Pending new archive after final edits; do not submit the older checkpoint as though it contains later work. |

## 3. Complete the public report and student review

The report is already published. Integrate the latest verified evidence, review the publication diff, then check updated assets anonymously and inspect final desktop/mobile, keyboard and print readability. Twelve chapters cover ten substantive brief sections; chapter count is not proof of the suggested 10–15 page-equivalent length.

Student reviews owner/contact, precise provider account tier, contribution history, evaluation judgments and AI disclosure. Observed runtime model is `gemini-3.5-flash-lite`; student confirmed Gemini API free tier on 24 November; no provider invoice inspected. Codex assistance and Gemini runtime are documented; Claude use is unconfirmed.

Student personally reviews and signs/dates full Appendix H: attribution/licence; demonstrable system; invented data/no real personal records; no consequential decisions about identifiable people; authentic evidence; no credentials including Git history; integrity/ethics acceptance. Do not publish an ID/signature unnecessarily; use the required course submission scope.

| Website/review field | State |
| --- | --- |
| Public report | https://gab26g.github.io/apicompass-datacheck/ |
| Initial anonymous resource check | Report + 31 linked resources HTTP 200; repeat for final additions. |
| Final visual/print and evidence integration | In progress; record actual final check after edits. |
| Owner/contact/provider tier, contributions/results/disclosure | Student factual review pending. |
| Appendix H signature/date | Student action pending. |

## 4. Record, host and embed

1. Stage the actual application, report, restricted-user dashboard/alarms/logs, unattended timestamps, restore proof and tested fault/runbook in script order. No credentials, MFA QR/codes or unrelated notifications on screen.
2. Use `docs/RECORDING-SCRIPT.md` for a seven-minute rehearsal. Student narrates and demonstrates the live reskin/AWS application and monitoring; identify saved restore/fault evidence as 23 November. No restore clone remains.
3. Explain whole-drill 1438 seconds (23m58s), including retries/diagnosis/private handoff/cleanup, and backup-age exposure 572 seconds (9m32s). These are observations, not guaranteed RPO/RTO or automated restore speed.
4. Verify actual exported duration **5:00–8:00**, audio/readability/privacy, captions or transcript. Preserve source footage. If the model stream fails, explain and use a bounded retry; do not silently replace failed live footage with a saved success.
5. Student chooses host/visibility and uploads the actual reviewed recording. Supply its real watch URL, insert accessible responsive embed/watch link, republish, then watch the full embed signed out.

| Presentation field | State |
| --- | --- |
| Actual recording/export and verified duration | Not recorded. |
| Host/visibility/watch URL | Student choice/upload pending. |
| Public embed/full signed-out playback | Pending real recording. |

## 5. Hand in and retain access

Submit the public website URL containing the video and the final private Git-history ZIP through the course channel. Confirm actual deadline/location rather than relying on the working target around 25 November. Retain receipt, final URLs/checksum and source footage. Recheck instructor access and remain ready to demonstrate AWS. Arrange scoped teardown after assessment; alerts do not stop resource charges. No course submission or teardown has been performed by this handoff.

## Final evidence additions

The student confirmed Gemini API free-tier access on 24 November. Added redacted actual IAM user-list, SecureString metadata, regional CloudTrail and six-alarm screenshots. `docs/evidence/cost-comparison-2026-11-24.md` records equal 24-hour UTC account-wide Usage-charge windows: 22 November $0.76, 23 November $1.26, with billing-delay and unrelated-workload limits. This is not project-only attribution or savings. The received alert email screenshot still needs the student; both receipts were already confirmed.

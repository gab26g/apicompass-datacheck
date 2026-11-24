# Recording and final submission checklist

Updated 24 November 2026 against SAM10 v3.5 WS-G, D1–D3 and Appendices B–D/H. Companion: `docs/RECORDING-SCRIPT.md`. A checked item records observed work, not a guarantee that the complete submission is finished. Historical proof keeps its real date.

## Evidence ready to stage

- [x] Public report: https://gab26g.github.io/apicompass-datacheck/ . The initial published report and 31 linked resources returned HTTP 200 without browser cookies or authentication. Recheck after the final evidence update.
- [x] Public reviewed source: https://github.com/gab26g/apicompass-datacheck , initial source/report commit `62efc307eac405a7597a8ad625f7d4b978f3524d`. This snapshot excludes original private development history; the instructor ZIP is a separate deliverable.
- [x] Authentic original/reskinned login comparison: `librechat-original-2026-11-24.jpg` and `cloud-login-2026-11-23.jpg`. Original frontend came from the pinned, unmodified LibreChat image in a fresh loopback-only local scope; its two containers, five volumes and one network were removed afterward.
- [x] Real cloud Gemini → saved DataCheck action → private API → versioned S3 interaction. Fresh normal-SDK full shipments answer returned 60 rows / 7 findings / 7 affected rows and all seven findings, request `18fd5a9c-2225-4212-ba36-02710bb658a7`; screenshot `cloud-complete-answer-2026-11-24.jpg`.
- [x] Real limitation answer and actual failed cloud answer retained. Intermittent provider-stream EOF failures remain a limitation with unknown cause. Temporary metadata-only diagnostics were removed and the original SDK hash restored; a later success does not prove the failure fixed.
- [x] Latest logging evidence: `logging-acceptance-2026-11-24.md`, question/jobs/database destination captures and fourteen-day retention. Literal sanitized synthetic question, duration, terminal outcome and version reached CloudWatch. Suspected sensitive input is omitted with an explicit status; capture is bounded, not universal personal-data detection.
- [x] Populated dashboard, six configured alarms and real health ALARM/OK SNS actions. Student dashboard capture: `cloud-dashboard-2026-11-24.jpg`. Both emails arrived by student confirmation.
- [x] Two genuine unattended runs per required job: `automation-runs-2026-11-23.json`. Temporary fifteen-minute backup assessment schedule is disclosed; six-hour production schedule restored. Manual/reactivation runs are excluded.
- [x] Fresh-volume restore, normal login, saved six-message conversation, private agent/action and fresh 60/7/7 tool-backed answer: recovery JSON/incident record and `cloud-restored-tool-2026-11-23.jpg`. Assessment scope was removed; production volumes were preserved.
- [x] Recovery timing: 23 November 11:36:41–12:00:39 UTC, whole drill 1438 seconds (23m58s), including failures/retries/diagnosis/cleanup/private handoff. Backup-age exposure 572 seconds (9m32s), not observed data loss or guaranteed RPO.
- [x] Real incident and tested prevention: inherited production Compose labels made recovery DataCheck match production discovery; explicit overrides, failing-then-passing regression, disjoint inventory and scoped cleanup verified. Earlier login rejection cause remains unknown.
- [x] Student IAM MFA count one, zero access keys and exactly one directly attached `APICompassStudentOperator` policy observed. Normal work uses the restricted student identity; root was used for scoped administrative reads.
- [x] Live checks: `live-boundaries-2026-11-24.json`. IAM-role credentials, allowed versioned S3 read/hash, denied deliberately nonexistent out-of-prefix key, private API 401/401/200/404/422 and no host-loopback listeners on 8000/27017. These are point-in-time probes, not an external scan or proof of every policy path.
- [x] Regional CloudTrail observed Logging, management read/write activity, log-file validation enabled; latest delivery 24 November 10:47:33 UTC+08 and validation 10:34:02 UTC+08. Single Singapore trail does not establish global IAM-event coverage.
- [x] All 40 deployed release files matched source `6b12aebaac0a4a7f54cc224a01675c07d7a55f06`. Later `9d11d9e` changes are documentation/diagnostic helper additions, not a production SDK fix. Recorded tests: 123 Python and 54 Node passed, including seven diagnostic tests.
- [x] Matched ten-probe, thirty-second before/after checks retained: both 10/10; means 435.586 ms and 440.767 ms. Docker/S3 overhead is included; no answer-latency, capacity, p95, savings or improvement claim.

## Close the remaining preparation items

- [ ] Integrate newest comparison/security/normal-answer evidence and publication status into the report. Inspect final desktop/mobile/keyboard/print presentation; refresh public resource checks after publishing.
- [ ] Preserve an authentic redacted received ALARM/OK email screenshot with date/time for WS-B5. Receipt is already confirmed; do not repeat a disruptive fault to generate mail.
- [ ] Student reviews owner/contact, precise provider account tier, contributions, evaluation verdicts and AI disclosure. Model observed: `gemini-3.5-flash-lite`; Codex assistance and Gemini runtime documented. Do not claim Claude use without confirmation.
- [ ] Retain measurement limits: initial quality 10/13 executed, not a fresh full-suite score. Account month-to-date US$2.42 includes unrelated usage and delayed charges; project-only matched cost is unmeasured. US$25 is an alert allowance, not a hard cap.
- [ ] Build/extract final private instructor ZIP after final commits; record actual filename/checksum in `docs/SUBMISSION-HANDOFF.md`. Verified earlier checkpoint exists; later changes require a new archive. Preserve actual `.git` and review metadata/history as well as source.

## Stage and record — target seven minutes

- [ ] Open report, signed-in application, restricted-user dashboard/alarms, question logs, restore proof, automation timestamps and runbook in script order. Suppress unrelated tabs/notifications; never record credentials or MFA QR/codes.
- [ ] Test ten seconds of microphone/screen playback; ensure evidence and dates are readable.
- [ ] Rehearse with an actual timer. Record/export **5:00–8:00**, including model waits. Word count is not duration verification.
- [ ] Solo student narrates and demonstrates live reskin/AWS application and monitoring. Label saved recovery/fault proof as 23 November; no recovery copy remains. If instructor requires a fresh live restore, follow bounded reviewed procedure/private login without deleting production data.
- [ ] Explain real failure, stream limitation, quality denominator, six-pillar verdicts, single-host risk and priorities. Use a bounded retry if a live model stream fails; retain/explain the failure rather than silently substituting footage.
- [ ] Review every exported frame for identifiers/credentials. Deterministic redaction may cover identifiers while preserving measurements/results; retain authentic source capture. Add captions or a transcript.

## Finish D1, D2, D3 and hand-in

- [ ] Student personally reviews and signs/dates full Appendix H, plus factual AI-assistance/contribution wording. No agent signs or certifies these affirmations.
- [ ] Student chooses video host/visibility, uploads reviewed actual recording and supplies real watch URL. Embed responsively with title/watch link; watch entire publicly accessible embed signed out.
- [ ] Recheck final website evidence/download/app links, print readability and required sections. Twelve chapters cover the brief's ten substantive sections; chapter count alone does not prove suggested 10–15 page-equivalent length.
- [ ] Deliver private source ZIP with authentic `.git` and README through course channel, together with public website URL containing video. GitHub download or `git archive` alone omits `.git` and is insufficient.
- [ ] Confirm actual deadline/submission location, retain receipt/checksums and recheck instructor access. Arrange scoped cloud teardown after assessment; budget alerts do not stop charges.

Recording, personal review/signature, final video hosting/embed and course submission remain personal actions. Engineering evidence and packaging work should continue until those are the remaining handoff steps.

## Final evidence additions

The student confirmed Gemini API free-tier access on 24 November. Added redacted actual IAM user-list, SecureString metadata, regional CloudTrail and six-alarm screenshots. `docs/evidence/cost-comparison-2026-11-24.md` records equal 24-hour UTC account-wide Usage-charge windows: 22 November $0.76, 23 November $1.26, with billing-delay and unrelated-workload limits. This is not project-only attribution or savings. The received alert email screenshot still needs the student; both receipts were already confirmed.

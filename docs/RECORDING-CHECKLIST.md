# Recording and final submission checklist

Updated 24 November 2026 against SAM10 v3.5 WS-G, D1–D3 and Appendices B–D/H. Companion: `docs/RECORDING-SCRIPT.md`. Checked entries identify evidenced work; unchecked entries are concrete remaining gates. Historical evidence may be shown with its real date. It does not become a fresh live demonstration by appearing in a video.

## Evidence already available — stage these before rehearsal

- [x] Cloud application login, one saved action/four operations, real Gemini → DataCheck → versioned S3 answer: `docs/evidence/cloud-integration-2026-11-23.md`, `cloud-login-2026-11-23.jpg`, `cloud-shipments-answer-2026-11-23.jpg`. Actual result 60 rows / 7 findings / 7 affected rows, shipments-v2, shipments-rules-v2. Request ID `a0418fb3-ba8e-420c-bcc6-92c4ce6f7762` belongs to the first dated cloud answer.
- [x] Limitation answer: `cloud-limitation-answer-2026-11-23.jpg`; the source lacks supplier/delay-cause fields. The initial evaluation separately retains genuine failures.
- [x] Actual CloudWatch question-attempt events: `cloud-question-logs-2026-11-23.jpg`, durations 3479.704 and 1834.423 ms after the saved-agent route correction. First two pre-fix cloud answers were unmonitored; exclude them from telemetry claims.
- [x] Successful isolated restore: `recovery-backup-2026-11-23.json`, `recovery-incident-2026-11-23.md`, `cloud-restored-tool-2026-11-23.jpg`. Normal login, recovered six-message conversation, private agent/action and fresh S3 tool answer 60/7/7 verified. Assessment resources were removed afterward; production volumes were preserved.
- [x] Timing: 11:36:41–12:00:39 UTC on 23 November, conservative whole-drill 1438 seconds (23m58s), including failed attempts/retries/diagnosis/cleanup/private handoff. Backup-age exposure 572 seconds (9m32s), not observed production data loss or an automated-restore benchmark.
- [x] Real metric-driven health ALARM 11:41:51 UTC and OK 11:51:51 UTC; SNS actions succeeded. Student confirmed both emails arrived. Receipt is user-attested; no inspected inbox screenshot is currently preserved.
- [x] Two unattended runs per automation: `automation-runs-2026-11-23.json`. Backups 05:30:33.686055 and 05:45:14.375573 UTC; health 05:40:30.814969 and 05:50:31.033152 UTC. Disclose temporary fifteen-minute backup assessment calendar; six-hour production calendar restored. Exclude timer-reactivation/manual runs.
- [x] Real fault/root cause/fix/prevention: inherited production Compose labels made recovery DataCheck match the production selector. Explicit label overrides, failing-then-passing regression, disjoint live inventory and scoped cleanup are documented in `recovery-incident-2026-11-23.md`. Earlier login rejection cause remains unknown.
- [x] Individual student IAM password and MFA completed; zero access keys; own-account dashboard viewed on 24 November. Capture: `docs/evidence/cloud-dashboard-2026-11-24.jpg`. This establishes own sign-in/dashboard access, not every allowed/denied operation. Parent session observation is the provenance for the latest own-account verification.

## Finish evidence and website content

- [ ] Refresh stale README/contribution/system-card/website statements against the latest evidence; identify actual release and any source/runtime drift. Preserve LibreChat source URL, author and MIT attribution and original synthetic-data provenance.
- [ ] Confirm precise Gemini model name and student's provider account tier; enter reviewed owner/contact and contributions. Student adjudicates AI-assisted evaluation/disclosure personally.
- [ ] Capture authentic original/reskinned comparison showing name/logo, wording, domain data/prompts and AWS integration. Retain three actual questions/answers including a failure, not only successful target cases.
- [ ] Show actual deployed topology: EC2/Caddy/chat/private MongoDB/private DataCheck, networking, external model, S3, runtime secrets, CloudWatch/SNS, backup and audit services only where actually present.
- [ ] Inspect all required dashboard signals and six actual alarms with thresholds, periods, missing-data behavior and email destinations. The 24 November dashboard capture supports dashboard access; inspect widget coverage/readability before claiming complete six-signal acceptance.
- [ ] Preserve an authentic redacted received alert email with date/time visible to meet WS-B5's screenshot wording. User-attested receipt is already established; do not repeat the disruptive fault just to produce another notification.
- [ ] Preserve database CloudWatch stream readback and finite retention. Shipper Result=success with 730 sanitized events is available, but delivery-service output alone is not console stream readback.
- [ ] Resolve or explicitly declare WS-B4's literal question-log gap: attempt events contain duration/outcome/version but deliberately omit prompt text; separately reviewed synthetic case prompts do not establish automatic question-text logging for every request. Do not claim full compliance from opaque IDs alone.
- [ ] Show S3 versioning, fourteen-day backup lifecycle, full recovery inventory and current effective production schedule. Keep operator-triggered restore backup distinct from unattended-run evidence.
- [ ] Complete security evidence: runtime-secret consumption metadata, actual role allow/deny checks and CloudTrail recording/delivery. Own-account dashboard access does not establish all these controls. Keep regional/global audit coverage limits explicit.
- [ ] Complete one sentence per security control/risk and a dated before/after security table. Review source, full Git history, website, screenshots, video and final archive for secrets.
- [ ] Keep tested fault commands, expected outputs, rollback, acceptance checks and last-tested metadata on the website. Show known incident timing without inventing the unknown initial fault-injection timestamp.
- [ ] Finish matched before/after measurements with same inputs/method/window, date range next to each number, screenshots, at least one graph and actual before/after project cost. Initial 10/13 and targeted retests are different populations; neither cloud spot checks nor account-wide credits establish a matched result.
- [ ] Revisit all six pillars with good/adequate/gap verdicts, first priority and reason; list three to five realistic next steps.

## Stage and record — seven minutes

- [ ] Open the reviewed site, signed-in AWS app, dashboard/alarms, question logs, restore screenshot/JSON, automation timestamps and incident/runbook in presentation order. Do not record credential entry; suppress notifications and unrelated tabs.
- [ ] Run a ten-second microphone/readability playback. Use legible zoom and visible operational dates/timezone. Label historical restore/fault evidence as 23 November; no assessment copy remains.
- [ ] Rehearse the companion script with an actual timer. Target 7:00, including model wait; recording/export must be 5:00–8:00. Word count alone does not verify duration.
- [ ] Demonstrate the live reskin/AWS app, dashboard and alarms, restored-login/tool proof and real fault evidence. The brief explicitly asks live demonstration; use dated historical proof transparently for long restore/fault operations and retain source footage. If the instructor requires a fresh live restore, use the reviewed bounded recovery procedure and private login, not an improvised production outage.
- [ ] Solo student narrates; if a pair, both present and can explain the full system. Review own contribution and AI-assistance wording before saying it.
- [ ] Inspect every exported frame for secrets and private account/email material; redact private fields without changing outcomes/timings. Do not manufacture success, swap a local answer into a cloud demo, or silently accelerate latency.
- [ ] Preserve the authentic source capture; add readable captions/transcript and verify exact model/service names.

## D1 — complete the twelve-chapter website

- [ ] Twelve chapters cover summary, original work, architecture/data, all nine system-card headings, evaluation/Q&As, baseline/monitoring, recovery, security, automation/incident/runbook, six pillars/cost, next steps/video, evidence/declaration. Twelve chapters are the chosen layout; the brief itself specifies ten content sections and approximately 10–15 pages excluding cover/contents.
- [ ] Embed screenshots/log excerpts/output beside claims. Downloads supplement the narrative; a separate evidence directory alone does not satisfy WS-G.
- [ ] Visually inspect desktop/mobile, keyboard navigation, readable evidence and print layout/page count. A structural verifier cannot establish those outcomes.
- [ ] Student reviews and signs/dates Appendix H; every partner signs. Include full required confirmations and reviewed two-sentence AI disclosure. Do not pre-sign or certify on the student's behalf.
- [ ] Publish only reviewed `submission-site` content to GitHub Pages or Vercel; record the public URL. Public hosting is not completed yet.
- [ ] Insert the real externally hosted video embed and accessible title with responsive aspect ratio; keep a normal watch link. Verify site, player, full playback, downloads and app link while signed out.

## D2 — complete the hosted video

- [ ] Record/export the student's actual presentation and verify duration 5:00–8:00, legible evidence and comprehensible audio.
- [ ] Host on YouTube, Vimeo or similar using visibility/access the student chooses; verify instructor access without another account or extra permissions.
- [ ] Embed the uploaded version on the public site and watch it through from the signed-out site. Recording/upload/embed are still unperformed at this checkpoint.

## D3 — source ZIP with real history and hand-in

- [ ] Finish reviewed real source commits, reproducible deployment/automation instructions and week-by-week contribution README. Reconcile runtime hotfixes with final source/release identifiers.
- [ ] Build a reviewed allowlisted source ZIP containing the actual hidden `.git` directory and README, custom source, tests, infra, automation, branding/configuration and necessary evidence. A normal GitHub source ZIP or `git archive` omits `.git` and is insufficient. Do not invent or replace commit history.
- [ ] Exclude private `.local`, environment/DPAPI caches, credentials, database volumes/dumps, unrelated upstream working copies and assignment/private handoff material. Review full included Git history, including previous/deleted content, for exposed secrets.
- [ ] Extract ZIP into a separate temporary folder; verify `.git` and README exist, `git log` reads real history, required files are present, and no private state is included. Record filename and checksum after the final archive is fixed. Final ZIP does not exist yet.
- [ ] Submit public website URL plus repository ZIP through the course channel, with video embedded; confirm actual deadline/location, retain receipt and recheck instructor access.

The remaining personal actions are provider-tier confirmation, contribution/result/declaration review, narration/recording, hosting-visibility choice, signature and course submission. They cannot be truthfully signed, spoken or certified on the student's behalf. Engineering publication/package/evidence work should continue independently within authorization.

# Final submission handoff

Prepared 24 November 2026. This is the execution order for final delivery, not a completed-submission certificate. Current website source is `submission-site/`; the recording script and checklist are in `docs/`. The AWS integration, restored login/conversation/action/fresh tool answer, actual isolation fault recovery and unattended automation runs already have evidence. Both ALARM/OK emails are student-confirmed. Individual student IAM password/MFA and own-account dashboard access are complete.

## 1. Freeze the reviewed source and facts

1. Finish concurrent source/site changes, review actual runtime/source identifiers and remove current-facing statements that still call completed cloud/recovery/IAM work unperformed. Keep dated failed attempts and limitations intact.
2. Complete README deployment, operations and weekly contribution instructions. Preserve LibreChat source/author/MIT credit and distinguish original work, borrowed dependencies and Codex assistance.
3. Review `docs/evidence/source-history-review-2026-11-24.md`. The 23 historical scanner matches were inspected in their exact blobs and resolved as expressions, synthetic fixtures or a placeholder. Final current/staged files still need their own check after all edits are staged. Never print candidate values during review.
4. Review final source, history, screenshots, website and video for secrets/private account data. The actual ZIP must also be reviewed. Do not certify the declaration until this is complete.
5. Make real reviewed commits and record the final commit/release identifiers below. Do not invent commits, rewrite history without separate authorization, or imply the deployed hotfixes match an older release automatically.

| Final source field | Fill from actual result |
| --- | --- |
| Branch / final commit | Pending final reviewed commit. |
| Deployed release and verified source parity | Pending final runtime/source reconciliation. |
| Final staged/tracked review | Pending after concurrent edits/staging. |
| History review | See 24 November review; 158 reachable blobs, 23 findings manually resolved; actual ZIP objects/metadata still require final inspection. |

## 2. Build the instructor repository ZIP with real `.git`

The instructor's ZIP is a private course deliverable containing authentic Git history. The public website should contain only reviewed website assets. These are different packages.

1. Choose a temporary packaging directory outside the repository. Copy an explicit allowlist: README, notices/licences, custom source/tests, requirements/configuration templates, branding, actions, scripts, infra, operations/deployment documentation, necessary reviewed evidence and website source. Include the **actual hidden `.git` directory**. Keep necessary pinned upstream setup/patch instructions reproducible; do not blindly copy an unrelated upstream checkout.
2. Exclude `.local/`, real `.env` files, DPAPI/bootstrap caches, credentials, database volumes/dumps, virtual environments, logs containing private data, private assignment text, account handoff files and unrelated project material. An ignore file alone does not enforce archive exclusions.
3. Inspect the copied `.git` metadata and included objects as well as source. Reachable commit scanning alone does not cover reflog/unreachable objects, hooks or all local metadata. Preserve authentic history; if a credible secret is found, stop delivery, rotate/revoke it and obtain the needed authorization for remediation. Do not quietly erase evidence or reinitialize the repository.
4. Commit author/committer email metadata contains personal information. Preserve it in the instructor ZIP as required, deliver through the private course channel and review this scope before submission. If publishing source separately, use an independently reviewed source snapshot when that personal history is not intended to be public. Do not publish the instructor archive as a website download by default.
5. ZIP the prepared directory with hidden `.git` included. A normal GitHub source ZIP or `git archive` does **not** include Git history and fails D3. Some archive tools also omit hidden items; verify the output rather than assuming.
6. Extract the finished ZIP to another temporary directory and check actual `.git`, README, expected source/configuration and evidence. Run `git log` in the extracted repository and inspect its real history. Run `git status` to understand the extracted state. Confirm no excluded private files are present. Do not connect extracted source to production automatically.
7. Record exact archive filename, byte size and SHA-256 after the final file is fixed. On Windows, `Get-FileHash -Algorithm SHA256 -LiteralPath '<final ZIP path>'` computes the checksum. Replace the placeholder locally; do not claim a checksum before a real file exists.

| Instructor archive field | Fill from actual result |
| --- | --- |
| Final ZIP filename/path | Not yet built. |
| Extracted `.git` / readable `git log` | Not yet checked. |
| Included-source/private-state review | Pending actual ZIP inspection. |
| ZIP size and SHA-256 | Pending final artifact. |

## 3. Finish the public website and declaration

1. Use `docs/SUBMISSION-EVIDENCE-MAP.md` to finish the twelve chapters and evidence next to each claim. The brief asks ten substantive content sections and roughly 10–15 pages, not twelve arbitrary pages. Keep the system card, actual service/network diagram, baseline, security before/after, incident/runbook, matched measurements/costs, graph, pillar verdicts and prioritized next steps substantive.
2. Resolve remaining proof gaps or state them explicitly: dated received-email screenshot (receipt already confirmed), DB CloudWatch stream/retention readback, final six-alarm/widget evidence, live audit/allow-deny proof and matched before/after project-cost/results. Question logging must satisfy the final implemented evidence; duration/outcome/version-only telemetry does not prove raw prompt logging. Do not retain a resolved gap after a real fix is verified.
3. Student reviews owner/contact, provider model/tier, contributions, evaluation verdicts, licences and two factual AI-assistance sentences. Do not claim use of an AI tool solely because someone prepared a handoff for it.
4. Student personally reviews and signs/dates Appendix H; both partners sign if applicable. Include all required affirmations: attribution/licence; system exists and can be demonstrated; invented data/no real personal records; no consequential decisions; authentic evidence; no credentials including history; integrity/ethics acceptance. No agent should sign or certify on the student's behalf.
5. Visually inspect desktop/mobile, keyboard access, evidence readability and print layout. Run the site's preparation/verification commands from `submission-site/README.md`; structural success alone does not prove visual or public-access acceptance.
6. Publish only the reviewed static website to GitHub Pages or Vercel with no private source/runtime folders. If a public repository is used for hosting, review the repository contents/history separately; the instructor's history ZIP is not the default public payload.
7. Record the actual public URL and check every evidence/download/application link while signed out. Keep the presentation slot honestly pending until a real hosted video exists.

| Website/declaration field | Fill from actual result |
| --- | --- |
| Public website URL / host | Not yet published. |
| Desktop/mobile/keyboard/print inspection | Pending final visual check. |
| Student owner/contact/model tier | Student review pending. |
| Appendix H signed/date | Student action pending; no signature fabricated. |
| Public access/download/link check | Pending actual public URL. |

## 4. Record, host and embed the presentation

1. Stage the actual app, website, own-account dashboard/alarms, logs, job timestamps, restored-tool proof and fault/runbook. Use `docs/RECORDING-SCRIPT.md` and `docs/RECORDING-CHECKLIST.md` for a seven-minute rehearsal. Never show credential entry, decrypted secrets, MFA QR/codes or unrelated private content.
2. Student narrates and demonstrates the reskin, live AWS app, dashboard/alarms, restore and fault, following the site's structure. Both students present if paired. Historical recovery/fault evidence must keep its real date; the restored clone was removed. Do not present saved evidence as a new live restore.
3. Keep recovery figures precise: 1438 seconds is the conservative entire drill including retries, diagnosis, cleanup and private handoff; 572 seconds is backup-age exposure, not measured data loss. Both real health emails arrived by student confirmation. Explain unknowns honestly.
4. Time an actual rehearsal, then record/export. Verify actual duration **5:00–8:00**, audio, readable screens and exact factual narration. Review every frame for privacy and retain authentic source footage. Captions/transcript improve access.
5. Student chooses video host/visibility on YouTube, Vimeo or similar; upload the reviewed final export. Unlisted does not mean fully private. Verify instructor access without extra account permissions.
6. Insert the actual hosted video embed into the website, with accessible title, responsive sizing and a normal watch link. Republish the reviewed site, then watch the embedded video from start to finish while signed out.

| Presentation field | Fill from actual result |
| --- | --- |
| Source/export file and verified duration | Not yet recorded. |
| External video URL / chosen visibility | Student upload pending. |
| Public embed + full signed-out playback | Pending real video and publication. |

## 5. Submit and keep the receipt

Submit one project website URL and the instructor repository ZIP through the course channel; the presentation must be embedded on that website. Confirm the actual instructor deadline and submission location rather than relying on the working target around 25 November. Retain the submission receipt, final archive checksum, source recording and final URLs until assessment finishes. Recheck access from a signed-out window after submission. Remain able to demonstrate the actual AWS system during office hours.

| Final hand-in field | Fill from actual result |
| --- | --- |
| Instructor deadline/location | Confirm directly. |
| Submitted website URL + ZIP | Not submitted. |
| Receipt/time | No receipt yet. |
| Post-submission access check | Pending actual submission. |

The personal final actions are factual/contribution/declaration review, provider-tier confirmation, narration, visibility choice, signature and course submission. Source review, packaging and website preparation can proceed independently within authorization. Blank fields identify real outstanding artifacts; they must be filled from observed results, not inferred from plans.

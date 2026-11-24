# Contribution and AI-assistance record

Updated 24 November 2026. Solo project selected and directed by Gab. This record distinguishes student decisions/private actions, Codex-assisted implementation and observed verification. It is not the signed declaration, a certification of student review, or a claim that AI-assisted code was written independently by the student.

## Student decisions and private actions

- Selected APICompass plus a new deterministic DataCheck API as a small AI/cloud operations project within SAM10, selected Gemini and directed continued work toward the assessment deliverables.
- Entered provider credentials directly in the application during local setup; privately supplied production runtime credentials and completed normal production account/login and action-binding handoffs. Credentials were not supplied in chat or retained in this record.
- Confirmed the personal AWS account and free-hostname plan. The initial US$20 allowance was superseded by an explicit **US$25 maximum** on 22 November. Approved the reviewed foundation/compute deployment and subsequent release/monitoring actions. AWS Budgets alerts are notifications, not a hard spending cap.
- Privately configured root MFA. The console independently confirmed root MFA enabled and no active root access keys. Budget configuration was performed with Codex assistance: actual-cost thresholds US$10/US$20/US$25 and forecast US$25, excluding credits/refunds, with no automatic budget action.
- Approved the scoped individual student operator identity/policy, privately chose the console password and configured MFA, then completed normal individual sign-in. MFA and no access keys were independently observed. Permitted dashboard/log access and the direct EC2 Connect → Session Manager path were verified; general Session Manager inventory is outside the current listing permission scope.
- Privately completed the restored application's normal-login verification. Independently observed recovery evidence then established the owned conversation, private action and fresh S3-backed model/tool result.
- Confirmed the SNS subscription and separately confirmed receipt of **both** actual health ALARM and recovery emails. This is student-attested inbox receipt; do not relabel it as an agent-inspected email screenshot.
- Communicated deadline estimates and authorized implementation/review agents. The actual course deadline and submission location must still be confirmed through the course channel.

These actions do not establish that the student independently authored the implementation, has reviewed every generated result, has recorded the presentation or has signed the declaration.

## Week-by-week dated record

The project progress log supplies the early observations; repository history begins on 21 November. Calendar-week rows organize the record and do not invent activity during unrecorded dates. Commit subjects/dates were read without printing author or committer personal metadata.

| Calendar week and observed dates | Student role/actions recorded | Codex-assisted implementation and evidence |
| --- | --- | --- |
| 2–8 November; checkpoint 7 November | Chose scope/provider and directed the local start. | Read/preserved LibreChat MIT attribution, pinned the base image/source, prepared minimal local Compose and stable DPAPI bootstrap, diagnosed Docker startup and observed the branded login. These are dated progress observations; no early Git commits are claimed. |
| 9–15 November; checkpoint 9 November | Entered the Gemini key privately, removed the duplicate action during setup, paused further work. | Implemented the initial eight-row inventory API/action, tested private-network API access, diagnosed duplicate function declarations/provider incompatibilities and observed the first successful local tool-backed answer. No work on the other dates in this week is asserted. |
| 16–22 November; checkpoints/commits 21–22 November | Resumed work, supplied credentials privately, confirmed account/hostname/budget choices, later raised the allowance to US$25, configured root MFA and approved reviewed AWS foundation/compute actions. | Expanded to three 60-row fixtures, explicit rules/contracts, local/S3 fail-closed storage, tests, reskin and real local evaluation. Prepared/deployed reviewed foundation and compute scope in Singapore. Commits: `cd346c4` local baseline, `1874f7c` guarded three-dataset storage, `1423c55` observed Gemini tool call, `8c380f4` branding/evaluation (21 November); `0df2812` foundation/budget preflight and `361634c` foundation observation (22 November). |
| 23–29 November; observed 23–24 November only | Approved release/monitoring updates and scoped IAM setup; privately enrolled/bound the production account, completed restored login and individual password/MFA/sign-in; confirmed alert receipt. | Implemented/deployed runtime, private setup helpers, telemetry, monitoring, backup/health/log-shipping jobs and isolated restore tooling. Captured real cloud answers, unattended jobs, actual fault/recovery and sanitized evidence; drafted site/recording/submission artifacts and reviewed source/history. Commits `c61b525`, `6cb15c6`, `c6d1cb3` (23 November) and `6b12aeb` (24 November) record production/operations, integration helpers, pinned-agent/recovery fixes and sanitized logging/recovery/submission work. Work after 24 November is not claimed. |

The table records completed observations and assistance, not estimated hours, a fabricated equal division of effort, or a promise that every course requirement is complete. See [PROGRESS.md](../PROGRESS.md), [cloud integration](evidence/cloud-integration-2026-11-23.md), [automation runs](evidence/automation-runs-2026-11-23.json) and [recovery incident](evidence/recovery-incident-2026-11-23.md) for dated outcomes and limitations.

## Codex-assisted work and verification

Codex assisted with project planning; local Compose/bootstrap and branding; the original API, synthetic fixtures, schemas and golden expectations; authentication/readiness and local/S3 adapters; bounded action/model instructions; tests, smoke/export/scoring scripts; AWS templates/runtime/secret loader; normal private enrollment/action transports; monitoring/log shipping; scheduled jobs; isolated restore and cleanup; diagnosis/prevention of real defects; evidence preparation; source/history review; website and recording/submission documentation. Authorized sub-agents contributed within assigned scopes. This code and prose must be described as AI-assisted.

Verification included reproduced failing regressions followed by fixes, actual local and cloud observations, live model/tool/S3 trace comparison, genuine scheduler histories, restored application-state/tool proof, scoped cleanup checks, alarm history and independently observed AWS control state. Private passwords, MFA secrets/codes and provider keys remained human inputs. Tests and screenshots establish only their named boundaries; unit tests are not live AWS proof and targeted model checks are not a full evaluation.

The integration owner reports the latest completed source checks as **123 Python and 47 Node tests passed**, associated with the 24 November `6b12aeb` source checkpoint. This contribution-document edit did not rerun them. The current synthetic-question logging update has been installed and production startup succeeded; its actual destination event is **not yet independently verified** at this record's checkpoint. Keep source implementation, runtime installation and observed log ingestion distinct.

The initial local assistant result remains **10/13 executed cases (76.9%)**, with two of fifteen planned cases unrun. Four targeted v3 passes and subsequent successful cloud acceptance cases do not replace that denominator. The scoring script calculates arithmetic over reviewed outcomes; factual adjudication still requires student review. No fresh full assistant evaluation is claimed. See [evaluation](EVALUATION.md).

## Borrowed work and tools

[LibreChat](https://github.com/LibreChat-AI/LibreChat/tree/v0.8.8), by its project and contributors, provides the base application under MIT; retain [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md). FastAPI, Uvicorn, Python, Docker, Caddy, the AWS SDK and MongoDB are existing dependencies/services, not original student work. Gemini is externally hosted; the student did not author, train, fine-tune or host its model. Attribute only this project's actual additions as custom implementation.

OpenAI Codex was used for engineering/documentation assistance and Gemini as the application's model. **Claude use is unconfirmed**; a prepared Claude handoff is not proof that Claude was used. Add another tool only if the student confirms its actual use and purpose.

## Before recording, signing and submitting

The student must understand and personally review the implementation/results, reproduce key workflows, verify provider tier/licensing/contact fields, correct inaccurate claims and review the contribution record. Record two factual sentences naming the AI tools actually used, their purposes and how their output was checked. Do not state that review, independent authorship or personal certification occurred before it does.

Remaining delivery work includes final source/runtime and log-event acceptance, actual archive/history/privacy checks, finished published website, the student's 5–8-minute externally hosted embedded recording, and the personally reviewed/signed/dated Appendix H declaration. No signature, recording, public URL or submission receipt is generated by this record. Follow the [final submission handoff](SUBMISSION-HANDOFF.md) and preserve authentic Git history in the private instructor ZIP.

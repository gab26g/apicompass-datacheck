# APICompass + DataCheck

SAM10 Systems Administration and Maintenance final project. APICompass adapts [LibreChat v0.8.8](https://github.com/LibreChat-AI/LibreChat/tree/v0.8.8), by the LibreChat project and contributors, under its MIT licence. DataCheck is the project's original deterministic, read-only API for three invented 60-row datasets: inventory, shipments and equipment. Gemini explains its structured findings; it cannot edit records. See [attribution](THIRD-PARTY-NOTICES.md), the [data contract](docs/DATA-CONTRACT.md) and [weekly contributions/AI assistance](docs/CONTRIBUTIONS.md).

## Verified handoff — 24 November 2026

The application is deployed on AWS in Singapore (`ap-southeast-1`) behind trusted HTTPS. Actual cloud browser/model/tool/S3 interactions returned shipments: **60 rows, seven findings across seven rows**, dataset/ruleset versions and a matching API request ID. A follow-up correctly declined unsupported supplier/delay causes. These are targeted acceptance observations, **not a fresh full assistant evaluation score**. [Cloud integration evidence](docs/evidence/cloud-integration-2026-11-23.md) preserves prompts, source metadata, outcomes and telemetry limits.

The CloudWatch/SNS dashboard and six-alarm stack are deployed. The subscription is confirmed; the student confirmed both real health ALARM/recovery emails arrived. Question-attempt events and database logs were read back in CloudWatch; the three project log groups have verified 14-day retention. Individual MFA-protected student IAM access works through the instance's direct EC2 Connect → Session Manager path. The general Session Manager inventory page requires an additional listing permission and is not the operating path. The integration owner most recently verified all four production containers up, health-bearing services healthy, four timers active and health success/exit zero.

[Automation evidence](docs/evidence/automation-runs-2026-11-23.json) records two regular unattended backup runs and two unattended health runs. Backup proof used a disclosed temporary fifteen-minute assessment calendar; the six-hour production calendar was restored. It does not imply two six-hour-spaced observations. An isolated restore recovered normal login, owned saved conversation, private action and a fresh S3-backed model/tool answer. The assessment copy was removed and production health rechecked. [Recovery/incident evidence](docs/evidence/recovery-incident-2026-11-23.md) preserves failed attempts, diagnosis, correction and prevention. The conservative whole drill took **1,438 seconds (23m58s)** including retries/private handoffs; **572 seconds (9m32s)** was backup-age exposure, not measured data loss or automated restore speed.

The final logging/recovery integration check recorded **123 Python and 47 Node tests passing**. A separate seven-test bounded provider-stream diagnostic also passed. These are software checks, not model answer scores. The initial local assistant evaluation remains **10/13 executed cases (76.9%)**, with two of fifteen planned cases unrun. Four targeted v3 retests are separate; see [evaluation](docs/EVALUATION.md).

The `runtime-v3` logging update is installed. All **40 release files** matched committed source `6b12aeb`; the existing runtime loader reused the SecureString and volumes. CloudWatch independently showed a captured synthetic question, its duration, version and failed outcome, plus real terminal job events. The visible footer explains the 14-day logging boundary. A fresh complete shipment answer passed after the original provider SDK was restored; intermittent stream failures remain a documented dependency limitation with unknown cause. Correct tool facts do not turn an incomplete answer into a pass. See [final acceptance](docs/evidence/final-acceptance-2026-11-24.md), [logging and actual failures](docs/evidence/logging-acceptance-2026-11-24.md) and dated evidence.

The [public report](https://gab26g.github.io/apicompass-datacheck/) and [reviewed public source](https://github.com/gab26g/apicompass-datacheck) are published. The report includes genuine original/reskinned UI comparison, populated monitoring, restore/incident proof, redacted security captures and a dated account-wide cost comparison. The student must still record the actual **5–8-minute** presentation, supply captions/transcript, host/embed it, review/sign the declaration and submit the private source ZIP containing authentic Git history. See [recording checklist](docs/RECORDING-CHECKLIST.md).

## Architecture and configuration boundaries

One `t3.small` EC2 host with encrypted EBS runs the separate `apicompass-prod` Compose project:

| Component | Role and boundary |
| --- | --- |
| Caddy proxy | Trusted HTTPS; only service publishing host TCP 80/443; forwards to chat. |
| APICompass/LibreChat | Accounts, saved conversations and branded chat; calls external Gemini. |
| MongoDB 8.0.20 | Single authenticated database, private container network and separate app user. |
| DataCheck | Private port 8000, bearer authentication, fixed four-operation action; production S3-only. |
| Private versioned S3 | Frozen datasets, reviewed application releases and database dump objects. |
| Instance role + Parameter Store | Scoped AWS access and runtime SecureString; no static workload access key. |
| CloudWatch + SNS | Dashboard, six alarms, bounded log shipping and real notification route. |
| Regional CloudTrail | Audit trail; Singapore-only coverage does not establish global IAM-event coverage. |

Gemini runs outside AWS. Only invented prompts/data may be sent to it; never enter personal records, credentials or consequential decisions about people. One host is a single point of failure. Backup briefly stops chat for a quiesced logical MongoDB dump; background TTL writes mean this is not a claimed atomic point-in-time snapshot. Health checks validate deterministic S3-backed behavior, disk and backup freshness; they do not independently establish Gemini availability or answer quality.

| Local development | Production |
| --- | --- |
| `compose.local.yaml`, project `apicompass-local` | `compose.production.yaml`, project `apicompass-prod` |
| Chat on `127.0.0.1:3080`; MongoDB/DataCheck private | Only proxy publishes 80/443; authenticated private MongoDB/DataCheck |
| Local CSVs; optional local token | Mandatory bearer token, versioned S3 and matching fixture hashes |
| User-provided Gemini key entered privately in app | Shared provider credential loaded from runtime SecureString |
| Windows DPAPI-encrypted bootstrap cache | Stable production keys in SSM |

Never expose the local Compose stack publicly, copy the laptop database/bootstrap cache to production or use dummy encryption keys to run direct Compose commands. Changing encryption keys can make saved credentials unreadable. Editing SSM MongoDB passwords alone does not rotate initialized database users. Preserve live keys and volumes.

## Run locally

Prerequisites: Windows, PowerShell 7 and Docker Desktop's running Linux engine. From this directory:

```powershell
./start-local.ps1 -ValidateOnly
./start-local.ps1
# After changing DataCheck:
./start-local.ps1 -RebuildDataCheck
```

Open `http://localhost:3080` after startup. The launcher downloads pinned images, supplies the bootstrap environment and generates reversible branding using Node inside the pinned LibreChat image; no host Node is required for branding. The upstream image and persistent volumes are preserved. Recheck overlay paths/layout before changing that image.

Stable keys are encrypted with Windows DPAPI in ignored `.local/bootstrap.clixml`, tied to the Windows user. Do not delete this cache while retaining encrypted chat credentials. Enter local provider credentials privately in the application, never in chat/source/screenshots/logs. A Docker startup failure on this workstation was resolved by restarting the installed Desktop through Windows Explorer; do not factory-reset Docker or delete volumes to repeat setup.

## Model, action and data setup

Follow [agent instructions](actions/AGENT-INSTRUCTIONS.md). Verified settings are Gemini `gemini-3.5-flash-lite`, thinking off, output limit 1024. The student confirmed Gemini API free-tier access on 24 November; no provider invoice was inspected. Keep **exactly one** DataCheck action; duplicates can cause duplicate function declarations. Its four operations list datasets, profile a selected dataset, return findings and list validation rules. Internal schema: `http://datacheck:8000/openapi.json`; action domain: `http://datacheck`; private destination: `datacheck:8000`.

Production [enrollment](docs/PRODUCTION-ENROLLMENT.md) and [action binding](docs/PRODUCTION-ACTION-BINDING.md) use normal private login and preserve ownership/authentication checks. Do not mint impersonation tokens, open public registration or copy local users. Enrollment/binding already succeeded here; do not create duplicate accounts/actions to repeat setup.

Production requires a nonlocal `DATACHECK_ENV`, nonempty `DATACHECK_API_TOKEN`, `DATACHECK_STORAGE=s3` and `DATACHECK_S3_BUCKET`. Exact LF fixture bytes live at `datasets/v2/inventory.csv`, `datasets/v2/shipments.csv` and `datasets/v2/equipment.csv`. Real version IDs and SHA-256 hashes are required; unavailable, changed, unversioned or oversized sources fail closed. Readiness validates all three sources; liveness only proves the process responds. The [data contract](docs/DATA-CONTRACT.md) defines expected findings, numeric bounds, row references and truncation semantics.

The instance role reads `/apicompass/prod/runtime` as SecureString; the loader validates values and passes them through memory/process environment without a persistent secret environment file. Privileged Docker/root access can inspect container configuration, so restrict it. Never print decrypted SSM, expanded Compose/container environments or shell tracing into evidence. See [private secret setup](docs/PRIVATE-SECRET-SETUP.md) and [runtime contract](docs/PRODUCTION-RUNTIME.md).

## Deployment and operations

Use reviewed source/release identifiers and actual stack outputs. Build/check/upload a reviewed release; verify its S3 version and payload hashes on the host. Preserve existing secrets/volumes. The host has operational fixes beyond older bundle manifests; final handoff must record a reconciled release. Successful startup alone does not prove HTTPS, user login or model/tool acceptance.

| Procedure | Source/runbook |
| --- | --- |
| Foundation/compute and deployment gates | [Compute](docs/COMPUTE-DEPLOYMENT.md), [checklist](docs/DEPLOYMENT-CHECKLIST.md), `infra/` |
| Runtime check/start/status/stop | [Production runtime](docs/PRODUCTION-RUNTIME.md), `scripts/start-production.sh` |
| Backup, health and interruption handling | [Operations runbook](docs/OPERATIONS-RUNBOOK.md), [acceptance](docs/OPERATIONS-ACCEPTANCE.md), `scripts/ops_jobs.py` |
| Isolated restore and cleanup | [Recovery evidence](docs/evidence/recovery-incident-2026-11-23.md), `scripts/recovery_stack.py`, `scripts/verify_restore.py` |
| Dashboard, alarms, SNS and audit | [Observability deployment](docs/OBSERVABILITY-DEPLOYMENT.md) |
| Answer telemetry/shipping | [Instrumentation](docs/QUESTION-TELEMETRY.md), [shipping](docs/QUESTION-TELEMETRY-SHIPPING.md) |
| Bounded MongoDB logs | [Database logging](docs/DATABASE-LOGGING.md) |

Production backup runs at UTC 00:15/06:15/12:15/18:15 plus up to one minute jitter; health runs every five minutes. Preserve at least seven days of dumps through the deployed S3 lifecycle policy. Two further timers ship question/database logs. Backup interruption can leave chat stopped: follow the bounded inspection/recovery procedure, and verify timer state after private maintenance pauses. Restore into a fresh labelled isolated target; remove that assessment copy after verification, preserving production.

The approved AWS allowance is US$25. Budget alerts notify; they are not a hard billing cap. Account credits do not remove ongoing resource costs. Do not stop/delete unrelated resources or destroy runtime keys/volumes as assumed cleanup.

## Development checks and evaluation

Python 3.14 was used for Windows development:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Helper/telemetry tests use Node 24; the pinned runtime was verified with Node 24.16.0:

```powershell
node --test tests/test_bind_production_action.cjs tests/test_create_production_user.cjs tests/test_question_telemetry.cjs tests/test_recovery_chat.cjs
```

Python checks cover exact findings, fail-closed authentication/storage, real-server log privacy, SDK-stubbed S3 behavior, release/runtime guards, operations and restore isolation. Node covers private setup/recovery transports and telemetry. These tests are distinct from live cloud acceptance and model quality. The httpx adapter's upstream deprecation warning is not itself a failure.

Smoke-check the running local API through its private container:

```powershell
Get-Content -Raw scripts/smoke.py | docker exec -i apicompass-local-datacheck-1 python -
```

API structured logs omit query values/credentials; default Uvicorn access logging is disabled. This alone is not complete chat-question logging. Deploy and observe the newer source opt-in update before claiming it active. Follow [EVALUATION.md](docs/EVALUATION.md) for fixed prompts, versions, actual answers and student-reviewed verdicts. The scoring script calculates arithmetic over reviewed outcomes; it does not judge correctness independently.

## Submission and remaining personal actions

The twelve-chapter [static report](submission-site/README.md) has a working local preview; public hosting remains pending. [Evidence mapping](docs/SUBMISSION-EVIDENCE-MAP.md), [recording script](docs/RECORDING-SCRIPT.md), [recording checklist](docs/RECORDING-CHECKLIST.md) and [final handoff](docs/SUBMISSION-HANDOFF.md) track the remaining artifacts. The course requires a **5–8-minute** externally hosted presentation embedded in the published website and a repository ZIP **including actual hidden `.git` history** and README. A source-only Git archive does not satisfy that history requirement.

Finish release/source parity, final staged/archive review, matched measurements/cost comparisons and public website acceptance. The [history review](docs/evidence/source-history-review-2026-11-24.md) contextually resolved reported pattern matches; final staged content, included Git metadata/objects, screenshots/video and actual ZIP still need review. Exclude ignored caches, real environment files, credentials, dumps and private assignment/account materials. Instructor history ZIP and public website are separate delivery scopes.

The student must confirm provider tier, review results/contributions and AI disclosure, understand/rehearse the system, personally narrate/record, choose video visibility, sign/date Appendix H and submit through the course channel. No recording, public URL, signature or receipt is claimed. [PROGRESS.md](PROGRESS.md) retains dated checkpoints; [CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md) records weekly work with explicit attribution and preserves historical failures.

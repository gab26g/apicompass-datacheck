# SYSTEM CARD: APICompass with DataCheck

Draft as of November 21, 2026. Local implementation only; replace pending fields with actual evidence before publishing. This follows Appendix C of the SAM10 guidelines v3.5.

## 1. What it does

APICompass lets a user ask about invented inventory, shipment and equipment records in ordinary language. DataCheck applies explicit validation rules, and an external AI model explains the returned findings. The model does not decide which records fail validation.

## 2. Who uses it, and who must not

Intended users: students and reviewers learning to inspect synthetic datasets and operate a small AI application. It is not a production quality-assurance service, a tool for personal records, or a system for decisions about identifiable people. All demo questions and records must remain invented.

## 3. Base system

LibreChat v0.8.8, by the LibreChat project and contributors, from https://github.com/LibreChat-AI/LibreChat. MIT licence; notice and exact image manifest are in THIRD-PARTY-NOTICES.md. LibreChat originally provides a general-purpose multi-provider chat interface, accounts, saved conversations and tools. The project uses an external Gemini API; it does not host or train the model.

## 4. What changed

| Part | Original base | APICompass | Status |
| --- | --- | --- | --- |
| Name and identity | General-purpose LibreChat | APICompass title, welcome, original SVG mark, navy/teal palette and read-only footer | Implemented locally; final website screenshot files remain pending. |
| Data/content | No project-specific records | Three original, 60-row synthetic CSV fixtures and explicit rules | Implemented and tested locally. |
| Domain wording/prompts | General chat | Dataset profiles, row findings, required/duplicate/type/range/category rules; original instructions and conversation starters | Instructions configured; starter copy saved for setup. |
| Interface | Upstream chat/tool UI | Branded read-only data-quality workflow with bounded tools | Desktop/mobile layouts checked; upstream layout and attribution preserved. |
| AWS services | No project AWS integration | Intended private versioned S3, runtime Parameter Store secrets, EC2, CloudWatch and SNS | S3 adapter tested with SDK stubs; live deployment pending. |

## 5. Data

There are 180 invented data rows in three CSVs, with three columns per file. No real patient, student, staff, supplier or customer records are present. Source bytes and fixture versions are tracked by a committed SHA-256 manifest; detailed rules and independently written expected findings are in DATA-CONTRACT.md. These are original project fixtures; their reuse licence has not yet been selected by the student.

Gemini receives the user's synthetic question, agent instructions and the tool results needed for the answer. Provider/account metadata is handled by the base application's provider integration. Never enter real personal records in a prompt. Dataset cells are treated as data, including instruction-like strings.

## 6. How good it is

Initial local evaluation under v1 instructions: 10 of 13 executed cases passed, approximately 76.9%; two deployment-dependent cases were not run. EVALUATION.md and the evidence JSON disclose the exact prompts, reference checks, conversations, verdicts and denominator. Review was assisted by Codex; student review remains pending. scripts/score_evaluation.py calculates the arithmetic from those reviews. Unit/API test success is a separate result, not model answer accuracy.

Observed failures: one complete-report answer stopped with a provider stream parse error, one ambiguous request scanned every dataset instead of clarifying, and one answer counted a duplicate group as one issue rather than two row findings. Later v2/v3 instructions were tested against the failed cases and a new counting question; the four final targeted checks passed. This is not a new full-suite score. The provider stream error's root cause is unconfirmed. Correct refusals were not automatically marked as failures.

## 7. How it is served

Current host: local Windows Docker Desktop. LibreChat, private MongoDB and private DataCheck are separate containers; only chat is published on 127.0.0.1:3080. DataCheck's four operations list datasets, return profiles, return findings and describe rules. Operational liveness/readiness routes are excluded from the model action schema.

Verified local model setting: Gemini 3.5 Flash Lite, thinking off, output limit 1024, with user-provided credentials entered directly in the application. Current provider pricing/quota tier has not been verified. If a source is unavailable, the API returns 503 rather than clean findings. If the model is unavailable, the UI must report the error; there is no offline model fallback.

AWS URL, instance type, region, secure runtime secret path and deployment date: pending. Do not publish the local Compose stack as a production deployment.

## 8. Limitations and risks

Fixed datasets only; no uploads, automatic repairs or write operations. Numeric fields intentionally accept only whole integers; shipment weights are whole kilograms. Findings are bounded, and truncated samples must be labelled. Numeric summaries include out-of-range but parseable integers. The model may select an incorrect tool, misread results, omit a caveat or invent a cause; reviewers must compare its explanation with returned values, versions and request IDs.

S3 versioning and exact fixture hashes are required in production. Changing a fixture requires an intentional new version, manifest and reviewed expected results; silently changing content is rejected. Authentication and source validation are tested in code; live IAM, network, TLS and database security still require deployment checks.

## 9. Operational summary

Local checks: liveness, readiness validating every fixture, bounded responses, token checks and sanitized correlated API logs. Uvicorn access logs are disabled to prevent query strings entering logs. Full question logging, dashboard, six tested alarms, received email, scheduled jobs, real backup restore with RPO/RTO, cost evidence and a controlled AWS incident remain pending.

Do not state availability, recovery time, production security, cost savings or assistant accuracy until measured in the deployed system. Intended scope remains one AWS region and one MongoDB database.

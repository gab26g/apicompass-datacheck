# Production integration evidence — 23 November 2026

## November 24 destination and individual-access follow-up

The normal MFA-protected `apicompass-student` console session opened the actual question events and the runtime `database-2026-11-23` stream. The database view loaded 202 events, including 23 November 16:38:29 UTC NETWORK/database_connection and ACCESS/database_authentication envelopes. Only fixed metadata fields were visible; raw messages, attributes, documents and credentials are excluded. Screenshot: [actual database destination](cloud-database-logs-2026-11-24.jpg). This loaded view is distinct from the historical 730-event shipper delivery total below.

All three project log groups (runtime, questions and jobs) showed two-week retention in the group listing. Jobs destination events were not inspected in this follow-up. The student also opened the populated dashboard and a normal SSM shell through EC2 Connect's Session Manager link, with existing permissions. The general Session Manager listing required an ungranted metadata-list action, so the direct permitted route was used without broadening IAM.

At 2026-11-23T16:47:00Z (24 November Manila), all four production containers were up, health-bearing services healthy, all four operational timers active, and the last health service result was success/exit zero. These are point-in-time observations, not continuous availability statistics. The following sections retain their original historical boundaries.

This records observed AWS application behavior, not local test output.

## Private action binding

The user completed normal hidden-input application login. The helper reported exactly one action with four operations. An independent read-only database check confirmed one action reference, one saved action and these tools: `list_datasets`, `get_dataset_profile`, `get_dataset_issues`, `list_validation_rules` (each stored with the `_action_datacheck` suffix). The backup timer was then confirmed active.

The initial helper failed after login because pinned LibreChat agent routes require a recognized browser user agent. The fixed identified client preserves bearer authentication, ownership checks and single-action guards. A transport regression failed before the correction; all 15 binding tests passed afterward. The mounted helper SHA256 was `6e62a561f41076126bedc5519865e9ad95f710477f097743a16f60810a270a1a`.

## First cloud question — correct findings

Prompt: “Inspect shipments. Give the total rows, issue_count and affected_row_count, list each finding, and include dataset_version, ruleset_version and request_id.”

The actual tool result was generated at `2026-11-23T11:16:41.648977+00:00` (19:16 Manila). The browser showed a real DataCheck tool call followed by an answer with:

- 60 rows; 7 individual findings; 7 affected rows.
- Both duplicate shipment-ID rows counted separately.
- The remaining findings: weight 0 outside range, nonnumeric weight `heavy`, missing shipment ID, invalid status `lost`, and weight 1001 outside range.
- Dataset `shipments-v2`; ruleset `shipments-rules-v2`.
- Request ID `a0418fb3-ba8e-420c-bcc6-92c4ce6f7762` matching the tool result.
- S3 source SHA256 `b8aef8c7a1e41d19074cef1da3cf2a48fbd3046b4f5311d5c58534aa0223aa18`, nonempty object version `rkoA9ZMWh3cM6VHKgo9z_HqGUQ2TBRBJ`.

Screenshot: [cloud answer](cloud-shipments-answer-2026-11-23.jpg). The tool's displayed 0.1 seconds is tool-call duration, not full model response latency.

## Second cloud question — unsupported cause

Prompt: “Why were these shipments delayed, and which supplier caused the delays?”

The browser showed another DataCheck call. The answer correctly identified only `shipment_id`, `weight_kg` and `status` as available columns and explained that supplier and delay information is absent. It did not invent a supplier or cause.

## Monitoring gap found during acceptance

These first two successful answers produced no question-attempt events. They must not be presented as monitored successes. Source investigation found pinned `createPayload.ts` appends `/agents` to the saved-agent admission URL, while the hook watched only the base path.

A new admission-to-final-stream regression failed with zero events before the fix; all 17 telemetry tests passed after accepting the exact saved-agent path as well. The corrected hook SHA256 is `4dfa7b52f38b6f2d86026e225b9992677817d1b8cbcf0188951d57be5965b83f`. It was installed and chat restarted; the service became healthy.

The CloudWatch console then independently showed these real, sanitized events in `/apicompass/prod/questions`, stream `question-attempts-2026-11-23`, with two-week retention:

| Synthetic question | Terminal event UTC | Question ID | Outcome | Observed duration |
| --- | --- | --- | --- | --- |
| Fresh shipments issue check | 2026-11-23T11:22:47.275Z | 5ae05a27-dc99-4d94-9892-277345cf2eb1 | succeeded | 3479.704 ms |
| Fresh-context “Check my data.” | 2026-11-23T11:23:10.397Z | 5fd9b525-521e-42b4-84ba-ac1432f4ff52 | succeeded | 1834.423 ms |

The fresh shipments answer again reported 60/7/7 with new **DataCheck API request ID** `03c7e96d-663e-4dcf-bd12-dce7e8eb39c9`. API request IDs and question-attempt IDs are separate identifiers. The fresh-context answer called the catalog, listed inventory/shipments/equipment and asked which to inspect. Synthetic prompts are documented here; raw prompts, credentials and dataset values are not sent to the telemetry log group. Screenshot: [reviewed replacement CloudWatch question capture](cloud-question-logs-2026-11-24.jpg).

Database log delivery initially failed because routine five-minute traffic exceeded the 500-event cold-start cap. A bounded read-only probe counted 865 envelopes, 729 unique, about109717 batch bytes. After a failing 1000-envelope regression, the cap became2000 with a900KiB batch-byte guard; all10 database shipper tests passed. The actual service then reported730 sanitized events delivered, Result=success, ExecMainStatus=0. CloudWatch database-stream readback remains a separate pending check.

These are targeted cloud cases, not a complete evaluation score. Restore/login/tool proof, alarm-email receipt and final submission acceptance remain separate requirements.

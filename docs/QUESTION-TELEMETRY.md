# Question telemetry — implemented, production integration pending

`scripts/question-telemetry.cjs` is an opt-in Node preload for the pinned LibreChat 0.8.8 HTTP server. It observes the public `http.Server` request event and wraps the selected response's public `write`/`end` methods. It forwards original arguments, callbacks, return values and streaming chunks immediately. It never reads the request body, authorization headers, cookies, raw headers or incoming client correlation IDs. It has no dependency and makes no AWS calls.

## Source-derived scope

Inspected the ignored upstream checkout at commit `e8f3be08623663d4ad7f7241e693c94469b63bb0`:

- `api/server/index.js` mounts `/api/agents`.
- `api/server/routes/agents/index.js` mounts the chat router under `/chat` and exposes `GET /chat/stream/:streamId`. Its stream writer emits `event: message` or `event: error`, each with JSON `data` followed by a blank line.
- `api/server/routes/agents/chat.js` maps `POST /` to the agent request controller.
- `api/server/controllers/agents/request.js:sendGenerationStarted` returns HTTP 200 JSON `{status:'started', streamId, generationCreatedAt}` **before the answer completes**. Terminal completion later publishes `{final:true, responseMessage:...}`; unfinished responses carry `unfinished:true`.
- `packages/api/src/utils/events.ts` and `api/server/middleware/error.js` also describe typed SSE errors, including errors after HTTP headers have already been sent.

The hook tracks `POST /api/agents/chat` (optional trailing slash) for the saved DataCheck agent. It correlates the small admission response internally with the generation-scoped SSE subscription `GET /api/agents/chat/stream/:streamId?generationCreatedAt=...`. It measures from question POST arrival to observed terminal response/transport completion. It also recognizes direct SSE on that same POST route if the pinned runtime takes that path. Admission HTTP 200 alone never counts as success.

This deliberately excludes ephemeral endpoint suffixes, resume/control/abort requests, compatibility APIs, queued/background generations and model-only `/api/ask` routes. Check the actual production browser request route and pinned image source before claiming coverage. No production runtime integration or real provider call has yet been verified by this implementation.

## Event contract

Each observed POST attempt emits at most one pure JSON line to stdout, with exactly these fields. The application logger is bypassed; there is no logger prefix.

| Field | Value |
| --- | --- |
| `event` | `question_attempt` |
| `schema_version` | `1` |
| `request_id` | Locally generated UUID, also returned in the admission response header `X-APICompass-Question-ID` |
| `app_version` | `APICOMPASS_VERSION` if it matches `[A-Za-z0-9._-]{1,64}`, otherwise fixed `apicompass-runtime-v2` |
| `librechat_version` | Fixed `0.8.8` |
| `outcome` | `succeeded`, `failed`, or `aborted` |
| `reason` | One of the internal reason values below |
| `http_status` | Integer 0–599; 0 means no terminal HTTP status was available |
| `duration_ms` | Finite 0–300000, using a monotonic clock |
| `timestamp` | Completion timestamp in UTC ISO 8601 format |

Reason values: `success`, `provider_error`, `uninspectable_stream`, `unfinished`, `missing_final`, `capacity_exceeded`, `observation_timeout`, `http_error`, `invalid_start_response`, `duplicate_start`, `disconnected`, `aborted`, `shutdown`. `success` maps to `succeeded`; `disconnected`/`aborted` map to `aborted`; all others map to `failed`.

Success requires a parsed `final:true` event containing a nonempty text answer in `responseMessage`, without any observed typed error or unfinished/reconciliation marker. A typed `event:error` or error-marked message fails even under HTTP 200 and even if a final marker also appears. A clean transport finish without the final answer is a failure. A premature transport close counts as aborted once; replays cannot count the attempt again. Here success means a final answer was observed at the HTTP transport, not that the answer's data interpretation is correct or that the human read it. Assistant evaluation remains separate.

The host shipper must validate/allowlist these fields into `/apicompass/prod/questions` and publish `AnswerSuccess` (`1` only for `succeeded`) and `AnswerFailure` (`1` for both `failed` and `aborted`) in namespace `APICompass`, dimension `Project=APICompass`, unit `Count`. Do not also configure metric extraction from the same events. Emitting stdout is not evidence of CloudWatch delivery, metric publication or alarm email. That pipeline is a separate integration gate.

## Bounds and privacy

The hook retains at most 128 active attempts, with five-minute observation expiry. It retains at most 8 KiB of the admission JSON and at most 64 KiB of one SSE frame, never the full response stream. SSE data is inspected transiently in memory, then discarded. Oversized, truncated, malformed or encoded/uninspectable frames fail conservatively; they cannot be counted as successful. UTF-8 and JSON chunk boundaries and CRLF framing are handled incrementally. Stream identifiers and generation epochs are used only as bounded in-memory correlation keys and never logged.

No prompt, answer, error description, request/response body, query string, header value, API key, user ID, conversation ID or stream ID is included in telemetry. A question hash is omitted because this hook deliberately does not inspect request-body fields. Map the opaque question request ID to separately recorded fixed evaluation-case evidence; the assignment's proof of which synthetic question was asked must come from that reviewed evidence, not a raw-question production log.

The registry is process-local and intended for this single chat process. Restart/termination loses unfinished attempts; SIGKILL/host failure cannot guarantee final telemetry. A missing SSE subscriber or an observation longer than five minutes becomes `failed/observation_timeout`, not a claim that the provider failed. Rejected/mismatched stream subscriptions do not cancel another attempt; an unresolved accepted POST later times out. If telemetry output itself fails, the hook preserves chat behavior and cannot guarantee an event. Compare attempted requests with received events during integration; do not promise exactly-once delivery across process or shipper failures.

## Opt-in production patch for parent review

No Compose file was changed. Add the following under the existing `chat` service only after the parent accepts the integration:

```yaml
environment:
  NODE_OPTIONS: "--require=/app/question-telemetry.cjs"
  APICOMPASS_QUESTION_TELEMETRY: "1"
  APICOMPASS_VERSION: "apicompass-runtime-v2"
volumes:
  - ./scripts/question-telemetry.cjs:/app/question-telemetry.cjs:ro
```

Merge these entries into the existing environment/volumes rather than replacing them. Inspect the pinned image's runtime `NODE_OPTIONS` before activation; preserve any required existing Node options. The upstream Dockerfiles' frontend heap option belongs to the build stage, but actual image configuration remains the authority. Rollback removes these opt-in entries and recreates only production chat through the validated runtime loader. No local service restart or cloud deployment was performed for this task.

## Verification

Run `node --test tests/test_question_telemetry.cjs` and `node --check scripts/question-telemetry.cjs`. The focused tests cover HTTP-200 provider errors, final-answer success, missing/unfinished final frames, abort/disconnect deduplication, both protocol stages, chunk splits/UTF-8/CRLF, oversized/truncated frames, no nonchat events, private-field access rejection, output privacy, fixed event schema, bounded capacity/timeouts, preserved callbacks/backpressure, and the public HTTP request-event hook.

Before enabling the shipper/timer, inspect the pinned running image route/protocol and Node version, enable the reviewed preload in production, verify one known successful question and one controlled failed provider/stream attempt, compare their opaque IDs and end-to-end durations, confirm exactly one sanitized line per attempt, then verify questions-log readback and success/failure metric values. Retain the baseline before enabling this change. Node tests do not establish any of those cloud outcomes.

References: [Node HTTP request, response write/end and finish/close events](https://nodejs.org/api/http.html), [Node preload with --require](https://nodejs.org/api/cli.html#-r---require-module).

# Production enrollment — reviewed source, not executed

Keep `ALLOW_REGISTRATION=false`. Create a fresh production user privately, then configure the DataCheck agent through LibreChat's authenticated builder/API. This procedure creates application access only; it creates no AWS IAM user, external account, email notification or new infrastructure.

## Source and image gate

Inspected the ignored LibreChat checkout at commit `e8f3be08623663d4ad7f7241e693c94469b63bb0`, whose package version is `v0.8.8`. Before execution, compare the actual pinned image's relevant files and exports to this checkout. Image tag/digest alone does not prove a helper interface matches the checked source. Parent owns this image/runtime check and all live actions.

The standard `npm run create-user` delegates to `config/create-user.js`. Its password prompt uses ordinary **visible** `askQuestion`; leaving it blank generates and prints a `Math.random` password. Do not give the user that unwrapped command or pass a password as an argument. `config/helpers.js` exports the existing `askSilentQuestion` for hidden terminal entry. `AuthService.registerUser` also logs the password-containing input on validation failure, so hiding only the terminal prompt is insufficient.

`scripts/create_production_user.cjs` is a small one-off wrapper around that same upstream CLI. It replaces only the password question with the upstream silent helper, adds hidden confirmation, rejects blank or 12–128-character violations, and refuses a nonempty user collection before prompting. It prevalidates with the actual upstream `registerSchema` before invoking registration and rechecks that no account exists. The helper process mutes the upstream logger and redacts `console.error` so registration/connection errors cannot expose submitted passwords or the Mongo URI. It does not modify the running server or save a password file.

`AuthService.registerUser` gives the first unscoped, single-tenant account the **LibreChat application ADMIN** role. Disclose this to the user before they start; run only after parent review of this access change. The account's email/name/username are chosen by the user, with no budget-notification address or other identity reused as a default. The upstream CLI derives default name/username from the user-entered email; the user can supply different values. Use a name of 3–80 characters and username of 2–80 characters accepted by the upstream validator. Verification is forced true through the trusted CLI argument, preventing verification-email delivery. This is a local administrative enrollment decision, not proof that the email mailbox was verified.

## Private user-operated terminal step

The parent operator resolves exactly one **production** chat container by labels `com.docker.compose.project=apicompass-prod` and `com.docker.compose.service=chat`. Confirm it is the pinned image and its working directory/source layout is `/app`. From `/opt/apicompass`, copy the reviewed wrapper into that container; no Compose edit or restart is needed:

```sh
docker cp scripts/create_production_user.cjs PRODUCTION_CHAT_CONTAINER_ID:/tmp/create_production_user.cjs
```

Then hand the Session Manager terminal to the user **before** running the following command. The user runs it directly, with no account/password arguments, shell tracing, terminal transcript capture or agent observation of their private entry:

```sh
docker exec -it --workdir /app PRODUCTION_CHAT_CONTAINER_ID node /tmp/create_production_user.cjs
```

Replace only the nonsecret container-ID placeholder before handoff. The wrapper rejects missing interactive TTYs and extra arguments. The user enters their own email, name and username, then enters and repeats their application password at the two **hidden** prompts. No characters should appear for either password prompt. Never leave a password blank. If the helper reports validation failure, it does not print the offending input; inspect account existence privately before rerunning. Do not run concurrent enrollment sessions.

After `User created successfully!`, the user clears the terminal before returning control:

```sh
printf '\033[2J\033[3J\033[H'
```

This clears the visible terminal/scrollback where supported; it is not deletion of any separately configured Session Manager recording. The parent must not inspect the private identity-entry output. Passwords remain hidden throughout. The user signs in to the production HTTPS URL privately, then hands back the authenticated builder for the nonsecret setup below. Retain only a sanitized user-created/login-success observation; do not export account records or password hashes. If there is already any user, this first-account wrapper refuses; do not remove users or reset credentials to make it pass.

## Agent setup through authenticated application routes

Use the builder so LibreChat applies its own validation, tool filtering, version history and owner permissions. Source `api/server/controllers/agents/v1.js` creates agents through `db.createAgent` and grants both agent-owner and remote-agent-owner access roles. Source `api/server/routes/agents/actions.js` validates the spec/domain, encrypts action credentials, derives action/tool names, versions the agent and saves the action. Raw Mongo inserts or a direct `Agent.create`/`Action.create` script bypass these invariants and are not proposed.

Configure a private agent owned by the newly enrolled user:

- Name: `DataCheck` (or the existing APICompass DataCheck name).
- Provider/model: Google / `gemini-3.5-flash-lite`; thinking off; maximum output 1024, matching the previously verified local setting. The production server already supplies the shared `GOOGLE_KEY`; do not ask the user to paste it again.
- Instructions: paste **all text from `actions/instructions-v3.txt` exactly**, preserving the scope-first, causal-question routing and duplicate-counting requirements. Do not use the surrounding setup guide as instructions.
- Enable only the intended DataCheck action. No file/code/browsing/MCP tools or extra copied action are needed.
- Use the three conversation starters in `actions/AGENT-INSTRUCTIONS.md` if desired; these are nonsecret.

Import `actions/datacheck.production.openapi.json` into one action. It declares OpenAPI 3.1, API version 0.2.0, private server `http://datacheck:8000`, and exactly these four operations: `list_datasets`, `get_dataset_profile`, `get_dataset_issues`, `list_validation_rules`. The editor derives domain `http://datacheck` by stripping the port; the production allowlist separately permits `datacheck:8000`. Keep that private destination; do not replace it with the public application URL. Select **API key / Bearer**, represented by `auth.type='service_http'`, `auth.authorization_type='bearer'`; the API key value is the token only, without an added `Bearer ` prefix. The request builder supplies that prefix.

The token must come privately from the production runtime parameter's `DATACHECK_API_TOKEN`, and must never be displayed in chat, shell arguments, arbitrary logs, screenshots or evidence. **Token binding remains a separate private step.** Do not inspect/decrypt any existing saved provider credential. Do not import the local database/encrypted bootstrap cache or regenerate production encryption keys. The frontend action editor calls `logger.log('actions', 'saving action', authFormData)` in this checkout, so do not assume using its visible form is sufficient to prevent secret logging under all client debug settings.

## Minimal supported API proposal for private token binding

No `configure_agent.cjs` mutation helper was added. Prefer a later small, reviewed backend helper that calls the real authenticated HTTP route rather than writing models directly. Source-derived request contract:

```text
POST /api/agents/actions/{agent_id}
Authorization: Bearer <short-lived authorized application token, memory only>
Content-Type: application/json

{
  action_id: <existing action ID when updating>,
  functions: <upstream parser-derived four function tools>,
  metadata: {
    domain: 'http://datacheck',
    raw_spec: <exact production OpenAPI file text>,
    api_key: <DATACHECK_API_TOKEN from runtime memory>,
    auth: { type: 'service_http', authorization_type: 'bearer' }
  }
}
```

This is a contract illustration, not a JSON document to paste with placeholders. The upstream frontend obtains `functions` via `validateAndParseOpenAPISpec(rawSpec)` then `openapiToFunction(validation.spec).functionSignatures.map(f => f.toObjectTool())`; do not hand-invent function definitions. The backend calls `encryptMetadata`, using `encryptSensitiveValue` under the existing production encryption keys. It strips `api_key` from the response. Reading/decrypting saved actions is not required to bind the new token.

A safe helper must accept only bounded opaque owner/agent/action IDs, verify the owner/agent/action association, parse exactly the four expected operation names and private URL, reject additional actions/tools, fetch the runtime token without printing it, and send only to `http://127.0.0.1:3080` inside the selected chat container. It must reuse an explicitly authorized application session or a reviewed short-lived token flow, require parent review before granting application access, and never print auth headers, response bodies or raw errors. The source provides `db.generateToken(user, expiresInMilliseconds)`, but minting an owner session is an application impersonation capability and has **not** been authorized/executed merely by this proposal. Confirm the actual pinned-image authentication strategy before implementing that option. No AWS IAM change is needed.

Update the existing action by its exact `action_id` instead of appending a second copy. Before any rerun, inspect sanitized action/tool counts; previous local duplication produced duplicate function declarations and provider failure. This is why a blind create script is inappropriate.

## Acceptance and limits

Verify public registration remains disabled; the user's private login succeeds; the agent contains the exact v3 instructions and intended model settings; exactly one four-operation action is attached; the bearer is stored through upstream encryption; missing/wrong DataCheck tokens fail; and a real model-to-tool shipments answer reports version v2, 60 rows, seven issues, seven affected rows, no truncation and the actual request ID. A successful account creation alone does not prove the provider or action works.

Five focused Node tests pass for hidden input routing, blank/short/oversized/mismatched password rejection, existing-account refusal before prompting, validation before the upstream logging path, and trusted verified-email registration. These are mocked/offline guard tests. The actual pinned-image interfaces, interactive Session Manager behavior, account creation, application-role grant, login and token binding have not been exercised by this task.

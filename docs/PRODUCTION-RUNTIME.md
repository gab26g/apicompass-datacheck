# Production runtime — prepared, not deployed

The reviewed runtime is a separate `apicompass-prod` Compose project with four services: `chat`, `mongodb`, `datacheck`, `proxy`. Only Caddy publishes TCP 80/443. MongoDB and DataCheck have no host ports. Compose-managed production volumes are separate from `apicompass-local`; never copy the laptop database or its Windows DPAPI bootstrap cache to production.

## Host and commands

Install the application release at `/opt/apicompass` with Docker and Compose available, plus boto3 in `/opt/apicompass-tools`. The host must have the existing foundation instance role, outbound AWS/registry/provider access, IMDSv2 required with response hop limit **2**, and a hostname resolving to its public IP. Upload the three exact, versioned `datasets/v2/*.csv` fixtures to the private foundation bucket before starting; DataCheck readiness verifies all three hashes and real S3 version IDs. No static AWS access keys are required. The startup loader uses boto3's default credential chain; keep credential files and AWS credential environment variables off this host so the instance role is used.

Set only nonsecret host configuration in the operator session (substitute the actual outputs):

```bash
cd /opt/apicompass
export APICOMPASS_HOSTNAME='PUBLIC-IP.sslip.io'
export DATACHECK_S3_BUCKET='FOUNDATION-BUCKET-NAME'
export AWS_REGION='ap-southeast-1'
export APICOMPASS_PYTHON='/opt/apicompass-tools/bin/python'
bash scripts/start-production.sh check
bash scripts/start-production.sh up
bash scripts/start-production.sh status
bash scripts/start-production.sh stop
```

`check` validates SSM, input and Compose syntax without starting services. `up` creates branding from the exact pinned LibreChat image, builds DataCheck, and waits up to 180 seconds for healthy services. Its success is container readiness, **not** evidence of a valid public TLS certificate, user sign-in, correct Gemini response or actual agent-to-tool authentication. `stop` gracefully stops production services with a 60-second timeout and retains volumes/certificate state. `status` prints service metadata, never expanded configuration. Every action requires the runtime parameter. There is deliberately no destructive volume-removal command.

For operations Python code, import `load_environment`, `compose_command` and `run_compose` from `scripts/runtime_secrets.py`. `load_environment()` returns validated process environment; `run_compose(args, env)` captures child output and returns the completed process or a sanitized error. Never print the environment, the SSM response, or arbitrary captured stdout/stderr. `compose_command` fixes the production project/file and disables automatic `.env` loading. Do not run `docker compose config` without `--quiet`, `docker inspect` environment output, shell tracing, `env`, or process-environment dumps in shared evidence.

## SecureString contract

Provision exactly one **SecureString** `/apicompass/prod/runtime` in Singapore through a private authorized operator flow. Its value is a JSON object containing exactly these eight string fields:

| Field | Requirement |
| --- | --- |
| `JWT_SECRET` | Independently generated random secret, at least 32 characters |
| `JWT_REFRESH_SECRET` | Independently generated random secret, at least 32 characters |
| `CREDS_KEY` | 32 random bytes encoded as exactly 64 hexadecimal characters |
| `CREDS_IV` | 16 random bytes encoded as exactly 32 hexadecimal characters |
| `MONGO_ROOT_PASSWORD` | Independent random password, at least 32 characters |
| `MONGO_APP_PASSWORD` | Independent random password, at least 32 characters |
| `DATACHECK_API_TOKEN` | Independent random bearer token, at least 32 characters |
| `GOOGLE_KEY` | Real shared production Gemini API key; `user_provided` is rejected |

Use hexadecimal or URL-safe random strings for generated secrets. No value may contain whitespace/control characters or exceed 4096 characters; the complete JSON must also fit the selected SSM parameter tier. Missing/extra/duplicate fields, wrong type, invalid key sizes, reused security keys, placeholders, failed AWS reads and a non-SecureString parameter all fail closed before any service starts. SDK error payloads and Compose output are suppressed on failures. The MongoDB URI percent-encodes the app password and authenticates against `APICompass`.

The loader reads this one parameter with `WithDecryption=True`, holds it in process memory and passes the environment to Compose. It creates no `secrets.env`, secret JSON, command-line secret arguments or persistent secret configuration file. Docker necessarily stores configured container environment in its privileged runtime state; restrict Docker/root/Session Manager access accordingly. MongoDB gets `/run` as a mode-0700 tmpfs for operations that need a temporary mode-0600 dump config; remove that file immediately after use. It contains no secret file during normal startup.

Keep these production values stable for the life of the fresh database. Editing the SSM MongoDB passwords does **not** rotate existing users: the official image initializes users only when its data volume is empty. Changing `CREDS_KEY`/`CREDS_IV` without a migration makes stored tool/provider credentials unreadable. Plan and verify explicit rotation/restore procedures before any such change.

## Authentication and application setup

MongoDB 8.0.20 runs with authentication, a separate `root` administrator and `apicompass` user scoped to `readWrite` on `APICompass`. The official initialization script reads the app password from the container environment, not embedded source or shell arguments. Health checks authenticate as the app user, so an incomplete or mismatched initialization fails readiness. This is standalone MongoDB; backups must follow the separate quiesced-chat procedure rather than claim oplog-based consistency.

DataCheck is mandatory-token, production-mode and S3-only. Its health check authenticates using the container environment without putting the token value in argv. Do not create a Caddy route for DataCheck or expose port 8000/27017. App action setup uses the private action domain `http://datacheck`, allowed address `datacheck:8000`, and exactly one action. Configure the bearer token privately in LibreChat's action authentication; **the token is not automatically copied into the fresh LibreChat database**.

Public registration and social login are disabled. Provision the intended production user through LibreChat's reviewed administration workflow in a private Session Manager session, then verify login. Do not temporarily open public registration or clone the local user database to bypass this step. Initial account/agent enrollment is still pending.

`GOOGLE_KEY` is a shared server key, rather than a user-supplied key prompt. Checked the bundled upstream sources: `packages/api/src/endpoints/google/initialize.ts` reads the environment key and only selects the per-user flow for the literal `user_provided`; `packages/api/src/endpoints/models.ts:getGoogleModels()` accepts `GOOGLE_MODELS`. The production list and title model are limited to `gemini-3.5-flash-lite`, matching the previously verified local model. Availability and the new production key still require a real production provider call. Recreate the v3 DataCheck agent with thinking off and output limit 1024; preserve exactly one action and capture fresh cloud evidence.

## HTTPS and verification gates

Caddy 2.11.9 Alpine uses the supplied public hostname, automatic HTTPS, persistent certificate state and reverse proxies only to `chat:3080`; LibreChat trusts one proxy. The free DNS hostname and CA issuance are external dependencies. Caddy access logs are disabled to avoid query/conversation leakage. Docker logs are bounded at three 10 MiB files per service; this does not replace the separate CloudWatch shipping/retention work.

Verify on the actual host: successful instance-role SSM read; S3 readiness with version/hash metadata for every dataset; app-user authentication and rejected unauthenticated Mongo access; rejected missing/incorrect DataCheck tokens; no published ports other than 80/443; valid trusted HTTPS with HTTP redirect; private account sign-in; one Gemini agent/tool answer containing the expected dataset counts/request ID; bounded logs without credential values. These cloud gates have **not** been executed by this implementation.

Offline checks completed November 22: ten focused runtime-loader unit tests passed under `.venv` Python; Docker Compose 5.4.0 accepted `config --quiet` using synthetic test-only values. No production container was started and no AWS resource was changed. The Caddy image/config and initial Mongo initialization still need real host runtime validation.

References: [Docker configs content](https://docs.docker.com/reference/compose-file/configs/), [Compose interpolation and env-file behavior](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/), [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https), [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [official Caddy image tags](https://hub.docker.com/_/caddy).

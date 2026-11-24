# Operations acceptance on the approved production host

Prepared November 23, 2026. This is a command checklist, not an execution record.
Run only in the approved Linux host's private operator session. No commands in
this document were executed against AWS or live containers during this audit.
Do not paste secrets, shell environment dumps, expanded Compose configuration,
Mongo documents or arbitrary child stderr into evidence.

## Verified source contract and outstanding gates

- Project `apicompass-prod`; service labels `chat`, `mongodb`, `datacheck`.
- `/opt/apicompass-tools/bin/python` matches bootstrap and both service units.
  Jobs need boto3, not the complete development dependency set.
- Mongo `/run` is tmpfs. Dump password uses stdin and a 0600 temporary config.
  Chat is briefly stopped and restarted only if originally running. Remote GNU
  timeout is 25 minutes plus five seconds; host deadline is 26 minutes.
- No fsync lock or unsupported standalone `--oplog` remains. This is a quiesced
  logical backup. TTL/direct-writer changes prevent an unverified atomic
  point-in-time claim. Test actual restored known state before accepting recovery.
- Restore atomically claims a fresh container name and anonymous volume. It has
  `--network none`, no host ports and Mongo loopback binding. Never connect
  production chat to it.
- Metrics use namespace `APICompass`, dimension `Project=APICompass`.
  Missing backup omits `BackupAgeHours` and fails health. Source health rejects
  age above eight hours; the dashboard retains the age graph and HealthFailure
  covers freshness failures. AnswerFailure now occupies the sixth alarm slot.
  Source disk health fails at 85% or more; template alarm is strictly above 85%.

Fresh offline audit: **24 tests passed**, from
`python -m unittest tests.test_ops tests.test_runtime_secrets` (14 operations,
10 runtime). These are mocked/offline tests, not live job evidence.
`systemd-analyze` is unavailable on the Windows authoring machine and WSL
inventory returned access denied. Linux unit verification remains mandatory;
no new image or package was installed to imitate it.

## 1. Prepare known state and install without enabling timers

First verify HTTPS, sign in to the intended production account, preserve a
synthetic conversation with a distinctive harmless marker, and verify exactly
one DataCheck action gives shipments-v2, 60 rows, seven issues and seven affected
rows. Record UTC time, synthetic marker and sanitized request ID. Do not create
new app messages between this baseline and its backup. Retain runtime encryption
keys in SSM; do not export them to evidence.

The following commands assume a root shell (`sudo -i`) and application already
deployed. Substitute only the nonsecret bucket output in `ops.env` beforehand.

```sh
cd /opt/apicompass
test -x /opt/apicompass-tools/bin/python
test -f /etc/apicompass/ops.env
stat -c '%a %U %n' /etc/apicompass/ops.env
# Required: root owner, mode 600, only nonsecret AWS_REGION,
# DATACHECK_S3_BUCKET and APICOMPASS_DISK_PATH settings.
df -h / /tmp
docker ps --format '{{.ID}} {{.Names}} {{.Status}}'
cp infra/systemd/apicompass-* /etc/systemd/system/
systemd-analyze verify /etc/systemd/system/apicompass-backup.service \
  /etc/systemd/system/apicompass-health.service \
  /etc/systemd/system/apicompass-backup.timer \
  /etc/systemd/system/apicompass-health.timer
systemd-analyze calendar '*-*-* 00,06,12,18:15:00 UTC'
systemd-analyze calendar '*-*-* *:00/5:00 UTC'
systemctl daemon-reload
```

Resolve exactly one running Mongo container and record only collection counts:

```sh
mongo_id=$(docker ps -q --filter label=com.docker.compose.project=apicompass-prod \
  --filter label=com.docker.compose.service=mongodb)
test -n "$mongo_id"
test "$(printf '%s\n' "$mongo_id" | wc -l)" -eq 1
docker exec "$mongo_id" mongosh --quiet --eval \
  'const a=db.getSiblingDB("APICompass"); if(!a.auth("apicompass",process.env.MONGO_APP_PASSWORD))quit(1); print(JSON.stringify({users:a.users.countDocuments({}),conversations:a.conversations.countDocuments({}),agents:a.agents.countDocuments({})}));'
```

Record expected counts privately. Counts alone do not prove the selected
conversation/action or login survived; the final manual recovery gate remains.
Review TTL indexes before making any consistency claim; avoid dumping full
documents or credentials merely to establish a baseline.

## 2. First manual backup and health

These commands run real future jobs and cause brief planned chat downtime.
The first backup must precede a successful freshness-aware health invocation.

```sh
systemctl start apicompass-backup.service
systemctl show apicompass-backup.service -p Result -p ExecMainStatus
journalctl -u apicompass-backup.service -n 20 -o cat --no-pager
systemctl start apicompass-health.service
systemctl show apicompass-health.service -p Result -p ExecMainStatus
journalctl -u apicompass-health.service -n 20 -o cat --no-pager
docker ps --format '{{.Names}} {{.Status}}'
# Confirm the credential file is absent; do not cat it:
docker exec "$mongo_id" sh -c 'test ! -e /run/apicompass-backup.yml'
```

Require Result=success, ExecMainStatus=0 and one sanitized succeeded event for
each job. Recheck HTTPS login and the known DataCheck answer after chat restart.
The backup event contains a unique `backup_key` and `archive_sha256`; it does
**not** contain VersionId. Resolve that key's actual version through a privileged
operator's S3 console or SDK read. Do not invent a version or confuse the event
UUID with S3 VersionId. Record key, version, length/hash, timestamps and exit
status privately. Backup implementation already HEAD-checks the exact uploaded
version's length/hash before returning success.

Use the operator's CloudWatch access to independently read back all five metrics
with the exact namespace/dimension above. The runtime instance role intentionally
has PutMetricData, not GetMetricData/GetMetricStatistics; do not broaden it just
to make an acceptance command work. Before enabling alerts, confirm SNS email
subscription and actual notification receipt. No log shipping is implemented
by these units; sanitized journald output is not CloudWatch Logs delivery proof.

## 3. Two real unattended runs of each timer

Only after the manual jobs pass:

```sh
systemctl enable --now apicompass-backup.timer apicompass-health.timer
systemctl list-timers 'apicompass-*' --all
systemctl show apicompass-backup.timer apicompass-health.timer \
  -p LastTriggerUSec -p NextElapseUSecRealtime
```

Keep the host running across **two scheduled backup firings**, normally six
hours apart, and at least two scheduled health firings, five minutes apart.
Manual `systemctl start` calls and Persistent catch-up firings do not replace two
observed regularly scheduled runs. After the second backup:

```sh
journalctl -u apicompass-backup.service --since '14 hours ago' -o cat --no-pager
journalctl -u apicompass-health.service --since '30 minutes ago' -o cat --no-pager
systemctl list-timers 'apicompass-*' --all
```

For each of the two runs record timer trigger UTC time, service exit status,
sanitized request ID, S3 key/version for backups and metric readback. Each backup
must have a distinct key/version. Keep failed attempts; do not silently replace
them with later successes in the report. If time does not permit the interval,
leave the unattended-run gate pending.

### Optional disclosed assessment schedule

Original WS-E says "Each automation has run at least twice with no human
involvement" and asks for timestamps. It does not mandate six-hour spacing.
WS-C separately requires scheduled dumps to S3 retained for at least seven days.
The six-hour interval is this project's production choice. An explicitly
disclosed temporary fifteen-minute schedule can demonstrate two real unattended
firings sooner; it cannot demonstrate six hours of production scheduling.
Do this only after a successful manual backup and recovered public login, with
enough free disk and no active backup. Keep backup downtime visible to the user.

Before changing anything, record the installed timer and next trigger. Refuse
to overwrite an existing assessment drop-in. In the approved root shell:

```sh
systemctl cat apicompass-backup.timer
systemctl show apicompass-backup.timer -p TimersCalendar -p NextElapseUSecRealtime
test ! -e /run/systemd/system/apicompass-backup.timer.d/90-assessment.conf
mkdir -p /run/systemd/system/apicompass-backup.timer.d
cat > /run/systemd/system/apicompass-backup.timer.d/90-assessment.conf <<'EOF'
[Timer]
OnCalendar=
OnCalendar=*-*-* *:00/15:00 UTC
RandomizedDelaySec=0
Persistent=false
EOF
systemd-analyze calendar '*-*-* *:00/15:00 UTC'
systemctl daemon-reload
systemctl restart apicompass-backup.timer
systemctl show apicompass-backup.timer -p TimersCalendar -p LastTriggerUSec -p NextElapseUSecRealtime
```

Do not start the service manually during the evidence window. Observe two
future quarter-hour firings, each with successful service completion, unique
service InvocationID, unique backup key and actual S3 VersionId, matching hash,
and restored public login. Record UTC timer trigger and completion times;
`journalctl -u apicompass-backup.service -o json` includes
`_SYSTEMD_INVOCATION_ID`. Read only the sanitized job event from that output.
If a backup spans a scheduled boundary, systemd will not start a second copy of
an already active service; wait for another real scheduled invocation. Do not
kill or shorten an active backup. The first pair normally takes fifteen to
thirty minutes plus job duration after activation. Health's existing five-minute
timer needs two corresponding successful autonomous invocations as well.

After the second successful scheduled backup, restore the normal configuration:

```sh
test -f /run/systemd/system/apicompass-backup.timer.d/90-assessment.conf
rm -- /run/systemd/system/apicompass-backup.timer.d/90-assessment.conf
systemctl daemon-reload
systemctl restart apicompass-backup.timer
systemctl cat apicompass-backup.timer
systemctl show apicompass-backup.timer -p TimersCalendar -p NextElapseUSecRealtime
```

Require the effective calendar to be 00:15, 06:15, 12:15 and 18:15 UTC with up
to sixty seconds jitter again. Keep the other drop-ins intact. Label website
evidence "two unattended runs on a temporary fifteen-minute assessment schedule;
six-hour production schedule restored". Retain failures and rollback evidence.

## 4. Candidate controlled incident: stop only DataCheck

Perform only in an agreed maintenance window after baseline recovery succeeds,
with no backup/restore currently active and an operator present to restore it.
This is a reversible application outage, not a data-loss or disk-fill exercise.
No security-group/IAM mutation or database deletion is needed. A failed job
must actually occur; manually setting an alarm state is not failure evidence.

```sh
(
  set -eu
  data_id=$(docker ps -q --filter label=com.docker.compose.project=apicompass-prod \
    --filter label=com.docker.compose.service=datacheck)
  test -n "$data_id"
  test "$(printf '%s\n' "$data_id" | wc -l)" -eq 1
  trap 'docker start "$data_id" >/dev/null' EXIT HUP INT TERM
  date -u '+incident_start=%Y-%m-%dT%H:%M:%SZ'
  docker stop --time 30 "$data_id"
  if systemctl start apicompass-health.service; then
    echo 'Unexpected healthy result: investigate before accepting incident'; exit 1
  fi
  systemctl show apicompass-health.service -p Result -p ExecMainStatus
  journalctl -u apicompass-health.service -n 12 -o cat --no-pager
  # Operator independently observes real HealthFailure=1, alarm state/email.
  # Keep the window bounded; restore even if alarm/email verification is delayed.
)
systemctl reset-failed apicompass-health.service
# Wait for actual DataCheck container readiness before this recovery check:
systemctl start apicompass-health.service
journalctl -u apicompass-health.service -n 12 -o cat --no-pager
```

The subshell's trap restarts the exact selected container on normal/error exit;
SIGKILL/host loss still requires manual recovery. The normal health timer can
also record the outage. CloudWatch uses period Maximum, so recovery within the
same five-minute bucket can remain ALARM until a later clean period. Record
actual failure, restored readiness, alarm/email and recovery timestamps. A very
brief outage may end before email is delivered; do not keep production down
indefinitely to manufacture a notification. Recheck HTTPS login and known tool
answer after recovery. This measures service recovery, not database restore RTO.

## 5. Fresh-target restore and known-state validation

In a root shell, load only the nonsecret bucket/region configuration and choose
the **actual** backup/version from step 2 or a recorded timer run:

```sh
cd /opt/apicompass
set -a
. /etc/apicompass/ops.env
set +a
restore_target="apicompass-restore-$(date -u +%Y%m%d%H%M%S)-$(/opt/apicompass-tools/bin/python -c 'import uuid; print(uuid.uuid4().hex[:8])')"
printf 'fresh_target=%s\n' "$restore_target"
/opt/apicompass-tools/bin/python scripts/ops_jobs.py restore \
  --key 'REPLACE_WITH_EXACT_BACKUP_KEY' \
  --version 'REPLACE_WITH_EXACT_S3_VERSION_ID' \
  --target "$restore_target" --confirm confirmed-fresh-target
docker inspect --format '{{.HostConfig.NetworkMode}} {{json .HostConfig.PortBindings}} {{index .Config.Labels "apicompass.purpose"}}' "$restore_target"
docker inspect --format '{{range .Mounts}}{{println .Destination .Name}}{{end}}' "$restore_target"
docker exec "$restore_target" mongosh --quiet --eval \
  'const a=db.getSiblingDB("APICompass"); print(JSON.stringify({users:a.users.countDocuments({}),conversations:a.conversations.countDocuments({}),agents:a.agents.countDocuments({})}));'
```

Require network `none`, no port bindings, purpose `isolated-restore`, fresh
anonymous data volume, checksum-validated restore success and expected counts.
The target intentionally runs without authentication inside its isolated network
namespace; do not publish its ports or connect it to a shared/production network.
Do not use `--drop`, existing containers, production mounts, or production chat
connection changes to speed up this drill. Failed restores leave the fresh
target for inspection; their existence is not recovery success.

### Read-only selected-record metadata proof

`scripts/verify_restore.py` records only counts from `users`, `conversations`,
`messages`, `agents` and `actions`, TTL-index counts for those collections, and
counts matching one pre-recorded synthetic conversation ID and agent ID.
The reviewed LibreChat source uses `Conversation.conversationId`,
`Message.conversationId`, `Agent.id` and `Action.agent_id`; the helper queries
these keys without returning documents, email addresses, message text, agent
instructions, action metadata or ciphertext. IDs are supplied by the operator,
never discovered by dumping database documents. No user credential is collected.

Before the selected backup, after known-state setup and while avoiding new
messages or agent edits, run:

```sh
umask 077
/opt/apicompass-tools/bin/python scripts/verify_restore.py baseline \
  --conversation-id 'ACTUAL_SYNTHETIC_CONVERSATION_ID' \
  --agent-id 'ACTUAL_SYNTHETIC_AGENT_ID' > /root/apicompass-restore-baseline.json
test "$?" -eq 0
```

After restoring that backup version, use the same IDs and baseline:

```sh
/opt/apicompass-tools/bin/python scripts/verify_restore.py restore \
  --target "$restore_target" --baseline /root/apicompass-restore-baseline.json \
  --conversation-id 'ACTUAL_SYNTHETIC_CONVERSATION_ID' \
  --agent-id 'ACTUAL_SYNTHETIC_AGENT_ID'
```

The helper refuses the production name, connected network, published ports,
missing restore purpose label, non-volume mounts, production Mongo volume
reuse, mismatched counts, missing conversation/messages/agent, or anything other
than exactly one action attached to that selected agent. Mongo inspection stays
in memory; failures emit only a fixed status. Baseline authenticates using the
existing Mongo app password inside the production container. Restore probe has
no credentials and reaches only its isolated container through `docker exec`.
Success says `metadata_matched_login_tool_pending`, deliberately preserving
the application acceptance gate. Matching counts are evidence of selected
records, not proof of content equivalence, credential decryption or login.
Nonzero TTL-index counts flag possible background mutation; do not mask a
mismatch by updating the baseline after backup.

**Known-state/login/tool gate remains manual and requires a separately reviewed
isolated application recovery setup.** Current `ops_jobs.py restore` restores
Mongo only and reports `manual_known_state_pending`; it cannot prove user login,
decryption of stored credentials or a working agent action. Do not launch an
extra chat service or attach networks ad hoc. Preserve the restored target until
the operator has a reviewed isolated chat/network plan using stable SSM keys,
fresh application volumes and only a loopback host binding. The operator must
then log in with the pre-recorded synthetic account, find its marker conversation
and verify exactly one action returns the expected shipment findings/request ID.
Keep production chat running against its original database throughout.

The separately reviewed application plan must account for these constraints:

- Mongo currently binds only its own loopback and has no network. Attaching a
  bridge or publishing a chat container alone cannot make that Mongo reachable.
- Preserve this original recovery target. Use a second fresh, authenticated
  recovery Mongo and fresh application volumes in a dedicated Compose project,
  with no production volume/network membership. Restore the same exact backup
  version there. Reusing production mounts or moving production chat is excluded.
- Give recovery chat the same stable SSM JWT and credential-encryption keys,
  loaded privately in memory. Use an authenticated recovery Mongo URI, never
  the production Mongo URI. Do not create an owner token or reset the password.
- Publish recovery chat on host `127.0.0.1` only and use an authenticated SSM
  port-forward session for the operator's browser. Give this stack its own
  DataCheck service named `datacheck`, private S3 configuration and existing
  bearer token; preserve the saved private action URL. Mongo gets no host port.
- Recovery chat needs outbound Gemini connectivity; an entirely disconnected
  `internal` network cannot prove the model/tool path. Outbound connectivity
  must not attach it to the production Compose network. Resource headroom for
  two app stacks must be checked on the small host before starting anything.
- The user enters the existing synthetic account password privately, opens
  the known marker conversation, and issues one new known DataCheck request.
  Observe 60 rows, seven issues and seven affected rows with a real request ID.
  This is actual restored login/conversation/tool proof, distinct from probing
  DataCheck directly or minting a session. Record recovery completion then.

### Executable second-stack assessment launcher (review before execution)

`scripts/recovery_stack.py` implements the separate-stack contract without
altering the original `--network none` recovery target. It creates a dedicated
bridge, three containers with `restart=no`, and Docker-generated fresh volumes.
All explicitly created resources carry `apicompass.purpose=assessment-recovery`
and the exact `apicompass.recovery` scope. Existing scopes are refused. Only
the checked-in public LibreChat YAML is bind-mounted, read-only; no production
volume, Docker socket or production network is mounted or attached.

The launcher requires Linux, at least 768 MiB available RAM, at least 1792 MiB
combined available RAM/free swap, and free disk greater than three archive
sizes plus 512 MiB. Caps are Mongo 384 MiB, DataCheck 192 MiB and chat 768 MiB.
These checks do not guarantee the small host can carry both stacks under model
load; monitor production responsiveness and abort the assessment if needed.
Do not lower the guard merely to force a pass.

Mongo uses a newly generated temporary root password and fresh data/configdb
volumes. Only `APICompass.*` is restored; the archived `admin` database is never
restored over the temporary root account. Hash, exact S3 VersionId and content
length must match before creating resources. Mongo has no host port. Its
temporary authentication config is stdin-fed, mode 0600 in `/run` tmpfs and
trap-removed; the archive copy inside its fresh volume is removed after restore.
The loader retains SSM secrets in process memory and passes named Docker env
variables without values in argv or an env file. Docker stores container env
metadata, as in production; privileged Docker operators must not dump it.

The existing production DataCheck image ID is reused with a fresh service and
private S3 configuration. No production container is stopped, modified or
restarted. Chat uses the pinned production image and stable SSM JWT/CREDS and
Gemini keys, but a recovery-only Mongo URI. Recovery Docker logging is disabled;
chat file logs stay in its own disposable volume and are excluded from the
production shipper. No second CloudWatch question telemetry is enabled.
Registration remains disabled. The assessment has outbound model/S3 access;
only chat is published, at **127.0.0.1:3081**. There is no Caddy/public endpoint.

After parent/operator review and inclusion of the launcher in the reviewed
host release, run in the approved root shell with nonsecret `ops.env` loaded:

```sh
cd /opt/apicompass
set -a
. /etc/apicompass/ops.env
set +a
recovery_name="apicompass-recovery-$(/opt/apicompass-tools/bin/python -c 'import uuid; print(uuid.uuid4().hex[:16])')"
printf 'recovery_name=%s\n' "$recovery_name"
date -u '+recovery_started=%Y-%m-%dT%H:%M:%SZ'
/opt/apicompass-tools/bin/python scripts/recovery_stack.py start \
  --name "$recovery_name" --key 'ACTUAL_EXACT_BACKUP_KEY' \
  --version 'ACTUAL_EXACT_S3_VERSION_ID' \
  --confirm assessment-only-fresh-stack
/opt/apicompass-tools/bin/python scripts/recovery_stack.py status --name "$recovery_name"
```

Success is `restored_stack_ready_login_tool_pending`, with archive SHA256 and
loopback port only. This includes a real S3-backed known DataCheck check and
chat readiness, but does not claim the restored saved action has decrypted or
the model has called it. Any failure preserves scoped resources for review;
run only the scoped teardown below before retrying with a new scope. Never
inspect raw container env/logs for diagnostics. OOM/state/port metadata can be
checked with explicit Docker inspection projections.

For real restored login and conversation proof, the user runs this directly in
their private interactive host terminal. Both email and password prompts are
hidden. No credential arguments, reset, new user or impersonation token is used:

```sh
/opt/apicompass-tools/bin/python scripts/recovery_stack.py login \
  --name "$recovery_name" --conversation-id 'ACTUAL_SYNTHETIC_CONVERSATION_ID' \
  --agent-id 'ACTUAL_PRIVATE_DATACHECK_AGENT_ID'
```

The helper POSTs `/api/auth/login` inside recovery chat, uses the returned
application session only in memory to GET the selected `/api/convos/{id}`,
checks its ID and owner-scoped HTTP success, verifies the restored private
agent/action and runs a fresh normal admission/SSE tool question before logout.
Success requires a fresh S3 shipments result and a matching60/7/7final answer,
with dataset/ruleset versions and the actual API request ID. Output contains
only allowlisted proof metadata; it does not display credentials, the session,
account record or conversation body. Failure reports a fixed stage and numeric
HTTP status only. Accounts
with two-factor authentication require the ordinary browser flow instead;
the helper does not bypass it.

For an additional visual demonstration, use an authenticated SSM port-forward from the user's
machine (Session Manager plugin and operator access already configured):

```sh
aws ssm start-session --target ACTUAL_PROJECT_INSTANCE_ID \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["3081"],"localPortNumber":["3081"]}'
```

Open `http://127.0.0.1:3081` locally, enter the existing synthetic account
credentials privately, open the known marker conversation and restored agent,
and send: `Check shipments for validation issues. Report total rows, issue
count, affected-row count and the request ID.` Require the saved action to
execute and a correct 60/7/7 answer with a real request ID. Record sanitized
tool trace/request ID and recovery completion UTC time. A second action, model
failure, wrong counts, absent conversation, or credential decryption failure
fails this acceptance attempt. Metadata checks alone do not establish success;
the private helper must report `restored_login_conversation_action_tool_verified`.
The recovered chat is unbranded
upstream UI; production reskin evidence comes from production.

Close the browser tab and port-forward after evidence capture. Then remove only
the exact reviewed assessment scope, including partially created stacks:

```sh
/opt/apicompass-tools/bin/python scripts/recovery_stack.py status --name "$recovery_name"
/opt/apicompass-tools/bin/python scripts/recovery_stack.py stop \
  --name "$recovery_name" --confirm remove-only-assessment-resources
/opt/apicompass-tools/bin/python scripts/recovery_stack.py status --name "$recovery_name"
```

Teardown inventories and validates purpose/scope labels on **all** candidates
before any removal, refuses Compose-labelled resources, stops exact assessment
containers and removes only scoped networks/volumes. There is no prune,
production Compose operation or named production volume lookup. The final
inventory must have zero counts. Verify production HTTPS/login and the original
Mongo/data-volume identity afterward. No launcher or test run alone is live
recovery evidence; this artifact still needs host execution and user acceptance.

RPO: record age of the selected recovery point at declared incident time;
six hours plus scheduling/dump/upload is a target only. RTO: time from declared
recovery start to verified known-state login and tool answer, not merely the
end of mongorestore. Until this gate is performed, leave RPO/RTO/consistent
application recovery unverified. Cleanup must target only the inspected
`isolated-restore` container and its anonymous volumes after evidence review;
never use a project-wide volume prune.

# APICompass operations: prepared, not deployed

These jobs have unit-test evidence only. No production host, timer installation,
successful S3 backup, real restore, two unattended runs, measured RPO/RTO, or
known-state login/tool recovery is established by these files. Do not count them
as completed cloud jobs. Monthly AWS allowance remains at most US$25;
no additional permanent service/database is introduced.

## Host and security contract

Use Linux/systemd, Python 3.11+, project requirements (including boto3), Docker,
and the production Compose project `apicompass-prod` with uniquely labelled
`chat`, `mongodb`, and `datacheck` services. Installation target is
`/opt/apicompass` with the shared /opt/apicompass-tools venv. MongoDB is authenticated, root user `root`,
application database `APICompass`, user `apicompass`, MongoDB 8.0.20. The Mongo
container must mount `/run` as tmpfs. Scripts address container IDs selected by
project/service labels, never Compose secret interpolation.

Create root-owned mode 0600 `/etc/apicompass/ops.env` with **non-secret** values:

```ini
AWS_REGION=ap-southeast-1
DATACHECK_S3_BUCKET=REPLACE_WITH_FOUNDATION_OUTPUT
APICOMPASS_DISK_PATH=/
```

Use the instance profile/default SDK credential chain; no access keys. Runtime
JSON comes from decrypted `/apicompass/prod/runtime`, with the existing exact
eight fields `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`, `DATACHECK_API_TOKEN`,
`JWT_SECRET`, `JWT_REFRESH_SECRET`, `CREDS_KEY`, `CREDS_IV`, `GOOGLE_KEY`.
Mongo password and DataCheck bearer are passed only through stdin/in-memory SDK
values. The password config is mode 0600 in Mongo's `/run` tmpfs and trap-removed.
No credential, response body, arbitrary exception text, or child stderr is logged.
Root/Docker membership is host-administrator access; restrict it accordingly.

The existing role allows GetParameter/GetParameters below `/apicompass/prod/`,
GetObject/GetObjectVersion for `datasets/v2/`, `releases/`, `backups/`, PutObject
only under `backups/`, prefix-scoped ListBucket, and PutMetricData in
`APICompass`. S3 remains private, TLS-only, versioned, SSE-S3. No extra IAM grant
is required by these jobs. PutObject is single-part, archives must be below
4 GiB. Ensure adequate host disk for one archive before activation. Host
temporary archive directories/files are 0700/0600 and deleted on all normal
success/failure exits. Host disk encryption is a deployment prerequisite.

## Backup every six hours

`python scripts/ops_jobs.py backup` obtains an exclusive Linux flock. It checks
Mongo tmpfs, observes whether production chat is running, stops that chat with
a 60-second grace period, takes `mongodump --archive --gzip` with root auth,
and restarts the same chat in `finally`. An originally stopped chat stays
stopped. Stop/dump/start failures fail the job. Upload occurs after chat restart,
so an upload failure leaves chat running and reports backup failure.

This standalone-Mongo strategy assumes chat is the only application writer and
there are no simultaneous administrator/direct database writes. Background
MongoDB TTL deletion may still modify collections: this is a quiesced logical
backup, not a verified atomic point-in-time snapshot. Review TTL indexes and
perform the actual known-state restore before claiming recovery consistency.
Do not use unsupported `--oplog` on standalone Mongo. The unsafe fsync-lock
prototype was removed after review found that a Docker-client timeout could
leave a later-acquired write lock behind. This job never acquires that lock.
GNU timeout inside the Mongo8 container bounds the dump/shell at 25 minutes,
TERM followed by KILL after five seconds; the host client allows 26 minutes.
The reviewed Mongo8 image was checked to contain GNU timeout9.4. Remote
disconnect/crash cleanup still needs a real controlled exercise, not a unit-test claim.
Brief planned chat downtime occurs at every backup. Timer times are 00:15,
06:15, 12:15 and 18:15 UTC plus up to one minute jitter. If the process/host is
killed/terminated before finally, chat may remain stopped. Finally does not
cover SIGKILL, default SIGTERM, host crash or power failure. Alert and manual
recovery are required; do not kill an active backup casually. After an interruption,
stop/disable the timer, inspect whether its dump is still running, wait for its
remote deadline or terminate only that confirmed process, and check the tmpfs
credential file has been removed. Start only the production chat container this
job stopped, then check login/readiness before re-enabling the timer. Do not
unlock a database lock owned by another operator. Record the failure honestly.

Objects use unique UTC timestamp+UUID keys under `backups/mongodb/`.
Job success requires a real S3 VersionId and HEAD readback with matching length
and SHA-256 metadata. Record version/key privately for restore. A successful
upload/readback does not prove restorability. No bucket-wide sync or delete is
used. Retention follows the foundation lifecycle policy; check its actual rule
before setting a recovery retention promise.

## Health every five minutes

`python scripts/ops_jobs.py health` calls the real authenticated
`/health/ready` and `/datasets/shipments/issues?limit=20` from **inside DataCheck**,
using its private loopback port and stdin bearer. Readiness must check all three
datasets. The known response must be shipments-v2, 60 rows, seven issues,
seven affected rows, not truncated, with versioned S3 source.
The seven finding signatures (row, column, rule) must match the golden fixture;
field values and explanations stay inside the container and are never logged.
Local/fallback storage, wrong answers, network/authentication failures, stale/missing backups,
and disk at least 85% used fail the job. This does not check public HTTPS,
LibreChat login, Gemini availability, or the full model-to-tool path.

Stdout/journal contains one allowlisted JSON event: job, status, UUID request ID,
duration_ms; health success also includes sanitized API request ID. Backup
success adds object key/hash. No findings are emitted. CloudWatch namespace is
`APICompass`, dimension `Project=APICompass` (no dynamic InstanceId):

| Metric | Unit | Meaning |
| --- | --- | --- |
| HealthFailure | Count | 0/1 per health invocation; includes known answer, backup freshness and disk |
| HealthLatencyMs | Milliseconds | private readiness + known-answer elapsed time, including SSM/container discovery |
| DiskUsedPercent | Percent | disk containing APICOMPASS_DISK_PATH; alert at 85% |
| BackupFailure | Count | 0/1 per backup attempt |
| BackupAgeHours | None | hours since latest nonempty archive object; alert above 8 |

Missing backups omit BackupAgeHours and set HealthFailure=1; they never publish
zero age. Missing metrics must be treated as breaching in future alarms,
because IAM/network/host failures can prevent metric publication. Metric API
failure fails the job. Alarms/dashboard/email delivery and CloudWatch log
shipping from journald are **pending**, not installed by these files. Existing
`/apicompass/prod/{runtime,questions,jobs}` log groups retain 14 days; a later
host log agent must ship sanitized job JSON to `jobs` without reading secrets.

## Isolated fresh-target restore drill

Choose an exact successful object version and unique target, for example:

```sh
/opt/apicompass-tools/bin/python scripts/ops_jobs.py restore \
  --key backups/mongodb/ACTUAL-TIMESTAMP-UUID.archive.gz \
  --version ACTUAL_VERSION_ID \
  --target apicompass-restore-20261122-test01 \
  --confirm confirmed-fresh-target
```

Replace placeholders from the backup evidence, not an arbitrary current object.
The script rejects production names, keys outside the backup prefix, missing
version, existing container/volume, unavailable Docker daemon, and hash mismatch
before launch. Docker atomically claims the target container name and allocates
a **new anonymous volume**, avoiding reuse of a named volume created after preflight. It creates an ephemeral Mongo
container with `--network none`, Mongo bind `127.0.0.1` inside the container,
**no published host ports**, 512 MiB memory, and no production volume mount.
It restores without `--drop`, leaves the isolated target for inspection, and
prints `manual_known_state_pending`. No extra database service remains in the
production Compose file. The restore target is deliberately not auto-deleted
on failure so evidence can be examined; clean up only its exact reviewed name.

Pre-record synthetic account ID, conversation IDs/counts and expected agent/tool
configuration before backup. Inspect the restored database via `docker exec`
without exposing stored credentials. **Manual pending:** attach a separately
isolated temporary chat instance with preserved runtime encryption keys and
fresh-target connection only, then verify the known account can log in,
conversation is present, and the DataCheck action still returns known findings.
This manual drill is not automated here and must never point production chat
at the restore database. Record timings and sanitized evidence. Stop/remove the
exact ephemeral container/volume only after inspection and explicit target
verification. Production recovery/cutover requires its own reviewed procedure.

## Install/activate only when the production host is available

Review sole-writer/TTL consistency limits, interruption recovery, free disk, role permissions,
SSM, private S3 fixtures, runtime mounts, and manual restart/restore procedure.
Do not run these commands against the current laptop services. On the approved
host, with non-secret environment installed:

```sh
sudo cp /opt/apicompass/infra/systemd/apicompass-* /etc/systemd/system/
sudo systemd-analyze verify /etc/systemd/system/apicompass-*.service /etc/systemd/system/apicompass-*.timer
sudo systemctl daemon-reload
sudo systemctl start apicompass-backup.service
sudo systemctl start apicompass-health.service
# Inspect sanitized journal, object/version and metric readbacks before enable:
sudo systemctl enable --now apicompass-backup.timer apicompass-health.timer
sudo systemctl list-timers 'apicompass-*'
```

No installation/activation was performed during implementation. Verify actual
Linux unit syntax on that host; Windows unit tests cannot prove systemd behavior.
Collect **at least two real unattended successful runs of each job** (backup
separated by its six-hour timer), timestamps, exit statuses, S3 versions and
metric readbacks. Missing/failure cases must also be demonstrated safely.

Target RPO: six hours plus jitter/dump/upload duration; this is an unmeasured
target, not a guarantee. Alert freshness threshold: eight hours. Measure actual
RPO from the known state's backup timestamp to simulated incident. RTO has no
established bound: measure from declared recovery start to verified known-state
login + tool result, including retrieval, restore and application validation.
Do not mark restore/RPO/RTO complete from dump success or unit tests.

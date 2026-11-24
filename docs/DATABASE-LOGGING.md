# Sanitized database operational logs

`scripts/ship_database.py` is prepared source, not proof of CloudWatch delivery.
It selects exactly one running Mongo using the fixed `apicompass-prod` project
and `mongodb` service labels. Recovery containers are excluded. It reads no
Docker environment and requires no Mongo credentials or database query.

Destination is the existing `/apicompass/prod/runtime` group, with daily
`database-YYYY-MM-DD` streams. That group is provisioned with fourteen-day
retention; verify the deployed setting independently. This adds no log group,
IAM grant or paid always-on service. The existing scoped host role and SDK
credential chain are used.

Only six fields leave the parser:

| Field | Safe representation |
| --- | --- |
| `t` | Valid UTC timestamp normalized to milliseconds |
| `s` | Fixed Mongo severity enum |
| `c` | Fixed Mongo component enum |
| `id` | Integer Mongo event ID, bounded 0 to 1,000,000,000 |
| `ctx` | Fixed context enum; numbered connections become `connection`, everything else `other` |
| `classification` | Fixed class derived from component; never from message text |

Raw `msg`, `attr`, namespace, query, documents, usernames, connection URI,
exceptions and arbitrary extra fields are discarded. Even unknown context
strings are never forwarded. This deliberately limits diagnostic detail;
these are operational envelopes, not query audit logs or a count of every
database operation. A connection class does not assert successful login.

Keep raw query profiling off (profiling level 0), and do not enable verbose
QUERY/COMMAND logging for this assessment. The shipper does not turn either on
or change Mongo configuration. Default Mongo slow-operation diagnostics can
still exist in Docker's bounded local logs; their messages/attributes are
never shipped. Do not claim raw query logging is disabled merely because this
sanitizer strips it. Verify the actual profile/verbosity settings separately,
without printing raw logs. A private host operator can authenticate within
the existing Mongo container and print only three numeric settings:

```sh
mongo_id=$(docker ps -q --filter label=com.docker.compose.project=apicompass-prod \
  --filter label=com.docker.compose.service=mongodb)
test -n "$mongo_id"
test "$(printf '%s\n' "$mongo_id" | wc -l)" -eq 1
docker exec "$mongo_id" mongosh --quiet --eval \
  'const a=db.getSiblingDB("admin"); if(!a.auth("root",process.env.MONGO_INITDB_ROOT_PASSWORD))quit(1); const p=db.getSiblingDB("APICompass").getProfilingStatus(); const v=a.runCommand({getParameter:1,logComponentVerbosity:1}); if(v.ok!==1)quit(1); print(JSON.stringify({profiling_level:p.was,query_verbosity:v.logComponentVerbosity.query.verbosity,command_verbosity:v.logComponentVerbosity.command.verbosity}));'
```

Require profiling level 0. Component verbosity -1 inherits its parent; review
the actual inherited effective level before asserting verbose query logging
is off. Do not dump `getParameter` output or runtime environment as evidence.

The collector is bounded to twenty seconds, 4 MiB scanned, 64 KiB per line and
500 envelopes per invocation. Malformed/non-Mongo lines are ignored; oversized
input fails safely without displaying it. Linux flock prevents concurrent
shipment. Root-only state stores an overlapping five-second cursor and hashes
of sanitized events, capped at 10,000 entries/1 MiB. Initial scan covers the
previous five minutes. Only after CloudWatch accepts the whole batch is state
atomically saved. A rejected/failed batch preserves the cursor; an ambiguous
API response can cause retry duplicates. Identical sanitized envelopes at the
same millisecond can be merged by deduplication. No metrics are manufactured.
An idle successful scan emits no database event and does not prove delivery.

Install only after parent/operator review and reviewed release deployment:

```sh
cd /opt/apicompass
cp infra/systemd/apicompass-database-logs.service /etc/systemd/system/
cp infra/systemd/apicompass-database-logs.timer /etc/systemd/system/
systemd-analyze verify /etc/systemd/system/apicompass-database-logs.service \
  /etc/systemd/system/apicompass-database-logs.timer
systemctl daemon-reload
systemctl start apicompass-database-logs.service
systemctl show apicompass-database-logs.service -p Result -p ExecMainStatus
journalctl -u apicompass-database-logs.service -n 8 -o cat --no-pager
```

Require success plus a positive `events_delivered` from genuine Mongo events;
independently read the actual CloudWatch stream and its retention through the
operator account. Check all records contain only the six safe fields, with no
messages or attributes. Only then enable:

```sh
systemctl enable --now apicompass-database-logs.timer
systemctl list-timers apicompass-database-logs.timer --all
```

If an old backlog exceeds scan/batch limits, preserve the failure and have the
operator review a deliberate cursor reset privately. Never forward raw logs,
relax the sanitizer, print discarded lines or quietly skip backlog to make an
acceptance screenshot. Linux unit syntax and live delivery remain host checks;
offline tests cannot establish them.

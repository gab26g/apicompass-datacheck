# Recovery drill and resolved isolation fault

Observed23November2026, AWS Singapore. All datasets are synthetic. Original production database volumes were preserved.

## Successful recovery gate

The final isolated copy used five fresh volumes. Its metadata matched the pre-backup baseline:1user,2conversations,8messages,1agent and1action; the selected saved conversation had6messages. Chat was reachable only through host loopback3081; database and DataCheck had no host-published ports.

The student entered existing application credentials at hidden prompts. Normal authentication succeeded; the helper verified the restored owned conversation, private agent and saved action. It then submitted a new normal saved-agent question, consumed its full SSE stream and validated both the fresh S3 tool result and final answer.

Actual result: row_count60, issue_count7, affected_row_count7, dataset_version`shipments-v2`, ruleset_version`shipments-rules-v2`, request_id`9a4d3ffc-1673-48af-8dec-c0d4b50a80ae`. API result generated11:59:38.487073UTC; answer persisted11:59:45.397UTC; successful verification independently observed12:00:39UTC. No credential, token or account identity was printed. [Actual terminal proof](cloud-restored-tool-2026-11-23.jpg).

The conservative whole-drill observed recovery duration is1438seconds (23m58s), from first restore attempt11:36:41UTC to verified observation12:00:39UTC. This includes failed attempts, diagnosis, cleanup, redeployment and human login/confirmation. It is not an automated restore speed benchmark. Backup age at the initial simulated incident was572seconds (9m32s), conservatively measured from backup request11:27:09UTC. This is recovery-point exposure for the drill, not observed production data loss or a guaranteed service-level objective.

After proof, explicit scoped teardown removed3assessment containers,1network and5volumes. Independent inventory returned zero for all three resource types. The temporary cleanup timer was stopped after teardown. Production health returned Result=success and ExecMainStatus=0.

## Fault, root cause and prevention

An earlier restored-account attempt stopped at login; its exact authentication rejection cause was not established and must not be attributed to the student's password. The safe diagnostic helper now reports a fixed stage and numeric HTTP status without printing private response bodies. The later normal login succeeded.

A separate concrete fault was reproduced: Docker inherited `com.docker.compose.project=apicompass-prod` from the custom DataCheck image into a recovery container. Production health selection then found two DataCheck containers and failed closed. The same inherited label caused normal recovery inventory/cleanup guards to reject the assessment scope. This did not merge database volumes, but it broke operational isolation by label.

The fix explicitly overrides Compose project/service labels with empty values on every recovery container, keeping assessment ownership labels. A new regression failed before this change, then all14recovery tests passed. Live verification subsequently showed exactly the four real production containers under the production selector, all expected services healthy, and exactly three containers under the separate assessment selector. Scoped inventory and teardown then succeeded without exceptions.

One differential deployment was rejected by its old/new-source guard because an insertion had an empty match anchor. A shell sequence nevertheless launched another old-code attempt; that sequencing mistake was acknowledged and the disposable copy removed. The corrected deployment used nonempty anchors, verified both complete source hashes, and was independently read back before launching another restore. Future deployment/restore steps must depend on a successful verified installation.

## Actual alarm evidence

CloudWatch console History for `apicompass-health` independently showed:

| UTC | Manila | Observation |
| --- | --- | --- |
|11:41:51|19:41:51|OK → In alarm; notification action successfully executed to project alerts topic.|
|11:51:51|19:51:51|In alarm → OK; notification action successfully executed to project alerts topic.|

These are actual metric-driven state transitions during the fault and recovery, not manually forced alarm states. The configured threshold is HealthFailure>0 for one five-minute maximum datapoint; missing data is breaching. Successful SNS action execution establishes publishing to the notification topic. The student separately confirmed that both the ALARM and OK emails arrived in the student inbox. This is user-attested inbox receipt, not an agent-inspected email screenshot.

## Operator runbook

1. Detect failed health job/HealthFailure alarm; inspect only project container names, labels, counts and fixed status metadata.
2. If production selection returns multiple DataCheck containers, stop further recovery launches. Inspect exact assessment ownership labels and production-name exclusion before deleting any disposable copy.
3. Deploy the explicit label override with old/new source-hash checks. Abort dependent actions if installation fails.
4. Restore only the exact versioned backup into a fresh labelled scope. Verify production selector count, disjoint volumes and loopback binding before private login.
5. Require restored normal login, saved conversation/action and a new correct tool-backed answer. Metadata or HTTP200alone is insufficient.
6. Explicitly tear down only that assessment scope, confirm zero resources, cancel its cleanup timer, and run production health again. Retain sanitized timing/proof and review alarm-email receipt.

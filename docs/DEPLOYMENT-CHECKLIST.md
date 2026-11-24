# Deployment gate — not yet deployed

The user approved a lean deployment with a maximum US$25 AWS allowance (November 22), still targeting lower costs for a short assessment window, and a free HTTPS hostname. There is no existing domain. Personal account sign-in is restored, Singapore is selected, root MFA is verified and APICompass-25USD budget alerts are configured. AWS shows 1/1 notification email verified. Credit estimates were checked; current regional compute estimate and assessment availability window still need verification before launch. Avoid paid extras/domain purchases. A budget alert is a notification, not a hard spending cap.

Deployed foundation: [storage, runtime role and logs](../infra/README.md), CREATE_COMPLETE November 22. It does not replace the compute, human IAM access and operations gates below. The application itself is still local.

## Before resource creation

- Confirm exact deadline, AWS account, region, authorised resource access and spending limit. Use individual access with MFA. Never request credentials in chat.
- Verify baseline resource use and an affordable instance with enough memory for LibreChat, MongoDB and DataCheck. Avoid adding RDS, NAT gateways, vector databases, load balancers or extra regions by default.
- Decide HTTPS hostname/certificate path, ownership and renewal. A free hostname is an option, not an approved external sign-up.
- Configure a useful day-one budget alert and resource tags before launch; retain sanitized proof.

## Configuration to implement and verify

- One host with authenticated private MongoDB and private DataCheck; publicly expose only the HTTPS entry point. Never expose 27017 or 8000.
- Instance role for the fixed private S3 dataset keys, backup prefix, required secret paths and telemetry. No static AWS credentials. Scope permissions and test actual denials.
- Versioned private S3 with public-access blocks and encryption. Upload exact fixture bytes; verify source.storage=s3, a real object_version and the expected hash on the deployed API response.
- Runtime secrets for model/tool/bootstrap/database credentials, retained securely across restarts. Preserve chat encryption keys through migration; do not generate replacements over an existing encrypted database.
- Replace local no-auth MongoDB and disable open registration once the intended user is provisioned. Verify production token enforcement, TLS, sessions and the actual chat-to-tool request.
- CloudTrail, finite log retention, request/question correlation and a populated dashboard. API logs alone are insufficient proof of question logging.
- Six relevant alarms connected to an email route; one received test alert. Health alarms must exercise real source availability, not just liveness.
- Scheduled DB backups to private S3 and scheduled dependency health checks. Each needs two unattended successes. Configure at least seven days of backup retention.
- Fresh-target restore of DB, content/config/secret access, a known saved state item and a working tool answer. Measure actual RPO and RTO; do not overwrite the only working database.
- Controlled reversible failure, evidence of detection, root cause, correction, prevention and a tested runbook. Preserve the working configuration for rollback.

## Final proof

Run the fixed assistant evaluation and matching baseline/after measurements. Publish a graph, actual/estimated costs distinguished, first/final six-pillar reviews and 3–5 next steps. Finish the evidence-backed website, embedded 5–8 minute video, reviewed declaration and ZIP with real .git history. Check everything for secrets before sharing. Keep the app available for assessment and agree a later teardown date.

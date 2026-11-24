# AWS foundation — deployed November 22

Stack `apicompass-foundation` reached CREATE_COMPLETE in Singapore at 15:28:49 +08:00. All seven resources succeeded. See [deployment evidence](../docs/evidence/aws-foundation-deployment-2026-11-22.md). Actual outputs are in ignored `.local/aws-foundation.json`; never copy credentials into that file. The checklist below describes the creation/acceptance workflow; compute, human operator access and runtime acceptance remain pending.

`foundation.json` is the first CloudFormation stack, intended for Singapore (`ap-southeast-1`). It creates one private versioned S3 bucket, three log groups and an EC2 runtime role/profile. It launches no instance and creates no users, passwords, access keys, public endpoint or model credentials. Deploying it alone does not make APICompass work in AWS.

## Access to review before creation

The role trusts only EC2. Its inline policy grants:

| Capability | Boundary |
| --- | --- |
| Read datasets, release bundle and restore backups | This stack's bucket, `datasets/v2/`, `releases/`, `backups/` only |
| Write backups | `backups/` only; no object delete, dataset write or bucket administration |
| List objects and versions | Those same prefixes only |
| Read runtime parameters | This account and region, `/apicompass/prod/*`; no parameter writes or recursive path access |
| Emit logs | The three pre-created `/apicompass/prod/` groups only |
| Emit metrics | `APICompass` namespace only |
| Receive Session Manager sessions | Managed-instance registration and four messaging-channel actions |

The three wildcard-resource statements are limited to metric submission and managed-instance communication APIs. They grant no ability to initiate a session on another instance. The human operator needs separate permissions to open sessions. No AWS managed policy is attached: the broader managed SSM policy also grants parameter reads beyond this application's path.

Runtime SecureString parameters are intended to use the account's AWS-managed `aws/ssm` key. A customer-managed KMS key would require a separately reviewed decrypt grant. Secret values must be entered privately and loaded at runtime; they do not belong in CloudFormation parameters, outputs, UserData or release bundles. The host role is a host-wide trust boundary; this template does not isolate secrets between containers on that host.

## Retention and costs

The bucket blocks public access, disables ACLs, uses SSE-S3 encryption and rejects non-TLS requests. Versioning is enabled. A uniquely named backup expires as current after 14 days, then remains noncurrent for another 14 days before permanent deletion (approximately 28 days total, plus asynchronous processing). Overwriting a key starts its noncurrent retention clock earlier; use unique timestamped backup keys. Dataset/release versions have no automatic expiry, so recovery evidence must be retained and storage reviewed at teardown. Incomplete multipart uploads expire after one day. All log groups retain events for 14 days.

The bucket is retained on stack deletion/replacement to protect recovery copies; retained storage can continue charging. Log groups follow normal stack deletion, so export required sanitized evidence first. The US$25 budget is account-wide monthly notification coverage, not an automatic cap or a lifetime project cap. Review gross estimated costs excluding credits before launching compute and agree the teardown date.

## Deployment gates and acceptance

1. Confirm budget recipient verified and review IAM changes at action time. CloudFormation requires `CAPABILITY_IAM`. Use the account bootstrap session only for this step; prepare an individual MFA-protected operator for routine work.
2. Upload this exact reviewed file to CloudFormation in Singapore and inspect its change set before execution. Completed November 22 via Template Studio because the browser file picker was unavailable; the visible template matched the reviewed JSON exactly.
3. Verify stack success, S3 public blocks/encryption/versioning, log retention and generated role/profile outputs. Upload only the three fixed synthetic CSVs to `datasets/v2/` and a secret-scanned deployment bundle to `releases/` through the operator, not by broadening runtime write access.
4. Verify actual runtime allow/deny behavior: permitted dataset read and backup write; denied unrelated bucket, dataset write, parameter outside the path and namespace outside APICompass. Static template validation does not prove IAM enforcement.
5. Continue compute/network/TLS, authenticated MongoDB, runtime secret loading and real S3-backed chat proof. CloudTrail, six alarms/SNS, dashboard, question instrumentation, scheduled jobs and fresh-target recovery remain separate required work.

Sources: [Session Manager instance permissions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html), [SSM managed policy reference](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html). Review role permissions again if the runtime implementation changes.

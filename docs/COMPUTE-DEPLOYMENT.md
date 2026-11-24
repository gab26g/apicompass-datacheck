# Single-host deployment — prepared, not launched

Use `python scripts/render_compute.py` to generate `infra/compute.json` from the base template and bootstrap shell script. Deploy only the rendered file, in Singapore, with the existing foundation instance-profile output. It creates a dedicated VPC/subnet/Internet Gateway/route, web security group, one t3.small Linux host and an associated Elastic IP. It creates no IAM role or database service.

Only TCP 80/443 are admitted publicly, for certificate issuance/redirect and HTTPS. SSH, MongoDB and DataCheck ports are not admitted. The runtime role permits administration through Session Manager without SSH keys. IMDSv2 is required and its response hop limit is 2 for container SDK access. A container compromise can therefore access the host role; use only fixed private tools and no arbitrary URL/file features. HTTPS/app authentication must be verified before enrollment; don't publish a working-app claim from stack success alone.

The host has 2 GiB RAM, 24 GiB encrypted gp3 and a 2 GiB swap file. CPU credits are **standard**, preventing surplus-credit charges at the cost of throttling when credits run out. Local idle memory was about 559 MiB across the three application containers; production headroom and model-driven concurrency remain unmeasured. This is a short single-user assessment deployment, with a single-host failure domain.

The latest regional Amazon Linux 2023 x86 AMI is resolved at creation through AWS's public parameter; record its actual AMI ID after launch. The bootstrap installs distribution Docker, a checksum-verified pinned Compose 5.8.0 binary from Docker's official GitHub release, and a Python 3.12 virtual environment with boto3 1.44.9. System Python 3.9 is left unchanged. The application directory is `/opt/apicompass`, host tooling is `/opt/apicompass-tools`. `/opt/apicompass-bootstrap.READY` signals prerequisite installation only. CloudFormation does not wait for this marker, so CREATE_COMPLETE does not establish host readiness.

No secret is embedded in UserData, parameters or outputs. App files, runtime SSM parameter and first-user enrollment are separate steps after host readiness. Use the reviewed release bundle and fixed private S3 keys; do not upload the repository root, `.local`, `.venv`, database dumps or provider credentials. The generated free hostname embeds the fixed public IP under `sslip.io`; a public CA certificate must still be issued and verified. This depends on external free DNS availability, not domain ownership.

## Cost and lifetime

Singapore EC2 console quoted t3.small Linux at US$0.0264/hour on November 22: 144 hours is US$3.8016 compute alone. Public IPv4, EBS, logs/metrics/alarms, storage/requests and data transfer add costs; check gross cost excluding credits. Keep the total within the user-approved US$25 project allowance. The existing unrelated ShopSmart instance contributes to the account-wide budget but is not this deployment. Confirm assessment availability/teardown timing; the budget does not stop charges.

An Elastic IP continues charging while allocated, including when the instance is stopped. Stopping the instance also retains EBS/storage charges. Normal stack deletion terminates this new host and deletes its root volume; ensure a verified usable backup before any teardown. Foundation S3 is retained separately by design. Never delete or stop the unrelated ShopSmart resources.

## Before launch / acceptance

- Review exact template and approve public web ingress/instance-role attachment at action time in the browser. No extra approval is needed merely to inspect/validate the prepared file.
- Inspect change set additions; reject changes to unrelated resources. Use existing foundation profile, not a new broad managed policy.
- Verify actual AMI, encrypted volume, credit mode, security group ingress, IMDSv2/hop limit and SSM online state; inspect safe bootstrap log and READY marker.
- Load runtime SecureString privately; verify authenticated private MongoDB/DataCheck and HTTPS. Provision the intended user then keep public registration disabled.
- Confirm S3 dataset version/hash in real cloud API/tool output, test denied role operations and start monitoring/backup timers only after reviewing their commands.

Sources: [AWS public AMI parameters](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/finding-an-ami-parameter-store.html), [Python in AL2023](https://docs.aws.amazon.com/linux/al2023/ug/python.html), [Docker Compose installation](https://docs.docker.com/compose/install/linux/), [Compose 5.8.0](https://github.com/docker/compose/releases/tag/v5.8.0), [free hostname service](https://nip.io/).

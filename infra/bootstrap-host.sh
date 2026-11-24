set -eu
umask 077
# UserData contains no secrets; its output is safe for the host bootstrap log.
# AL2023 includes curl-minimal; installing full curl alongside it conflicts.
dnf install -y docker python3.12 python3.12-pip unzip
systemctl enable --now docker amazon-ssm-agent
install -d -m 0755 /usr/local/lib/docker/cli-plugins
cd /var/tmp
curl --fail --location --retry 5 --output docker-compose-linux-x86_64 https://github.com/docker/compose/releases/download/v5.8.0/docker-compose-linux-x86_64
curl --fail --location --retry 5 --output docker-compose-linux-x86_64.sha256 https://github.com/docker/compose/releases/download/v5.8.0/docker-compose-linux-x86_64.sha256
sha256sum --check docker-compose-linux-x86_64.sha256
install -m 0755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
rm -f docker-compose-linux-x86_64 docker-compose-linux-x86_64.sha256
curl --fail --location --retry 5 --output buildx-v0.39.1.linux-amd64 https://github.com/docker/buildx/releases/download/v0.39.1/buildx-v0.39.1.linux-amd64
curl --fail --location --retry 5 --output buildx-checksums.txt https://github.com/docker/buildx/releases/download/v0.39.1/checksums.txt
grep 'buildx-v0.39.1.linux-amd64$' buildx-checksums.txt | sha256sum --check -
install -m 0755 buildx-v0.39.1.linux-amd64 /usr/local/lib/docker/cli-plugins/docker-buildx
rm -f buildx-v0.39.1.linux-amd64 buildx-checksums.txt
python3.12 -m venv /opt/apicompass-tools
/opt/apicompass-tools/bin/pip install --disable-pip-version-check boto3==1.44.9
install -d -m 0700 /opt/apicompass
# A small swap file gives container startup headroom. EBS is encrypted by the template.
if ! test -f /swapfile-apicompass; then
    dd if=/dev/zero of=/swapfile-apicompass bs=1M count=2048 status=none
    chmod 0600 /swapfile-apicompass
    mkswap /swapfile-apicompass
fi
if ! swapon --show=NAME --noheadings | grep -Fxq /swapfile-apicompass; then
    swapon /swapfile-apicompass
fi
if ! grep -q '^/swapfile-apicompass ' /etc/fstab; then
    printf '/swapfile-apicompass none swap sw 0 0\n' >> /etc/fstab
fi
docker compose version
printf 'Host prerequisites ready; application and secrets are not installed.\n' > /opt/apicompass-bootstrap.READY

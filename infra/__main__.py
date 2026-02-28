import pulumi
import pulumi_gcp as gcp

PROJECT_ID = "autoreitbuch-bot"
REGION = "us-central1"
ZONE = "us-central1-a"

config = pulumi.Config()

# ---------------------------------------------------------------------------
# APIs
# ---------------------------------------------------------------------------
api_services = {
    api: gcp.projects.Service(
        f"api-{api}",
        service=f"{api}.googleapis.com",
        disable_on_destroy=False,
    )
    for api in ["compute", "secretmanager"]
}

# ---------------------------------------------------------------------------
# Service Account for the VM
# ---------------------------------------------------------------------------
vm_sa = gcp.serviceaccount.Account(
    "vm-sa",
    account_id="autoreitbuch-vm-sa",
    display_name="Autoreitbuch VM Service Account",
    opts=pulumi.ResourceOptions(depends_on=list(api_services.values())),
)

sa_member = vm_sa.email.apply(lambda e: f"serviceAccount:{e}")

gcp.projects.IAMMember("sa-secret-accessor",
    project=PROJECT_ID,
    role="roles/secretmanager.secretAccessor",
    member=sa_member,
)
gcp.projects.IAMMember("sa-log-writer",
    project=PROJECT_ID,
    role="roles/logging.logWriter",
    member=sa_member,
)

# ---------------------------------------------------------------------------
# Secrets  (set values via: pulumi config set --secret <name> <value>)
# ---------------------------------------------------------------------------
SECRET_NAMES = ["telegram_token", "telegram_chat_id", "reitbuch_user", "reitbuch_password"]

for name in SECRET_NAMES:
    secret = gcp.secretmanager.Secret(
        f"secret-{name}",
        secret_id=name.upper(),
        replication=gcp.secretmanager.SecretReplicationArgs(
            auto=gcp.secretmanager.SecretReplicationAutoArgs(),
        ),
        opts=pulumi.ResourceOptions(depends_on=[api_services["secretmanager"]]),
    )
    gcp.secretmanager.SecretVersion(
        f"secret-version-{name}",
        secret=secret.id,
        secret_data=config.require_secret(name),
    )

# ---------------------------------------------------------------------------
# VM startup script — setzt Python/uv/systemd auf, wartet auf ersten Deploy
# ---------------------------------------------------------------------------
startup_script = f"""#!/bin/bash
set -euxo pipefail

PROJECT="{PROJECT_ID}"

# Python + uv
apt-get update -y
apt-get install -y python3 python3-pip curl
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="/root/.local/bin:$PATH"

# Arbeitsverzeichnis
mkdir -p /opt/autoreitbuch

# Credentials aus Secret Manager holen und in .env schreiben
# (wird beim ersten 'make deploy' überschrieben — hier nur als Vorlage)
TELEGRAM_TOKEN=$(gcloud secrets versions access latest --secret=TELEGRAM_TOKEN --project=$PROJECT)
TELEGRAM_CHAT_ID=$(gcloud secrets versions access latest --secret=TELEGRAM_CHAT_ID --project=$PROJECT)
REITBUCH_USER=$(gcloud secrets versions access latest --secret=REITBUCH_USER --project=$PROJECT)
REITBUCH_PASSWORD=$(gcloud secrets versions access latest --secret=REITBUCH_PASSWORD --project=$PROJECT)

cat > /opt/autoreitbuch/.env <<EOF
TELEGRAM_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID
REITBUCH_USER=$REITBUCH_USER
REITBUCH_PASSWORD=$REITBUCH_PASSWORD
EOF

# systemd Service
cat > /etc/systemd/system/autoreitbuch.service <<'UNIT'
[Unit]
Description=Autoreitbuch Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/autoreitbuch
EnvironmentFile=/opt/autoreitbuch/.env
ExecStart=/root/.local/bin/uv run python src/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable autoreitbuch
# Service startet erst wenn Code via 'make deploy' hochgeladen wurde
"""

# ---------------------------------------------------------------------------
# Firewall: SSH
# ---------------------------------------------------------------------------
gcp.compute.Firewall(
    "allow-ssh",
    network="default",
    allows=[gcp.compute.FirewallAllowArgs(protocol="tcp", ports=["22"])],
    target_tags=["autoreitbuch"],
    source_ranges=["0.0.0.0/0"],
)

# ---------------------------------------------------------------------------
# e2-micro VM (always free in us-central1)
# ---------------------------------------------------------------------------
vm = gcp.compute.Instance(
    "autoreitbuch-vm",
    machine_type="e2-micro",
    zone=ZONE,
    tags=["autoreitbuch"],
    boot_disk=gcp.compute.InstanceBootDiskArgs(
        initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
            image="debian-cloud/debian-12",
            size=20,
        ),
    ),
    network_interfaces=[gcp.compute.InstanceNetworkInterfaceArgs(
        network="default",
        access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs()],
    )],
    service_account=gcp.compute.InstanceServiceAccountArgs(
        email=vm_sa.email,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    ),
    metadata_startup_script=startup_script,
)

pulumi.export("vm_ip", vm.network_interfaces[0].access_configs[0].nat_ip)

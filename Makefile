PROJECT  = autoreitbuch-bot
REGION   = us-central1
ZONE     = $(REGION)-a
VM       = autoreitbuch-vm-cddf6d9

.PHONY: infra deploy redeploy logs ssh

## Infrastruktur hochfahren (einmalig / bei Änderungen)
infra:
	cd infra && pulumi up

## Code auf die VM kopieren + Bot (neu)starten
deploy:
	tar czf - --exclude='*/__pycache__' --exclude='*.pyc' src/ pyproject.toml uv.lock | \
	  gcloud compute ssh $(VM) --zone=$(ZONE) --project=$(PROJECT) -- \
	  "cd /opt/autoreitbuch && tar xzf - && sudo /root/.local/bin/uv sync --no-dev && sudo systemctl restart autoreitbuch"

## Nur Bot neustarten (kein Code-Upload)
redeploy:
	gcloud compute ssh $(VM) --zone=$(ZONE) --project=$(PROJECT) -- \
	  "sudo systemctl restart autoreitbuch"

## Bot-Logs live verfolgen
logs:
	gcloud compute ssh $(VM) --zone=$(ZONE) --project=$(PROJECT) -- \
	  "sudo journalctl -u autoreitbuch -f"

## SSH in die VM
ssh:
	gcloud compute ssh $(VM) --zone=$(ZONE) --project=$(PROJECT)


# PVE-Onetimeopenclaw

**Ein Befehl auf dem Proxmox-Node: Ubuntu-VM wird angelegt, OpenClaw installiert, Onboarding startet.**

## One-Click auf dem Proxmox-Node

Auf dem **Proxmox-Host (Node)** als **root** einmal ausführen:

```bash
curl -fsSL https://raw.githubusercontent.com/DEIN-GITHUB-USER/PVE-Onetimeopenclaw/main/install.sh | bash
```

**Was passiert:**

1. Es wird eine **Ubuntu-24.04-VM** (Cloud-Image) erstellt und gestartet (Standard-VMID: 9001).
2. Darin wird **OpenClaw** per offiziellem Ansible-Installer eingerichtet.
3. Im gleichen Terminal startet **OpenClaw-Onboarding** (Channels, Tailscale, Daemon usw.).

Danach läuft OpenClaw in der VM. Später verbinden: `ssh -i /root/.openclaw-oneclick-key ubuntu@<VM-IP>`.

## Optionen (Umgebungsvariablen)

- `OPENCLAW_VMID=9001` – VMID der VM (Standard: 9001)
- `OPENCLAW_VMNAME=openclaw-ubuntu` – Name der VM
- `OPENCLAW_STORAGE=local-lvm` – Proxmox-Speicher für Disk/Cloud-Init

## Voraussetzungen (Node)

- **Proxmox VE** (auf dem Node ausführen)
- **root**
- Internet (für Ubuntu-Image und OpenClaw)
- Speicher `local-lvm` (oder per `OPENCLAW_STORAGE` anpassen)

## Ohne Proxmox (nur Debian/Ubuntu)

Wenn du das Skript **nicht** auf einem Proxmox-Node ausführst (z. B. direkt auf einem Ubuntu-Server), wird OpenClaw wie bisher auf **diesem** System installiert und das Onboarding dort gestartet.

---

Details und Ablauf: [PLAN.md](PLAN.md).

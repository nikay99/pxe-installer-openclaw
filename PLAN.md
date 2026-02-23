# Plan: One-Click OpenClaw auf Proxmox

## Ziel

**Ein Befehl auf dem Proxmox-Node:** Ubuntu-VM wird angelegt, OpenClaw darin installiert, Onboarding startet. Der User macht einmal `curl … | bash` auf dem Node – fertig.

---

## Was wir brauchen (auf dem Node)

| Was | Details |
|-----|--------|
| **Wo** | Proxmox-Node (Shell als root) |
| **Rechte** | root |
| **Netzwerk** | Internet (Ubuntu-Image, OpenClaw) |
| **Speicher** | z. B. `local-lvm` (per `OPENCLAW_STORAGE` änderbar) |
| **Nutzeraktion** | Eine Zeile: `curl -fsSL <URL> \| bash` |

---

## Gewählte Methode (auf dem Node)

1. **Proxmox erkannt** (`/etc/pve`, `qm` vorhanden):
   - Ubuntu-24.04-Cloud-Image herunterladen (gecacht in `/var/lib/vz/template/cache/`).
   - VM anlegen (Standard-VMID 9001): `qm create`, Disk importieren, Cloud-Init (User `ubuntu`, SSH-Key).
   - VM starten, per Guest Agent die IP holen, auf SSH warten.
   - In der VM: offiziellen OpenClaw-Installer ausführen (`curl … | bash`).
   - Im gleichen Terminal: `ssh -t ubuntu@<VM-IP> 'sudo -i -u openclaw openclaw onboard --install-daemon'` → User landet im Onboarding.
   - SSH-Key bleibt unter `/root/.openclaw-oneclick-key` für spätere Verbindung.

2. **Kein Proxmox** (normales Debian/Ubuntu):
   - Wie bisher: offiziellen Installer auf diesem System ausführen, danach Onboarding starten.

---

## Ablauf (ein curl auf dem Node)

1. User führt auf dem **Proxmox-Node** aus:  
   `curl -fsSL https://raw.githubusercontent.com/<DEIN-USER>/PVE-Onetimeopenclaw/main/install.sh | bash`
2. Skript erkennt Proxmox, legt Ubuntu-VM an, startet sie, wartet auf SSH.
3. In der VM: OpenClaw wird installiert (Ansible, systemd, Tailscale, UFW, Docker usw.).
4. Skript startet **automatisch** das Onboarding in der VM (gleiches Terminal) – User macht dort Channels, Daemon usw.
5. Danach: VM läuft mit OpenClaw; Verbindung z. B. mit `ssh -i /root/.openclaw-oneclick-key ubuntu@<VM-IP>`.

---

## Was in der Ubuntu-VM installiert wird (offizieller Installer)

- Systemd-Service (openclaw), Auto-Start, Hardening
- OpenClaw, Node.js 22.x + pnpm
- Docker CE + Compose V2 (Agent-Sandboxen), UFW, Tailscale

---

## Nächste Schritte nach der Installation (User)

Das Onboarding startet **automatisch** in der VM (im gleichen Terminal). Dort: Tailscale, Channels (WhatsApp/Telegram/…), Daemon einrichten.

Später erneut in die VM: `ssh -i /root/.openclaw-oneclick-key ubuntu@<VM-IP>`, dann ggf. `sudo -i -u openclaw` und `openclaw onboard --install-daemon`.

---

## Dateien in diesem Projekt

| Datei | Zweck |
|-------|--------|
| `PLAN.md` | Dieser Plan |
| `install.sh` | One-Click-Installer (Prüfungen + Aufruf offizieller Installer) |
| `README.md` | Kurzanleitung + die eine curl-Zeile für den User |

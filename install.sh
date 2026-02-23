#!/bin/bash
# PVE-Onetimeopenclaw: One-Click auf dem Proxmox-Node
# Legt eine Ubuntu-VM an, installiert darin OpenClaw und startet das Onboarding.
# Ein Befehl auf dem Node – fertig.
set -e

OPENCLAW_INSTALL_URL="https://raw.githubusercontent.com/openclaw/openclaw-ansible/main/install.sh"
UBUNTU_IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
VMID="${OPENCLAW_VMID:-9001}"
VMNAME="${OPENCLAW_VMNAME:-openclaw-ubuntu}"
STORAGE="${OPENCLAW_STORAGE:-local-lvm}"
CACHE_DIR="/var/lib/vz/template/cache"
IMAGE_CACHE="$CACHE_DIR/openclaw-ubuntu-noble-amd64.img"

echo "=============================================="
echo "  PVE-Onetimeopenclaw – One-Click auf dem Node"
echo "=============================================="
echo ""

# ---- Nur auf Proxmox-Node: Ubuntu-VM anlegen und OpenClaw darin installieren ----
if [ -d /etc/pve ] && command -v qm &>/dev/null; then
  echo "[OK] Proxmox-Node erkannt. Erstelle Ubuntu-VM und installiere OpenClaw darin."
  echo ""

  if [ "$EUID" -ne 0 ]; then
    echo "FEHLER: Bitte als root auf dem Proxmox-Node ausführen."
    exit 1
  fi

  WORK_DIR=$(mktemp -d)
  KEY_FILE="/root/.openclaw-oneclick-key"
  ssh-keygen -t rsa -b 2048 -f "$KEY_FILE" -N "" -q

  # Ubuntu-Image cachen
  mkdir -p "$CACHE_DIR"
  if [ ! -f "$IMAGE_CACHE" ]; then
    echo "[1/6] Lade Ubuntu-Cloud-Image herunter (einmalig)..."
    wget -q -O "$IMAGE_CACHE" "$UBUNTU_IMAGE_URL" || { echo "Download fehlgeschlagen."; exit 1; }
  else
    echo "[1/6] Ubuntu-Image bereits vorhanden."
  fi

  # Bestehende VM mit dieser ID ggf. stoppen/löschen
  if qm status "$VMID" &>/dev/null; then
    echo "VM $VMID existiert bereits. Stoppe und lösche sie..."
    qm stop "$VMID" 2>/dev/null || true
    qm destroy "$VMID" 2>/dev/null || true
  fi

  echo "[2/6] Erstelle VM $VMID ($VMNAME)..."
  qm create "$VMID" --name "$VMNAME" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0 --scsihw virtio-scsi-pci
  qm set "$VMID" --ide2 "$STORAGE:cloudinit"
  qm importdisk "$VMID" "$IMAGE_CACHE" "$STORAGE"
  DISK=$(qm config "$VMID" | sed -n 's/^unused[0-9]*:[[:space:]]*//p' | head -1)
  [ -z "$DISK" ] && DISK="${STORAGE}:vm-${VMID}-disk-0"
  qm set "$VMID" --scsi0 "$DISK"
  qm set "$VMID" --delete unused0 2>/dev/null || true
  qm set "$VMID" --boot order=scsi0
  qm set "$VMID" --serial0 socket --vga serial0
  qm set "$VMID" --agent enabled=1
  qm set "$VMID" --ciuser ubuntu
  qm set "$VMID" --sshkeys "$KEY_FILE.pub"

  echo "[3/6] Starte VM..."
  qm start "$VMID"

  echo "[4/6] Warte auf Gast-IP (Guest Agent)..."
  VMIP=""
  for i in $(seq 1 30); do
    sleep 5
    OUT=$(qm guest cmd "$VMID" network-get-interfaces 2>/dev/null) || true
    VMIP=$(echo "$OUT" | grep -oP '"ip-address":"\K[^"]+' | grep -v '^127\.' | head -1)
    [ -n "$VMIP" ] && break
  done
  if [ -z "$VMIP" ]; then
    echo "Konnte VM-IP nicht ermitteln. Bitte prüfe die VM (VMID $VMID) und verbinde manuell:"
    echo "  ssh -i $KEY_FILE ubuntu@<VM-IP>"
    echo "  curl -fsSL $OPENCLAW_INSTALL_URL | bash"
    echo "  sudo -i -u openclaw openclaw onboard --install-daemon"
    rm -rf "$WORK_DIR"
    exit 1
  fi

  echo "[5/6] Warte auf SSH auf $VMIP..."
  for i in $(seq 1 30); do
    if ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -i "$KEY_FILE" ubuntu@"$VMIP" exit 2>/dev/null; then
      break
    fi
    sleep 5
  done
  if ! ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no -i "$KEY_FILE" ubuntu@"$VMIP" exit 2>/dev/null; then
    echo "SSH zur VM fehlgeschlagen. VM läuft (VMID $VMID). Verbinde manuell:"
    echo "  ssh -i $KEY_FILE ubuntu@$VMIP"
    rm -rf "$WORK_DIR"
    exit 1
  fi

  echo "[6/6] Installiere OpenClaw in der VM..."
  ssh -o StrictHostKeyChecking=accept-new -i "$KEY_FILE" ubuntu@"$VMIP" "curl -fsSL $OPENCLAW_INSTALL_URL | bash" || true

  echo ""
  echo "=============================================="
  echo "  OpenClaw-Onboarding starten (in der VM)"
  echo "=============================================="
  echo "  VM: $VMIP (VMID $VMID) | User: ubuntu | Key: $KEY_FILE"
  echo ""
  ssh -t -o StrictHostKeyChecking=accept-new -i "$KEY_FILE" ubuntu@"$VMIP" "sudo -i -u openclaw openclaw onboard --install-daemon"

  echo ""
  echo "VM läuft weiter. Später verbinden: ssh -i $KEY_FILE ubuntu@$VMIP"
  rm -rf "$WORK_DIR"
  exit 0
fi

# ---- Nicht auf Proxmox: Klassische Installation auf diesem System (Debian/Ubuntu) ----
echo "[OK] Kein Proxmox-Node – installiere OpenClaw auf diesem System."
echo ""

if command -v apt-get &>/dev/null; then
  [ -f /etc/pve/version ] 2>/dev/null && echo "Hinweis: Für Node-Install (Ubuntu-VM mit anlegen) auf dem Proxmox-Host ausführen."
else
  echo "FEHLER: Nur Debian/Ubuntu (oder Proxmox-Node) werden unterstützt."
  exit 1
fi

if [ "$EUID" -ne 0 ] && ! command -v sudo &>/dev/null; then
  echo "FEHLER: Bitte als root ausführen oder sudo installieren."
  exit 1
fi

echo "Starte offiziellen OpenClaw-Ansible-Installer..."
curl -fsSL "$OPENCLAW_INSTALL_URL" | bash

echo ""
echo "=============================================="
echo "  OpenClaw-Onboarding starten ..."
echo "=============================================="
if sudo -u openclaw command -v openclaw &>/dev/null; then
  sudo -i -u openclaw openclaw onboard --install-daemon
else
  echo "  sudo -i -u openclaw"
  echo "  openclaw onboard --install-daemon"
fi

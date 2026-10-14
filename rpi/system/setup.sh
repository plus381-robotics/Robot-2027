#!/usr/bin/env bash
# Primenjuje kompletnu konfiguraciju RPi 4 iz log book-a "Podesavanje Pi".
# Bezbedno je pokretati vise puta: svaki korak proverava stanje pre izmene.
#
#   sudo ./rpi/system/setup.sh            # primeni sve
#   sudo DRY_RUN=1 ./rpi/system/setup.sh  # samo prikazi sta bi uradio
#
# Ne instalira RT kernel ni ROS 2 (to su rucni koraci 2 i 8 iz log book-a).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN="${DRY_RUN:-0}"
TARGET_USER="${SUDO_USER:-pi}"
STAMP="$(date +%Y%m%d-%H%M%S)"

CMDLINE="${CMDLINE:-/boot/firmware/cmdline.txt}"
CONFIG="${CONFIG:-/boot/firmware/config.txt}"
WANTED_CMDLINE="isolcpus=3 rcu_nocbs=3 irqaffinity=0-2"

log()  { echo -e "\e[1;34m[setup]\e[0m $*"; }
warn() { echo -e "\e[1;33m[upozorenje]\e[0m $*"; }
run()  { if [[ "$DRY_RUN" == "1" ]]; then echo "  (dry-run) $*"; else eval "$*"; fi; }
backup() { [[ -f "$1" ]] && run "cp -a '$1' '$1.bak-$STAMP'"; }

if [[ $EUID -ne 0 ]]; then
  echo "Pokreni sa sudo." >&2
  exit 1
fi
if [[ ! -f "$CMDLINE" ]]; then
  echo "$CMDLINE ne postoji. Da li je ovo Ubuntu na Raspberry Pi-ju?" >&2
  exit 1
fi

# --- 1. Kernel parametri -------------------------------------------------------
log "Kernel parametri ($CMDLINE)"
current="$(head -n1 "$CMDLINE")"
cleaned="$(echo "$current" | tr ' ' '\n' \
  | grep -v -E '^(isolcpus|rcu_nocbs|nohz_full|irqaffinity|processor\.max_cstate)=' \
  | grep -v '^$' | tr '\n' ' ' | sed 's/ *$//' || true)"
desired="$cleaned $WANTED_CMDLINE"
if [[ "$current" == "$desired" ]]; then
  log "  vec podeseno"
else
  backup "$CMDLINE"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  (dry-run) upis u $CMDLINE"
  else
    printf '%s\n' "$desired" > "$CMDLINE"
  fi
  log "  novo: $desired"
  NEED_REBOOT=1
fi

# --- 2. GPIO UART iskljucen (Nucleo ide preko USB) -----------------------------
log "Serijski port ($CONFIG)"
if grep -q -E '^\s*(enable_uart=1|dtoverlay=uart1)\s*$' "$CONFIG"; then
  backup "$CONFIG"
  run "sed -i -E 's/^\s*(enable_uart=1|dtoverlay=uart1)\s*$/# \1  # iskljuceno: Nucleo ide preko USB/' '$CONFIG'"
  NEED_REBOOT=1
else
  log "  vec podeseno"
fi
run "systemctl disable --now serial-getty@ttyS0.service serial-getty@ttyAMA0.service 2>/dev/null || true"

# --- 3. Memorija, limiti, RT throttling ----------------------------------------
log "Swap"
run "swapoff -a"
if grep -q -E '^[^#].*\sswap\s' /etc/fstab; then
  backup /etc/fstab
  run "sed -i -E '/^[^#].*\sswap\s/s/^/# /' /etc/fstab"
fi

log "RT limiti (/etc/security/limits.d/99-realtime.conf)"
run "cat > /etc/security/limits.d/99-realtime.conf <<'LIM'
@realtime soft rtprio 99
@realtime hard rtprio 99
@realtime soft memlock unlimited
@realtime hard memlock unlimited
LIM"

log "Grupe za korisnika $TARGET_USER"
run "groupadd -f realtime"
run "usermod -aG realtime,dialout,video '$TARGET_USER'"

log "RT throttling (/etc/sysctl.d/99-realtime.conf)"
run "echo 'kernel.sched_rt_runtime_us = 950000' > /etc/sysctl.d/99-realtime.conf"
run "sysctl -p /etc/sysctl.d/99-realtime.conf >/dev/null"

# --- 4. CPU governor -----------------------------------------------------------
log "CPU governor performance"
run "install -m 0644 '$SCRIPT_DIR/systemd/cpu-performance.service' /etc/systemd/system/"
run "systemctl daemon-reload"
run "systemctl enable --now cpu-performance.service"

# --- 5. Servisi i zastita kernela ----------------------------------------------
log "Iskljucivanje unattended-upgrades i ModemManager"
run "systemctl disable --now unattended-upgrades 2>/dev/null || true"
run "systemctl disable --now ModemManager 2>/dev/null || true"

log "Zamrzavanje RT kernel paketa"
rt_pkgs="$(dpkg -l | awk '$1 ~ /^(ii|hi)$/ && $2 ~ /realtime/ {print $2}' | tr '\n' ' ')"
if [[ -n "$rt_pkgs" ]]; then
  run "apt-mark hold $rt_pkgs >/dev/null"
else
  warn "  RT kernel paketi nisu pronadjeni (da li je RT kernel instaliran?)"
fi

# --- 6. Udev pravila -----------------------------------------------------------
log "Udev pravila (/dev/nucleo, /dev/pico, /dev/lidar)"
run "install -m 0644 '$SCRIPT_DIR/udev/99-eurobot.rules' /etc/udev/rules.d/"
run "udevadm control --reload-rules && udevadm trigger"

# --- 7. Alati ------------------------------------------------------------------
log "Alati (apt) - gcc-arm-none-eabi je velik, ovo moze trajati 10-20 min"
run "apt-get update"
run "DEBIAN_FRONTEND=noninteractive apt-get install -y \
  stlink-tools openocd gcc-arm-none-eabi ninja-build python3-serial picocom \
  rt-tests stress-ng git cmake build-essential"

log "Gotovo."
if [[ "${NEED_REBOOT:-0}" == "1" ]]; then
  warn "Promenjeni su boot fajlovi. Restartuj: sudo reboot"
fi
warn "Promena grupa vazi tek posle ponovne prijave."

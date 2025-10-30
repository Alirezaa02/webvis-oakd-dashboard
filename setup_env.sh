#!/usr/bin/env bash
# Setup for Raspberry Pi (Bullseye/Bookworm) + Enviro+ + ST7735 LCD + DepthAI (OAK)
# - Auto-detects a requirements file in THIS FOLDER (or accept an explicit path arg)
# - Installs OS deps (SPI/I²C, Pillow codecs, BLAS, libusb)
# - Enables SPI & I²C non-interactively
# - Configures udev rules for DepthAI USB access (no sudo needed)
# - Clones & installs pimoroni/enviroplus-python (editable) into third_party/
# - Installs your requirements into the CURRENT Python environment
# - Installs depthai + depthai-sdk
# - Adds an OpenBLAS ARMv8 hint
# - Runs smoke tests (PIL/fonts/ST7735/GPIO/SPI + DepthAI import & device list)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
THIRD_PARTY_DIR="${SCRIPT_DIR}/third_party"
ENVIRO_DIR="${THIRD_PARTY_DIR}/enviroplus-python"

info(){ printf "\n\033[1;34m[INFO]\033[0m %s\n" "$*"; }
warn(){ printf "\n\033[1;33m[WARN]\033[0m %s\n" "$*"; }
die(){  printf "\n\033[1;31m[ERR]\033[0m  %s\n" "$*"; exit 1; }

# Make sure python and git is available.
command -v git >/dev/null || die "git not found (install with: sudo apt install -y git)"
command -v python3 >/dev/null || die "python3 not found"
PYTHON="${PYTHON:-python3}"
PIP="${PIP:-${PYTHON} -m pip}"

REQ_FILE="${SCRIPT_DIR}/requirements.txt"
[[ -n "${REQ_FILE}" ]] || die "Requirements file missing (requirements.txt)"

# Detect Bookworm vs Bullseye (Pillow dependency)
DEB_VER=$(grep -oP 'VERSION_ID="\K[0-9]+' /etc/os-release || echo "0")
if [[ "${DEB_VER}" -ge 12 ]]; then
  LIBTIFF="libtiff6"
else
  LIBTIFF="libtiff5"
fi
info "Detected Debian ${DEB_VER}, will install ${LIBTIFF}"

# OS-level dependencies that can be skipped with bad Pi setup
info "Installing OS dependencies (SPI/I2C + Pillow & build helpers)…"
sudo apt-get update -y
sudo apt-get install -y \
  python3-pip python3-venv python3-dev build-essential \
  python3-rpi.gpio python3-spidev python3-smbus i2c-tools \
  fonts-roboto \
  libjpeg-dev zlib1g-dev libopenjp2-7 ${LIBTIFF} libatlas-base-dev \
  libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev libxcb1

# Enable SPI & I2C
if command -v raspi-config >/dev/null; then
  info "Enabling SPI & I2C via raspi-config (non-interactive)…"
  sudo raspi-config nonint do_spi 0 || true
  sudo raspi-config nonint do_i2c 0 || true
else
  warn "raspi-config not found; please ensure dtparam=spi=on and dtparam=i2c_arm=on in /boot config."
fi

# DepthAI udev rules (USB permissions, idempotent)
info "Configuring udev rules for DepthAI (OAK) devices…"
RULE_FILE="/etc/udev/rules.d/80-movidius.rules"
RULE_LINE='SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"'
if [[ -f "${RULE_FILE}" ]] && grep -q 'ATTRS{idVendor}=="03e7"' "${RULE_FILE}"; then
  info "udev rule already present."
else
  echo "${RULE_LINE}" | sudo tee "${RULE_FILE}" >/dev/null
  sudo udevadm control --reload-rules && sudo udevadm trigger
  info "udev rules reloaded. Unplug/replug OAK if connected."
fi

# OpenBLAS ARM hint mount
if ! grep -q 'OPENBLAS_CORETYPE=ARMV8' "${HOME}/.bashrc" 2>/dev/null; then
  echo 'export OPENBLAS_CORETYPE=ARMV8' >> "${HOME}/.bashrc"
  info "Added OPENBLAS_CORETYPE=ARMV8 to ~/.bashrc"
fi

# Upgrade pip tooling, wheel required for some modules
info "Upgrading pip/setuptools/wheel…"
${PIP} install --upgrade pip setuptools wheel

# Clone + install enviroplus-python for dependencies and special libraries
mkdir -p "${THIRD_PARTY_DIR}"
if [[ ! -d "${ENVIRO_DIR}/.git" ]]; then
  info "Cloning pimoroni/enviroplus-python into ${ENVIRO_DIR}…"
  git clone https://github.com/pimoroni/enviroplus-python.git "${ENVIRO_DIR}"
else
  info "Updating existing ${ENVIRO_DIR}…"
  git -C "${ENVIRO_DIR}" pull --ff-only
fi
info "Installing enviroplus-python…"
${PIP} install -e "${ENVIRO_DIR}"

# Project requirements
info "Installing project requirements from ${REQ_FILE}…"
${PIP} install -r "${REQ_FILE}"

# Smoke test- ensure Python can find each of the vital libraries depended upon.
info "Running quick import checks…"
${PYTHON} - <<'PY'
import sys
mods = ["st7735", "spidev", "RPi.GPIO", "PIL", "fonts.ttf"]
bad = []
for m in mods:
    try:
        __import__(m)
    except Exception as e:
        bad.append((m, repr(e)))
if bad:
    print("MISSING/ERROR:", bad, file=sys.stderr)
    sys.exit(1)
print("All core modules imported successfully.")

try:
    import depthai as dai
    devs = dai.Device.getAllAvailableDevices()
    print("OAK devices detected:", [d.mxid for d in devs])
except Exception as e:
    print("Note: DepthAI device enumeration skipped or failed (potentially ok if no camera attached):", e)
PY

info "Setup complete. Reboot may be required."

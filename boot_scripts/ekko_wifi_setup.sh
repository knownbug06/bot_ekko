#!/bin/bash

PORTAL_SSID="Ekko-WiFi-Setup"
PORTAL_PASS="ekko1234"
UI_DIR="/usr/local/share/wifi-connect/ui"
CONNECT_TIMEOUT=60   # seconds to wait for NM to establish internet
CHECK_INTERVAL=5
PORTAL_ACTIVITY_TIMEOUT=300  # seconds before wifi-connect gives up (no phone connected)

log() { echo "$(date '+%Y-%m-%d %H:%M:%S'): $*"; }

has_internet() {
    ping -c1 -W5 8.8.8.8 &>/dev/null || ping -c1 -W5 1.1.1.1 &>/dev/null
}

# Wait for NetworkManager to be ready before doing anything
until nmcli general status &>/dev/null; do
    sleep 2
done

log "Waiting up to ${CONNECT_TIMEOUT}s for internet..."
elapsed=0
while [ $elapsed -lt $CONNECT_TIMEOUT ]; do
    if has_internet; then
        log "Internet available — skipping setup portal"
        exit 0
    fi
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
done

log "No internet after ${CONNECT_TIMEOUT}s — launching setup portal (SSID: $PORTAL_SSID)"
wifi-connect \
    --portal-ssid "$PORTAL_SSID" \
    --portal-passphrase "$PORTAL_PASS" \
    --ui-directory "$UI_DIR" \
    --activity-timeout "$PORTAL_ACTIVITY_TIMEOUT"

wc_exit=$?
log "wifi-connect exited with code $wc_exit"

# Give NM a moment to connect to the newly configured network
sleep 15

if has_internet; then
    log "Internet now available — done"
    exit 0
fi

log "Still no internet — service will restart and retry"
exit 1

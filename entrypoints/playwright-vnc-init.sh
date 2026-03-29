#!/bin/bash

VNC_PORT=${VNC_PORT:-5900}
NOVNC_PORT=${NOVNC_PORT:-6080}
export DISPLAY=:0

start_xvfb() {
  # Large virtual framebuffer so xrandr can resize down to any client viewport
  Xvfb :0 -screen 0 1920x1080x24 +extension RANDR &>/tmp/xvfb.log &
  echo $! > /tmp/xvfb.pid
  echo "[vnc-init] Xvfb started (pid $!)"
}

start_x11vnc() {
  # Wait for display to be ready
  for i in $(seq 1 20); do
    xdpyinfo -display :0 >/dev/null 2>&1 && break
    sleep 0.5
  done
  x11vnc -display :0 -forever -nopw -rfbport "$VNC_PORT" -xrandr &>/tmp/x11vnc.log &
  echo $! > /tmp/x11vnc.pid
  echo "[vnc-init] x11vnc started (pid $!)"
}

start_fluxbox() {
  fluxbox &>/tmp/fluxbox.log &
  echo $! > /tmp/fluxbox.pid
  echo "[vnc-init] fluxbox started (pid $!)"
}

start_websockify() {
  # Write index.html as a standalone redirect (not a symlink) to the full noVNC viewer.
  # IMPORTANT: never symlink or overwrite vnc.html — it is the full noVNC UI with toolbar.
  rm -f /usr/share/novnc/index.html
  cat > /usr/share/novnc/index.html <<'EOF'
<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=vnc.html?autoconnect=true&resize=remote">
</head><body></body></html>
EOF
  websockify --web /usr/share/novnc/ "$NOVNC_PORT" "localhost:$VNC_PORT" &>/tmp/websockify.log &
  echo $! > /tmp/websockify.pid
  echo "[vnc-init] websockify started (pid $!)"
}

is_running() {
  local pid_file=$1
  [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null
}

# Initial startup
start_xvfb
sleep 1
start_x11vnc
start_fluxbox
sleep 1
start_websockify

echo "[vnc-init] All services started. Watchdog running..."

# Watchdog loop — restart any crashed process
while true; do
  sleep 5

  if ! is_running /tmp/xvfb.pid; then
    echo "[vnc-init] Xvfb crashed — restarting..."
    start_xvfb
    sleep 1
  fi

  if ! is_running /tmp/x11vnc.pid; then
    echo "[vnc-init] x11vnc crashed — restarting..."
    start_x11vnc
  fi

  if ! is_running /tmp/fluxbox.pid; then
    echo "[vnc-init] fluxbox crashed — restarting..."
    start_fluxbox
  fi

  if ! is_running /tmp/websockify.pid; then
    echo "[vnc-init] websockify crashed — restarting..."
    start_websockify
  fi
done

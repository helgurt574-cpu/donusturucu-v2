#!/bin/sh
export GDK_BACKEND=x11
unset WAYLAND_DISPLAY
export PATH="/home/gabar/codex_cubic/donusturucu/build/qa-tools/root/usr/bin:$PATH"
exec /home/gabar/codex_cubic/donusturucu/build/qa-tools/root/usr/bin/xvfb-run "$@"

#!/usr/bin/env bash
# /etc/profile.d/picobird-console.sh
#
# Auto-launches the picoBird Pro admin console when a user logs in on
# the physical console (tty1-tty6) with an HDMI display connected.
# SSH sessions exit immediately without displaying anything.

export PYTHONPATH="/opt/picobird-pro"

alias picobird-console='PYTHONPATH=/opt/picobird-pro /opt/picobird-pro/venv/bin/python -m server.console'

# Only auto-launch on a physical TTY (not SSH / serial).
case "$(tty)" in
    /dev/tty[1-6])
        PYTHONPATH=/opt/picobird-pro /opt/picobird-pro/venv/bin/python -m server.console
        ;;
esac

#!/usr/bin/env bash
# /etc/profile.d/picobird-console.sh
#
# Auto-launches the picoBird Pro admin console when a user logs in on
# the physical console (tty1-tty6) with an HDMI display connected.
# SSH sessions exit immediately without displaying anything.
#
# Also installs a 'picobird-console' alias for manual re-launch.

alias picobird-console='/opt/picobird-pro/venv/bin/python -m server.console'

# Only auto-launch on a physical TTY (not SSH / serial).
case "$(tty)" in
    /dev/tty[1-6])
        /opt/picobird-pro/venv/bin/python -m server.console
        ;;
esac

#!/bin/bash
# Backward-compatible wrapper.
# Il launcher ufficiale è OpenHackintosh.command.
cd "$(dirname "$0")" || exit 1
exec bash ./OpenHackintosh.command "$@"

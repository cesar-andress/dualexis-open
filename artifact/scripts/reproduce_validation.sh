#!/usr/bin/env bash
# Thin wrapper — prefer artifact/commands.sh
set -euo pipefail
exec bash "$(dirname "$0")/../commands.sh"

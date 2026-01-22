#!/bin/bash

set -e

HOST="${1:-user@beelink-linux.local}"
shift 2>/dev/null || true
ssh "$HOST" journalctl -u vastai-scraper ${@:--f -n 50}

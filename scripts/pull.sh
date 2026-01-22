#!/bin/bash

set -e

HOST="${1:-user@beelink-linux.local}"
REMOTE_DIR="~/vastai-scraper/data"
LOCAL_DIR="./data"

mkdir -p "$LOCAL_DIR"
rsync -avz --delete --include='*.csv' --exclude='*' "$HOST:$REMOTE_DIR/" "$LOCAL_DIR/"

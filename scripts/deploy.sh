#!/bin/bash

set -e

HOST="${1:-user@beelink-linux.local}"
REMOTE_DIR="~/vastai-scraper"

echo "Deploying to $HOST..."

# Sync files
rsync -avz \
    --delete \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='data/' \
    --exclude='.DS_Store' \
    . \
    "$HOST:$REMOTE_DIR/"

# Install dependencies and restart service
ssh "$HOST" << 'EOF'
    set -e
    command -v node >/dev/null || { echo "node not found in PATH"; exit 1; }
    cd ~/vastai-scraper
    command -v pnpm >/dev/null || npm install -g pnpm
    pnpm install --prod
    sudo systemctl link "$(pwd)/systemd/vastai-scraper.service" 2>/dev/null || true
    sudo systemctl daemon-reload
    sudo systemctl enable vastai-scraper
    sudo systemctl restart vastai-scraper
    sleep 5
    sudo systemctl status vastai-scraper --no-pager
    sudo journalctl -u vastai-scraper -n 50 --no-pager --since "10 seconds ago"
EOF

echo "Deploy complete."

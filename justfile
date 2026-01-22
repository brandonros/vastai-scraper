set shell := ["bash", "-uc"]

default_host := "user@beelink-linux.local"

# Run analysis
analyze:
    cd analysis && uv run analyze.py

# Deploy to remote host
deploy host=default_host:
    #!/bin/bash
    set -e
    echo "Deploying to {{host}}..."
    rsync -avz \
        --delete \
        --exclude='.git/' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='node_modules/' \
        --exclude='.DS_Store' \
        --exclude='data/' \
        --exclude='analysis/' \        
        . \
        "{{host}}:~/vastai-scraper/"
    ssh "{{host}}" << 'EOF'
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

# Monitor logs on remote host
monitor host=default_host *args="-f -n 50":
    ssh "{{host}}" journalctl -u vastai-scraper {{args}}

# Pull data from remote host
pull host=default_host:
    mkdir -p ./data
    rsync -avz --delete --include='*.csv' --exclude='*' "{{host}}:~/vastai-scraper/data/" ./data/

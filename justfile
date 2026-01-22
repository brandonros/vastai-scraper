set shell := ["bash", "-uc"]

default_host := "user@beelink-linux.local"

# Run scraper locally
run:
    pnpm install
    node index.mjs

# Run analysis
analyze:
    cd analysis && uv run analyze.py

# Deploy to remote host
deploy host=default_host:
    #!/bin/bash
    set -e
    REPO="git@github.com:brandonros/vastai-scraper.git"
    echo "Deploying to {{host}}..."
    ssh "{{host}}" << EOF
        set -e
        if [ -d ~/vastai-scraper/.git ]; then
            echo "Pulling latest..."
            cd ~/vastai-scraper && git pull
        else
            echo "Cloning repo..."
            git clone "$REPO" ~/vastai-scraper
        fi
        command -v node >/dev/null || { echo "node not found in PATH"; exit 1; }
        cd ~/vastai-scraper
        command -v pnpm >/dev/null || npm install -g pnpm
        pnpm install --prod
        sudo systemctl link "\$(pwd)/systemd/vastai-scraper.service" 2>/dev/null || true
        sudo systemctl daemon-reload
        sudo systemctl enable vastai-scraper
        sudo systemctl restart vastai-scraper
        sleep 5
        sudo systemctl status vastai-scraper --no-pager
    EOF
    echo "Deploy complete."

# Monitor logs on remote host
monitor host=default_host *args="-f -n 50":
    ssh "{{host}}" journalctl -u vastai-scraper {{args}}

# Pull data from remote host
pull host=default_host:
    mkdir -p ./data
    rsync -avz --delete --include='*.csv' --exclude='*' "{{host}}:~/vastai-scraper/data/" ./data/

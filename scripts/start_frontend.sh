#!/bin/bash
cd "$(dirname "$0")/../frontend"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 22 2>/dev/null || echo "Using system node..."
npm run dev

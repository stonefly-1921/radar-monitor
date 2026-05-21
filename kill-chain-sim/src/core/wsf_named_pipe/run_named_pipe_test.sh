#!/bin/bash
# run_named_pipe_test.sh
# Starts Python pipe server first, then runs AFSIM with the named pipe test scenario
# Must be run from project root or adjust paths

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$HOME/.openclaw/workspace/kill-chain-sim"
AFSIM_BIN="D:/afsim-2.9.0-win64/bin/mission.exe"
SCENARIO="$WORKSPACE/src/sim/kill_chain_named_pipe_test.txt"
PIPE_SERVER="$WORKSPACE/src/core/wsf_named_pipe/wsf_named_pipe_server.py"

echo "=== Starting Kill Chain Pipe Server ==="
echo "Start Python pipe server manually in another terminal:"
echo "  python $PIPE_SERVER"
echo ""
echo "Then run AFSIM with:"
echo "  $AFSIM_BIN $SCENARIO"

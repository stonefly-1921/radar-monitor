#!/bin/bash
# Run kill_chain_np_multi 3 times and collect results
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim

for i in 1 2 3; do
  echo "===== RUN $i/3 ====="
  rm -f afsim_track_out.txt kill_chain_np_ack.txt kill_chain_np_cmd.txt sensor_cmd.txt
  python src/tools/kill_chain_np_fire_controller.py --scenario src/sim/kill_chain_np_multi.txt
  echo "EXIT: $?"
  echo ""
done

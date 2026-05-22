"""Verify kill chain stats using the controller's own logic."""
import sys
sys.path.insert(0, r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\tools")
from kill_chain_np_fire_controller import KillChainController

c = KillChainController(r"C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\sim\kill_chain_np_multi.txt")
c.run()

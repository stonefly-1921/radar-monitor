@echo off
:: DIS Track Monitor - listens for AFSIM entity state PDUs
cd /d C:\Users\15041\.openclaw\workspace\kill-chain-sim
set PYTHONPATH=C:\Users\15041\.openclaw\workspace\kill-chain-sim;%PYTHONPATH%
python src\tools\dis_track_monitor.py
@echo off
echo Starting SLA Monitoring Scheduler...
echo This will check for SLA breaches every 15 minutes.
echo Press Ctrl+C to stop the scheduler.
echo.

python scripts/scheduler.py

pause

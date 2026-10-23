"""
scheduler.py — Task scheduler for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import sys
import os
import time
from datetime import datetime

# Add the parent directory to the path so we can import from services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sla_service import check_sla_breaches, get_sla_status


def run_sla_monitoring():
    """Run SLA monitoring and print results."""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running SLA monitoring...")
        
        alerted_escalations = check_sla_breaches()
        status = get_sla_status()
        
        print(f"   SLA Status: {status['total_assigned']} assigned, {status['overdue_count']} overdue, {status['warning_count']} warning")
        
        if alerted_escalations:
            print(f"   ✅ Sent {len(alerted_escalations)} SLA breach alerts")
        else:
            print("   ✅ No SLA breaches detected")
            
    except Exception as e:
        print(f"   ❌ Error in SLA monitoring: {e}")


def main():
    """Main scheduler loop."""
    print("=" * 60)
    print("Leila IT Help Desk - Task Scheduler Started")
    print("=" * 60)
    print("SLA monitoring will run every 15 minutes")
    print("Press Ctrl+C to stop the scheduler")
    print("=" * 60)
    
    try:
        # Run immediately on start
        run_sla_monitoring()
        
        # Then run every 15 minutes (900 seconds)
        while True:
            time.sleep(900)  # 15 minutes
            run_sla_monitoring()
            
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("Scheduler stopped by user")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Scheduler error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

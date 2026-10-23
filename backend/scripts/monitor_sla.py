"""
monitor_sla.py — Scheduled SLA monitoring script for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sla_service import check_sla_breaches, get_sla_status


def main():
    """Main function to run SLA monitoring."""
    print("=" * 60)
    print(f"SLA Monitoring Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check for SLA breaches and send alerts
    try:
        alerted_escalations = check_sla_breaches()
        print(f"✅ SLA breach alerts sent for {len(alerted_escalations)} escalations")
        
        if alerted_escalations:
            print(f"   Alerted escalation IDs: {', '.join(alerted_escalations)}")
        else:
            print("   No SLA breaches detected")
            
    except Exception as e:
        print(f"❌ Error during SLA breach check: {e}")
        return 1
    
    # Get and display SLA status
    try:
        status = get_sla_status()
        print("\n📊 SLA Status Summary:")
        print(f"   Total assigned escalations: {status['total_assigned']}")
        print(f"   Overdue escalations: {status['overdue_count']}")
        print(f"   Warning escalations (within 2h of breach): {status['warning_count']}")
        print(f"   SLA period: {status['sla_hours']} hours")
        
    except Exception as e:
        print(f"❌ Error getting SLA status: {e}")
        return 1
    
    print("=" * 60)
    print("SLA monitoring check completed successfully")
    return 0


if __name__ == "__main__":
    from datetime import datetime
    exit_code = main()
    sys.exit(exit_code)

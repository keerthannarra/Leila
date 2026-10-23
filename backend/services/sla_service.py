"""
sla_service.py — SLA monitoring service for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import List

from database import SessionLocal
from models import Escalation, User
from services.notification_service import send_sla_breach_alert


SLA_HOURS = 4  # SLA period in hours


def check_sla_breaches() -> List[str]:
    """
    Check for escalations that have exceeded SLA and send alerts.
    
    Returns:
        List of escalation IDs that were alerted
    """
    alerted_escalations = []
    
    with SessionLocal() as db:
        # Get all assigned escalations that are not resolved and exceed SLA
        sla_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=SLA_HOURS)
        
        overdue_escalations = db.query(Escalation).filter(
            Escalation.assigned_agent_id.isnot(None),
            Escalation.resolution_status != 'resolved',
            Escalation.created_at < sla_threshold
        ).all()
        
        for escalation in overdue_escalations:
            # Calculate how overdue the escalation is
            hours_overdue = (datetime.now(timezone.utc).replace(tzinfo=None) - escalation.created_at).total_seconds() / 3600 - SLA_HOURS
            
            # Get agent details
            agent = db.query(User).filter(User.id == escalation.assigned_agent_id).first()
            
            if agent:
                # Send SLA breach alert
                jira_url = f"{os.getenv('JIRA_URL', '')}/browse/{escalation.jira_reference}" if escalation.jira_reference else ""
                
                success = send_sla_breach_alert(
                    agent_email=agent.email,
                    agent_name=agent.name,
                    jira_url=jira_url,
                    original_query=escalation.original_query,
                    hours_overdue=hours_overdue
                )
                
                if success:
                    alerted_escalations.append(escalation.id)
                    print(f"SLA breach alert sent for escalation {escalation.id} to agent {agent.name}")
                else:
                    print(f"Failed to send SLA breach alert for escalation {escalation.id}")
            else:
                print(f"Agent not found for escalation {escalation.id}")
    
    return alerted_escalations


def get_sla_status() -> dict:
    """
    Get SLA status summary for monitoring.
    
    Returns:
        Dict with SLA statistics
    """
    with SessionLocal() as db:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Total assigned escalations
        total_assigned = db.query(Escalation).filter(
            Escalation.assigned_agent_id.isnot(None),
            Escalation.resolution_status != 'resolved'
        ).count()
        
        # Overdue escalations
        sla_threshold = now - timedelta(hours=SLA_HOURS)
        overdue_count = db.query(Escalation).filter(
            Escalation.assigned_agent_id.isnot(None),
            Escalation.resolution_status != 'resolved',
            Escalation.created_at < sla_threshold
        ).count()
        
        # Warning escalations (within 2 hours of SLA breach)
        warning_threshold = now - timedelta(hours=SLA_HOURS - 2)
        warning_count = db.query(Escalation).filter(
            Escalation.assigned_agent_id.isnot(None),
            Escalation.resolution_status != 'resolved',
            Escalation.created_at < warning_threshold,
            Escalation.created_at >= sla_threshold
        ).count()
        
        return {
            "total_assigned": total_assigned,
            "overdue_count": overdue_count,
            "warning_count": warning_count,
            "sla_hours": SLA_HOURS,
            "check_time": now.isoformat()
        }


if __name__ == "__main__":
    # Run SLA check when executed directly
    print("Running SLA breach check...")
    alerted = check_sla_breaches()
    print(f"SLA breach alerts sent for {len(alerted)} escalations")
    
    # Print SLA status
    status = get_sla_status()
    print(f"SLA Status: {status}")

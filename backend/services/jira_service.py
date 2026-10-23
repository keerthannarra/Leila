"""
jira_service.py — Jira API integration for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import json
import os
from typing import Optional, Dict, Any
from jira import JIRA

from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL", "")
JIRA_USERNAME = os.getenv("JIRA_USERNAME", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "IT")

_client: Optional[JIRA] = None


def _get_client() -> JIRA:
    """Get or create JIRA client instance."""
    global _client
    if _client is None:
        if not all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
            raise ValueError("Jira configuration missing. Check JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN in .env")
        
        _client = JIRA(
            server=JIRA_URL,
            basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN)
        )
    return _client


def create_ticket(
    summary: str,
    description: str,
    issue_type: str = "Task",
    priority: str = "Medium",
    labels: Optional[list] = None
) -> Dict[str, Any]:
    """
    Create a Jira ticket and return ticket details.
    
    Returns:
        Dict containing ticket key, URL, and ID
    """
    try:
        client = _get_client()
        
        # Prepare issue fields
        issue_dict = {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": description,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
        
        if labels:
            issue_dict["labels"] = labels
        
        # Create the issue
        issue = client.create_issue(fields=issue_dict)
        
        # Add comment with chat context
        if "escalated from" in description.lower():
            client.add_comment(
                issue.key,
                "This ticket was automatically created from Leila IT Help Desk chat escalation."
            )
        
        return {
            "key": issue.key,
            "id": issue.id,
            "url": f"{JIRA_URL}/browse/{issue.key}",
            "success": True
        }
        
    except Exception as exc:
        return {
            "key": None,
            "id": None,
            "url": None,
            "success": False,
            "error": str(exc)
        }


def update_ticket_status(ticket_key: str, status: str, comment: Optional[str] = None) -> bool:
    """
    Update Jira ticket status and optionally add comment.
    
    Args:
        ticket_key: Jira ticket key (e.g., "IT-123")
        status: New status (e.g., "In Progress", "Done", "Closed")
        comment: Optional comment to add
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = _get_client()
        
        # Add comment if provided
        if comment:
            client.add_comment(ticket_key, comment)
        
        # Transition the issue (this depends on your Jira workflow)
        # You may need to map status names to transition IDs
        transitions = client.transitions(ticket_key)
        target_transition = None
        
        for transition in transitions:
            if status.lower() in transition['name'].lower():
                target_transition = transition
                break
        
        if target_transition:
            client.transition_issue(ticket_key, target_transition['id'])
            return True
        else:
            # Fallback: try to set status directly (may not work for all Jira configs)
            client.update_issue(ticket_key, {"status": status})
            return True
            
    except Exception as exc:
        print(f"Error updating Jira ticket {ticket_key}: {exc}")
        return False


def get_ticket_info(ticket_key: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a Jira ticket.
    
    Args:
        ticket_key: Jira ticket key (e.g., "IT-123")
        
    Returns:
        Dict with ticket info or None if not found
    """
    try:
        client = _get_client()
        issue = client.issue(ticket_key)
        
        return {
            "key": issue.key,
            "id": issue.id,
            "summary": issue.fields.summary,
            "description": issue.fields.description,
            "status": issue.fields.status.name,
            "priority": issue.fields.priority.name if issue.fields.priority else None,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "url": f"{JIRA_URL}/browse/{issue.key}",
            "created": issue.fields.created,
            "updated": issue.fields.updated
        }
        
    except Exception as exc:
        print(f"Error getting Jira ticket {ticket_key}: {exc}")
        return None


def add_comment(ticket_key: str, comment: str) -> bool:
    """
    Add a comment to a Jira ticket.
    
    Args:
        ticket_key: Jira ticket key
        comment: Comment text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = _get_client()
        client.add_comment(ticket_key, comment)
        return True
    except Exception as exc:
        print(f"Error adding comment to Jira ticket {ticket_key}: {exc}")
        return False


def test_connection() -> Dict[str, Any]:
    """
    Test connection to Jira API.
    
    Returns:
        Dict with connection status and details
    """
    try:
        client = _get_client()
        # Try to get current user info
        current_user = client.current_user()
        
        # Try to get project info
        projects = client.projects()
        project_exists = any(p.key == JIRA_PROJECT_KEY for p in projects)
        
        return {
            "success": True,
            "connected_as": current_user.name,
            "email": current_user.emailAddress,
            "project_found": project_exists,
            "project_key": JIRA_PROJECT_KEY,
            "jira_url": JIRA_URL
        }
        
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "jira_url": JIRA_URL,
            "project_key": JIRA_PROJECT_KEY
        }

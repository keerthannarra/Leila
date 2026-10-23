"""
notification_service.py — Email notification service for Leila IT Help Desk Agent.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "leila.helpdesk@example.com")


def send_escalation_assignment_alert(
    agent_email: str, agent_name: str, jira_url: str, original_query: str
) -> bool:
    """
    Sends an email alert to the assigned agent containing escalation details.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[Mock Email] Notification would have been sent to {agent_email} for Jira: {jira_url}")
        print("Please configure SMTP credentials in .env to enable real email sending.")
        return False

    subject = "New Escalation Assigned to You"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>New Escalation Assigned</h2>
        <p>Hi <strong>{agent_name}</strong>,</p>
        <p>A new IT Help Desk escalation has been assigned to you.</p>
        <div style="background: #f4f4f4; padding: 15px; border-radius: 5px; margin: 15px 0;">
            <p><strong>Original User Query:</strong></p>
            <p style="font-style: italic;">"{original_query}"</p>
        </div>
        <p><strong>Jira Story:</strong> <a href="{jira_url}">{jira_url}</a></p>
        <br/>
        <p>Best regards,<br/>Leila IT Help Desk</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = agent_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, agent_email, msg.as_string())
        server.quit()
        print(f"Successfully sent escalation email to {agent_email}")
        return True
    except Exception as e:
        print(f"Failed to send escalation email to {agent_email}: {e}")
        return False


def send_new_escalation_alert(jira_url: str, original_query: str) -> bool:
    """
    Sends an email alert to the admin every time an escalation occurs.
    """
    admin_email = "narrakeerthanreddy@gmail.com"
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[Mock Email] Alert would have been sent to {admin_email} for Jira: {jira_url}")
        print("Please configure SMTP credentials in .env to enable real email sending.")
        return False

    subject = "ALERT: New Escalation Created"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2>🚨 Action Required: New Escalation</h2>
        <p>A new escalation ticket has been created in the IT Help Desk system.</p>
        <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0;">
            <p><strong>User Query:</strong></p>
            <p style="font-style: italic;">"{original_query}"</p>
        </div>
        <p><strong>Jira Story:</strong> <a href="{jira_url}">{jira_url}</a></p>
        <br/>
        <p>Please review and assign this ticket as soon as possible.</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = admin_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, admin_email, msg.as_string())
        server.quit()
        print(f"Successfully sent new escalation alert to {admin_email}")
        return True
    except Exception as e:
        print(f"Failed to send new escalation alert to {admin_email}: {e}")
        return False


def send_sla_breach_alert(agent_email: str, agent_name: str, jira_url: str, original_query: str, hours_overdue: float) -> bool:
    """
    Sends an email alert to the assigned agent when an escalation exceeds SLA.
    """
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[Mock Email] SLA breach alert would have been sent to {agent_email} for Jira: {jira_url}")
        print("Please configure SMTP credentials in .env to enable real email sending.")
        return False

    subject = "🚨 URGENT: SLA Breach Alert - Escalation Overdue"
    
    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #dc3545;">🚨 URGENT: SLA Breach Alert</h2>
        <p>Hi <strong>{agent_name}</strong>,</p>
        <p><strong style="color: #dc3545;">An escalation assigned to you has exceeded the 4-hour SLA period.</strong></p>
        
        <div style="background: #f8d7da; padding: 15px; border-left: 4px solid #dc3545; margin: 15px 0;">
            <p><strong>⏰ SLA Status:</strong> <span style="color: #dc3545;">{hours_overdue:.1f} hours overdue</span></p>
            <p><strong>Original User Query:</strong></p>
            <p style="font-style: italic;">"{original_query}"</p>
        </div>
        
        <p><strong>Jira Story:</strong> <a href="{jira_url}">{jira_url}</a></p>
        
        <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0;">
            <p><strong>⚠️ Immediate Action Required:</strong></p>
            <ul>
                <li>Please review and address this escalation immediately</li>
                <li>Contact the user if additional information is needed</li>
                <li>Update the Jira ticket with your progress</li>
                <li>If resolution requires more time, document the reasons</li>
            </ul>
        </div>
        
        <br/>
        <p>Best regards,<br/>Leila IT Help Desk System</p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = agent_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM_EMAIL, agent_email, msg.as_string())
        server.quit()
        print(f"Successfully sent SLA breach alert to {agent_email}")
        return True
    except Exception as e:
        print(f"Failed to send SLA breach alert to {agent_email}: {e}")
        return False

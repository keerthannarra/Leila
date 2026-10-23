import os

content_to_add = """

# ---------------------------------------------------------------------------
# GET /chat/sessions/{user_id}
# ---------------------------------------------------------------------------

@router.get("/sessions/{user_id}")
def get_user_sessions(user_id: str, db: DBSession = Depends(get_db)):
    \"\"\"Returns all chat sessions for a user, grouped with first query as title.\"\"\"
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )
    
    result = []
    for s in sessions:
        # Get the first interaction to use as a title
        first_interaction = (
            db.query(Interaction)
            .filter(Interaction.session_id == s.id)
            .order_by(Interaction.timestamp.asc())
            .first()
        )
        title = first_interaction.query_text if first_interaction else "New Chat"
        result.append({
            "id": s.id,
            "title": title[:50] + ("..." if len(title) > 50 else ""),
            "status": s.status,
            "created_at": s.created_at.isoformat() + "Z",
        })
    return result


# ---------------------------------------------------------------------------
# GET /chat/sessions/{session_id}/history
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/history")
def get_session_history(session_id: str, db: DBSession = Depends(get_db)):
    \"\"\"Returns the interaction history for a specific session.\"\"\"
    interactions = (
        db.query(Interaction)
        .filter(Interaction.session_id == session_id)
        .order_by(Interaction.timestamp.asc())
        .all()
    )
    
    history = []
    for i in interactions:
        history.append({
            "id": f"u-{i.id}",
            "role": "user",
            "content": i.query_text,
            "timestamp": i.timestamp.isoformat() + "Z",
        })
        
        if i.response_text:
            meta = {
                "interaction_id": i.id,
                "session_id": i.session_id,
                "escalated": i.escalation_flag,
                "jira_reference": i.jira_reference,
            }
            history.append({
                "id": f"a-{i.id}",
                "role": "assistant",
                "content": i.response_text,
                "timestamp": i.timestamp.isoformat() + "Z",
                "type": "escalation" if i.escalation_flag else "answer",
                "meta": meta
            })
            
    return {"messages": history}
"""

with open('routers/chat.py', 'a', encoding='utf-8') as f:
    f.write(content_to_add)

print("Added session endpoints to chat.py")

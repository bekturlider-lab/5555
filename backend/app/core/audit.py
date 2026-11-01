from ..models import AuditEvent, Notification


def audit(db, actor, action, entity_id="", **details):
    db.add(AuditEvent(actor_id=actor.id if actor else None, action=action, entity_id=entity_id, details=details))


def notify(db, user_id, title, body, link="/bank/history"):
    if user_id:
        db.add(Notification(user_id=user_id, title=title, body=body, link=link))

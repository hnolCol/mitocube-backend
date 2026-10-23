from fastapi import BackgroundTasks
from jinja2 import Environment, FileSystemLoader
from typing import List, Optional

from config.settings.email import get_email_settings
from lib.database.abstract.Database import DatabaseABC

email_settings = get_email_settings()

templates = [email_settings.message_attribute_request_reviewed_template]

TEMPLATE_ENV = Environment(loader=FileSystemLoader(email_settings.mail_template_dir), autoescape=False)


def send_message_in_background(background_tasks : BackgroundTasks,
                               db : DatabaseABC,
                               subject : str,
                               user_tags : List[str],
                               body : dict = {},
                               template_name : str = "attribute_request_reviewed.txt",
                               submission_tag : Optional[str] = None) -> None:
    """Sends a read-only in-app notification from MitoCube Support, the in-app
    counterpart of send_email_in_background. Each call creates one conversation
    for the given users containing the rendered template. Recipients cannot reply."""
    if template_name not in templates:
        raise ValueError("Template_name not found.")

    def _send():
        try:
            content = TEMPLATE_ENV.get_template(template_name).render(**body).strip()
            conversation_tag = db.messages.insert_system_message(
                user_tags=user_tags,
                title=subject,
                content=content,
                sender_tag=email_settings.message_sender_tag,
                submission_tag=submission_tag,
            )
            if conversation_tag is None:
                print(f"[messages] Could not send '{subject}' to {user_tags} (recipient not found).")
        except Exception as e:
            print(f"[messages] Failed to send '{subject}' to {user_tags}: {e}")

    background_tasks.add_task(_send)
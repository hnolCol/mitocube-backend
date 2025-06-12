from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import Literal
from config.settings.email import get_email_settings

email_settings = get_email_settings( )


templates = [email_settings.mail_verification_template, 
             email_settings.mail_confirmation_template,
             email_settings.mail_project_state_template,
             email_settings.mail_submission_complete_template,
             email_settings.mail_account_generated_template]

MAIL_CONFIG = ConnectionConfig(
                MAIL_USERNAME=email_settings.mail_username,
                MAIL_PASSWORD=email_settings.mail_password.get_secret_value(),
                MAIL_FROM=email_settings.mail_default_sender,
                MAIL_PORT=email_settings.mail_port,
                MAIL_SERVER=email_settings.mail_server,
                MAIL_FROM_NAME=email_settings.mail_from_name,
                MAIL_SSL_TLS=email_settings.mail_use_tls_ssl,
                MAIL_STARTTLS=email_settings.mail_start_tls,
                USE_CREDENTIALS=email_settings.mail_use_crendentials,
                VALIDATE_CERTS=email_settings.mail_validate_certs,
                TEMPLATE_FOLDER=email_settings.mail_template_dir
            )

def send_email_in_background(background_tasks : BackgroundTasks, 
                             subject : str, 
                             email_to: list[EmailStr], 
                             cc : list[EmailStr] = [], 
                             body : dict = {}, 
                             template_mame : str = "verification_code.html",
                             include_setting_cc : bool = True) -> None:
    """Sends a message via mail"""

    message = MessageSchema(
        subject=subject,
        recipients=email_to,
        cc = cc + email_settings.mail_cc if include_setting_cc  else cc,
        template_body=body,
        subtype=MessageType.html,
    )
    fm = FastMail(MAIL_CONFIG)

    if template_mame not in templates:
        raise ValueError("Template_name not found.")

    background_tasks.add_task(fm.send_message, message, template_name=template_mame)


async def async_send_email(subject : str, 
                             email_to: list[EmailStr], 
                             cc : list[EmailStr] = [], 
                             body : dict = {}, 
                             template_mame : str = "verification_code.html",
                             include_setting_cc : bool = True) -> None:
    """"""
    message = MessageSchema(
        subject=subject,
        recipients=email_to,
        cc = cc + email_settings.mail_cc if include_setting_cc  else cc,
        template_body=body,
        subtype=MessageType.html,
    )
    fm = FastMail(MAIL_CONFIG)
    await fm.send_message(message,template_name=template_mame)
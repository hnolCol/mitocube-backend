from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType  # Package Fastapi-mail
from pydantic import EmailStr
from typing import Dict, List, Literal
from config import SystemSettings

system_settings = SystemSettings.get_system_settings()  # Question, is it kept all the time? move to local environment? But how to do the class without?

class EMailHandler:
    __templates = [system_settings.mail_template_email_confirmation,
                   system_settings.mail_template_login_code]

    __config = ConnectionConfig(MAIL_USERNAME=system_settings.mail_username.get_secret_value(),
                                MAIL_PASSWORD=system_settings.mail_password.get_secret_value(),
                                MAIL_FROM=system_settings.mail_username.get_secret_value(),
                                MAIL_PORT=system_settings.mail_port,
                                MAIL_SERVER=system_settings.mail_server.get_secret_value(),
                                MAIL_FROM_NAME=system_settings.mail_from_name,
                                MAIL_SSL_TLS=system_settings.mail_use_tls_ssl,
                                MAIL_STARTTLS=system_settings.mail_start_tls,
                                USE_CREDENTIALS=system_settings.mail_use_credentials,
                                VALIDATE_CERTS=system_settings.mail_validate_certs,
                                TEMPLATE_FOLDER=system_settings.mail_template_dir)

    @staticmethod
    def send_email_in_background(background_tasks: BackgroundTasks,
                                 subject: str,
                                 email_to: List[str],
                                 cc: List[str] | None = None,
                                 body: Dict[str, str] | None = None,
                                 template_name: str = "verification_code.html",
                                 include_setting_cc: bool = True):

        message = MessageSchema(subject = subject,
                                recipients = email_to,
                                cc = cc + system_settings.mail_cc if include_setting_cc else cc if cc else [],
                                template_body = body if body else {},
                                subtype = MessageType.html)
        fm = FastMail(EMailHandler.__config)

        if template_name not in EMailHandler.__templates:
            raise ValueError("Template_name '{}' not found.".format(template_name))

        background_tasks.add_task(fm.send_message, message, template_name=template_name)

    @staticmethod
    async def send_async_email(subject: str,
                               email_to: List[EmailStr],
                               cc: List[EmailStr] | None = None,
                               body: Dict[str, str] | None = None,
                               template_name: str = "verification_code.html",
                               include_setting_cc: bool = True):

        if template_name not in EMailHandler.__templates:
            raise ValueError("Template_name '{}' not found.".format(template_name))

        message = MessageSchema(subject=subject,
                                recipients=email_to,
                                cc = cc + system_settings.mail_cc if include_setting_cc else cc if cc else [],
                                template_body=body if body else {},
                                subtype=MessageType.html)

        fm = FastMail(EMailHandler.__config)
        await fm.send_message(message, template_name = template_name)

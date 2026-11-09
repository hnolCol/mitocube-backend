from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from typing import List, Optional

from config.enums.users.roles import UserRolesEnum
from config.models.messages import ConversationInput, MessageInput
from config.models.tickets import (
    TicketAttachmentModel,
    TicketCreatedResponse,
    TicketInput,
    TicketModel,
    TicketReplyInput,
    TicketStatusEnum,
)
from config.models.user import UserModel
from config.settings.email import get_email_settings
from config.settings.general import get_general_settings
from lib.database.abstract.Database import DatabaseABC
from lib.database.Database import get_db
from services import ticket_attachments
from services.mail import send_email_in_background
from services.random_generators import get_random_string
from services.users import get_user_from_token

EMAIL_SETTINGS = get_email_settings()
GENERAL_SETTINGS = get_general_settings()

router = APIRouter(dependencies=[Depends(get_user_from_token)],
                   prefix="/api",
                   tags=["Support Tickets"])

RESOLVED_NOTE = (
    "Ticket {reference} has been marked as resolved.\n\n"
    "If the issue is still there, reply in this conversation and the ticket will be reopened. "
    "For a different issue, please submit a new ticket through the Contact page."
)


def is_user_admin(user: UserModel = Depends(get_user_from_token)) -> UserModel:
    if user.role < UserRolesEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can manage support tickets.")
    return user


def _get_admin_emails(db: DatabaseABC) -> List[str]:
    return [u.email for u in db.users.get_users()
            if u.role >= UserRolesEnum.ADMIN and u.email is not None]


def _full_name(user: UserModel) -> str:
    return f"{user.firstname} {user.lastname}".strip()


def _get_ticket_or_404(ticket_tag: str, db: DatabaseABC) -> TicketModel:
    ticket = db.tickets.get_ticket(ticket_tag)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


def _get_ticket_with_access(ticket_tag: str, user: UserModel, db: DatabaseABC) -> TicketModel:
    """Returns the ticket if the user raised it or is an admin, 404/403 otherwise."""
    ticket = _get_ticket_or_404(ticket_tag, db)
    if ticket.raised_by != user.tag and user.role < UserRolesEnum.ADMIN:
        raise HTTPException(status_code=403, detail="You have no access to this ticket.")
    return ticket


def _notify_ticket_created(background_task: BackgroundTasks, db: DatabaseABC, user: UserModel,
                           ticket: TicketInput, reference: str) -> None:
    """Emails the user a confirmation with the ticket reference and notifies all admins.
    The ticket is already stored at this point, so mail problems are logged instead of raised."""
    if user.email is not None:
        try:
            send_email_in_background(background_tasks=background_task,
                                     subject=f"[{reference}] Support Request",
                                     email_to=[user.email],
                                     include_setting_cc=False,
                                     body={
                                         "app_name": GENERAL_SETTINGS.app_name,
                                         "user": _full_name(user),
                                         "reference": reference,
                                         "title": ticket.title,
                                     },
                                     template_name=EMAIL_SETTINGS.mail_ticket_received_template)
        except Exception as e:
            print(f"[mail] Failed to queue the confirmation email for ticket {reference}: {e}")

    emails = _get_admin_emails(db)
    if len(emails) == 0:
        print(f"[mail] No admin with an email found for ticket {reference}, sending to the CC address only.")
        return
    try:
        send_email_in_background(background_tasks=background_task,
                                 subject=f"Support Ticket {reference}: {ticket.title}",
                                 email_to=emails,
                                 include_setting_cc=True,
                                 body={
                                     "app_name": GENERAL_SETTINGS.app_name,
                                     "user": _full_name(user),
                                     "reference": reference,
                                     "title": ticket.title,
                                     "description": ticket.description,
                                     "url": GENERAL_SETTINGS.url,
                                 },
                                 template_name=EMAIL_SETTINGS.mail_ticket_new_template)
    except Exception as e:
        print(f"[mail] Failed to queue the admin email for ticket {reference}: {e}")


def _notify_ticket_resolved(background_task: BackgroundTasks, db: DatabaseABC,
                            ticket: TicketModel, resolver: UserModel) -> None:
    """Emails the user who raised the ticket that it was resolved and by whom.
    The status is already stored at this point, so mail problems are logged instead of raised."""
    requester = db.users.get_user_by_tag(tag=ticket.raised_by)
    if requester is None:
        print(f"[notify] Ticket raiser {ticket.raised_by} not found, ticket {ticket.reference}.")
        return
    if requester.email is None:
        return
    try:
        send_email_in_background(background_tasks=background_task,
                                 subject=f"[{ticket.reference}] Support Request Resolved",
                                 email_to=[requester.email],
                                 include_setting_cc=False,
                                 body={
                                     "app_name": GENERAL_SETTINGS.app_name,
                                     "user": _full_name(requester),
                                     "reference": ticket.reference,
                                     "title": ticket.title,
                                     "resolver": _full_name(resolver),
                                     "url": GENERAL_SETTINGS.url,
                                 },
                                 template_name=EMAIL_SETTINGS.mail_ticket_resolved_template)
    except Exception as e:
        print(f"[mail] Failed to queue the resolved email for ticket {ticket.reference}: {e}")


def _ensure_conversation(ticket: TicketModel, admin: UserModel, db: DatabaseABC) -> str:
    """Returns the ticket's conversation, creating it on first contact with the user's
    original request as first message (backdated to ticket creation). Adds the admin
    as participant if needed."""
    if ticket.conversation_tag is not None:
        if not db.messages.is_participant(conversation_tag=ticket.conversation_tag, user_tag=admin.tag):
            db.messages.add_participants(conversation_tag=ticket.conversation_tag, user_tags=[admin.tag])
        return ticket.conversation_tag

    conversation_tag = db.messages.insert_conversation(
        created_by=admin.tag,
        conversation=ConversationInput(
            user_tags=[ticket.raised_by],
            title=f"[{ticket.reference}] {ticket.title}",
        ),
    )
    if conversation_tag is None:
        raise HTTPException(status_code=400, detail="Conversation could not be created.")
    db.tickets.link_conversation(ticket_tag=ticket.tag, conversation_tag=conversation_tag)
    db.messages.insert_message(conversation_tag=conversation_tag,
                               sender_tag=ticket.raised_by,
                               message=MessageInput(content=ticket.description),
                               created_at=ticket.created_at)
    return conversation_tag


# ---------- user ----------

@router.post("/tickets", status_code=201, summary="Creates a support ticket from the contact form. Emails the user and all admins.")
def create_ticket(body: TicketInput,
                  background_task: BackgroundTasks,
                  user: UserModel = Depends(get_user_from_token),
                  db: DatabaseABC = Depends(get_db)) -> TicketCreatedResponse:
    """Creates an open ticket. No conversation is created until an admin replies."""
    created = db.tickets.insert_ticket(user_tag=user.tag, ticket=body)
    if created is None:
        raise HTTPException(status_code=400, detail="Ticket could not be created.")
    _notify_ticket_created(background_task, db, user, body, created.reference)
    return created


@router.get("/tickets/mine", summary="Returns the tickets raised by the current user.")
def get_my_tickets(user: UserModel = Depends(get_user_from_token),
                   db: DatabaseABC = Depends(get_db)) -> List[TicketModel]:
    """Returns the current user's tickets, most recently active first."""
    return db.tickets.get_tickets_for_user(user_tag=user.tag)


# ---------- admin ----------

@router.get("/tickets", summary="Returns the ticket queue, optionally filtered by status. Admin rights required.")
def get_ticket_queue(status: Optional[TicketStatusEnum] = None,
                     user: UserModel = Depends(is_user_admin),
                     db: DatabaseABC = Depends(get_db)) -> List[TicketModel]:
    """Returns all tickets. Tickets awaiting a reply come first, then by status and activity."""
    return db.tickets.get_tickets(status=status)


@router.get("/tickets/{ticket_tag}", summary="Returns a ticket. Admin rights or being the ticket raiser required.")
def get_ticket(ticket_tag: str,
               user: UserModel = Depends(get_user_from_token),
               db: DatabaseABC = Depends(get_db)) -> TicketModel:
    """Returns a single ticket including its handler and conversation tag."""
    return _get_ticket_with_access(ticket_tag, user, db)


@router.post("/tickets/{ticket_tag}/reply", summary="Replies to and/or resolves a ticket. The first admin to act becomes the handler. Admin rights required.")
def reply_to_ticket(ticket_tag: str,
                    body: TicketReplyInput,
                    background_task: BackgroundTasks,
                    user: UserModel = Depends(is_user_admin),
                    db: DatabaseABC = Depends(get_db)) -> TicketModel:
    """A reply moves the ticket to In Progress; `resolve` marks it as Resolved, posts a
    note to the user's conversation and emails the user. Only the handler can act on
    a ticket once it is assigned."""
    ticket = _get_ticket_or_404(ticket_tag, db)

    content = body.content.strip()
    if not content and not body.resolve:
        raise HTTPException(status_code=400, detail="Write a reply or resolve the ticket.")

    if not db.tickets.assign(ticket_tag=ticket_tag, admin_tag=user.tag):
        raise HTTPException(status_code=409,
                            detail=f"This ticket is already handled by {ticket.assigned_to_name or 'another admin'}.")

    new_status = TicketStatusEnum.RESOLVED if body.resolve else TicketStatusEnum.IN_PROGRESS
    conversation_tag = _ensure_conversation(ticket, user, db)

    if content:
        db.messages.insert_message(conversation_tag=conversation_tag,
                                   sender_tag=user.tag,
                                   message=MessageInput(content=content))

    if new_status != ticket.status:
        db.tickets.set_status(ticket_tag=ticket_tag, status=new_status)
        if new_status == TicketStatusEnum.RESOLVED:
            db.messages.insert_message(conversation_tag=conversation_tag,
                                       sender_tag=user.tag,
                                       message=MessageInput(content=RESOLVED_NOTE.format(reference=ticket.reference)))
            _notify_ticket_resolved(background_task, db, ticket, user)

    return db.tickets.get_ticket(ticket_tag)


# ---------- attachments ----------

async def _read_upload(file: UploadFile, max_size: int) -> bytes:
    """Reads the whole upload, raising 413 as soon as the size limit is exceeded."""
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_size:
            raise HTTPException(status_code=413,
                                detail=f"The image is larger than {max_size // (1024 * 1024)} MB.")
    return bytes(data)


@router.post("/tickets/{ticket_tag}/attachments", status_code=201,
             summary="Uploads an image (e.g. a screenshot) to a ticket. Ticket raiser or admin required.")
async def upload_attachment(ticket_tag: str,
                            file: UploadFile = File(...),
                            user: UserModel = Depends(get_user_from_token),
                            db: DatabaseABC = Depends(get_db)) -> TicketAttachmentModel:
    """Stores a PNG/JPEG/GIF/WebP image on disk and its metadata in the database.
    The image type is verified from the file's magic bytes, not the filename."""
    ticket = _get_ticket_with_access(ticket_tag, user, db)
    max_size = GENERAL_SETTINGS.ticket_attachment_max_size_mb * 1024 * 1024
    data = await _read_upload(file, max_size)
    detected = ticket_attachments.detect_image_type(data)
    if detected is None:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG, GIF or WebP images are allowed.")
    mime, ext = detected
    attachment_tag = get_random_string(N=12)
    path = ticket_attachments.get_attachment_path(ticket.tag, attachment_tag, ext)
    ticket_attachments.save_attachment_file(path, data)
    attachment = db.tickets.insert_attachment(ticket_tag=ticket.tag,
                                              attachment_tag=attachment_tag,
                                              uploaded_by=user.tag,
                                              filename=ticket_attachments.sanitize_filename(file.filename),
                                              content_type=mime,
                                              size=len(data),
                                              extension=ext)
    if attachment is None:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Attachment could not be stored.")
    return attachment


@router.get("/tickets/{ticket_tag}/attachments",
            summary="Lists the image attachments of a ticket. Ticket raiser or admin required.")
def list_attachments(ticket_tag: str,
                     user: UserModel = Depends(get_user_from_token),
                     db: DatabaseABC = Depends(get_db)) -> List[TicketAttachmentModel]:
    _get_ticket_with_access(ticket_tag, user, db)
    return db.tickets.get_attachments_for_ticket(ticket_tag)


@router.get("/tickets/{ticket_tag}/attachments/{attachment_tag}",
            summary="Downloads an image attachment. Ticket raiser or admin required.")
def download_attachment(ticket_tag: str,
                        attachment_tag: str,
                        user: UserModel = Depends(get_user_from_token),
                        db: DatabaseABC = Depends(get_db)) -> FileResponse:
    _get_ticket_with_access(ticket_tag, user, db)
    attachment = db.tickets.get_attachment(attachment_tag)
    if attachment is None or attachment.ticket_tag != ticket_tag:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    path = ticket_attachments.get_attachment_path(ticket_tag, attachment.tag, attachment.extension)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment file not found.")
    return FileResponse(path, media_type=attachment.content_type, filename=attachment.filename)
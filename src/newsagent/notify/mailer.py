import email
import html
import imaplib
import io
import logging
import smtplib
from datetime import date
from email.header import decode_header, make_header
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

from PIL import Image

from newsagent.config import get_settings

log = logging.getLogger("newsagent")


def send_preview(paths: list[Path], caption: str, token: str) -> None:
    s = get_settings()

    def link(action: str) -> str:
        return f"mailto:{s.smtp_user}?subject={quote(f'{action} {token}')}"

    msg = EmailMessage()
    msg["Subject"] = f"Approve today's Instagram post ({date.today():%d %b}) #{token[:4]}"
    msg["From"] = s.smtp_user
    msg["To"] = s.approver_email
    msg.set_content(
        f"Open in an HTML mail client.\nApprove: {link('APPROVE')}\nReject: {link('REJECT')}"
    )

    imgs = "".join(
        f'<img src="cid:s{i}" width="260" style="margin:4px;border:1px solid #ddd">'
        for i in range(len(paths))
    )
    btn = "display:inline-block;padding:14px 28px;color:#fff;text-decoration:none;border-radius:6px;font:bold 16px Arial"
    msg.add_alternative(
        f"""<h2>Today's carousel is ready</h2>
<p><a href="{link("APPROVE")}" style="{btn};background:#1a8a3c">Approve</a>&nbsp;
<a href="{link("REJECT")}" style="{btn};background:#c8102e">Reject</a></p>
<p>Tap a button, then press <b>Send</b> on the reply that opens.</p>
{imgs}<pre style="white-space:pre-wrap;font:14px Arial">{html.escape(caption)}</pre>""",
        subtype="html",
    )
    body = msg.get_payload()[1]
    for i, p in enumerate(paths):
        buf = io.BytesIO()
        im = Image.open(p)
        im.thumbnail((540, 675))
        im.save(buf, "JPEG", quality=80)
        body.add_related(buf.getvalue(), "image", "jpeg", cid=f"<s{i}>")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(s.smtp_user, s.smtp_password)
        srv.send_message(msg)
    log.info("Preview email sent to %s", s.approver_email)


def check_reply(token: str) -> str | None:
    """Return 'approve', 'reject' or None, based on today's mail from the approver."""
    s = get_settings()
    since = date.today().strftime("%d-%b-%Y")
    with imaplib.IMAP4_SSL("imap.gmail.com") as m:
        m.login(s.smtp_user, s.smtp_password)
        m.select("INBOX")
        _, data = m.search(None, "SINCE", since, "FROM", f'"{s.approver_email}"')
        ids = data[0].split()
        log.info("Found %d message(s) from the approver today", len(ids))
        for i in reversed(ids):  # newest first
            _, parts = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
            msg = email.message_from_bytes(parts[0][1])
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            if token in subject:
                if "APPROVE" in subject.upper():
                    return "approve"
                if "REJECT" in subject.upper():
                    return "reject"
    return None

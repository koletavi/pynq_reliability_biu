"""Optional lab mail. This is the only module that opens an SMTP connection.

A missing secrets/notify.json, a blank host, or a blank password appends the
notice to data/notify.log and returns. Callers keep running.
"""

import argparse
import json
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS = REPO_ROOT / "secrets" / "notify.json"
LOG_PATH = REPO_ROOT / "data" / "notify.log"


def _text(value):
    if value is None:
        return ""
    return str(value).strip()


def load_settings(path=None):
    """Return the JSON object, or None when the file is missing or unreadable."""
    settings_path = Path(path) if path is not None else DEFAULT_SETTINGS
    if not settings_path.is_file():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def mail_is_configured(settings):
    """True when host and password are both non-blank."""
    if not isinstance(settings, dict):
        return False
    if not _text(settings.get("smtp_host")):
        return False
    if not _text(settings.get("password")):
        return False
    return True


def addresses_for(settings, group_names):
    """Mailbox list for the named groups, plus the TA address."""
    found = []
    groups = settings.get("groups") if isinstance(settings, dict) else {}
    if not isinstance(groups, dict):
        groups = {}
    for name in group_names:
        raw = groups.get(name, [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, (list, tuple)):
            continue
        for item in raw:
            text = _text(item)
            if text:
                found.append(text)
    ta = _text(settings.get("ta")) if isinstance(settings, dict) else ""
    if ta:
        found.append(ta)
    unique = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique


def append_log(text):
    """Append one notice to data/notify.log. Never raises."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(text.rstrip() + "\n\n")
    except OSError:
        return


def _message(subject, body, mailbox, recipients):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mailbox
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    return message


def _send_smtp(settings, message):
    """Open SMTP, upgrade with STARTTLS, and send. The From mailbox is the login."""
    host = _text(settings.get("smtp_host"))
    password = _text(settings.get("password"))
    mailbox = _text(settings.get("username")) or _text(settings.get("from"))
    port_value = settings.get("smtp_port", 587)
    try:
        port = int(port_value)
    except (TypeError, ValueError):
        port = 587
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(mailbox, password)
        smtp.send_message(message)


def send_notice(event, board, group, folder, group_names, settings_path=None):
    """Send one notice, or append it to data/notify.log. Never raises.

    group_names selects entries under "groups" in the JSON. The TA address
    is always added. No CSV is attached.
    """
    subject = f"PYNQ lab: {event}, {board}"
    body = "\n".join([
        f"event: {event}",
        f"board: {board}",
        f"group: {group}",
        f"folder: {folder}",
    ])
    try:
        settings = load_settings(settings_path)
        if not mail_is_configured(settings):
            append_log(f"{subject}\n{body}")
            return
        recipients = addresses_for(settings, group_names)
        if not recipients:
            append_log(f"{subject}\n{body}")
            return
        mailbox = _text(settings.get("username")) or _text(settings.get("from"))
        message = _message(subject, body, mailbox, recipients)
        _send_smtp(settings, message)
    except Exception as exc:
        append_log(f"mail not sent: {subject}\n{exc.__class__.__name__}: {exc}\n{body}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Send one test notice, or write it to data/notify.log when mail is not configured."
    )
    parser.add_argument("--test", metavar="GROUP", help="Group name, for example groupA")
    args = parser.parse_args(argv)
    if not args.test:
        parser.print_usage()
        return 2
    send_notice(
        "test",
        args.test,
        args.test,
        str(LOG_PATH.parent),
        [args.test],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Отправка писем.

MVP-реализация:
- если в .env заданы SMTP_* — письмо отправляется через SMTP;
- иначе ссылка подтверждения логируется в консоль (dev-режим).

`outbox` хранит «отправленные» письма в памяти процесса — используется для
ручной проверки в dev и для сквозных тестов (по аналогии с тест-outbox в Django).
Не использовать как источник правды в production.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import get_settings

logger = logging.getLogger("app.mailer")

# Журнал «отправленных» писем для dev/тестов: [{"to", "subject", "token", "link"}]
outbox: list[dict[str, str]] = []


def _verification_link(token: str) -> str:
    base = get_settings().FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/verify-email?token={token}"


def _password_reset_link(token: str) -> str:
    base = get_settings().FRONTEND_BASE_URL.rstrip("/")
    return f"{base}/reset-password?token={token}"


def _smtp_send(to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    use_ssl = settings.SMTP_USE_SSL or settings.SMTP_PORT == 465
    if use_ssl:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
            smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)


def send_verification_email(to_email: str, token: str) -> None:
    settings = get_settings()
    link = _verification_link(token)
    subject = "Подтверждение email — Online School Messenger"
    body = (
        "Здравствуйте!\n\n"
        "Чтобы подтвердить адрес электронной почты, перейдите по ссылке:\n"
        f"{link}\n\n"
        f"Ссылка действительна {settings.EMAIL_VERIFICATION_TTL_HOURS} ч.\n"
        "Если вы не регистрировались, просто проигнорируйте это письмо."
    )

    outbox.append({"to": to_email, "subject": subject, "token": token, "link": link})

    if settings.SMTP_HOST:
        try:
            _smtp_send(to_email, subject, body)
            print(f"[EMAIL] sent verification to {to_email}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось отправить письмо подтверждения на %s", to_email)
            print(f"[EMAIL ERROR] {to_email}: {exc!r}")
    else:
        logger.warning("[DEV] Письмо подтверждения для %s: %s", to_email, link)
        print(f"[DEV EMAIL] verify {to_email}: {link}")


def send_password_reset_email(to_email: str, token: str) -> None:
    settings = get_settings()
    link = _password_reset_link(token)
    subject = "Сброс пароля — Online School Messenger"
    body = (
        "Здравствуйте!\n\n"
        "Чтобы задать новый пароль, перейдите по ссылке:\n"
        f"{link}\n\n"
        f"Ссылка действительна {settings.PASSWORD_RESET_TTL_HOURS} ч.\n"
        "Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо."
    )

    outbox.append({"to": to_email, "subject": subject, "token": token, "link": link})

    if settings.SMTP_HOST:
        try:
            _smtp_send(to_email, subject, body)
            print(f"[EMAIL] sent password reset to {to_email}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Не удалось отправить письмо сброса пароля на %s", to_email)
            print(f"[EMAIL ERROR] {to_email}: {exc!r}")
    else:
        logger.warning("[DEV] Письмо сброса пароля для %s: %s", to_email, link)
        print(f"[DEV EMAIL] reset {to_email}: {link}")

r"""Создание первого администратора без очистки базы данных.

Запуск (из папки backend):
    .\.venv\Scripts\python.exe scripts\create_admin.py --nickname admin --email admin@school.ru

Пароль можно передать аргументом --password или через переменную ADMIN_PASSWORD.
Если не указан — будет запрошен интерактивно (без эха).

Скрипт НЕ удаляет существующие данные. По умолчанию отказывается создавать admin,
если в базе уже есть активный администратор. Флаг --force снимает это ограничение
(но никнейм и email всё равно должны быть свободны).

НЕ используйте scripts/seed.py на production — он полностью стирает messenger.db.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import db, storage  # noqa: E402
from app.models import UserInDB, UserRole  # noqa: E402
from app.password_policy import validate_password_strength  # noqa: E402
from app.security import hash_password  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Создать администратора в существующей базе (без wipe)."
    )
    parser.add_argument("--nickname", default="admin", help="Никнейм (по умолчанию: admin)")
    parser.add_argument(
        "--email",
        default=None,
        help="Email (по умолчанию: <nickname>@example.com)",
    )
    parser.add_argument("--first-name", default="Admin", dest="first_name")
    parser.add_argument("--last-name", default="User", dest="last_name")
    parser.add_argument(
        "--password",
        default=None,
        help="Пароль (иначе ADMIN_PASSWORD или интерактивный ввод)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Создать admin даже если активный администратор уже есть",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    db.init_db()

    if not args.force and storage.count_active_admins() > 0:
        print(
            "Ошибка: в базе уже есть активный администратор. "
            "Используйте --force, если нужно добавить ещё одного.",
            file=sys.stderr,
        )
        sys.exit(1)

    nickname = args.nickname.strip()
    email = (args.email or f"{nickname}@example.com").strip().lower()

    if storage.get_user_by_nickname(nickname) is not None:
        print(f"Ошибка: никнейм {nickname!r} уже занят.", file=sys.stderr)
        sys.exit(1)
    if storage.get_user_by_email(email) is not None:
        print(f"Ошибка: email {email!r} уже зарегистрирован.", file=sys.stderr)
        sys.exit(1)

    password = args.password or os.environ.get("ADMIN_PASSWORD")
    if not password:
        password = getpass.getpass("Пароль администратора: ")
    if not password:
        print("Ошибка: пароль не может быть пустым.", file=sys.stderr)
        sys.exit(1)
    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        sys.exit(1)

    user = UserInDB(
        nickname=nickname,
        role=UserRole.admin,
        hashed_password=hash_password(password),
        email=email,
        first_name=args.first_name,
        last_name=args.last_name,
        email_verified=True,
    )
    storage.create_user(user)

    print("Администратор создан:")
    print(f"  id:       {user.id}")
    print(f"  nickname: {user.nickname}")
    print(f"  email:    {user.email}")
    print("  role:     admin")


if __name__ == "__main__":
    main()

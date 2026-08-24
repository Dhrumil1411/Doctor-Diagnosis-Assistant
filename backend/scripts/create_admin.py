import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import SessionLocal
from app.models.users import User, UserRole


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update an admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True, help="min 8 characters")
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    email = args.email.lower()
    if len(args.password) < 8:
        print("ERROR: password must be at least 8 characters", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(args.password),
                full_name=args.full_name,
                role=UserRole.admin,
            )
            db.add(user)
            action = "created"
        else:
            user.hashed_password = hash_password(args.password)
            user.full_name = args.full_name
            user.role = UserRole.admin
            user.is_active = True
            action = "updated"
        db.commit()

    print(f"Admin {action}: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

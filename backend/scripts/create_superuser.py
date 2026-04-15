#!/usr/bin/env python3
"""
Create Superuser Script

Creates a superuser account for admin access.
Usage: uv run python scripts/create_superuser.py
"""

import asyncio
import getpass
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.ext.asyncio import AsyncSession

from blacklight.common.database import SessionLocal
from blacklight.features.auth.models import User
from blacklight.features.auth.repositories import UserRepository
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_superuser():
    """Create a superuser account"""
    print("=== Create Superuser ===\n")

    # Get user input
    email = input("Email: ").strip()
    if not email:
        print("Error: Email is required")
        return

    full_name = input("Full Name (optional): ").strip() or None

    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")

    if password != password_confirm:
        print("Error: Passwords do not match")
        return

    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        return

    # Create user
    async with SessionLocal() as session:
        user_repo = UserRepository(session)

        # Check if user already exists
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            print(f"\nUser with email {email} already exists.")
            promote = input("Promote to superuser? (y/n): ").strip().lower()
            if promote == "y":
                existing_user.is_superuser = True
                existing_user.is_active = True
                existing_user.is_verified = True
                await session.commit()
                print(f"\n✓ User {email} promoted to superuser!")
            return

        # Hash password
        hashed_password = pwd_context.hash(password)

        # Create user
        from datetime import datetime

        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=True,
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        print(f"\n✓ Superuser created successfully!")
        print(f"  Email: {user.email}")
        print(f"  ID: {user.id}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"\nYou can now login at http://localhost:5173/login")


if __name__ == "__main__":
    asyncio.run(create_superuser())

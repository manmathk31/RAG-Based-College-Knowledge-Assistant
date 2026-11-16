"""Create or update an authorized student account. Run from backend directory."""
import asyncio
import getpass
import re
from sqlalchemy import select
from app.db.session import init_db, get_db, close_db
from app.db.auth_models import StudentModel
from app.core.security import hash_password

async def main():
    email=input("Student email address: ").strip().lower()
    name=input("Student full name: ").strip()
    password=getpass.getpass("Temporary password (min 12 characters): ")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+",email): raise SystemExit("Invalid email.")
    if len(password)<12: raise SystemExit("Password must be at least 12 characters.")
    init_db()
    async for db in get_db():
        result=await db.execute(select(StudentModel).where(StudentModel.email==email))
        student=result.scalar_one_or_none()
        if student:
            student.full_name=name;student.password_hash=hash_password(password);student.is_active=True
        else:
            db.add(StudentModel(email=email,full_name=name,password_hash=hash_password(password),is_active=True))
        await db.commit()
        print(f"Student account provisioned: {email}")
        break
    await close_db()

if __name__=="__main__": asyncio.run(main())

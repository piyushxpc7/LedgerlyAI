from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.org import Org
from app.models.user import User, UserRole
from app.models.client import Client
from app.auth import hash_password

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Check if any user exists
        if db.query(User).first():
            print("Database already seeded.")
            return

        # Create Org
        org = Org(name="Demo CA Firm")
        db.add(org)
        db.flush()
        
        # Create Admin
        admin = User(
            org_id=org.id,
            email="admin@demo.com",
            password_hash=hash_password("password123"),
            role=UserRole.ADMIN
        )
        db.add(admin)
        db.flush()
        
        # Create Staff
        staff = User(
            org_id=org.id,
            email="staff@demo.com",
            password_hash=hash_password("password123"),
            role=UserRole.STAFF
        )
        db.add(staff)
        
        # Create Client
        client = Client(
            org_id=org.id,
            name="Alpha Corp",
            gstin="29ABCDE1234F1Z5",
            pan="ABCDE1234F",
            fy="2023-24"
        )
        db.add(client)
        
        db.commit()
        print("Database seeded successfully!")
        print("Admin: admin@demo.com / password123")
        print("Staff: staff@demo.com / password123")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

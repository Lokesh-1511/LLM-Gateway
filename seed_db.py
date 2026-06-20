import os
from database import SessionLocal, engine
from models import Base, Department, User
from auth_service import get_password_hash

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if department exists
    dept = db.query(Department).filter(Department.name == "Engineering").first()
    if not dept:
        dept = Department(name="Engineering")
        db.add(dept)
        db.commit()
        db.refresh(dept)
        print("Created Department:", dept.name)
        
    # Check if user exists
    user = db.query(User).filter(User.email == "admin@promptops.local").first()
    if not user:
        user = User(
            email="admin@promptops.local",
            hashed_password=get_password_hash("admin123"),
            department_id=dept.id,
            role="admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print("Created User:", user.email)
    else:
        print("Admin user already exists.")
        
    db.close()

if __name__ == "__main__":
    seed()

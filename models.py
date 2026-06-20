import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Department(Base):
    __tablename__ = 'departments'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, index=True)

class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    department_id = Column(String(36), ForeignKey('departments.id'))
    role = Column(String, default="user") # admin, user

    department = relationship("Department")

class RequestLog(Base):
    __tablename__ = 'request_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)
    original_prompt = Column(String)
    was_pii_detected = Column(Boolean, default=False)
    was_cache_hit = Column(Boolean, default=False)
    token_count = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    estimated_cost = Column(Float, default=0.0)
    
    user_id = Column(String(36), ForeignKey('users.id'), nullable=True)
    department_id = Column(String(36), ForeignKey('departments.id'), nullable=True)

    user = relationship("User")
    department = relationship("Department")

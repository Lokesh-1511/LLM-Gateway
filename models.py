import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

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

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'))
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    pii_mappings = relationship("PIIMapping", back_populates="chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = 'messages'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(36), ForeignKey('chats.id'))
    role = Column(String) # "user" or "assistant"
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")

class PIIMapping(Base):
    __tablename__ = 'pii_mappings'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(36), ForeignKey("chats.id"))
    real_value = Column(String, index=True)
    fake_value = Column(String, index=True)

    chat = relationship("Chat", back_populates="pii_mappings")

class PromptCache(Base):
    __tablename__ = 'prompt_cache'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    prompt_text = Column(String)
    embedding = Column(Vector(384))
    response_json = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

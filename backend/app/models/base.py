from sqlalchemy import Column, String, Text, Float, DateTime, JSON, Enum, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid
import enum


class Base(DeclarativeBase):
    pass


class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    awaiting_review = "awaiting_review"
    submitted = "submitted"
    failed = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    name = Column(String)
    linkedin_id = Column(String, unique=True, nullable=True)
    linkedin_access_token = Column(String, nullable=True)
    linkedin_profile_url = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    email_notifications = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resumes = relationship("Resume", back_populates="user")
    applications = relationship("Application", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    filename = Column(String)
    raw_text = Column(Text)
    parsed_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    company = Column(String)
    location = Column(String)
    description = Column(Text)
    url = Column(String, unique=True)
    source = Column(String)
    match_score = Column(Float, default=0.0)
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    resume_id = Column(String, ForeignKey("resumes.id"))
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    form_data = Column(JSON)
    pending_questions = Column(JSON, default=list)
    error_log = Column(Text)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job")

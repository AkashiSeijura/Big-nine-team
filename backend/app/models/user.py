from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserTelegramId(Base):
    __tablename__ = "user_telegram_ids"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="telegram_ids")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="operator")  # operator | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    telegram_ids: Mapped[list["UserTelegramId"]] = relationship("UserTelegramId", back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="assignee", foreign_keys="Ticket.assigned_to")
    kb_files: Mapped[list["KbFile"]] = relationship("KbFile", back_populates="uploader")

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), default="与 Ta 的对话")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Analysis.created_at.desc()",
    )
    profile: Mapped["ConversationProfile | None"] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20))  # me | friend | self_narrative
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False
    )
    draft_text: Mapped[str] = mapped_column(Text)
    intent_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    anger_risk: Mapped[int] = mapped_column(Integer)  # 0-100
    anger_level: Mapped[str] = mapped_column(String(20))
    anger_reasons: Mapped[str] = mapped_column(Text)
    personalized_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)
    optimized_versions: Mapped[str] = mapped_column(Text)  # JSON string
    advice: Mapped[str] = mapped_column(Text)
    profile_tip: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="analyses")


class ConversationProfile(Base):
    __tablename__ = "conversation_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), unique=True, nullable=False
    )
    insights_json: Mapped[str] = mapped_column(Text)
    summary_compact: Mapped[str] = mapped_column(Text)
    message_count_at_build: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="profile")

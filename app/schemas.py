from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = "与 Ta 的对话"
    note: str | None = None


class ConversationOut(BaseModel):
    id: int
    title: str
    note: str | None
    user_narrative: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    self_narrative_count: int = 0
    has_profile: bool = False
    profile_stale: bool = False

    model_config = {"from_attributes": True}


class NarrativeUpdate(BaseModel):
    user_narrative: str = ""


class MessageCreate(BaseModel):
    role: str = Field(pattern="^(me|friend|self_narrative)$")
    content: str = Field(min_length=1)


class ImportSelfNarrativeRequest(BaseModel):
    text: str = Field(min_length=1)
    clear_existing_self: bool = False


class ClearMessagesRequest(BaseModel):
    scope: str = Field(
        pattern="^(all|dialogue|self_narrative)$",
        description="all=全部, dialogue=我+Ta对话, self_narrative=仅自述",
    )


class ClearMessagesRequest(BaseModel):
    """all=全部 | chat=仅对话(我+Ta) | self_narrative=仅自述"""
    scope: str = Field(pattern="^(all|chat|self_narrative)$")


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportRequest(BaseModel):
    text: str = Field(min_length=1)
    friend_nickname: str | None = None
    clear_existing: bool = False


class ImportResponse(BaseModel):
    imported: int
    skipped: int
    total_messages: int
    self_narrative_total: int = 0


class ProfileOut(BaseModel):
    conversation_id: int
    insights: dict[str, Any]
    summary_compact: str
    message_count_at_build: int
    created_at: datetime
    updated_at: datetime
    is_stale: bool


class AnalyzeRequest(BaseModel):
    draft: str = Field(min_length=1)
    intent: str | None = None


class OptimizedVersion(BaseModel):
    label: str
    text: str


class AnalyzeResponse(BaseModel):
    anger_risk: int
    anger_level: str
    anger_reasons: list[str]
    personalized_reasons: list[str] = []
    optimized_versions: list[OptimizedVersion]
    advice: str
    profile_tip: str = ""
    analysis_id: int | None = None
    used_profile: bool = False


class AnalysisOut(BaseModel):
    id: int
    draft_text: str
    intent_note: str | None
    anger_risk: int
    anger_level: str
    anger_reasons: list[str]
    personalized_reasons: list[str] = []
    optimized_versions: list[OptimizedVersion]
    advice: str
    profile_tip: str = ""
    created_at: datetime

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db
from app.deepseek import analyze_message
from app.import_parser import parse_chat_text, parse_self_narrative_text
from app.models import Analysis, Conversation, ConversationProfile, Message
from app.profile_ai import build_personal_profile
from app.schemas import (
    AnalysisOut,
    AnalyzeRequest,
    AnalyzeResponse,
    ConversationCreate,
    ConversationOut,
    ImportRequest,
    ImportResponse,
    ImportSelfNarrativeRequest,
    ClearMessagesRequest,
    MessageCreate,
    MessageOut,
    NarrativeUpdate,
    OptimizedVersion,
    ProfileOut,
)

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


def _message_counts(db: Session, conversation_id: int) -> tuple[int, int]:
    total = (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == conversation_id)
        .scalar()
        or 0
    )
    self_n = (
        db.query(func.count(Message.id))
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == "self_narrative",
        )
        .scalar()
        or 0
    )
    return total, self_n


def _conv_meta(db: Session, c: Conversation) -> ConversationOut:
    count, self_n = _message_counts(db, c.id)
    prof = (
        db.query(ConversationProfile)
        .filter(ConversationProfile.conversation_id == c.id)
        .first()
    )
    has_profile = prof is not None
    stale = has_profile and count > prof.message_count_at_build
    return ConversationOut(
        id=c.id,
        title=c.title,
        note=c.note,
        user_narrative=c.user_narrative,
        created_at=c.created_at,
        updated_at=c.updated_at,
        message_count=count,
        self_narrative_count=self_n,
        has_profile=has_profile,
        profile_stale=stale,
    )


def _narrative_text(c: Conversation) -> str | None:
    t = (c.user_narrative or "").strip()
    return t or None


def _load_profile_dict(db: Session, conversation_id: int) -> dict | None:
    prof = (
        db.query(ConversationProfile)
        .filter(ConversationProfile.conversation_id == conversation_id)
        .first()
    )
    if not prof:
        return None
    return json.loads(prof.insights_json)


def _import_messages(
    db: Session,
    conversation_id: int,
    parsed: list[dict[str, str]],
    clear_existing: bool = False,
    clear_existing_self: bool = False,
    only_roles: set[str] | None = None,
) -> ImportResponse:
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")

    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    if clear_existing:
        q.delete()
    elif clear_existing_self:
        q.filter(Message.role == "self_narrative").delete()

    imported = 0
    for item in parsed:
        role = item["role"]
        if only_roles and role not in only_roles:
            continue
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=item["content"],
        )
        db.add(msg)
        imported += 1

    if imported:
        from datetime import datetime

        c.updated_at = datetime.utcnow()
    db.commit()

    total, self_n = _message_counts(db, conversation_id)
    return ImportResponse(
        imported=imported,
        skipped=0,
        total_messages=total,
        self_narrative_total=self_n,
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="暖心对话助手", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "api_configured": bool(settings.deepseek_api_key),
    }


@app.get("/api/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db)):
    rows = db.query(Conversation).order_by(Conversation.updated_at.desc()).all()
    return [_conv_meta(db, c) for c in rows]


@app.post("/api/conversations", response_model=ConversationOut)
def create_conversation(body: ConversationCreate, db: Session = Depends(get_db)):
    c = Conversation(title=body.title, note=body.note)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _conv_meta(db, c)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")
    return _conv_meta(db, c)


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")
    db.delete(c)
    db.commit()
    return {"ok": True}


@app.delete(
    "/api/conversations/{conversation_id}/narrative",
    response_model=ConversationOut,
)
def delete_narrative(conversation_id: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")
    c.user_narrative = None
    from datetime import datetime

    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _conv_meta(db, c)


@app.patch(
    "/api/conversations/{conversation_id}/narrative",
    response_model=ConversationOut,
)
def update_narrative(
    conversation_id: int,
    body: NarrativeUpdate,
    db: Session = Depends(get_db),
):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")
    text = body.user_narrative.strip()
    c.user_narrative = text if text else None
    from datetime import datetime

    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    return _conv_meta(db, c)


@app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id):
        raise HTTPException(404, "对话不存在")
    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )


@app.post(
    "/api/conversations/{conversation_id}/messages",
    response_model=MessageOut,
)
def add_message(
    conversation_id: int,
    body: MessageCreate,
    db: Session = Depends(get_db),
):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")
    msg = Message(
        conversation_id=conversation_id,
        role=body.role,
        content=body.content.strip(),
    )
    db.add(msg)
    from datetime import datetime

    c.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(msg)
    return msg


@app.delete("/api/conversations/{conversation_id}/messages/{message_id}")
def delete_message(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
):
    msg = db.get(Message, message_id)
    if not msg or msg.conversation_id != conversation_id:
        raise HTTPException(404, "记录不存在")
    c = db.get(Conversation, conversation_id)
    db.delete(msg)
    if c:
        from datetime import datetime

        c.updated_at = datetime.utcnow()
    db.commit()
    total, self_n = _message_counts(db, conversation_id)
    return {
        "ok": True,
        "total_messages": total,
        "self_narrative_total": self_n,
    }


@app.post("/api/conversations/{conversation_id}/messages/clear")
def clear_messages(
    conversation_id: int,
    body: ClearMessagesRequest,
    db: Session = Depends(get_db),
):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")

    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    if body.scope == "dialogue":
        q = q.filter(Message.role.in_(["me", "friend"]))
    elif body.scope == "self_narrative":
        q = q.filter(Message.role == "self_narrative")

    deleted = q.delete()
    from datetime import datetime

    c.updated_at = datetime.utcnow()
    db.commit()
    total, self_n = _message_counts(db, conversation_id)
    return {
        "ok": True,
        "deleted": deleted,
        "total_messages": total,
        "self_narrative_total": self_n,
    }


@app.delete("/api/conversations/{conversation_id}/profile")
def delete_profile(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id):
        raise HTTPException(404, "对话不存在")
    prof = (
        db.query(ConversationProfile)
        .filter(ConversationProfile.conversation_id == conversation_id)
        .first()
    )
    if not prof:
        raise HTTPException(404, "尚无画像")
    db.delete(prof)
    db.commit()
    return {"ok": True}


@app.post(
    "/api/conversations/{conversation_id}/import",
    response_model=ImportResponse,
)
def import_text(
    conversation_id: int,
    body: ImportRequest,
    db: Session = Depends(get_db),
):
    parsed = parse_chat_text(body.text, body.friend_nickname)
    if not parsed:
        raise HTTPException(
            400,
            "未能识别任何消息。请使用格式：我：内容 / Ta：内容，或填写 Ta 昵称匹配微信导出",
        )
    return _import_messages(db, conversation_id, parsed, body.clear_existing)


@app.post(
    "/api/conversations/{conversation_id}/import-self-narrative",
    response_model=ImportResponse,
)
def import_self_narrative(
    conversation_id: int,
    body: ImportSelfNarrativeRequest,
    db: Session = Depends(get_db),
):
    parsed = parse_self_narrative_text(body.text)
    if not parsed:
        raise HTTPException(
            400,
            "未能识别自述内容。可用「自述：正文」，或用空行 / --- 分隔多段",
        )
    return _import_messages(
        db,
        conversation_id,
        parsed,
        clear_existing_self=body.clear_existing_self,
        only_roles={"self_narrative"},
    )


@app.post(
    "/api/conversations/{conversation_id}/import-file",
    response_model=ImportResponse,
)
async def import_file(
    conversation_id: int,
    file: UploadFile = File(...),
    friend_nickname: str | None = Form(None),
    clear_existing: bool = Form(False),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(400, "无法解码文件，请使用 UTF-8 或 GBK 编码的 txt")

    parsed = parse_chat_text(text, friend_nickname)
    if not parsed:
        raise HTTPException(400, "文件中未识别到有效对话行")
    return _import_messages(db, conversation_id, parsed, clear_existing)


@app.get(
    "/api/conversations/{conversation_id}/profile",
    response_model=ProfileOut | None,
)
def get_profile(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id):
        raise HTTPException(404, "对话不存在")
    prof = (
        db.query(ConversationProfile)
        .filter(ConversationProfile.conversation_id == conversation_id)
        .first()
    )
    if not prof:
        return None
    count = (
        db.query(func.count(Message.id))
        .filter(Message.conversation_id == conversation_id)
        .scalar()
        or 0
    )
    return ProfileOut(
        conversation_id=conversation_id,
        insights=json.loads(prof.insights_json),
        summary_compact=prof.summary_compact,
        message_count_at_build=prof.message_count_at_build,
        created_at=prof.created_at,
        updated_at=prof.updated_at,
        is_stale=count > prof.message_count_at_build,
    )


@app.post(
    "/api/conversations/{conversation_id}/profile/build",
    response_model=ProfileOut,
)
async def build_profile(conversation_id: int, db: Session = Depends(get_db)):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    narrative = _narrative_text(c)
    self_count = sum(1 for m in msgs if m.role == "self_narrative")
    chat_count = len(msgs) - self_count
    if chat_count < 5 and self_count < 3 and not narrative:
        raise HTTPException(
            400,
            "至少需要 5 条对话，或 3 条 Ta 自述，或填写「手动旁白」后再生成画像",
        )

    context = [{"role": m.role, "content": m.content} for m in msgs]

    try:
        insights, _raw = await build_personal_profile(context, narrative)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"DeepSeek 分析失败: {e}") from e

    compact = insights.get("summary_compact") or insights.get("reference_card", "")
    prof = (
        db.query(ConversationProfile)
        .filter(ConversationProfile.conversation_id == conversation_id)
        .first()
    )
    if prof:
        prof.insights_json = json.dumps(insights, ensure_ascii=False)
        prof.summary_compact = compact[:4000]
        prof.message_count_at_build = len(msgs)
        from datetime import datetime

        prof.updated_at = datetime.utcnow()
    else:
        prof = ConversationProfile(
            conversation_id=conversation_id,
            insights_json=json.dumps(insights, ensure_ascii=False),
            summary_compact=compact[:4000],
            message_count_at_build=len(msgs),
        )
        db.add(prof)

    db.commit()
    db.refresh(prof)

    return ProfileOut(
        conversation_id=conversation_id,
        insights=insights,
        summary_compact=prof.summary_compact,
        message_count_at_build=prof.message_count_at_build,
        created_at=prof.created_at,
        updated_at=prof.updated_at,
        is_stale=False,
    )


@app.post(
    "/api/conversations/{conversation_id}/analyze",
    response_model=AnalyzeResponse,
)
async def analyze_draft(
    conversation_id: int,
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
):
    c = db.get(Conversation, conversation_id)
    if not c:
        raise HTTPException(404, "对话不存在")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    context = [{"role": m.role, "content": m.content} for m in msgs]
    profile = _load_profile_dict(db, conversation_id)
    narrative = _narrative_text(c)

    try:
        result, raw = await analyze_message(
            body.draft.strip(),
            body.intent.strip() if body.intent else None,
            context,
            profile,
            narrative,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"DeepSeek 调用失败: {e}") from e

    record = Analysis(
        conversation_id=conversation_id,
        draft_text=body.draft.strip(),
        intent_note=body.intent,
        anger_risk=result["anger_risk"],
        anger_level=result["anger_level"],
        anger_reasons=json.dumps(result["anger_reasons"], ensure_ascii=False),
        personalized_reasons=json.dumps(
            result.get("personalized_reasons", []), ensure_ascii=False
        ),
        optimized_versions=json.dumps(
            result["optimized_versions"], ensure_ascii=False
        ),
        advice=result["advice"],
        profile_tip=result.get("profile_tip") or "",
        raw_response=raw,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return AnalyzeResponse(
        anger_risk=result["anger_risk"],
        anger_level=result["anger_level"],
        anger_reasons=result["anger_reasons"],
        personalized_reasons=result.get("personalized_reasons", []),
        optimized_versions=[
            OptimizedVersion(**v) for v in result["optimized_versions"]
        ],
        advice=result["advice"],
        profile_tip=result.get("profile_tip", ""),
        analysis_id=record.id,
        used_profile=profile is not None or narrative is not None,
    )


@app.get(
    "/api/conversations/{conversation_id}/analyses",
    response_model=list[AnalysisOut],
)
def list_analyses(conversation_id: int, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id):
        raise HTTPException(404, "对话不存在")
    rows = (
        db.query(Analysis)
        .filter(Analysis.conversation_id == conversation_id)
        .order_by(Analysis.created_at.desc())
        .limit(50)
        .all()
    )
    out = []
    for a in rows:
        pers = []
        if a.personalized_reasons:
            try:
                pers = json.loads(a.personalized_reasons)
            except json.JSONDecodeError:
                pers = []
        out.append(
            AnalysisOut(
                id=a.id,
                draft_text=a.draft_text,
                intent_note=a.intent_note,
                anger_risk=a.anger_risk,
                anger_level=a.anger_level,
                anger_reasons=json.loads(a.anger_reasons),
                personalized_reasons=pers,
                optimized_versions=[
                    OptimizedVersion(**v)
                    for v in json.loads(a.optimized_versions)
                ],
                advice=a.advice,
                profile_tip=a.profile_tip or "",
                created_at=a.created_at,
            )
        )
    return out

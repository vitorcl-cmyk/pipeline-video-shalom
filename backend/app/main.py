"""FastAPI app: registro/login (JWT), upload de fotos, geração de vídeo
em background, limite diário por usuário, listagem e download de jobs."""
from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, time, timezone
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import pipeline
from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
)
from app.config import settings
from app.database import Base, engine, get_db
from app.models import JobStatus, User, VideoJob, VideoStyle
from app.schemas import (
    DailyUsageOut,
    Token,
    UserCreate,
    UserOut,
    VideoJobCreateResponse,
    VideoJobOut,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Reels Imobiliário API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha inválidos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


def _jobs_created_today(db: Session, user_id: str) -> int:
    return (
        db.query(VideoJob)
        .filter(VideoJob.user_id == user_id, VideoJob.created_at >= _today_start_utc())
        .count()
    )


def _process_job(job_id: str) -> None:
    """Executa a geração do vídeo (chamado em background)."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        job = db.query(VideoJob).filter(VideoJob.id == job_id).first()
        if job is None:
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            photo_paths = [Path(p) for p in job.input_photos]
            output_path = settings.OUTPUT_DIR / f"{job.id}.mp4"
            pipeline.generate_video(photo_paths, job.style, output_path)

            job.output_path = str(output_path)
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha ao processar job %s", job_id)
            job.status = JobStatus.FAILED
            job.error_message = str(exc)[:2000]
            job.completed_at = datetime.now(timezone.utc)

        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Video jobs
# ---------------------------------------------------------------------------

@app.post("/jobs", response_model=VideoJobCreateResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    background_tasks: BackgroundTasks,
    style: VideoStyle = Form(...),
    photos: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    used_today = _jobs_created_today(db, current_user.id)
    if used_today >= settings.DAILY_VIDEO_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite diário de {settings.DAILY_VIDEO_LIMIT} vídeos atingido. Tente novamente amanhã.",
        )

    if not photos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envie ao menos uma foto")
    if len(photos) > settings.MAX_PHOTOS_PER_JOB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo de {settings.MAX_PHOTOS_PER_JOB} fotos por vídeo",
        )

    job_id = uuid.uuid4().hex
    job_dir = settings.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for i, photo in enumerate(photos):
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de arquivo não suportado: {photo.content_type}",
            )

        suffix = Path(photo.filename or "").suffix or ".jpg"
        dest = job_dir / f"{i:03d}{suffix}"

        size = 0
        max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
        with dest.open("wb") as f:
            while chunk := photo.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    f.close()
                    shutil.rmtree(job_dir, ignore_errors=True)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Foto '{photo.filename}' excede {settings.MAX_UPLOAD_MB}MB",
                    )
                f.write(chunk)

        saved_paths.append(str(dest))

    job = VideoJob(
        id=job_id,
        user_id=current_user.id,
        style=style,
        status=JobStatus.PENDING,
        input_photos=saved_paths,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_process_job, job.id)

    remaining = settings.DAILY_VIDEO_LIMIT - (used_today + 1)
    return VideoJobCreateResponse(job=job, remaining_today=max(remaining, 0))


@app.get("/jobs", response_model=list[VideoJobOut])
def list_jobs(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(VideoJob)
        .filter(VideoJob.user_id == current_user.id)
        .order_by(VideoJob.created_at.desc())
        .all()
    )


@app.get("/jobs/{job_id}", response_model=VideoJobOut)
def get_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.id == job_id, VideoJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    return job


@app.get("/jobs/{job_id}/download")
def download_job(job_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(VideoJob).filter(VideoJob.id == job_id, VideoJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    if job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vídeo ainda não está pronto")

    output_path = Path(job.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo de vídeo não encontrado")

    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"reel-{job.id}.mp4",
    )


@app.get("/usage/today", response_model=DailyUsageOut)
def usage_today(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    used = _jobs_created_today(db, current_user.id)
    return DailyUsageOut(
        used_today=used,
        limit=settings.DAILY_VIDEO_LIMIT,
        remaining=max(settings.DAILY_VIDEO_LIMIT - used, 0),
    )


@app.get("/health")
def health():
    return {"status": "ok"}

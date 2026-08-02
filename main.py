from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parent; DATA_DIR = BASE_DIR / "data"; UPLOAD_DIR = DATA_DIR / "uploads"; REPORT_DIR = DATA_DIR / "reports"
for folder in (UPLOAD_DIR, REPORT_DIR): folder.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DATA_DIR / 'insightpilot.db'}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    business_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_path: Mapped[str] = mapped_column(String)
    stage: Mapped[str] = mapped_column(String, default="queued")
    agent_status: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    cleaned_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    charts_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    approved_insights: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    rejected_insights: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    events: Mapped[List["MissionEvent"]] = relationship(back_populates="mission", cascade="all, delete-orphan")
class MissionEvent(Base):
    __tablename__ = "mission_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String); status: Mapped[str] = mapped_column(String); message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    mission: Mapped[Mission] = relationship(back_populates="events")
Base.metadata.create_all(engine)
class MissionCreated(BaseModel): mission_id: str; message: str
class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    agent_name: str; status: str; message: str; timestamp: datetime
class MissionStatusResponse(BaseModel): mission_id: str; stage: str; agent_status: Dict[str, str]; error: Optional[str] = None; events: List[EventResponse]
class InsightResponse(BaseModel): claim: str; evidence_field: str; evidence_value: float | int
class RejectedInsightResponse(BaseModel): insight: InsightResponse; reason: str
class MissionResultsResponse(BaseModel):
    mission_id: str; stage: str; cleaned_data_summary: Dict[str, Any]; charts_data: Dict[str, Any]; approved_insights: List[InsightResponse]; rejected_insights: List[RejectedInsightResponse]
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
app = FastAPI(title="InsightPilot AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
def _create(source: Path, goal: Optional[str], tasks: BackgroundTasks, db: Session) -> MissionCreated:
    mission_id = str(uuid4()); db.add(Mission(id=mission_id, source_path=str(source), business_goal=goal, agent_status={})); db.commit()
    from orchestrator import run_mission
    tasks.add_task(run_mission, mission_id)
    return MissionCreated(mission_id=mission_id, message="Mission queued for analysis.")
@app.post("/missions", response_model=MissionCreated, status_code=202)
async def create_mission(background_tasks: BackgroundTasks, file: UploadFile = File(...), business_goal: Optional[str] = None, db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, "Please upload a CSV file.")
    content = await file.read()
    if not content: raise HTTPException(400, "The uploaded CSV is empty.")
    path = UPLOAD_DIR / f"{uuid4()}.csv"; path.write_bytes(content)
    return _create(path, business_goal, background_tasks, db)
@app.get("/sample-dataset", response_model=MissionCreated, status_code=202)
def sample_dataset(background_tasks: BackgroundTasks, business_goal: Optional[str] = None, db: Session = Depends(get_db)):
    source = DATA_DIR / "sample_superstore.csv"
    if not source.exists(): raise HTTPException(500, "Bundled sample dataset is missing.")
    return _create(source, business_goal or "Explore the sample Superstore sales data", background_tasks, db)
def _mission(mission_id: str, db: Session) -> Mission:
    mission = db.get(Mission, mission_id)
    if not mission: raise HTTPException(404, "Mission not found.")
    return mission
@app.get("/missions/{mission_id}/status", response_model=MissionStatusResponse)
def status(mission_id: str, db: Session = Depends(get_db)):
    mission = _mission(mission_id, db); events = db.query(MissionEvent).filter_by(mission_id=mission_id).order_by(MissionEvent.timestamp).all()
    return MissionStatusResponse(mission_id=mission.id, stage=mission.stage, agent_status=mission.agent_status or {}, error=mission.error, events=events)
@app.get("/missions/{mission_id}/results", response_model=MissionResultsResponse)
def results(mission_id: str, db: Session = Depends(get_db)):
    mission = _mission(mission_id, db)
    if mission.stage == "failed": raise HTTPException(422, mission.error or "Mission failed.")
    if mission.stage != "complete": raise HTTPException(409, "Analysis is still in progress.")
    return MissionResultsResponse(mission_id=mission.id, stage=mission.stage, cleaned_data_summary=mission.cleaned_summary or {}, charts_data=mission.charts_data or {}, approved_insights=mission.approved_insights or [], rejected_insights=mission.rejected_insights or [])
@app.get("/missions/{mission_id}/report.pdf")
def report(mission_id: str, db: Session = Depends(get_db)):
    mission = _mission(mission_id, db)
    if mission.stage != "complete": raise HTTPException(409, "Report is available when analysis completes.")
    from orchestrator import generate_pdf_report
    path = generate_pdf_report(mission, REPORT_DIR / f"{mission_id}.pdf")
    return FileResponse(path, media_type="application/pdf", filename="insightpilot-report.pdf")

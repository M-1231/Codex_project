from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from agents.data_engineer import clean_dataframe
from agents.eda_agent import analyze_dataframe
from agents.insight_agent import generate_insights
from agents.qa_agent import verify_insights

def _event(db: Any, mission: Any, agent: str, status: str, message: str) -> None:
    from main import MissionEvent
    statuses = dict(mission.agent_status or {}); statuses[agent] = status; mission.agent_status = statuses
    db.add(MissionEvent(mission_id=mission.id, agent_name=agent, status=status, message=message)); db.commit()

def run_mission(mission_id: str) -> None:
    from main import Mission, SessionLocal
    db = SessionLocal()
    try:
        mission = db.get(Mission, mission_id)
        if not mission: return
        mission.stage = "data_engineer"; db.commit(); _event(db, mission, "data_engineer", "running", "Reading and cleaning CSV data.")
        try: raw = pd.read_csv(mission.source_path)
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc: raise ValueError(f"Invalid CSV: {exc}") from exc
        if raw.empty or not len(raw.columns): raise ValueError("Invalid CSV: file has no data rows or columns.")
        cleaned, log = clean_dataframe(raw)
        mission.cleaned_summary = {"original_rows": int(len(raw)), "cleaned_rows": int(len(cleaned)), "columns": cleaned.columns.tolist(), "cleaning_log": log}
        _event(db, mission, "data_engineer", "complete", "Data cleaning complete.")
        mission.stage = "eda_agent"; db.commit(); _event(db, mission, "eda_agent", "running", "Computing descriptive analysis.")
        stats = analyze_dataframe(cleaned)
        mission.charts_data = {"top_categories": stats["top_categories"], "correlations": stats["correlations"], "trend": stats["trend"]}
        _event(db, mission, "eda_agent", "complete", "Exploratory analysis complete.")
        mission.stage = "insight_agent"; db.commit(); _event(db, mission, "insight_agent", "running", "Generating evidence-grounded insights.")
        insights = generate_insights(stats, mission.business_goal); _event(db, mission, "insight_agent", "complete", f"Generated {len(insights)} candidate insights.")
        mission.stage = "qa_agent"; db.commit(); _event(db, mission, "qa_agent", "running", "Verifying insight evidence.")
        checked = verify_insights(stats, insights); mission.approved_insights = checked["approved"]; mission.rejected_insights = checked["rejected"]
        _event(db, mission, "qa_agent", "complete", f"Approved {len(checked['approved'])} insights."); mission.stage = "complete"; db.commit()
    except Exception as exc:
        mission = db.get(Mission, mission_id)
        if mission:
            mission.stage = "failed"; mission.error = str(exc); _event(db, mission, "orchestrator", "failed", str(exc))
    finally: db.close()

def generate_pdf_report(mission: Any, output_path: Path) -> str:
    styles = getSampleStyleSheet(); doc = SimpleDocTemplate(str(output_path), pagesize=letter, leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    story = [Paragraph("InsightPilot AI Report", styles["Title"]), Paragraph(f"Business goal: {mission.business_goal or 'Not specified'}", styles["BodyText"]), Spacer(1, 14), Paragraph("Approved insights", styles["Heading2"])]
    for item in mission.approved_insights or []:
        story += [Paragraph(f"- {item['claim']} Evidence: {item['evidence_field']} = {item['evidence_value']}", styles["BodyText"]), Spacer(1, 6)]
    story += [Spacer(1, 10), Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["BodyText"])]
    doc.build(story); return str(output_path)

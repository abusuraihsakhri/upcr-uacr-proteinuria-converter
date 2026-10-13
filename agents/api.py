"""
FastAPI REST API Server for Upcr Uacr Proteinuria Converter.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from upcr_uacr import calculate_metrics, ValidationError
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Upcr Uacr Proteinuria Converter API",
    description="Urine ratio calculator API; legacy audit-demo endpoints are not clinical decision support",
    version="1.1.0",
)


class ChatRequest(BaseModel):
    query: str



class UrineRatioRequest(BaseModel):
    protein_mg_dl: Optional[float] = None
    albumin_mg_dl: Optional[float] = None
    creatinine_mg_dl: Optional[float] = None
    upcr_mg_g: Optional[float] = None
    uacr_mg_g: Optional[float] = None
    creatinine_g_day: Optional[float] = None


@app.post("/api/convert")
def api_convert(payload: UrineRatioRequest):
    """Calculate from matched spot concentrations or independently measured ratios."""
    try:
        return calculate_metrics(**payload.model_dump())
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "upcr-uacr-proteinuria-converter", "version": "1.1.0", "legacy_audit_endpoints": "demonstration only"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}

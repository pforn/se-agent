from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.db.app_db import (
    get_audit_log,
    get_dashboard_stats,
    get_health_score_history,
    list_customers,
    list_product_feedback,
    upsert_customer,
)

templates = Jinja2Templates(directory="src/ui/templates")

router = APIRouter()


# ── Dashboard ─────────────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    customers = list_customers(settings.app_db_path)
    stats = get_dashboard_stats(settings.app_db_path)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "customers": customers,
        "stats": stats,
    })


# ── Customer Detail ───────────────────────────────────────────────────


@router.get("/customer/{customer_id}", response_class=HTMLResponse)
async def customer_detail(request: Request, customer_id: str):
    customers = list_customers(settings.app_db_path)
    customer = next((c for c in customers if c["customer_id"] == customer_id), None)
    health_history = get_health_score_history(settings.app_db_path, customer_id) if customer else []
    audit = get_audit_log(settings.app_db_path, customer_id, limit=10) if customer else []
    feedback = list_product_feedback(settings.app_db_path, customer_id) if customer else []
    return templates.TemplateResponse("customer.html", {
        "request": request,
        "customer": customer,
        "health_history": health_history,
        "audit_log": audit,
        "feedback": feedback,
    })


# ── Customer Create ───────────────────────────────────────────────────


@router.post("/customer/create")
async def create_customer(request: Request, customer_id: str = Form(...), customer_name: str = Form(...)):
    upsert_customer(settings.app_db_path, customer_id, customer_name)
    customers = list_customers(settings.app_db_path)
    return templates.TemplateResponse(
        "partials/customer_list.html",
        {"request": request, "customers": customers},
    )


# ── JSON API Endpoints ────────────────────────────────────────────────


@router.get("/api/health-history/{customer_id}")
async def api_health_history(customer_id: str):
    history = get_health_score_history(settings.app_db_path, customer_id)
    return JSONResponse(content=history)


@router.get("/api/feedback-summary")
async def api_feedback_summary():
    from src.db.app_db import get_feedback_summary
    summary = get_feedback_summary(settings.app_db_path)
    return JSONResponse(content=summary)


# ── HTMX Partials ─────────────────────────────────────────────────────


@router.get("/customer/{customer_id}/audit", response_class=HTMLResponse)
async def customer_audit(request: Request, customer_id: str):
    audit = get_audit_log(settings.app_db_path, customer_id)
    return templates.TemplateResponse("partials/audit_trail.html", {"request": request, "audit_log": audit})


@router.get("/customer/{customer_id}/feedback", response_class=HTMLResponse)
async def customer_feedback(request: Request, customer_id: str):
    feedback = list_product_feedback(settings.app_db_path, customer_id)
    return templates.TemplateResponse("partials/feedback_list.html", {"request": request, "feedback": feedback})


from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import settings
from src.db.app_db import list_customers, upsert_customer

templates = Jinja2Templates(directory="src/ui/templates")

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    customers = list_customers(settings.app_db_path)
    return templates.TemplateResponse("dashboard.html", {"request": request, "customers": customers})


@router.get("/customer/{customer_id}", response_class=HTMLResponse)
async def customer_detail(request: Request, customer_id: str):
    customers = list_customers(settings.app_db_path)
    customer = next((c for c in customers if c["customer_id"] == customer_id), None)
    return templates.TemplateResponse("customer.html", {"request": request, "customer": customer})


@router.post("/customer/create")
async def create_customer(request: Request, customer_id: str = Form(...), customer_name: str = Form(...)):
    upsert_customer(settings.app_db_path, customer_id, customer_name)
    customers = list_customers(settings.app_db_path)
    return templates.TemplateResponse(
        "partials/customer_list.html",
        {"request": request, "customers": customers},
    )

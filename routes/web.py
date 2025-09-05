# routes/web.py
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import config
from services.hub_service import search_products

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str | None = None, tag: str = "", min_price: float | None = None, max_price: float | None = None, limit: int = 20):
    results = await search_products(q, tag, min_price, max_price, limit)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "name": config.HUB_NAME,
            "q": q or "",
            "tag": tag or "",
            "results": results or [],
        },
    )

@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str | None = None, tag: str = "", min_price: float | None = None, max_price: float | None = None, limit: int = 20):
    # Provide an alternate path that renders the same search UI
    results = await search_products(q, tag, min_price, max_price, limit)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "name": config.HUB_NAME,
            "q": q or "",
            "tag": tag or "",
            "results": results or [],
        },
    )

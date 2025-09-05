"""Web UI routes for HTML rendering.

These endpoints render minimal search pages using Jinja2. They proxy to the
service layer for search results and feed them to a shared template.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

import config
from services.hub_service import search_products

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
):
    """Render the main search page with optional filters."""
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
async def search_page(
    request: Request,
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
):
    """Alternative path to render the same search UI."""
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


# Map hub UI paths to the same search interface for convenience
@router.get("/hub", response_class=HTMLResponse)
async def hub_home(
    request: Request,
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
):
    """Hub landing page rendering the shared search template."""
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


@router.get("/hub/search", response_class=HTMLResponse)
async def hub_search(
    request: Request,
    q: str | None = None,
    tag: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 20,
):
    """Hub search path rendering the shared search template."""
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


@router.get("/hub/product/{id}", response_class=PlainTextResponse)
async def hub_product_page(id: str) -> str:
    """Minimal placeholder product page."""
    return f"Product page placeholder for {id}"


@router.get("/hub/seller/{id}", response_class=PlainTextResponse)
async def hub_seller_page(id: str) -> str:
    """Minimal placeholder seller page."""
    return f"Seller page placeholder for {id}"

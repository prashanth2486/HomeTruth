"""HTTP API. The PDF endpoint is POST so income never has to be stored or put in a URL."""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from api.auth_routes import router as auth_router
from catalog import (
    CatalogUnavailable,
    filter_listings,
    listing_by_id,
    load_catalog,
    locality_by_name,
    map_localities,
    search_localities,
)
from chat import respond
from db import init_db
from features import location_for
from predict import analyze, compare
from report import build_pdf
from schemas import AnalysisResult, AnalyzeRequest, ChatRequest, CompareRequest, CompareResult
from validation import InputError


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="HomeTruth", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)

DIST = ROOT / "web" / "dist"


@app.exception_handler(InputError)
async def handle_input_error(_request, exc: InputError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


def _catalog() -> dict:
    try:
        return load_catalog()
    except CatalogUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
def analyze_listing(body: AnalyzeRequest):
    return analyze(body)


@app.post("/compare", response_model=CompareResult)
def compare_listings(body: CompareRequest):
    return compare(body)


@app.post("/chat")
def chat(body: ChatRequest):
    return respond(body)


@app.post("/report")
def report(body: AnalysisResult):
    pdf = build_pdf(body)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=hometruth-estimate.pdf"},
    )


@app.get("/localities")
def localities(q: str = "", limit: int = Query(default=24, ge=1, le=100)):
    catalog = _catalog()
    return {
        "note": catalog["note"],
        "localities": search_localities(catalog, q, limit),
    }


@app.get("/localities/{name}/location")
def locality_location(name: str):
    return location_for(name)


@app.get("/localities/{name}")
def locality_detail(
    name: str,
    bhk: int | None = None,
    verdict: str | None = None,
    max_price: float | None = None,
    sort: str = "price",
    limit: int = Query(default=40, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    catalog = _catalog()
    summary = locality_by_name(catalog, name)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No locality named {name}.")
    page = filter_listings(
        catalog,
        locality=summary["name"],
        bhk=bhk,
        verdict=verdict,
        max_price=max_price,
        sort=sort if sort in {"price", "gap"} else "price",
        limit=limit,
        offset=offset,
    )
    return {"note": catalog["note"], "locality": summary, **page}


@app.get("/listings")
def listings(
    locality: str | None = None,
    bhk: int | None = None,
    verdict: str | None = None,
    max_price: float | None = None,
    sort: str = "price",
    limit: int = Query(default=40, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    catalog = _catalog()
    page = filter_listings(
        catalog,
        locality=locality,
        bhk=bhk,
        verdict=verdict,
        max_price=max_price,
        sort=sort if sort in {"price", "gap"} else "price",
        limit=limit,
        offset=offset,
    )
    return {"note": catalog["note"], **page}


@app.get("/listings/{listing_id}")
def one_listing(listing_id: str):
    catalog = _catalog()
    item = listing_by_id(catalog, listing_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"No listing {listing_id}.")
    return {"note": catalog["note"], "listing": item}


@app.get("/map")
def map_points():
    catalog = _catalog()
    return {"note": catalog["note"], "localities": map_localities(catalog)}


def _mount_site() -> None:
    assets = DIST / "assets"
    if not assets.is_dir():
        return
    app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def site(full_path: str):
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Site has not been built.")


_mount_site()

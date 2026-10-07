"""HTTP API. The PDF endpoint is POST so income never has to be stored or put in a URL."""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response

from chat import respond
from predict import analyze, compare
from report import build_pdf
from schemas import AnalysisResult, AnalyzeRequest, ChatRequest, CompareRequest, CompareResult
from validation import InputError

app = FastAPI(title="HomeTruth", version="0.1.0")


@app.exception_handler(InputError)
async def handle_input_error(_request, exc: InputError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


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

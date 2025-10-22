# app.py
import json
from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pubmed_tool import search_pubmed  # your existing logic file

app = FastAPI(title="PubMed Search Tool", version="1.0.0", openapi_version="3.0.3")

class Article(BaseModel):
    pmid: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    authors: List[str] = []
    doi: Optional[str] = None
    mesh_terms: List[str] = []
    url: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[Article]

class HealthResponse(BaseModel):
    status: str

@app.get("/", tags=["meta"])
def root():
    return {"service": "PubMed Search Tool", "status": "ok", "hint": "See /docs and /search"}

@app.get("/healthz", response_model=HealthResponse, tags=["meta"], operation_id="healthz")
def healthz():
    return {"status": "ok"}

MAX_ABS = 1200  # keep responses compact; reduce 503 risk

@app.get(
    "/search",
    response_model=SearchResponse,
    summary="Search PubMed and return structured results (SORTED BY DATE)",
    tags=["pubmed"],
    operation_id="pubmed_search_recent"
)
def search(
    q: str = Query(..., description="PubMed query string"),
    max_results: int = Query(3, ge=1, le=200),                 # smaller default helps
    mindate: Optional[str] = Query(None, description="YYYY or YYYY/MM/DD"),
    maxdate: Optional[str] = Query(None, description="YYYY or YYYY/MM/DD")
):
    try:
        result = search_pubmed(q, max_results=max_results, mindate=mindate, maxdate=maxdate)

        # --- Guard 1: if someone accidentally returned a JSON string, parse it ---
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                # If two JSON objects got concatenated as a string, keep only the first one
                first_split = result.find("}{")
                candidate = result[:first_split+1] if first_split != -1 else result
                result = json.loads(candidate)

        # --- Guard 2: trim abstracts to keep payload small (avoid 503 in LLM step) ---
        if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
            for art in result["results"]:
                if isinstance(art, dict) and "abstract" in art and art["abstract"]:
                    if len(art["abstract"]) > MAX_ABS:
                        art["abstract"] = art["abstract"][:MAX_ABS] + "…"

        # Validate & return as proper JSON object (never a quoted string)
        return SearchResponse(**result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

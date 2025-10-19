from typing import List, Optional
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyUrl

from pubmed_tool import search_pubmed  # your existing logic

# Force OpenAPI 3.0.x so Dify is happy
app = FastAPI(
    title="PubMed Search Tool",
    version="1.0.0",
    openapi_version="3.0.3"
)

# --- Pydantic response models so the schema is explicit ---

class Article(BaseModel):
    pmid: Optional[str] = None
    title: Optional[str] = None
    abstract: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[str] = None
    authors: List[str] = []
    doi: Optional[str] = None
    mesh_terms: List[str] = []
    url: Optional[str] = None  # could use AnyUrl, but Optional[str] is lenient

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

@app.get(
    "/search",
    response_model=SearchResponse,
    summary="Search PubMed and return structured results",
    tags=["pubmed"],
    operation_id="pubmed_search"  # stable ID helps some tooling
)
def search(
    q: str = Query(..., description="PubMed query string"),
    max_results: int = Query(25, ge=1, le=200),
    mindate: Optional[str] = Query(None, description="YYYY or YYYY/MM/DD"),
    maxdate: Optional[str] = Query(None, description="YYYY or YYYY/MM/DD")
):
    """
    Calls PubMed (E-utilities) and returns structured results.
    """
    try:
        result = search_pubmed(q, max_results=max_results, mindate=mindate, maxdate=maxdate)
        # result is already a dict like {"query": ..., "count": ..., "results": [...]}
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from typing import Optional
from pubmed_tool import search_pubmed

app = FastAPI(title="PubMed Search Tool", version="1.0.0")

@app.get("/search")
def search(
    q: str = Query(..., description="PubMed query string"),
    max_results: int = Query(25, ge=1, le=200),
    mindate: Optional[str] = Query(None),
    maxdate: Optional[str] = Query(None)
):
    try:
        result = search_pubmed(q, max_results=max_results,
                               mindate=mindate, maxdate=maxdate)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

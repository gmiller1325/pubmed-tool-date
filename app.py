{\rtf1\ansi\ansicpg1252\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 from fastapi import FastAPI, Query\
from fastapi.responses import JSONResponse\
from typing import Optional\
from pubmed_tool import search_pubmed\
\
app = FastAPI(title="PubMed Search Tool", version="1.0.0")\
\
@app.get("/search")\
def search(\
    q: str = Query(..., description="PubMed query string"),\
    max_results: int = Query(25, ge=1, le=200),\
    mindate: Optional[str] = Query(None),\
    maxdate: Optional[str] = Query(None)\
):\
    try:\
        result = search_pubmed(q, max_results=max_results,\
                               mindate=mindate, maxdate=maxdate)\
        return JSONResponse(result)\
    except Exception as e:\
        return JSONResponse(\{"error": str(e)\}, status_code=500)\
}
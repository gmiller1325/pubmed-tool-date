import os
import time
import requests
from typing import List, Dict, Any, Optional
from lxml import etree


NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def _build_params(extra: dict) -> dict:
    params = {"retmode": "json"}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    params.update(extra)
    return params

def _rate_limit_sleep():
    # Gentle pacing so you don't hit PubMed rate limits.
    time.sleep(0.12 if NCBI_API_KEY else 0.35)

def esearch(query: str, max_results: int = 50,
            mindate: Optional[str] = None, maxdate: Optional[str] = None) -> List[str]:
    """
    Return a list of PMIDs for the query.
    mindate/maxdate: 'YYYY' or 'YYYY/MM/DD' (publication date window)
    """
    _rate_limit_sleep()
    params = _build_params({
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "pub_date",
    })
    if mindate or maxdate:
        params["datetype"] = "pdat"
        if mindate: params["mindate"] = mindate
        if maxdate: params["maxdate"] = maxdate

    r = requests.get(f"{BASE}/esearch.fcgi", params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("esearchresult", {}).get("idlist", [])

def efetch_abstracts(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch detailed records (title, abstract, authors, journal, year, DOI, MeSH terms).
    """
    if not pmids:
        return []
    _rate_limit_sleep()
    params = _build_params({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    })
    r = requests.get(f"{BASE}/efetch.fcgi", params=params, timeout=60)
    r.raise_for_status()
    root = etree.fromstring(r.content)

    results = []
    for art in root.findall(".//PubmedArticle"):
        # PMID
        pmid_el = art.find(".//PMID")
        pmid = pmid_el.text.strip() if pmid_el is not None else None

        # Title
        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        # Abstract (may be split in parts)
        abs_elems = art.findall(".//Abstract/AbstractText")
        abstract = " ".join("".join(a.itertext()).strip() for a in abs_elems) if abs_elems else ""

        # Journal & Year
        journal_el = art.find(".//Journal/Title")
        journal = journal_el.text.strip() if journal_el is not None else ""
        year_el = art.find(".//JournalIssue/PubDate/Year")
        year = year_el.text.strip() if year_el is not None else ""

        # Authors
        authors = []
        for au in art.findall(".//AuthorList/Author"):
            last = (au.findtext("LastName") or "").strip()
            fore = (au.findtext("ForeName") or "").strip()
            if last or fore:
                authors.append(f"{last}, {fore}".strip(", "))

        # DOI (if available)
        doi = ""
        for iden in art.findall(".//ArticleIdList/ArticleId"):
            if iden.get("IdType") == "doi":
                doi = (iden.text or "").strip()

        # MeSH terms
        mesh_terms = []
        for mt in art.findall(".//MeshHeading/DescriptorName"):
            if mt.text:
                mesh_terms.append(mt.text.strip())

        results.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "year": year,
            "authors": authors,
            "doi": doi,
            "mesh_terms": mesh_terms,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        })

    return results

def search_pubmed(query: str,
                  max_results: int = 25,
                  mindate: Optional[str] = None,
                  maxdate: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point: run a query and return structured results.
    """
    pmids = esearch(query=query, max_results=max_results, mindate=mindate, maxdate=maxdate)
    records = efetch_abstracts(pmids)
    return {
        "query": query,
        "count": len(records),
        "results": records
    }

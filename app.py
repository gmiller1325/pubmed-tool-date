import os
import time
import requests
from flask import Flask, request, jsonify

# This line creates the web server
app = Flask(__name__)

# This loads your secret API key from Render's "Environment Variables"
# Make sure you set this variable in your Render service settings
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

# A simple "health check" route. You can visit this in your browser
# (e.g., https://your-tool-name.onrender.com/) to see if the server is running.
@app.route('/')
def home():
    return "PubMed Search Tool is alive and running!"

# This is your main tool endpoint that Dify will call.
# The full URL will be something like: https://your-tool-name.onrender.com/search-pubmed
@app.route('/search-pubmed', methods=['POST'])
def pubmed_search_endpoint():
    
    # 1. Get the query from the JSON Dify sends
    data = request.json
    query_string = data.get('query')

    if not query_string:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    if not NCBI_API_KEY:
        # This error will show in your Render logs if you forget the key
        return jsonify({"error": "Server is missing NCBI_API_KEY"}), 500

    try:
        # --- FIX #1: Prevent 429 "Too Many Requests" Error ---
        time.sleep(0.2)  # Pause to stay within NCBI's rate limit

        # --- Part A: Search PubMed to get PMIDs ---
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query_string,
            "api_key": NCBI_API_KEY,
            "retmode": "json",
            "retmax": 3  # Get the top 3 results
        }
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status() # Stop if there's an API error
        search_data = search_response.json()
        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return jsonify({"formatted_results": "No relevant articles found on PubMed."})

        # --- Part B: Fetch summaries for those PMIDs ---
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),
            "api_key": NCBI_API_KEY,
            "retmode": "json"
        }
        summary_response = requests.get(summary_url, params=summary_params)
        summary_response.raise_for_status()
        summary_data = summary_response.json()
        
        # --- FIX #2: Prevent Citation Hallucinations ---
        # "Weld" the PMID and its metadata together into a single, clean string
        final_context_string = ""
        for pmid in pmids:
            result = summary_data.get("result", {}).get(pmid, {})
            title = result.get("title", "No title available.")
            authors = ", ".join([author["name"] for author in result.get("authors", [])])
            pubdate = result.get("pubdate", "No date available.")
            
            final_context_string += (
                f"---[START OF CITATION]---\n"
                f"Source: [PMID: {pmid}]\n"
                f"Title: {title}\n"
                f"Authors: {authors}\n"
                f"Date: {pubdate}\n"
                f"---[END OF CITATION]---\n\n"
            )
        
        # --- Part C: Return the clean, formatted string to Dify ---
        return jsonify({"formatted_results": final_context_string})

    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": f"API request error: {req_err}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == "__main__":
    # This part tells Render how to start the server
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

import os
import time
import requests
from flask import Flask, request, jsonify

# Initialize the Flask web server
app = Flask(__name__)

# Load your secret NCBI API key from an environment variable
# Hosting platforms (like Railway/Render) use this for security
NCBI_API_KEY = os.environ.get("NCBI_API_KEY")

if not NCBI_API_KEY:
    print("Error: NCBI_API_KEY environment variable not set.")
    # In a real app, you might exit or raise an error
    # For now, we'll just print a warning.
    
@app.route('/')
def home():
    # A simple route to check if the app is running
    return "PubMed Search Tool is alive and running!"

@app.route('/search-pubmed', methods=['POST'])
def pubmed_search_endpoint():
    """
    This is the main API endpoint that Dify will call.
    It expects a JSON payload like: {"query": "search term"}
    """
    
    # Get the JSON data that Dify sends
    data = request.json
    query_string = data.get('query')

    if not query_string:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    if not NCBI_API_KEY:
        return jsonify({"error": "Server is missing NCBI_API_KEY"}), 500

    try:
        # --- FIX 1: Prevent 429 "Too Many Requests" Error ---
        time.sleep(0.2)  # Pause to stay within NCBI's 10 requests/sec limit

        # --- Part A: Search PubMed to get a list of PMIDs ---
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query_string,
            "api_key": NCBI_API_KEY,
            "retmode": "json",
            "retmax": 3  # Get the top 3 most relevant results
        }
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()  # Raise an error on bad responses
        search_data = search_response.json()
        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return jsonify({"formatted_results": "No relevant articles found on PubMed."})

        # --- Part B: Fetch summaries for those PMIDs ---
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "pubmed",
            "id": ",".join(pmids),  # Join PMIDs with a comma
            "api_key": NCBI_API_KEY,
            "retmode": "json"
        }
        summary_response = requests.get(summary_url, params=summary_params)
        summary_response.raise_for_status()
        summary_data = summary_response.json()
        
        # --- FIX 2: Prevent Citation Hallucinations ---
        # "Weld" the PMIDs and abstracts together into one clean string
        final_context_.string = ""
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
        
        # --- Part C: Return the formatted string back to Dify ---
        return jsonify({"formatted_results": final_context_string})

    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": f"API request error: {req_err}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == "__main__":
    # This block lets you run the server locally for testing
    # It will run on port 8080 by default
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
        print(first["title"])\
        print(first["url"])\
}

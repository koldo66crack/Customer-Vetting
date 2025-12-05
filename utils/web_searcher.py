"""
Web search utility using Tavily API.
Searches for company information using multiple queries.
"""

import os
import json
from tavily import TavilyClient


def search_company(company_name):
    """
    Search for company information using Tavily API with multiple queries.
    
    Args:
        company_name (str): Name of the company to search for
        
    Returns:
        dict: Combined search results from multiple queries in JSON format
    """
    try:
        # Initialize Tavily client
        tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        # Define search queries with their result counts
        search_queries = [
            {"query": f'"{company_name} UK"', "max_results": 10},
            {"query": f'"{company_name} UK news"', "max_results": 10},
            {"query": f'"{company_name} UK reviews"', "max_results": 10}
        ]
        
        # Store all results
        all_results = {
            "company_name": company_name,
            "searches": []
        }
        
        # Perform each search
        for search_config in search_queries:
            query = search_config["query"]
            max_results = search_config["max_results"]
            
            print(f"Searching: '{query}' (max {max_results} results)")
            
            search_results = tavily_client.search(
                query=query,
                search_depth="basic",
                max_results=max_results
            )
            
            # Extract relevant data with URLs
            results_list = []
            for result in search_results.get('results', []):
                results_list.append({
                    "title": result.get('title', 'N/A'),
                    "url": result.get('url', 'N/A'),
                    "content": result.get('content', 'N/A')
                })
            
            all_results["searches"].append({
                "query": query,
                "result_count": len(results_list),
                "results": results_list
            })
            
            print(f"  Found {len(results_list)} results")
        
        total_results = sum(s["result_count"] for s in all_results["searches"])
        print(f"\nTotal results collected: {total_results}")
        
        return all_results
    
    except Exception as e:
        raise Exception(f"Error searching for company: {str(e)}")


def main():
    """Test function for web searcher - saves results to testing/ folder."""
    from dotenv import load_dotenv
    from datetime import datetime
    load_dotenv()
    
    # Test with a sample company
    test_company = input("Enter company name to search: ")
    
    print("\n=== Starting Web Search ===\n")
    
    # Search for company
    results = search_company(test_company)
    
    # Print summary
    print("\n=== Search Summary ===")
    for search in results["searches"]:
        print(f"\nQuery: '{search['query']}'")
        print(f"Results: {search['result_count']}")
        for idx, result in enumerate(search['results'], 1):
            print(f"  {idx}. {result['title'][:60]}...")
            print(f"     URL: {result['url']}")
    
    # Save to testing folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company_name = test_company.replace(" ", "_").replace("/", "-")
    filename = f"testing/{safe_company_name}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {filename}")


if __name__ == "__main__":
    main()


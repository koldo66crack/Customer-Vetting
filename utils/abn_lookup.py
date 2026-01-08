"""
ABN Lookup scraper for Australian Business Register.
Searches and retrieves company information from https://abr.business.gov.au/
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime


BASE_URL = "https://abr.business.gov.au"
SEARCH_URL = f"{BASE_URL}/Search/ResultsActive"
DETAIL_URL = f"{BASE_URL}/ABN/View"

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def search_abn_by_name(company_name):
    """
    Search ABN Lookup by company name.
    
    Args:
        company_name (str): Company name to search for
        
    Returns:
        list: List of matching results with ABN, name, type, and location
    """
    try:
        print(f"Searching ABN Lookup for: {company_name}")
        
        params = {"SearchText": company_name}
        response = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the results table
        results_table = soup.find("table")
        if not results_table:
            print("No results found")
            return []
        
        results = []
        rows = results_table.find_all("tr")[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 4:
                # Extract ABN from the link
                abn_link = cells[0].find("a")
                abn = abn_link.get_text(strip=True) if abn_link else "N/A"
                
                # Check if ABN is active (look for "Active" text in cell)
                status = "Active" if "Active" in cells[0].get_text() else "Cancelled"
                
                result = {
                    "abn": abn,
                    "status": status,
                    "name": cells[1].get_text(strip=True),
                    "type": cells[2].get_text(strip=True),
                    "location": cells[3].get_text(strip=True)
                }
                results.append(result)
        
        print(f"Found {len(results)} result(s)")
        return results
    
    except requests.RequestException as e:
        raise Exception(f"Error searching ABN Lookup: {str(e)}")


def get_abn_details(abn):
    """
    Get detailed information for a specific ABN.
    
    Args:
        abn (str): ABN number (with or without spaces)
        
    Returns:
        dict: Detailed ABN information
    """
    try:
        # Remove spaces from ABN for the URL
        abn_clean = abn.replace(" ", "")
        
        print(f"Fetching details for ABN: {abn}")
        
        params = {"abn": abn_clean}
        response = requests.get(DETAIL_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Initialize result dictionary
        details = {
            "abn": abn,
            "entity_name": "N/A",
            "status": "N/A",
            "entity_type": "N/A",
            "gst_registered": "N/A",
            "location": "N/A",
            "business_names": [],
            "last_updated": "N/A"
        }
        
        # Find all tables on the page
        tables = soup.find_all("table")
        
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                header = row.find("th")
                cell = row.find("td")
                
                if header and cell:
                    header_text = header.get_text(strip=True).lower()
                    cell_text = cell.get_text(strip=True)
                    
                    # Map headers to our fields
                    if "entity name" in header_text:
                        details["entity_name"] = cell_text
                    elif "abn status" in header_text:
                        details["status"] = cell_text
                    elif "entity type" in header_text:
                        details["entity_type"] = cell_text
                    elif "goods & services tax" in header_text or "gst" in header_text:
                        details["gst_registered"] = cell_text
                    elif "main business location" in header_text:
                        details["location"] = cell_text
                    elif "business name" in header_text and "from" not in header_text:
                        # This is the business name column header, skip
                        pass
        
        # Extract business names from the business names table
        # Business names are in a separate table with "Business name" and "From" columns
        for table in tables:
            header_row = table.find("tr")
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all("th")]
                if "business name" in headers and "from" in headers:
                    # This is the business names table
                    data_rows = table.find_all("tr")[1:]  # Skip header
                    for row in data_rows:
                        cells = row.find_all("td")
                        if cells:
                            business_name = cells[0].get_text(strip=True)
                            if business_name and business_name != "N/A":
                                details["business_names"].append(business_name)
        
        # Extract last updated date from the page
        page_text = soup.get_text()
        if "ABN last updated:" in page_text:
            # Find the list item with last updated info
            list_items = soup.find_all("li")
            for li in list_items:
                li_text = li.get_text(strip=True)
                if "ABN last updated:" in li_text:
                    details["last_updated"] = li_text.replace("ABN last updated:", "").strip()
                    break
        
        return details
    
    except requests.RequestException as e:
        raise Exception(f"Error fetching ABN details: {str(e)}")


def get_top_search_results(company_name, limit=10):
    """
    Search by company name and return top results for user selection.
    (For future use: let user choose from multiple matches)
    
    Args:
        company_name (str): Company name to search for
        limit (int): Maximum number of results to return (default: 10)
        
    Returns:
        list: Top search results (up to limit)
    """
    search_results = search_abn_by_name(company_name)
    return search_results[:limit]


def lookup_company(company_name=None, abn=None):
    """
    Main function to lookup a company and return full details.
    
    If ABN is provided, fetches details directly.
    If only company name is provided, searches and returns details for the first result.
    
    Args:
        company_name (str, optional): Company name to search for
        abn (str, optional): ABN number (if known, takes priority)
        
    Returns:
        dict: Full company details, or None if not found
    """
    # Validate inputs
    if not company_name and not abn:
        raise ValueError("Either company_name or abn must be provided")
    
    # If ABN is provided, fetch details directly
    if abn:
        print(f"ABN provided, fetching details directly...")
        return get_abn_details(abn)
    
    # Otherwise, search by company name
    search_results = search_abn_by_name(company_name)
    
    if not search_results:
        print(f"No results found for '{company_name}'")
        return None
    
    # Get details for the first result
    first_result = search_results[0]
    print(f"Using first result: '{first_result['name']}'")
    
    details = get_abn_details(first_result["abn"])
    
    return details


def main():
    """Test function for ABN Lookup scraper - saves results to testing/ folder."""
    
    print("\n=== ABN Lookup Scraper Test ===\n")
    
    # Ask for ABN first (optional)
    test_abn = input("Enter ABN (or press Enter to skip): ").strip()
    
    # Ask for company name
    test_company = input("Enter company name to search: ").strip()
    
    # Handle empty inputs
    if not test_abn:
        test_abn = None
    if not test_company:
        test_company = None
    
    # Validate we have at least one input
    if not test_abn and not test_company:
        print("No input provided. Using default test (company name: SIPBN)")
        test_company = "SIPBN"
    
    # Use the main lookup_company function
    print("\n--- Running Lookup ---")
    details = lookup_company(company_name=test_company, abn=test_abn)
    
    if not details:
        print("No results found. Exiting.")
        return
    
    # Display results
    print("\n--- Company Details ---")
    print(f"Entity Name: {details['entity_name']}")
    print(f"ABN: {details['abn']}")
    print(f"Status: {details['status']}")
    print(f"Entity Type: {details['entity_type']}")
    print(f"GST Registered: {details['gst_registered']}")
    print(f"Location: {details['location']}")
    print(f"Business Names: {', '.join(details['business_names']) if details['business_names'] else 'None'}")
    print(f"Last Updated: {details['last_updated']}")
    
    # Save to testing folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create safe filename
    if test_abn:
        safe_name = f"abn_{test_abn.replace(' ', '')}"
    else:
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in test_company)
        safe_name = safe_name.replace(" ", "_")[:50]
    filename = f"testing/abn_lookup_{safe_name}_{timestamp}.json"
    
    output_data = {
        "search_query": {
            "company_name": test_company,
            "abn": test_abn
        },
        "result": details
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {filename}")


if __name__ == "__main__":
    main()


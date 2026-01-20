"""
Customer Vetting Pipeline - Data Gathering Orchestrator
Runs all data sources concurrently and returns structured results for report generation.
"""

import concurrent.futures
import json
from utils.apify_scrapers import get_linkedin_company_details, get_linkedin_company_posts, get_website_traffic
from utils.abn_lookup import lookup_company
from utils.web_searcher import search_company


def run_vetting_pipeline(company_name, linkedin_url, website_domain, abn):
    """
    Run data gathering processes concurrently (excludes CreditorWatch).
    CreditorWatch must be called separately due to Playwright threading limitations on Windows.
    
    Args:
        company_name (str): Company name for ABN lookup and web search
        linkedin_url (str): LinkedIn company profile URL
        website_domain (str): Website domain for SimilarWeb (e.g., "example.com")
        abn (str): Australian Business Number
        
    Returns:
        dict: Structured results from all data sources with success/error status
    """
    print(f"\n{'='*60}")
    print(f"Starting vetting pipeline for: {company_name}")
    print(f"{'='*60}\n")
    
    # Initialize results structure
    results = {
        "company_name": company_name,
        "inputs": {
            "linkedin_url": linkedin_url,
            "website_domain": website_domain,
            "abn": abn
        },
        "data_sources": {
            "linkedin_details": {"status": "pending", "data": None, "error": None},
            "linkedin_posts": {"status": "pending", "data": None, "error": None},
            "website_traffic": {"status": "pending", "data": None, "error": None},
            "abn_lookup": {"status": "pending", "data": None, "error": None},
            "web_search": {"status": "pending", "data": None, "error": None}
        }
    }
    
    # Define tasks for thread pool
    tasks = [
        ("linkedin_details", get_linkedin_company_details, (linkedin_url,)),
        ("linkedin_posts", get_linkedin_company_posts, (linkedin_url, 10)),
        ("website_traffic", get_website_traffic, (website_domain,)),
        ("abn_lookup", lookup_company, (company_name, abn)),
        ("web_search", search_company, (company_name,))
    ]
    
    # Run tasks concurrently in thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        # Submit all tasks
        future_to_key = {}
        for key, func, args in tasks:
            future = executor.submit(func, *args)
            future_to_key[future] = key
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                data = future.result()
                results["data_sources"][key]["status"] = "success"
                results["data_sources"][key]["data"] = data
                print(f"✅ {key}: completed successfully")
            except Exception as e:
                results["data_sources"][key]["status"] = "error"
                results["data_sources"][key]["error"] = str(e)
                print(f"❌ {key}: failed - {str(e)}")
    
    # Summary
    success_count = sum(1 for ds in results["data_sources"].values() if ds["status"] == "success")
    total_count = len([ds for ds in results["data_sources"].values() if ds["status"] != "skipped"])
    print(f"\n{'='*60}")
    print(f"Pipeline complete: {success_count}/{total_count} sources succeeded")
    print(f"{'='*60}\n")
    
    return results


def format_results_for_report(pipeline_results):
    """
    Format pipeline results into a string suitable for the report generator.
    
    Args:
        pipeline_results (dict): Results from run_vetting_pipeline()
        
    Returns:
        str: Formatted string with all gathered data
    """
    output_parts = []
    
    # Company header
    output_parts.append(f"COMPANY: {pipeline_results['company_name']}")
    output_parts.append("=" * 60)
    
    # LinkedIn Company Details
    linkedin_details = pipeline_results["data_sources"]["linkedin_details"]
    output_parts.append("\n### LINKEDIN COMPANY DETAILS ###")
    if linkedin_details["status"] == "success":
        output_parts.append(json.dumps(linkedin_details["data"], indent=2, ensure_ascii=False))
    else:
        output_parts.append(f"[Data unavailable: {linkedin_details['error']}]")
    
    # LinkedIn Posts
    linkedin_posts = pipeline_results["data_sources"]["linkedin_posts"]
    output_parts.append("\n### LINKEDIN RECENT POSTS ###")
    if linkedin_posts["status"] == "success":
        output_parts.append(json.dumps(linkedin_posts["data"], indent=2, ensure_ascii=False))
    else:
        output_parts.append(f"[Data unavailable: {linkedin_posts['error']}]")
    
    # Website Traffic (SimilarWeb)
    website_traffic = pipeline_results["data_sources"]["website_traffic"]
    output_parts.append("\n### WEBSITE TRAFFIC (SIMILARWEB) ###")
    if website_traffic["status"] == "success":
        output_parts.append(json.dumps(website_traffic["data"], indent=2, ensure_ascii=False))
    else:
        output_parts.append(f"[Data unavailable: {website_traffic['error']}]")
    
    # ABN Lookup
    abn_lookup = pipeline_results["data_sources"]["abn_lookup"]
    output_parts.append("\n### ABN LOOKUP (AUSTRALIAN BUSINESS REGISTER) ###")
    if abn_lookup["status"] == "success":
        output_parts.append(json.dumps(abn_lookup["data"], indent=2, ensure_ascii=False))
    else:
        output_parts.append(f"[Data unavailable: {abn_lookup['error']}]")
    
    # Web Search
    web_search = pipeline_results["data_sources"]["web_search"]
    output_parts.append("\n### WEB SEARCH RESULTS ###")
    if web_search["status"] == "success":
        output_parts.append(json.dumps(web_search["data"], indent=2, ensure_ascii=False))
    else:
        output_parts.append(f"[Data unavailable: {web_search['error']}]")
    
    # CreditorWatch
    creditorwatch = pipeline_results["data_sources"]["creditorwatch"]
    output_parts.append("\n### CREDITORWATCH (FINANCIAL RISK DATA) ###")
    if creditorwatch["status"] == "success":
        data = creditorwatch["data"]
        # Use GPT cleaned text if available, otherwise fall back to raw data
        if data.get("gpt_cleaned_text"):
            output_parts.append(data["gpt_cleaned_text"])
        else:
            # Fallback to structured data (without full_text which is too messy)
            clean_data = {k: v for k, v in data.items() if k != "full_text"}
            output_parts.append(json.dumps(clean_data, indent=2, ensure_ascii=False))
    elif creditorwatch["status"] == "skipped":
        output_parts.append(f"[Skipped: {creditorwatch['error']}]")
    else:
        output_parts.append(f"[Data unavailable: {creditorwatch['error']}]")
    
    return "\n".join(output_parts)


def main():
    """Test function for the pipeline."""
    from dotenv import load_dotenv
    from utils.creditorwatch_scraper import get_creditorwatch_data
    load_dotenv()
    
    print("\n=== Pipeline Test ===\n")
    
    # Get inputs
    company_name = input("Enter company name: ").strip()
    linkedin_url = input("Enter LinkedIn company URL: ").strip()
    website_domain = input("Enter website domain (e.g., example.com): ").strip()
    abn = input("Enter ABN: ").strip()
    
    # Run pipeline (5 concurrent sources)
    results = run_vetting_pipeline(
        company_name=company_name,
        linkedin_url=linkedin_url,
        website_domain=website_domain,
        abn=abn
    )
    
    # Format for report
    formatted = format_results_for_report(results)
    print("\n=== Formatted Output ===")
    print(formatted)


if __name__ == "__main__":
    main()


"""
Data scraping utilities using Apify.
Extracts company details and posts from LinkedIn profiles, and website traffic data from SimilarWeb.
"""

from apify_client import ApifyClient
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def get_linkedin_company_details(company_url):
    """
    Extract company details from LinkedIn company profile.
    
    Args:
        company_url (str): LinkedIn company profile URL
        
    Returns:
        dict: Cleaned company details with selected fields
    """
    try:
        # Initialize the ApifyClient with API token
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        print(f"Fetching LinkedIn company details for: {company_url}")
        
        # Prepare the Actor input
        run_input = {"url": [company_url]}
        
        # Run the Actor and wait for it to finish
        run = client.actor("bn2Zqf05Giqym1kiD").call(run_input=run_input)
        
        # Fetch Actor results from the run's dataset
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)
        
        print(f"Retrieved {len(results)} result(s)")
        
        # Get the first result (should only be one for a single company URL)
        raw_data = results[0] if results else {}
        
        # Extract and return only the fields we need in the specified order
        cleaned_data = {
            "name": raw_data.get("name", "N/A"),
            "description": raw_data.get("description", "N/A"),
            "headquarters": raw_data.get("Headquarters", "N/A"),
            "slogan": raw_data.get("slogan", "N/A"),
            "industry": raw_data.get("Industry", "N/A"),
            "founded": raw_data.get("Founded", "N/A"),
            "number_of_employees": raw_data.get("numberOfEmployees", "N/A"),
            "followers_count": raw_data.get("FollowersCount", "N/A")
        }
        
        return cleaned_data
    
    except Exception as e:
        raise Exception(f"Error fetching LinkedIn company details: {str(e)}")


def get_linkedin_company_posts(company_url, limit=10):
    """
    Extract recent posts from LinkedIn company profile.
    
    Args:
        company_url (str): LinkedIn company profile URL
        limit (int): Maximum number of posts to retrieve (default: 10)
        
    Returns:
        list: List of cleaned company posts with selected fields
    """
    try:
        # Initialize the ApifyClient with API token
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        print(f"Fetching LinkedIn posts for: {company_url}")
        
        # Prepare the Actor input
        run_input = {
            "company_name": company_url,
            "page_number": 1,
            "limit": limit,
            "sort": "recent"
        }
        
        # Run the Actor and wait for it to finish
        run = client.actor("mrThmKLmkxJPehxCg").call(run_input=run_input)
        
        # Fetch Actor results from the run's dataset
        raw_posts = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            raw_posts.append(item)
        
        print(f"Retrieved {len(raw_posts)} post(s)")
        
        # Clean and extract only the fields we need from each post
        cleaned_posts = []
        for post in raw_posts:
            cleaned_post = {
                "text": post.get("text", "N/A"),
                "posted_date": post.get("posted_at", {}).get("relative", "N/A") + " ago",
                "total_reactions": post.get("stats", {}).get("total_reactions", 0)
            }
            cleaned_posts.append(cleaned_post)
        
        return cleaned_posts
    
    except Exception as e:
        raise Exception(f"Error fetching LinkedIn company posts: {str(e)}")


def get_website_traffic(domain):
    """
    Extract website traffic data from SimilarWeb.
    
    Args:
        domain (str): Website domain (e.g., "example.com")
        
    Returns:
        dict: Cleaned website traffic data with selected fields
    """
    try:
        # Initialize the ApifyClient with API token
        client = ApifyClient(os.getenv("APIFY_API_TOKEN"))
        
        print(f"Fetching website traffic data for: {domain}")
        
        # Prepare the Actor input
        run_input = {
            "domains": [domain]
        }
        
        # Run the Actor and wait for it to finish
        run = client.actor("yOYYzj2J5K88boIVO").call(run_input=run_input)
        
        # Fetch Actor results from the run's dataset
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)
        
        print(f"Retrieved {len(results)} result(s)")
        
        # Get the first result (should only be one for a single domain)
        raw_data = results[0] if results else {}
        
        # Extract estimated monthly visits (all available months)
        estimated_monthly_visits = raw_data.get("estimatedMonthlyVisits", {})
        
        # Extract traffic sources and find the top 2
        traffic_sources_raw = raw_data.get("trafficSources", {})
        # Sort traffic sources by value (descending) and get top 2
        sorted_sources = sorted(traffic_sources_raw.items(), key=lambda x: x[1], reverse=True)
        top_traffic_sources = dict(sorted_sources[:2]) if sorted_sources else {}
        
        # Extract country rank data
        country_rank = raw_data.get("countryRank", {})
        
        # Extract and return only the fields we need
        cleaned_data = {
            "estimated_monthly_visits": estimated_monthly_visits,
            "visits": raw_data.get("visits", "N/A"),
            "time_on_site": raw_data.get("timeOnSite", "N/A"),
            "top_traffic_sources": top_traffic_sources,
            "country_code": country_rank.get("CountryCode", "N/A"),
            "country_rank": country_rank.get("Rank", "N/A")
        }
        
        return cleaned_data
    
    except Exception as e:
        raise Exception(f"Error fetching website traffic data: {str(e)}")


def main():
    """Test function for website traffic scraper - saves results to testing/ folder."""
    
    print("\n=== Website Traffic Scraper Test ===\n")
    
    # Test with a sample domain
    test_domain = input("Enter website domain (e.g., sipbn.com.au): ").strip()
    
    if not test_domain:
        print("No domain provided. Using default test domain.")
        test_domain = "sipbn.com.au"
    
    # Fetch website traffic data
    traffic_data = get_website_traffic(test_domain)
    
    # Print summary of cleaned data
    print("\n=== Cleaned Traffic Data ===")
    print(f"Domain: {test_domain}")
    print(f"Current Visits: {traffic_data.get('visits', 'N/A')}")
    print(f"Time on Site: {traffic_data.get('time_on_site', 'N/A')} seconds")
    print(f"Country: {traffic_data.get('country_code', 'N/A')} (Rank: {traffic_data.get('country_rank', 'N/A')})")
    
    print(f"\nTop Traffic Sources:")
    for source, value in traffic_data.get('top_traffic_sources', {}).items():
        print(f"  {source}: {value:.2%}")
    
    print(f"\nEstimated Monthly Visits:")
    for month, visits in traffic_data.get('estimated_monthly_visits', {}).items():
        print(f"  {month}: {visits}")
    
    # Save to testing folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean domain name for filename
    safe_domain = test_domain.replace(".", "_").replace("/", "-")
    filename = f"testing/website_traffic_{safe_domain}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(traffic_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {filename}")


if __name__ == "__main__":
    main()
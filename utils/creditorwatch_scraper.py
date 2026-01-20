"""
CreditorWatch Scraper - Automated login and company data retrieval.
Uses Playwright to log into CreditorWatch and fetch company financial data.

Extraction approach:
1. Screenshot of the Summary tab (kept in memory, not saved to disk)
2. Text extraction from all dashboard sections
3. Processes with GPT-4o-mini for cleaned, comprehensive text extraction

Note: Due to Playwright/asyncio conflicts with Streamlit on Windows, use
run_creditorwatch_in_subprocess() when calling from Streamlit apps.

Deployment note: Playwright requires Chromium. For Streamlit Cloud, add a
packages.txt file with: chromium, chromium-driver, and run `playwright install chromium`
"""

import os
import json
import time
import base64
import tempfile
import multiprocessing
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from openai import OpenAI

load_dotenv()


def _creditorwatch_worker(abn: str, result_file: str):
    """
    Worker function that runs in a subprocess to avoid asyncio conflicts.
    Writes the result (or error) to a temp file.
    """
    try:
        # Re-load env vars in subprocess
        load_dotenv()
        data = get_creditorwatch_data(abn)
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({"success": True, "data": data}, f, ensure_ascii=False)
    except Exception as e:
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({"success": False, "error": str(e)}, f)


def run_creditorwatch_in_subprocess(abn: str, timeout: int = 300) -> dict:
    """
    Run CreditorWatch scraper in a separate process to avoid Streamlit/Playwright asyncio conflicts.
    Uses a temp file for IPC to avoid Windows Queue issues with large data.
    
    Args:
        abn (str): Australian Business Number
        timeout (int): Maximum time to wait in seconds (default: 5 minutes)
        
    Returns:
        dict: Company data from CreditorWatch
        
    Raises:
        Exception: If scraping fails or times out
    """
    # Create temp file for result communication
    fd, result_file = tempfile.mkstemp(suffix='.json', prefix='cw_result_')
    os.close(fd)  # Close the file descriptor, we'll write to it by path
    
    try:
        process = multiprocessing.Process(target=_creditorwatch_worker, args=(abn, result_file))
        process.start()
        process.join(timeout=timeout)
        
        if process.is_alive():
            process.terminate()
            process.join()
            raise Exception(f"CreditorWatch scraper timed out after {timeout} seconds")
        
        # Read result from temp file
        if not os.path.exists(result_file) or os.path.getsize(result_file) == 0:
            raise Exception("CreditorWatch scraper process ended without returning data")
        
        with open(result_file, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        if result["success"]:
            return result["data"]
        else:
            raise Exception(result["error"])
    
    finally:
        # Clean up temp file
        if os.path.exists(result_file):
            os.unlink(result_file)


def get_creditorwatch_data(abn: str) -> dict:
    """
    Log into CreditorWatch and retrieve company data for a given ABN.
    Processes with GPT-4o-mini for cleaned text extraction.
    
    Args:
        abn (str): Australian Business Number (with or without spaces)
        
    Returns:
        dict: Company data from CreditorWatch including risk score, status, etc.
              Includes 'gpt_cleaned_text' field with cleaned comprehensive text
    """
    # Clean ABN - remove spaces
    abn_clean = abn.replace(" ", "")
    
    # Get credentials from environment
    email = os.getenv("CW_LOGIN_EMAIL")
    password = os.getenv("CW_LOGIN_PASSWORD")
    
    if not email or not password:
        raise ValueError("CW_LOGIN_EMAIL and CW_LOGIN_PASSWORD must be set in .env file")
    
    print(f"Starting CreditorWatch scraper for ABN: {abn_clean}")
    
    with sync_playwright() as p:
        # Launch browser in headless mode for production
        # Use system Chromium on Streamlit Cloud (Linux), fall back to Playwright's Chromium locally
        import shutil
        import platform
        
        chromium_path = None
        if platform.system() == "Linux":
            # Try to find system Chromium on Streamlit Cloud
            for path in ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome"]:
                if shutil.which(path.split('/')[-1]) or os.path.exists(path):
                    chromium_path = path
                    print(f"Using system Chromium at: {chromium_path}")
                    break
        
        if chromium_path:
            browser = p.chromium.launch(headless=True, executable_path=chromium_path)
        else:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Step 1: Navigate to login page
            print("Navigating to login page...")
            page.goto("https://login.creditorwatch.com.au/")
            print("Login page loaded")
            
            # Step 2: Handle cookie consent if it appears (click outside or dismiss)
            # We'll try to interact with the login form directly - cookies popup shouldn't block it
            try:
                # Wait for email input to be visible
                page.wait_for_selector('input[placeholder="Enter your email"]', timeout=10000)
            except PlaywrightTimeout:
                print("Email input not found, trying to dismiss cookie popup...")
                # Try clicking "Allow All" if cookie popup blocks
                try:
                    page.click('text="Allow All"', timeout=3000)
                    page.wait_for_selector('input[placeholder="Enter your email"]', timeout=10000)
                except:
                    pass
            
            # Step 3: Enter email and click Next
            print("Entering email...")
            page.fill('input[placeholder="Enter your email"]', email)
            time.sleep(1)  # Wait after entering email
            page.click('button:has-text("Next")')
            
            # Step 4: Wait for password field and enter password
            print("Entering password...")
            page.wait_for_selector('input[placeholder="Password"]', timeout=10000)
            page.fill('input[placeholder="Password"]', password)
            time.sleep(1)  # Wait after entering password
            # Step 5: Click Sign In
            print("Signing in...")
            page.click('button:has-text("Sign In")')
            
            # Step 6: Wait for dashboard to load (indicates successful login)
            print("Waiting for login to complete...")
            page.wait_for_url("**/reporting/**", timeout=30000)
            print("Login successful!")
            
            # Step 7: Navigate to company profile
            profile_url = f"https://app.creditorwatch.com.au/reporting/organisation/profile/{abn_clean}"
            print(f"Navigating to company profile: {profile_url}")
            page.goto(profile_url)
            
            # Step 8: Wait for profile data to load
            page.wait_for_selector('h1, h2', timeout=15000)
            print("Waiting for page content to fully load...")
            time.sleep(7)  # Extended wait for dynamic content and charts to render
            
            # Step 9: Extract data from the page (screenshot kept in memory)
            print("Extracting company data...")
            data = extract_all_sections(page, abn_clean)
            
            print("Data extraction complete!")
            
            # Step 10: Process with GPT-4o-mini for cleaned text
            if data.get("screenshot_bytes") and data.get("full_text"):
                gpt_cleaned_text = process_with_gpt(
                    screenshot_bytes=data["screenshot_bytes"],
                    full_text=data["full_text"],
                    company_name=data.get("company_name", "Unknown"),
                    abn=abn_clean
                )
                
                data["gpt_cleaned_text"] = gpt_cleaned_text
                # Remove screenshot bytes from final data (not needed in output)
                del data["screenshot_bytes"]
            
            return data
            
        except Exception as e:
            print(f"Error during scraping: {str(e)}")
            raise
            
        finally:
            browser.close()


def extract_all_sections(page, abn_clean: str) -> dict:
    """
    Extract screenshot and text from all CreditorWatch dashboard sections.
    Screenshot is kept in memory (not saved to disk).
    
    Captures:
    1. Full-page screenshot of Summary tab (kept in memory as bytes)
    2. Text from all tabs: Summary, RiskScore, Payment Rating, Enquiries, Risk Data, ASIC Data, Timeline
    
    Args:
        page: Playwright page object
        abn_clean: ABN without spaces (e.g., "14603455509")
        
    Returns:
        dict: Contains screenshot bytes and text from all sections
    """
    # Initialize data structure
    data = {
        "abn": abn_clean,
        "company_name": None,
        "page_url": page.url,
        "screenshot_bytes": None,  # Screenshot kept in memory
        "extraction_timestamp": datetime.now().isoformat(),
        "full_text": None  # Single text extraction of entire page
    }
    
    # Get company name from page title
    try:
        title = page.title()
        if "|" in title:
            data["company_name"] = title.split("|")[0].strip()
    except:
        pass
    
    # 1. SCREENSHOT: Take full-page screenshot
    print("  → Capturing screenshot of Summary tab...")
    try:
        # Wait for content to be visible (not just present)
        try:
            page.wait_for_selector('text="Summary Information"', timeout=5000)
        except:
            pass  # Continue even if this specific text isn't found
        
        # Extra wait for charts/dynamic content to render
        page.wait_for_timeout(2000)
        
        # Get screenshot as bytes (no file path = returns bytes)
        data["screenshot_bytes"] = page.screenshot(full_page=True)
        print(f"    ✅ Screenshot captured ({len(data['screenshot_bytes']):,} bytes)")
    except Exception as e:
        print(f"    ⚠️ Screenshot failed: {str(e)}")
    
    # 2. TEXT EXTRACTION: Expand all sections and extract all text at once
    print("  → Expanding all 'Detailed View' sections...")
    
    # Expand all collapsible sections on the entire page
    expanded_count = expand_all_detailed_views(page)
    
    if expanded_count > 0:
        print(f"    ✅ Expanded {expanded_count} sections")
        # Wait for all expansions to complete
        page.wait_for_timeout(2000)
    else:
        print("    ⚠️ No 'Detailed View' sections found to expand")
    
    # Extract all text from the page in one go
    print("  → Extracting all page text...")
    try:
        full_text = page.inner_text('body')
        data["full_text"] = full_text.strip()
        
        # Show extraction summary
        char_count = len(full_text)
        word_count = len(full_text.split())
        preview = full_text[:150].replace('\n', ' ') if full_text else "[empty]"
        print(f"    ✅ Extracted {char_count:,} characters ({word_count:,} words)")
        print(f"    Preview: {preview}...")
        
    except Exception as e:
        print(f"    ⚠️ Text extraction failed: {str(e)}")
        data["full_text"] = f"[Extraction failed: {str(e)}]"
    
    return data


def expand_all_detailed_views(page) -> int:
    """
    Click all 'Detailed View' buttons on the current page to expand hidden content.
    
    Returns:
        int: Number of sections successfully expanded
    """
    expanded_count = 0
    
    try:
        # Find all "Detailed View" links/buttons
        detailed_buttons = page.query_selector_all('a:has-text("Detailed View")')
        
        if not detailed_buttons:
            # Try alternative selector
            detailed_buttons = page.query_selector_all('text="Detailed View"')
        
        if detailed_buttons:
            print(f"    → Found {len(detailed_buttons)} 'Detailed View' buttons to expand")
            
            for i, button in enumerate(detailed_buttons):
                try:
                    button.click()
                    page.wait_for_timeout(500)  # Wait for expansion animation
                    expanded_count += 1
                except:
                    pass  # Button might not be clickable, skip
        
        return expanded_count
        
    except Exception as e:
        print(f"    ⚠️ Could not expand sections: {str(e)}")
        return expanded_count


def process_with_gpt(screenshot_bytes: bytes, full_text: str, company_name: str, abn: str) -> str:
    """
    Process screenshot and text with GPT to create clean, comprehensive text.
    
    Strategy:
    1. Send screenshot to GPT (vision) to see the visual structure
    2. Provide messy extracted text with all the expanded details
    3. Ask GPT to reconstruct clean, organized text with ALL information preserved
    
    Args:
        screenshot_bytes: Screenshot image as bytes (in memory)
        full_text: Extracted text from the full page (messy, with buttons/navigation)
        company_name: Company name for context
        abn: ABN for context
        
    Returns:
        str: Clean, comprehensive text blob with all dashboard information
    """
    print("\n  → Processing with GPT...")
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Encode screenshot bytes as base64
        base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Create the prompt
        prompt = f"""You are processing a CreditorWatch company profile for {company_name} (ABN: {abn}).

**YOUR TASK:**
Create a clean, comprehensive text document that contains ALL the information from this CreditorWatch dashboard. This is NOT a summary - you must include every detail, but without duplicates.

**WHAT YOU'RE WORKING WITH:**
1. **Screenshot**: Shows the visual layout and structure of the dashboard (use this to understand organization)
2. **Extracted Text**: Contains all the detailed information, but it's messy - includes button labels, navigation text, duplicate sections, and poor formatting

**YOUR GOAL:**
Transform the messy extracted text into a well-organized, readable document that preserves EVERY piece of information. Think of this as cleaning up and reorganizing the dashboard content into a narrative format.

**INSTRUCTIONS:**
1. Use the screenshot to understand the proper organization and structure
2. Extract ALL information from both the screenshot and text
3. Remove clutter (button labels like "Detailed View", "Collapse View", navigation elements, etc.)
4. De-duplicate repeated information
5. Organize information logically with clear section headers
6. Present data in a readable format (not JSON - use natural paragraphs and lists)
7. Include EVERYTHING: risk scores, company details, financial data, directors, shareholders, timeline events, etc.

**SECTION ORGANIZATION:**
Organize your output with a similar structure to the CreditorWatch dashboard, which has the following sections:
- Summary
- RiskScore
- Payment Rating
- Enquiries
- Risk Data
- ASIC Data
- Timeline

**OUTPUT FORMAT:**
- Plain text with clear section headers (use "=== Section Name ===" format)
- Write in complete sentences and paragraphs
- Use natural language, not telegraphic style
- Include all numbers, dates, names, addresses exactly as they appear
- Do NOT omit any details - this will be used by another AI to generate reports

**THINGS TO FLAG:**
- A deregistration notice is a big deal and the user should know.
- Anything from risk data shown in red should be flagged.
- Status changes are also worth noting.
- Defaults
- Credit inquiries

**IMPORTANT:** Output ONLY the cleaned text. Do not include any meta-commentary, markdown formatting, or code blocks.

---

**MESSY EXTRACTED TEXT TO CLEAN:**
{full_text[:50000]}
"""

        # Call GPT with vision
        print("    → Sending request to GPT (gpt-4o-mini)...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            #model="gpt-5-nano",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}",
                                "detail": "high"  # High detail for better text extraction
                            }
                        }
                    ]
                }
            ],
            #max_completion_tokens=6000,  # Increased for comprehensive text output
            max_tokens=6000,  # Increased for comprehensive text output
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # Extract the response
        cleaned_text = response.choices[0].message.content.strip()
        
        print(f"    ✅ GPT processing complete! Generated {len(cleaned_text):,} characters")
        return cleaned_text
        
    except Exception as e:
        print(f"    ⚠️ GPT processing failed: {str(e)}")
        return f"[GPT processing error: {str(e)}]"


def main():
    """Test function for the CreditorWatch scraper."""
    print("\n=== CreditorWatch Scraper Test ===\n")
    
    # Test ABN
    test_abn = input("Enter ABN to lookup (or press Enter for default): ").strip()
    if not test_abn:
        test_abn = "14 603 455 509"  # H5 Enterprises
    
    try:
        data = get_creditorwatch_data(test_abn)
        
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE")
        print("="*60)
        
        # Display summary
        print(f"\nCompany: {data.get('company_name', 'Unknown')}")
        print(f"ABN: {data.get('abn', 'Unknown')}")
        print(f"Timestamp: {data.get('extraction_timestamp', 'Unknown')}")
        
        # Show text extraction summary
        full_text = data.get("full_text", "")
        if full_text and not full_text.startswith("["):
            char_count = len(full_text)
            word_count = len(full_text.split())
            print(f"\nFull page text extracted:")
            print(f"  ✅ {char_count:,} characters")
            print(f"  ✅ {word_count:,} words")
        else:
            print(f"\n  ⚠️ Text extraction: {full_text[:100] if full_text else 'None'}")
        
        # Show GPT processing result
        if data.get("gpt_cleaned_text"):
            cleaned_length = len(data["gpt_cleaned_text"])
            if not data["gpt_cleaned_text"].startswith("[GPT processing error"):
                print(f"\n✅ GPT cleaned text generated ({cleaned_length:,} characters)")
                # Show preview
                preview = data["gpt_cleaned_text"][:300].replace('\n', ' ')
                print(f"   Preview: {preview}...")
            else:
                print(f"\n⚠️ GPT processing had errors")
        
        print("\n✅ Test complete! (No files saved - data kept in memory)")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


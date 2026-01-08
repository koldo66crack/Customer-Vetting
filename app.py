"""
Customer Vetting Software - Main Streamlit Application
Analyzes client information to assess trustworthiness before service commitment.
"""

import streamlit as st
from dotenv import load_dotenv
from pipeline import run_vetting_pipeline, format_results_for_report
from utils.report_generator import generate_vetting_report

# Load environment variables from .env file
load_dotenv()


def inject_custom_css():
    """Inject custom CSS for professional styling."""
    st.markdown("""
    <style>
    /* Import Google Font - Outfit for modern professional look */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global font override */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1a365d 0%, #2c5282 50%, #2b6cb0 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(26, 54, 93, 0.15);
    }
    
    .main-header h1 {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.5px;
    }
    
    .main-header p {
        color: #e2e8f0;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 300;
        line-height: 1.6;
    }
    
    /* Section header styling */
    .section-header {
        color: #e2e8f0;
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0.5rem 0 1.5rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #2b6cb0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Style Streamlit inputs */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 1.5px solid #cbd5e0;
        padding: 0.65rem 0.9rem;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #2b6cb0;
        box-shadow: 0 0 0 3px rgba(43, 108, 176, 0.1);
    }
    
    /* Primary button styling */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2b6cb0 0%, #1a365d 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.85rem 2rem;
        font-size: 1.05rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 14px rgba(43, 108, 176, 0.25);
    }
    
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(43, 108, 176, 0.35);
    }
    
    /* Report header styling */
    .report-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding-bottom: 1rem;
        margin: 1.5rem 0;
        border-bottom: 2px solid #2b6cb0;
    }
    
    .report-header h2 {
        color: #e2e8f0;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    /* Status messages styling */
    .stSuccess, .stWarning, .stError {
        border-radius: 8px;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem 0;
        margin-top: 3rem;
        border-top: 1px solid #3d4a5c;
    }
    
    .footer p {
        color: #718096;
        font-size: 0.85rem;
        margin: 0;
    }
    
    /* Data source status styling */
    .source-status {
        padding: 0.5rem 0;
        font-size: 0.9rem;
    }
    
    /* Hide Streamlit default elements for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #2d3748;
    }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """Render the main header section."""
    st.markdown("""
    <div class="main-header">
        <h1>📋 Customer Vetting Software</h1>
        <p>Generate comprehensive trustworthiness assessments for prospective clients.<br>
        This tool gathers data from multiple sources and uses AI to help you make informed decisions.</p>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """Render the footer section."""
    st.markdown("""
    <div class="footer">
        <p>Customer Vetting Software • Powered by AI Analysis</p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="Customer Vetting Software",
        page_icon="📋",
        layout="wide"
    )
    
    # Inject custom CSS
    inject_custom_css()
    
    # Render header
    render_header()
    
    # Input section
    st.markdown('<div class="section-header">🏢 Company Information</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        company_name = st.text_input(
            "Company Name *",
            placeholder="Enter the company name...",
            help="Used for ABN lookup and web search"
        )
        
        linkedin_url = st.text_input(
            "LinkedIn Company URL *",
            placeholder="https://www.linkedin.com/company/...",
            help="Full URL to the company's LinkedIn page"
        )
    
    with col2:
        website_domain = st.text_input(
            "Website Domain *",
            placeholder="example.com.au",
            help="Domain only (used for traffic analysis)"
        )
        
        abn = st.text_input(
            "ABN (Optional)",
            placeholder="12 345 678 901",
            help="If known, provides more accurate ABN lookup"
        )
    
    # Generate report button
    if st.button("🔍 Generate Vetting Report", type="primary", use_container_width=True):
        # Validate required fields
        missing_fields = []
        if not company_name or not company_name.strip():
            missing_fields.append("Company Name")
        if not linkedin_url or not linkedin_url.strip():
            missing_fields.append("LinkedIn Company URL")
        if not website_domain or not website_domain.strip():
            missing_fields.append("Website Domain")
        
        if missing_fields:
            st.error(f"⚠️ Please fill in the required fields: {', '.join(missing_fields)}")
            return
        
        try:
            # Step 1: Run the data gathering pipeline
            with st.spinner("🔄 Gathering data from all sources..."):
                pipeline_results = run_vetting_pipeline(
                    company_name=company_name.strip(),
                    linkedin_url=linkedin_url.strip(),
                    website_domain=website_domain.strip(),
                    abn=abn.strip() if abn else None
                )
            
            # Show data gathering summary
            success_count = sum(1 for ds in pipeline_results["data_sources"].values() if ds["status"] == "success")
            if success_count == 5:
                st.success("✅ All data sources retrieved successfully!")
            else:
                st.warning(f"⚠️ Data gathered from {success_count}/5 sources. Some sources may have failed.")
            
            # Show detailed status in expander
            with st.expander("📊 View Data Source Status", expanded=(success_count < 5)):
                source_labels = {
                    "linkedin_details": "LinkedIn Company Details",
                    "linkedin_posts": "LinkedIn Recent Posts",
                    "website_traffic": "Website Traffic (SimilarWeb)",
                    "abn_lookup": "ABN Lookup",
                    "web_search": "Web Search Results"
                }
                for key, ds in pipeline_results["data_sources"].items():
                    label = source_labels.get(key, key)
                    if ds["status"] == "success":
                        st.markdown(f"✅ **{label}**: Retrieved successfully")
                    else:
                        st.markdown(f"❌ **{label}**: {ds['error']}")
            
            # Step 2: Format results for the report
            formatted_data = format_results_for_report(pipeline_results)
            
            # Step 3: Generate the vetting report
            with st.spinner("🤖 Analyzing data and generating report..."):
                report = generate_vetting_report(
                    gathered_data=formatted_data
                )
            
            st.success("✅ Report generated successfully!")
            
            # Display the report
            st.markdown("""
            <div class="report-header">
                <h2>📊 Vetting Report</h2>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(report)
            
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            print(f"Error: {str(e)}")
    
    # Footer
    render_footer()


if __name__ == "__main__":
    main()

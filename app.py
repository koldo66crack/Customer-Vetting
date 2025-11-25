"""
Customer Vetting Software - Main Streamlit Application
Analyzes client documents to assess trustworthiness before service commitment.
"""

import streamlit as st
import json
from dotenv import load_dotenv
from utils.pdf_extractor import extract_text_from_pdf
from utils.report_generator import generate_vetting_report
from utils.web_searcher import search_company

# Load environment variables from .env file
load_dotenv()


def main():
    """Main application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="Customer Vetting Software",
        page_icon="📋",
        layout="wide"
    )
    
    # Title and description
    st.title("📋 Customer Vetting Software")
    st.markdown("""
    Generate a comprehensive trustworthiness assessment for prospective clients.
    This tool combines document analysis with web research to help you make informed decisions.
    """)
    
    st.divider()
    
    # Company name and document upload in columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🏢 Company Information")
        company_name = st.text_input(
            "Company Name",
            placeholder="Enter the company name...",
            help="This will be used for web research",
            label_visibility="collapsed"
        )
    
    with col2:
        st.subheader("📄 Upload Client Documents")
        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload any relevant PDF documents (ABN, ASIC, LinkedIn, SimilarWeb, etc.)",
            label_visibility="collapsed"
        )
    
    st.divider()
    
    # Generate report button
    if st.button("🔍 Generate Vetting Report", type="primary", use_container_width=True):
        # Validate company name is entered
        if not company_name or not company_name.strip():
            st.error("⚠️ Please enter a company name before generating the report.")
            return
        
        # Validate that at least one file is uploaded
        if not uploaded_files:
            st.error("⚠️ Please upload at least one PDF document before generating the report.")
            return
        
        try:
            # Step 1: Extract text from all PDFs
            with st.spinner(f"📖 Extracting text from {len(uploaded_files)} PDF(s)..."):
                all_documents_text = ""
                
                for idx, uploaded_file in enumerate(uploaded_files, 1):
                    print(f"Extracting text from PDF {idx}/{len(uploaded_files)}: {uploaded_file.name}")
                    
                    file_text = extract_text_from_pdf(uploaded_file)
                    
                    # Add document separator with filename
                    all_documents_text += f"\n\n{'='*80}\n"
                    all_documents_text += f"DOCUMENT {idx}: {uploaded_file.name}\n"
                    all_documents_text += f"{'='*80}\n\n"
                    all_documents_text += file_text
            
            st.success("✅ Text extraction completed!")
            
            # Step 2: Perform web search
            with st.spinner(f"🌐 Searching the web for '{company_name}'..."):
                web_results = search_company(company_name)
                # Convert to JSON string for the prompt
                web_research_json = json.dumps(web_results, indent=2, ensure_ascii=False)
            
            st.success("✅ Web research completed!")
            
            # Step 3: Generate the vetting report
            with st.spinner("🤖 Analyzing all data and generating report... This may take a moment."):
                report = generate_vetting_report(
                    documents_text=all_documents_text,
                    web_research=web_research_json
                )
            
            st.success("✅ Report generated successfully!")
            
            # Display the report
            st.divider()
            st.header("📊 Vetting Report")
            st.markdown(report)
            
        except Exception as e:
            st.error(f"❌ An error occurred: {str(e)}")
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    main()


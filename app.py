import streamlit as st
import pandas as pd
import json
import csv
import io
import re
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from typing import List, Dict

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Alltroo Rally Extractor",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM STYLING
# ============================================================================

st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stMetric {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
        }
        .rally-card {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .success-box {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        .info-box {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# RALLY EXTRACTOR CLASS
# ============================================================================

class AlltrooRallyExtractor:
    """Extract rally data from Alltroo rallies page"""
    
    def __init__(self):
        self.rallies: List[Dict[str, str]] = []
        self.error_message = None
    
    def extract_from_html(self, html_content: str) -> bool:
        """Parse HTML and extract rallies from the new structure"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            self.rallies = []
            
            # Find all rally item wrappers (updated to reflect new structure)
            item_wrappers = soup.find_all('div', class_='card cardRally')
            
            if not item_wrappers:
                self.error_message = "No rallies found in HTML. Check if page structure has changed."
                return False
            
            for wrapper in item_wrappers:
                try:
                    # Extract link (updated to use a tag with 'link--noStyle')
                    link_elem = wrapper.find('a', href=True)
                    link = link_elem.get('href', '') if link_elem else ''
                    
                    # Extract image URL (updated to grab image inside card__thumbnail)
                    img_elem = wrapper.find('img', src=True)
                    image_url = img_elem.get('src', '') if img_elem else ''
                    image_url = re.sub(r'-\d+x\d+', '', image_url)  # Remove sizing
                    
                    # Extract rally name (updated to find h3 tag)
                    name_elem = wrapper.find('h3', class_='heading heading--xsmall')
                    name = name_elem.get_text(strip=True) if name_elem else ''
                    
                    # Extract description (updated to find span with class 'body body--xsmall')
                    description_elem = wrapper.find('span', class_='body body--xsmall')
                    description = description_elem.get_text(strip=True) if description_elem else ''
                    
                    # Validate and add
                    if name and description and link:
                        rally = {
                            'Rally Name': name,
                            'Description': description,
                            'Link': link,
                            'Image URL': image_url
                        }
                        self.rallies.append(rally)
                
                except Exception as e:
                    continue
            
            if not self.rallies:
                self.error_message = "Failed to extract rally data. Check HTML structure."
                return False
            
            return True
        
        except Exception as e:
            self.error_message = f"Error parsing HTML: {str(e)}"
            return False
    
    def from_url(self, url: str = "https://alltroo.com/rallies/") -> bool:
        """Fetch and parse from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            return self.extract_from_html(response.text)
        
        except requests.exceptions.Timeout:
            self.error_message = "Request timeout. Please try again."
            return False
        except requests.exceptions.ConnectionError:
            self.error_message = "Connection error. Check your internet connection."
            return False
        except Exception as e:
            self.error_message = f"Error fetching page: {str(e)}"
            return False
    
    def get_dataframe(self) -> pd.DataFrame:
        """Convert rallies to pandas DataFrame"""
        return pd.DataFrame(self.rallies)
    
    def export_csv(self) -> io.StringIO:
        """Export to CSV format"""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['Rally Name', 'Description', 'Link', 'Image URL']
        )
        writer.writeheader()
        writer.writerows(self.rallies)
        
        output.seek(0)
        return output.getvalue()
    
    def export_tsv(self) -> io.StringIO:
        """Export to TSV format"""
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=['Rally Name', 'Description', 'Link', 'Image URL'],
            delimiter='\t'
        )
        writer.writeheader()
        writer.writerows(self.rallies)
        
        output.seek(0)
        return output.getvalue()

# ============================================================================
# PAGE LAYOUT
# ============================================================================

# Header
st.markdown("# 🎉 Alltroo Rally Extractor")
st.markdown("Extract current rallies from Alltroo and download as CSV")

# Sidebar
st.sidebar.markdown("## ⚙️ Settings")

extract_method = st.sidebar.radio(
    "Choose extraction method:",
    ["Auto Fetch from Website", "Paste HTML"]
)

# ============================================================================
# MAIN CONTENT
# ============================================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Rallies to Extract", value="Latest", delta="Real-time")

with col2:
    st.metric(label="Data Fields", value="4", delta="Name, Description, Link, Image")

with col3:
    st.metric(label="Export Formats", value="3", delta="CSV, TSV, JSON")

st.divider()

# ============================================================================
# EXTRACTION SECTION
# ============================================================================

st.markdown("## 📥 Extract Rally Data")

extractor = AlltrooRallyExtractor()
success = False

if extract_method == "Auto Fetch from Website":
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url_input = st.text_input(
            label="Alltroo URL:",
            value="https://alltroo.com/rallies/",
            help="Enter the Alltroo rallies page URL"
        )
    
    with col2:
        extract_button = st.button(
            "🔄 Extract",
            use_container_width=True,
            type="primary"
        )
    
    if extract_button:
        with st.spinner("Fetching and extracting rally data..."):
            success = extractor.from_url(url_input)
        
        if success:
            st.success(f"✅ Successfully extracted {len(extractor.rallies)} rallies!")
        else:
            st.error(f"❌ {extractor.error_message}")

else:  # Paste HTML
    st.info("📋 Paste the HTML content of the rallies page below")
    
    html_input = st.text_area(
        label="HTML Content:",
        height=200,
        placeholder="Paste HTML content here...",
        help="Right-click on webpage → View Page Source → Copy and paste"
    )
    
    if st.button("🔍 Extract from HTML", type="primary", use_container_width=True):
        if html_input.strip():
            with st.spinner("Extracting rally data..."):
                success = extractor.extract_from_html(html_input)
            
            if success:
                st.success(f"✅ Successfully extracted {len(extractor.rallies)} rallies!")
            else:
                st.error(f"❌ {extractor.error_message}")
        else:
            st.error("❌ Please paste HTML content first")

# ============================================================================
# RESULTS SECTION
# ============================================================================

if success and extractor.rallies:
    st.divider()
    st.markdown("## 📊 Extracted Rallies")
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(label="Total Rallies", value=len(extractor.rallies))
    
    with col2:
        st.metric(label="Extraction Time", value=datetime.now().strftime("%H:%M:%S"))
    
    with col3:
        st.metric(label="Data Fields", value="4")
    
    with col4:
        st.metric(label="Status", value="Ready")
    
    st.divider()
    
    # Display data in table
    st.markdown("### 📋 Rally Details")
    df = extractor.get_dataframe()
    st.dataframe(
        df,
        use_container_width=True,
        height=400,
        hide_index=True
    )
    
    st.divider()
    
    # Display individual rally cards
    st.markdown("### 🎪 Rally Cards")
    
    # Create tabs for each rally
    tabs = st.tabs([f"Rally {i+1}" for i in range(len(extractor.rallies))])
    
    for idx, (tab, rally) in enumerate(zip(tabs, extractor.rallies)):
        with tab:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"#### {rally['Rally Name']}")
                st.markdown(f"**Description:** {rally['Description']}")
                st.markdown(f"**Link:** [{rally['Link']}]({rally['Link']})")
                st.markdown(f"**Image URL:** {rally['Image URL']}")
            
            with col2:
                # Try to display image
                try:
                    st.image(rally['Image URL'], use_column_width=True)
                except:
                    st.info("Image preview unavailable")
    
    st.divider()
    
    # ================================================================
    # DOWNLOAD SECTION
    # ================================================================
    
    st.markdown("## 💾 Download Data")
    
    col1, col2, col3 = st.columns(3)
    
    # CSV Download
    with col1:
        csv_data = extractor.export_csv()
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name=f"alltroo_rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    # TSV Download
    with col2:
        tsv_data = extractor.export_tsv()
        st.download_button(
            label="📥 Download TSV",
            data=tsv_data,
            file_name=f"alltroo_rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv",
            mime="text/tab-separated-values",
            use_container_width=True
        )
    
    # Excel Download
    with col3:
        # Create Excel file
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, sheet_name='Rallies', index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        st.download_button(
            label="📥 Download Excel",
            data=excel_buffer,
            file_name=f"alltroo_rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    st.divider()

   # Assuming `extractor.rallies` is the data you want to display as JSON
    json_data = json.dumps(extractor.rallies, indent=2)

   # Display the collection content as JSON in a text area
    st.subheader("Collection Content as JSON:")
    st.text_area("JSON Content", json_data, height=300)
    
    # Export options
    st.markdown("### 🔄 Additional Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Copy to clipboard button
        if st.button("📋 Copy Table as Markdown", use_container_width=True):
            markdown_table = df.to_markdown(index=False)
            st.code(markdown_table, language="markdown")
            st.success("✅ Markdown table copied!")
    
    with col2:
        # JSON export
        import json
        json_data = json.dumps(extractor.rallies, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_data,
            file_name=f"alltroo_rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    st.divider()
    
    # Data summary
    st.markdown("### 📈 Data Summary")
    
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.markdown("**Extract Information:**")
        st.markdown(f"- Total Rallies: `{len(extractor.rallies)}`")
        st.markdown(f"- Extracted at: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
        st.markdown(f"- Data Fields: `4` (Name, Description, Link, Image)")
        st.markdown(f"- Unique Rally Names: `{len(set(r['Rally Name'] for r in extractor.rallies))}`")
    
    with summary_col2:
        st.markdown("**Available Downloads:**")
        st.markdown("- ✅ CSV (Excel compatible)")
        st.markdown("- ✅ TSV (Tab-separated)")
        st.markdown("- ✅ Excel (XLSX)")
        st.markdown("- ✅ JSON (API ready)")
        st.markdown("- ✅ Markdown (Documentation)")

# ============================================================================
# HELP SECTION
# ============================================================================

st.divider()

st.markdown("## ❓ How to Use")

with st.expander("👉 Click to expand instructions"):
    st.markdown("""
    ### Option 1: Auto Fetch (Recommended)
    1. Keep the default URL: `https://alltroo.com/rallies/`
    2. Click the **Extract** button
    3. Wait for data to load
    4. Download in your preferred format
    
    ### Option 2: Paste HTML
    1. Visit https://alltroo.com/rallies/
    2. Right-click → **View Page Source**
    3. Copy all HTML (Ctrl+A, Ctrl+C)
    4. Paste into the text area
    5. Click **Extract from HTML**
    6. Download in your preferred format
    
    ### Data Fields
    Each rally includes:
    - **Rally Name**: The title of the rally
    - **Description**: What you can win
    - **Link**: Direct URL to the rally page
    - **Image URL**: Full-resolution promotional image
    
    ### Export Formats
    - **CSV**: Import to Excel, Google Sheets
    - **TSV**: Tab-separated for data analysis
    - **Excel**: Native .xlsx format
    - **JSON**: For API integration
    - **Markdown**: For documentation
    """)

with st.expander("🛠️ Troubleshooting"):
    st.markdown("""
    ### No rallies found?
    - Check your internet connection
    - Verify the URL is correct
    - Page structure may have changed
    
    ### Image preview not showing?
    - Image URL is still extracted correctly
    - Check the URL field to access directly
    
    ### Download not working?
    - Try a different format (CSV, TSV, Excel)
    - Check browser download settings
    - Allow pop-ups if using strict settings
    
    ### Want to schedule daily extracts?
    - Run this app on a server using Streamlit Cloud
    - Use the Python script directly with cron/Task Scheduler
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.markdown("### 📖 Documentation")
    st.markdown("[View on GitHub](https://github.com/optiblackcode/alltroo-rales-collection)")  # Link to documentation

with footer_col2:
    st.markdown("### 🐛 Report Issues")
    st.markdown("[GitHub Issues](https://github.com/optiblackcode/alltroo-rales-collection/issues/new)")  # Link to report issues

with footer_col3:
    st.markdown("### 💡 Feature Requests")
    st.markdown("[Suggest Improvements](https://github.com/optiblackcode/alltroo-rales-collection/issues/new)")  # Link to feature requests

st.markdown("---")
st.markdown(f"**Last updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Version:** 1.0")
st.markdown("*Alltroo Rally Extractor - Extract and download rally data easily*")

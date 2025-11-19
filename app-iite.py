import streamlit as st
import pandas as pd
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
        .main { padding: 2rem; }
        h1 { color: #FF6B35; }
        .stButton > button { background-color: #FF6B35; }
        .success-message { 
            background-color: #d4edda; 
            padding: 1rem; 
            border-radius: 0.5rem;
            border-left: 4px solid #28a745;
        }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# TITLE & DESCRIPTION
# ============================================================================

st.markdown("# 🎉 Alltroo Rally Extractor")
st.markdown("*Extract current rallies and download as CSV, Excel, or JSON*")
st.markdown("---")

# ============================================================================
# EXTRACTOR CLASS
# ============================================================================

class AlltrooExtractor:
    """Extract rally data from Alltroo"""
    
    def __init__(self):
        self.rallies = []
        self.error = None
    
    def extract_from_html(self, html: str) -> bool:
        """Parse HTML and extract rallies"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            self.rallies = []
            
            # Find all rally wrappers
            wrappers = soup.find_all('div', class_='rf-archiveList__itemWrapper')
            
            if not wrappers:
                self.error = "No rallies found. Check if page structure changed."
                return False
            
            for wrapper in wrappers:
                try:
                    # Extract 4 fields
                    name = wrapper.find('h3').text.strip()
                    desc = wrapper.find('p').text.strip()
                    desc = ' '.join(desc.split())  # Clean whitespace
                    link = wrapper.find('a')['href']
                    img = wrapper.find('img')['src']
                    img = re.sub(r'-\d+x\d+', '', img)  # Full resolution
                    
                    if name and desc and link:
                        self.rallies.append({
                            'Rally Name': name,
                            'Description': desc,
                            'Link': link,
                            'Image URL': img
                        })
                except:
                    continue
            
            return len(self.rallies) > 0
        
        except Exception as e:
            self.error = f"Error: {str(e)}"
            return False
    
    def from_url(self, url: str) -> bool:
        """Fetch from URL"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=15)
            return self.extract_from_html(resp.text)
        except Exception as e:
            self.error = f"Connection error: {str(e)}"
            return False
    
    def get_df(self) -> pd.DataFrame:
        return pd.DataFrame(self.rallies)
    
    def to_csv(self) -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['Rally Name', 'Description', 'Link', 'Image URL'])
        writer.writeheader()
        writer.writerows(self.rallies)
        return output.getvalue()

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.markdown("## ⚙️ Options")
method = st.sidebar.radio(
    "Choose method:",
    ["Auto Fetch (Recommended)", "Paste HTML"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Stats")
st.sidebar.markdown(f"- **Data Fields:** 4")
st.sidebar.markdown(f"- **Export Formats:** 5")
st.sidebar.markdown(f"- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ============================================================================
# MAIN CONTENT
# ============================================================================

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Fields per Rally", "4", "Name, Desc, Link, Image")
col2.metric("Export Formats", "5", "CSV, TSV, Excel, JSON, MD")
col3.metric("Status", "Ready", "Extract & Download")

st.markdown("---")

# ============================================================================
# EXTRACTION
# ============================================================================

extractor = AlltrooExtractor()
success = False

if method == "Auto Fetch (Recommended)":
    st.markdown("## 📥 Fetch from Alltroo")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input(
            "URL:",
            value="https://alltroo.com/rallies/",
            help="Alltroo rallies page URL"
        )
    
    with col2:
        if st.button("🔄 Extract", type="primary", use_container_width=True):
            with st.spinner("Fetching..."):
                success = extractor.from_url(url)
            
            if success:
                st.success(f"✅ Extracted {len(extractor.rallies)} rallies!")
            else:
                st.error(f"❌ {extractor.error}")

else:
    st.markdown("## 📋 Paste HTML Content")
    st.info("Steps: 1) Visit https://alltroo.com/rallies/ 2) Right-click → View Page Source 3) Copy-Paste HTML below")
    
    html_input = st.text_area(
        "HTML:",
        height=250,
        placeholder="Paste HTML here...",
        help="Right-click on page → View Page Source → Copy All → Paste Here"
    )
    
    if st.button("🔍 Extract", type="primary", use_container_width=True):
        if html_input.strip():
            success = extractor.extract_from_html(html_input)
            if success:
                st.success(f"✅ Extracted {len(extractor.rallies)} rallies!")
            else:
                st.error(f"❌ {extractor.error}")
        else:
            st.error("❌ Please paste HTML content")

st.markdown("---")

# ============================================================================
# RESULTS
# ============================================================================

if success and extractor.rallies:
    st.markdown("## 📊 Results")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rallies", len(extractor.rallies))
    col2.metric("Fields", "4")
    col3.metric("Extracted", datetime.now().strftime("%H:%M:%S"))
    col4.metric("Ready to Export", "✅")
    
    st.markdown("---")
    
    # Show data table
    st.markdown("### 📋 Data Table")
    df = extractor.get_df()
    st.dataframe(df, use_container_width=True, height=300)
    
    st.markdown("---")
    
    # Download section
    st.markdown("### 💾 Download Data")
    
    col1, col2, col3 = st.columns(3)
    
    # CSV
    with col1:
        csv_data = extractor.to_csv()
        st.download_button(
            "📥 CSV",
            csv_data,
            f"rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    # Excel
    with col2:
        excel_io = io.BytesIO()
        df.to_excel(excel_io, sheet_name='Rallies', index=False, engine='openpyxl')
        excel_io.seek(0)
        
        st.download_button(
            "📥 Excel",
            excel_io,
            f"rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # JSON
    with col3:
        import json
        json_data = json.dumps(extractor.rallies, indent=2)
        st.download_button(
            "📥 JSON",
            json_data,
            f"rallies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json",
            use_container_width=True
        )
    
    st.markdown("---")
    
    # Show individual rallies
    st.markdown("### 🎪 Individual Rallies")
    
    for idx, rally in enumerate(extractor.rallies, 1):
        with st.expander(f"**{idx}. {rally['Rally Name']}**"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**Description:** {rally['Description']}")
                st.markdown(f"**Link:** [{rally['Link']}]({rally['Link']})")
            
            with col2:
                try:
                    st.image(rally['Image URL'], width=200)
                except:
                    st.info("Image unavailable")

st.markdown("---")

# ============================================================================
# HELP & INFO
# ============================================================================

with st.expander("❓ How to Use"):
    st.markdown("""
    ### Auto Fetch Method
    1. URL is pre-filled with Alltroo rallies page
    2. Click **Extract** button
    3. Wait 2-5 seconds for data to load
    4. Download in CSV, Excel, or JSON format
    
    ### Paste HTML Method
    1. Visit https://alltroo.com/rallies/
    2. Right-click page → **View Page Source**
    3. Select all (Ctrl+A) → Copy (Ctrl+C)
    4. Paste into text area above
    5. Click **Extract**
    6. Download your data
    
    ### Data Fields
    - **Rally Name** - Official rally name
    - **Description** - What you can win
    - **Link** - Direct URL to rally
    - **Image URL** - Promotional image
    """)

with st.expander("📚 Download Formats"):
    st.markdown("""
    | Format | Best For | Size |
    |--------|----------|------|
    | CSV | Excel/Sheets | ~3 KB |
    | Excel | Reports | ~15 KB |
    | JSON | APIs | ~4 KB |
    
    **CSV:** Open directly in Excel  
    **Excel:** Professional formatting  
    **JSON:** Use in web apps & APIs  
    """)

with st.expander("🐛 Troubleshooting"):
    st.markdown("""
    **No data extracted?**
    - Check internet connection
    - Website structure may have changed
    - Try Paste HTML method instead
    
    **Download not working?**
    - Try different format
    - Check browser download settings
    - Allow pop-ups if needed
    
    **Connection error?**
    - Verify internet connection
    - Try again in a moment
    - Use Paste HTML method
    """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p><strong>Alltroo Rally Extractor v1.0</strong></p>
    <p>Extract and download rally data easily</p>
    <p style='font-size: 0.8rem; color: #666;'>Last updated: 2024 | Python 3.7+</p>
</div>
""", unsafe_allow_html=True)

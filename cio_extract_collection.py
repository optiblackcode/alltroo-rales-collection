import streamlit as st
import requests
import json
import pandas as pd
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Dict

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Customer.io Collection Toolkit",
    page_icon="🎉",
    layout="wide"
)

# ============================================================================
# CUSTOMER.IO CONFIG
# ============================================================================
BASE_URL = "https://api.customer.io/v1/collections"
API_KEY = st.secrets["credentials"]["app_api_key"]

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ============================================================================
# API HELPERS
# ============================================================================
def fetch_collections():
    try:
        res = requests.get(BASE_URL, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        if isinstance(data, list):
            return data

        if isinstance(data, dict) and "collections" in data:
            return data["collections"]

        st.error("Unexpected collections response format")
        return []

    except Exception as e:
        st.error(f"Failed to fetch collections: {e}")
        return []


def fetch_collection_details(collection_id):
    try:
        res = requests.get(f"{BASE_URL}/{collection_id}/content", headers=HEADERS)
        res.raise_for_status()

        raw = res.text.strip()

        # Try full JSON
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: line-by-line JSON
        rows = []
        for line in raw.splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        return rows

    except Exception as e:
        st.error(f"Failed to fetch collection content: {e}")
        return []

# ============================================================================
# ALLTROO RALLY EXTRACTOR
# ============================================================================
class AlltrooRallyExtractor:
    def __init__(self):
        self.rallies: List[Dict[str, str]] = []
        self.error = None

    def from_url(self, url: str) -> bool:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            res.raise_for_status()
            return self._parse_html(res.text)
        except Exception as e:
            self.error = str(e)
            return False

    def _parse_html(self, html: str) -> bool:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("div", class_="card cardRally")

        if not cards:
            self.error = "No rallies found"
            return False

        self.rallies = []

        for card in cards:
            link = card.find("a", href=True)
            img = card.find("img", src=True)
            title = card.find("h3")
            desc = card.find("span")

            if not (link and title and desc):
                continue

            image_url = img["src"] if img else ""
            image_url = re.sub(r"-\d+x\d+", "", image_url)

            self.rallies.append({
                "Rally Name": title.get_text(strip=True),
                "Description": desc.get_text(strip=True),
                "Link": link["href"],
                "Image URL": image_url
            })

        return True

    def dataframe(self):
        return pd.DataFrame(self.rallies)

# ============================================================================
# SIDEBAR
# ============================================================================
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Customer.io Collection Manager",
        "Live Rallies",
        "Alltroo Rally Extractor"
    ]
)

# ============================================================================
# PAGE 1: COLLECTION MANAGER
# ============================================================================
if page == "Customer.io Collection Manager":
    st.title("📦 Customer.io Collection Manager")

    collections = fetch_collections()
    if not collections:
        st.warning("No collections found")
    else:
        name_to_id = {c["name"]: c["id"] for c in collections}
        selected = st.selectbox("Select Collection", list(name_to_id.keys()))

        if st.button("Fetch Collection Content"):
            data = fetch_collection_details(name_to_id[selected])

            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                json_data = json.dumps(data, indent=2)
                st.text_area("JSON", json_data, height=300)

                st.download_button("Download CSV", df.to_csv(index=False), "collection.csv")
                st.download_button("Download JSON", json_data, "collection.json")

# ============================================================================
# PAGE 2: LIVE RALLIES
# ============================================================================
if page == "Live Rallies":
    st.title("🎪 Live Rallies")

    collections = fetch_collections()
    if not collections:
        st.warning("No collections found")
    else:
        name_to_id = {c["name"]: c["id"] for c in collections}
        selected = st.selectbox("Select Rally Collection", list(name_to_id.keys()))

        if st.button("Load Live Rallies"):
            rallies = fetch_collection_details(name_to_id[selected])

            if rallies:
                cols = st.columns(3)
                for i, rally in enumerate(rallies):
                    with cols[i % 3]:
                        st.markdown(f"### {rally.get('Rally Name', '-')}")
                        st.image(rally.get("Image URL", ""), use_column_width=True)
                        st.caption(rally.get("Description", ""))
                        st.markdown(f"[Visit Rally]({rally.get('Link', '#')})")

# ============================================================================
# PAGE 3: ALLTROO RALLY EXTRACTOR (UPLOAD FLOW)
# ============================================================================
if page == "Alltroo Rally Extractor":
    st.title("🎉 Alltroo Rally Extractor")

    extractor = AlltrooRallyExtractor()

    url = st.text_input(
        "Alltroo Rallies URL",
        value="https://alltroo.com/rallies/"
    )

    # STEP 1 — Extract
    if st.button("Extract Rallies", type="primary"):
        with st.spinner("Extracting rallies..."):
            success = extractor.from_url(url)

        if not success:
            st.error(extractor.error)
        else:
            st.success(f"Extracted {len(extractor.rallies)} rallies")
            st.session_state["rallies_ready"] = True
            st.session_state["rallies"] = extractor.rallies

    # STEP 2 — Preview + Select Collection
    if st.session_state.get("rallies_ready"):
        df = pd.DataFrame(st.session_state["rallies"])
        st.dataframe(df, use_container_width=True, hide_index=True)

        collections = fetch_collections()
        name_to_id = {c["name"]: c["id"] for c in collections}

        selected_collection = st.selectbox(
            "Select Collection to Upload",
            list(name_to_id.keys())
        )

        if st.button("Next → Upload"):
            st.session_state["selected_collection_id"] = name_to_id[selected_collection]
            st.session_state["ready_to_upload"] = True

    # STEP 3 — Upload (ONLY after Next)
    if st.session_state.get("ready_to_upload"):
        st.warning("This will REPLACE the collection content")

        if st.button("⬆️ Upload to Customer.io", type="primary"):
            payload = json.dumps(st.session_state["rallies"], indent=2)

            with st.spinner("Uploading..."):
                res = requests.put(
                    f"{BASE_URL}/{st.session_state['selected_collection_id']}/content",
                    headers=HEADERS,
                    data=payload
                )

            if res.status_code in [200, 201, 204]:
                st.success("✅ Upload successful")
                st.session_state.clear()
            else:
                st.error("❌ Upload failed")
                st.code(res.text)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

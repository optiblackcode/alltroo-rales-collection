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
# HELPERS
# ============================================================================
def parse_concatenated_json_objects(raw_text: str):
    objects = []
    for line in raw_text.splitlines():
        try:
            objects.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return objects


def fetch_collections():
    try:
        res = requests.get(BASE_URL, headers=HEADERS)
        res.raise_for_status()
        return res.json().get("collections", [])
    except Exception as e:
        st.error(f"Failed to fetch collections: {e}")
        return []


def fetch_collection_details(collection_id):
    try:
        res = requests.get(f"{BASE_URL}/{collection_id}/content", headers=HEADERS)
        res.raise_for_status()

        if res.headers.get("Content-Type", "").startswith("application/json"):
            return res.json() if isinstance(res.json(), list) else []

        return parse_concatenated_json_objects(res.text)

    except Exception as e:
        st.error(f"Failed to fetch collection content: {e}")
        return []


# ============================================================================
# ALLTROO RALLY EXTRACTOR
# ============================================================================
class AlltrooRallyExtractor:
    def __init__(self):
        self.rallies: List[Dict[str, str]] = []
        self.error_message = None

    def extract_from_html(self, html: str) -> bool:
        try:
            soup = BeautifulSoup(html, "html.parser")
            self.rallies = []

            cards = soup.find_all("div", class_="card cardRally")
            if not cards:
                self.error_message = "No rallies found"
                return False

            for card in cards:
                link = card.find("a", href=True)
                image = card.find("img", src=True)
                title = card.find("h3")
                desc = card.find("span")

                if not (link and title and desc):
                    continue

                image_url = image["src"] if image else ""
                image_url = re.sub(r"-\d+x\d+", "", image_url)

                self.rallies.append({
                    "Rally Name": title.get_text(strip=True),
                    "Description": desc.get_text(strip=True),
                    "Link": link["href"],
                    "Image URL": image_url
                })

            return True

        except Exception as e:
            self.error_message = str(e)
            return False

    def from_url(self, url: str) -> bool:
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            res.raise_for_status()
            return self.extract_from_html(res.text)
        except Exception as e:
            self.error_message = str(e)
            return False

    def dataframe(self):
        return pd.DataFrame(self.rallies)


# ============================================================================
# SIDEBAR NAVIGATION
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
        names = [c["name"] for c in collections]
        id_map = {c["name"]: c["id"] for c in collections}

        selected = st.selectbox("Select Collection", names)
        collection_id = id_map[selected]

        if st.button("Fetch Collection Content"):
            data = fetch_collection_details(collection_id)
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
    names = [c["name"] for c in collections]
    id_map = {c["name"]: c["id"] for c in collections}

    selected = st.selectbox("Select Rally Collection", names)

    if st.button("Load Live Rallies"):
        rallies = fetch_collection_details(id_map[selected])

        if rallies:
            cols = st.columns(3)
            for i, rally in enumerate(rallies):
                with cols[i % 3]:
                    st.markdown(f"### {rally.get('Rally Name', '-')}")
                    st.image(rally.get("Image URL", ""), use_column_width=True)
                    st.caption(rally.get("Description", ""))
                    st.markdown(f"[Visit]({rally.get('Link', '#')})")


# ============================================================================
# PAGE 3: ALLTROO RALLY EXTRACTOR
# ============================================================================
if page == "Alltroo Rally Extractor":
    st.title("🎉 Alltroo Rally Extractor")

    extractor = AlltrooRallyExtractor()

    url = st.text_input(
        "Alltroo Rallies URL",
        value="https://alltroo.com/rallies/"
    )

    collections = fetch_collections()
    names = [c["name"] for c in collections]
    id_map = {c["name"]: c["id"] for c in collections}

    selected_collection = st.selectbox("Upload to Collection", names)

    if st.button("Extract Rallies", type="primary"):
        with st.spinner("Extracting rallies..."):
            success = extractor.from_url(url)

        if success:
            st.success(f"Extracted {len(extractor.rallies)} rallies")
        else:
            st.error(extractor.error_message)

    if extractor.rallies:
        df = extractor.dataframe()
        st.dataframe(df, use_container_width=True, hide_index=True)

        json_payload = json.dumps(extractor.rallies, indent=2)
        st.text_area("JSON Payload", json_payload, height=300)

        st.download_button("Download CSV", df.to_csv(index=False), "rallies.csv")
        st.download_button("Download JSON", json_payload, "rallies.json")

        if st.button("⬆️ Upload to Customer.io", type="primary"):
            with st.spinner("Uploading..."):
                res = requests.put(
                    f"{BASE_URL}/{id_map[selected_collection]}/content",
                    headers=HEADERS,
                    data=json_payload
                )

            if res.status_code in [200, 201, 204]:
                st.success("✅ Upload successful")
            else:
                st.error("❌ Upload failed")
                st.code(res.text)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

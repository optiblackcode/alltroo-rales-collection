import streamlit as st
import requests
import json
import pandas as pd

# ============================================================================
# Default Base URL (US Region)
# ============================================================================
base_url = "https://api.customer.io/v1/collections"

# API Key stored in secrets.toml for security
api_key = st.secrets["credentials"]["app_api_key"]

# Headers for API request
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

# ============================================================================
# Helper function to parse concatenated JSON objects
# ============================================================================
def parse_concatenated_json_objects(raw_text: str):
    """
    Safely parses multiple JSON objects concatenated together.
    Returns a list of dicts.
    """
    objects = []
    raw_lines = raw_text.splitlines()  # Split by line breaks
    
    for line in raw_lines:
        try:
            # Attempt to load each line as a separate JSON object
            objects.append(json.loads(line))
        except json.JSONDecodeError:
            # If decoding fails, skip that line (or log an error)
            st.warning(f"Failed to decode line: {line}")
    
    return objects

# ============================================================================
# Fetch Collections List (GET /v1/collections)
# ============================================================================
def fetch_collections():
    """Fetch the list of collections"""
    try:
        response = requests.get(base_url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes
        collections_data = response.json()
        
        # Parse collections data and extract necessary details
        collections = []
        for collection in collections_data['collections']:
            collections.append({
                "id": collection['id'],
                "name": collection['name'],
                "schema": collection['schema'],
                "rows": collection['rows']
            })
        return collections
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching collections: {e}")
        return []

# ============================================================================
# Fetch Collection Details (GET /v1/collections/:id/content)
# ============================================================================
def fetch_collection_details(collection_id):
    """Fetch details of a specific collection"""
    url = f"{base_url}/{collection_id}/content"

    try:
        # Fetch response from API
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad status codes

        # Check if the response content type is JSON
        if response.headers['Content-Type'] == 'application/json':
            # Case 1: Normal JSON response
            data = response.json()

            # If the response contains data directly
            if isinstance(data, list):
                return data

            st.error("Response format is not as expected.")
            return []

        # Case 2: Broken / concatenated JSON objects (your case)
        raw_text = response.text.strip()
        parsed_objects = parse_concatenated_json_objects(raw_text)

        if parsed_objects:
            return parsed_objects

        st.error("Could not parse collection content")
        return []

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching collection details: {e}")
        return []

# ============================================================================
# STREAMLIT UI
# ============================================================================
st.title("Customer.io Collection Manager")

# Step 1: Dropdown for Collection Selection
st.markdown("### Select Collection")

collections = fetch_collections()

if collections:
    collection_names = [col['name'] for col in collections]
    collection_ids = {col['name']: col['id'] for col in collections}
    
    selected_collection = st.selectbox("Choose a collection", collection_names)
    
    if selected_collection:
        collection_id = collection_ids[selected_collection]
        
        # Display the schema and row count
        selected_collection_info = next(
            col for col in collections if col['name'] == selected_collection
        )
        st.markdown(f"**Schema**: {', '.join(selected_collection_info['schema'])}")
        st.markdown(f"**Rows**: {selected_collection_info['rows']}")
        
        # Step 2: Fetch Collection Details
        if st.button("Get Collection Details"):
            st.spinner("Fetching collection content...")
            collection_details = fetch_collection_details(collection_id)
            
            if collection_details:
                # Step 3: Display Collection Data in DataFrame
                collection_data = collection_details
                
                if collection_data:
                    # Create a pandas DataFrame
                    df = pd.DataFrame(collection_data)
                    st.dataframe(df, use_container_width=True)

                    # Step 4: Export to CSV
                    csv_data = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv_data,
                        file_name=f"collection_{collection_id}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No data found for this collection.")
            else:
                st.error("Failed to fetch collection details.")
else:
    st.warning("No collections found. Please check your API key or the Customer.io account.")

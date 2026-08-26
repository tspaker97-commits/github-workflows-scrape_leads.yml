import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

OUTPUT_DIR = "output_leads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# TARGET DATASET REGISTRY
SOCRATA_TARGETS = [
    {"market": "New York City, NY", "domain": "data.cityofnewyork.us", "dataset": "jz4z-kudi", "type": "Code Violation"},
    {"market": "Austin, TX", "domain": "data.austintexas.gov", "dataset": "6wtj-zbtb", "type": "Code Violation"},
    {"market": "Fort Worth, TX", "domain": "data.fortworthtexas.gov", "dataset": "spnu-bq4u", "type": "Code Violation"},
    {"market": "Los Angeles, CA", "domain": "data.lacity.org", "dataset": "2uz8-3tj3", "type": "Code Violation"},
    {"market": "Kansas City, MO", "domain": "data.kcmo.org", "dataset": "vq3e-m9ge", "type": "Code Violation"},
    {"market": "New Orleans, LA", "domain": "data.nola.gov", "dataset": "3ehi-je3s", "type": "Code Violation"},
    {"market": "Seattle, WA", "domain": "data.seattle.gov", "dataset": "ez4a-iug7", "type": "Code Violation"},
    {"market": "Richmond, VA", "domain": "data.richmondgov.com", "dataset": "83t5-hbac", "type": "Tax Delinquency"},
]

ARCGIS_TARGETS = [
    {
        "market": "Nashville, TN",
        "url": "https://services2.arcgis.com/dQgLLbbQuetPEv68/arcgis/rest/services/Codes_Cases_Past_90_Days/FeatureServer/0",
        "type": "Code Violation"
    },
    {
        "market": "Wake County, NC",
        "url": "https://services1.arcgis.com/vHnS4nSl02jwF0d9/arcgis/rest/services/Wake_County_Code_Cases/FeatureServer/0",
        "type": "Code Violation"
    },
    {
        "market": "Greensboro, NC",
        "url": "https://services3.arcgis.com/tdsK97645v56UjOa/arcgis/rest/services/Code_Violations/FeatureServer/0",
        "type": "Code Violation"
    },
    {
        "market": "Syracuse, NY",
        "url": "https://services6.arcgis.com/bdP50HG5opNmRlan/arcgis/rest/services/Code_Violations/FeatureServer/0",
        "type": "Code Violation"
    }
]

def fetch_socrata(domain: str, dataset: str, limit: int = 2000) -> pd.DataFrame:
    url = f"https://{domain}/resource/{dataset}.json"
    params = {"$limit": limit, "$order": ":id DESC"}
    try:
        res = requests.get(url, headers=HEADERS, params=params, timeout=25)
        if res.status_code == 200:
            return pd.json_normalize(res.json())
    except Exception as e:
        logging.warning(f"Failed Socrata query on {domain}/{dataset}: {e}")
    return pd.DataFrame()

def fetch_arcgis(url: str, limit: int = 2000) -> pd.DataFrame:
    query_url = f"{url.rstrip('/')}/query"
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "resultRecordCount": limit,
        "returnGeometry": "false"
    }
    try:
        res = requests.get(query_url, headers=HEADERS, params=params, timeout=25)
        if res.status_code == 200:
            features = res.json().get("features", [])
            return pd.DataFrame([f.get("attributes", {}) for f in features])
    except Exception as e:
        logging.warning(f"Failed ArcGIS query on {url}: {e}")
    return pd.DataFrame()

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d")
    logging.info("Starting automated municipal ingestion...")
    all_leads = []

    for target in SOCRATA_TARGETS:
        logging.info(f"Ingesting: {target['market']} ({target['type']})")
        df = fetch_socrata(target["domain"], target["dataset"])
        if not df.empty:
            df["Source_Market"] = target["market"]
            df["Distress_Type"] = target["type"]
            df["Scraped_Date"] = timestamp
            all_leads.append(df)

    for target in ARCGIS_TARGETS:
        logging.info(f"Ingesting: {target['market']} ({target['type']})")
        df = fetch_arcgis(target["url"])
        if not df.empty:
            df["Source_Market"] = target["market"]
            df["Distress_Type"] = target["type"]
            df["Scraped_Date"] = timestamp
            all_leads.append(df)

    if all_leads:
        master_df = pd.concat(all_leads, ignore_index=True)
        csv_path = os.path.join(OUTPUT_DIR, f"master_courthouse_leads_{timestamp}.csv")
        master_df.to_csv(csv_path, index=False)
        logging.info(f"Saved {len(master_df)} rows to {csv_path}")
    else:
        logging.error("No leads collected.")

if __name__ == "__main__":
    main()

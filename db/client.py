import os
import requests
from datetime import date

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def fetch_all_contracts():
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/contracts?select=*",
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def fetch_active_contracts():
    today = date.today().isoformat()

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/contracts"
        f"?start_date=lte.{today}&end_date=gt.{today}",
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()

def insert_contract(payload):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/contracts",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 Supabase INSERT:", r.status_code, r.text)

    r.raise_for_status()


import os
import requests
from datetime import datetime, date
from core.utils import build_contract_code

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def fetch_all_contracts():

    url = (
        f"{SUPABASE_URL}/rest/v1/contracts"
        f"?select=*"
        f"&order=start_date.desc"
    )

    print("📡 FETCH ALL URL:", url)

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=10,
    )

    print("📡 STATUS:", r.status_code)
    print("📡 BODY:", r.text)

    r.raise_for_status()

    return r.json()


def fetch_active_contracts():
    today = date.today().isoformat()

    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/contracts"
        f"?is_closed=eq.false"
        f"&start_date=lte.{today}"
        f"&end_date=gte.{today}",
        headers=HEADERS,
        timeout=10,
    )

    r.raise_for_status()
    return r.json()


def save_contract_to_db(data, files):

    url = os.environ["SUPABASE_URL"] + "/rest/v1/contracts"

    headers = {
        "apikey": os.environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_KEY']}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    start = datetime.strptime(data["START_DATE"], "%d.%m.%Y")
    end = datetime.strptime(data["END_DATE"], "%d.%m.%Y")

    nights = (end - start).days
    contract_code = build_contract_code(
        data["START_DATE"],
        data["FLAT_NUMBER"],
    )

    payload = {
        "contract_code": contract_code,
        "flat_number": data.get("FLAT_NUMBER"),

        "client_name": data.get("CLIENT_NAME"),
        "client_id": data.get("CLIENT_ID"),
        "client_address": data.get("CLIENT_ADDRESS"),
        "client_mail": data.get("CLIENT_MAIL"),
        "client_number": data.get("CLIENT_NUMBER"),

        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": end.strftime("%Y-%m-%d"),
        "nights": nights,

        "price_per_day": int(data["PRICE_PER_DAY"]),
        "total_price": int(data["TOTAL_PRICE"]),
        "deposit": int(data["DEPOSIT"]),

        "checkout_time": data["CHECKOUT_TIME"],
        "is_closed": False,
    }

    r = requests.post(url, json=payload, headers=headers, timeout=10)

    print("🟡 Supabase INSERT status:", r.status_code)
    print("🟡 Supabase INSERT body:", r.text)
    
    if r.status_code not in (200, 201):
        raise RuntimeError("Supabase insert failed")

def close_contract(
    contract_code: str,
    actual_checkout_date: date,
    returned_deposit: int,
    deposit_comment: str | None,
):

    contract = get_contract_by_code(contract_code)

    if not contract:
        raise ValueError("Contract not found")

    if contract["is_closed"]:
        raise ValueError("Contract already closed")
    
    url = (
        os.environ["SUPABASE_URL"]
        + f"/rest/v1/contracts?contract_code=eq.{contract_code}"
    )

    payload = {
        "actual_checkout_date": actual_checkout_date.isoformat(),
        "returned_deposit": returned_deposit,
        "deposit_comment": deposit_comment,
        "is_closed": True,
    }

    headers = {
        "apikey": os.environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_KEY']}",
        "Content-Type": "application/json",
    }

    r = requests.patch(url, json=payload, headers=headers, timeout=10)

    print("🟡 CLOSE STATUS:", r.status_code)
    print("🟡 CLOSE BODY:", r.text)

    r.raise_for_status()


def get_contract_by_code(contract_code: str):

    url = (
        SUPABASE_URL
        + f"/rest/v1/contracts?contract_code=eq.{contract_code}&select=*"
    )

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()

    rows = r.json()

    if not rows:
        return None

    return rows[0]


def insert_contract(payload):
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/contracts",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 Supabase INSERT:", r.status_code, r.text)

    r.raise_for_status()


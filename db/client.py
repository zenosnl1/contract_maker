import os
import requests
from datetime import datetime, date, timedelta
from core.utils import build_contract_code

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def insert_expense(payload):

    url = SUPABASE_URL + "/rest/v1/expenses"

    r = requests.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 EXPENSE INSERT:", r.status_code, r.text)

    r.raise_for_status()

def fetch_expenses_by_month(year: str, month: str):

    start = f"{year}-{month}-01"

    if month == "12":
        end = f"{int(year)+1}-01-01"
    else:
        end = f"{year}-{int(month)+1:02}-01"

    url = (
        SUPABASE_URL
        + "/rest/v1/expenses"
        + f"?expense_date=gte.{start}&expense_date=lt.{end}"
        + "&order=expense_date.asc"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)

    r.raise_for_status()

    return r.json()


def fetch_fixed_expense_by_id(fid):

    url = SUPABASE_URL + f"/rest/v1/fixed_expenses?id=eq.{fid}"

    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    rows = r.json()
    return rows[0] if rows else None

def delete_fixed_expense(fid):

    url = SUPABASE_URL + f"/rest/v1/fixed_expenses?id=eq.{fid}"

    r = requests.delete(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

def update_fixed_expense(fid, payload):

    url = SUPABASE_URL + f"/rest/v1/fixed_expenses?id=eq.{fid}"

    r = requests.patch(
        url,
        headers={**HEADERS, "Prefer": "return=minimal"},
        json=payload,
        timeout=10,
    )
    r.raise_for_status()


def fetch_fixed_expenses():

    url = SUPABASE_URL + "/rest/v1/fixed_expenses?order=id.asc"

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 FETCH FIXED:", r.status_code, r.text)

    r.raise_for_status()

    return r.json()

def fetch_contract_violations_for_period(
    contract_code: str,
    start_date: str,
    actual_end_date: str,
):

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + "?contract_code=eq."
        + contract_code
        + "&created_at=gte."
        + start_date
        + "&created_at=lte."
        + actual_end_date
    )

    r = requests.get(url, headers=HEADERS, timeout=10)

    print("🟡 FETCH PERIOD VIOLATIONS:", r.status_code, r.text)

    r.raise_for_status()

    return r.json()

def fetch_penalties_by_contract_codes(codes: list[str]):

    if not codes:
        return {}

    # eq.(a,b,c)
    in_clause = ",".join(codes)

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + "?contract_code=in.("
        + in_clause
        + ")"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)

    r.raise_for_status()

    rows = r.json()

    penalties = {}

    for v in rows:
        penalties.setdefault(v["contract_code"], 0)
        penalties[v["contract_code"]] += int(v["amount"])

    return penalties



def fetch_expenses_last_30_days():

    since = (date.today() - timedelta(days=30)).isoformat()

    url = (
        SUPABASE_URL
        + "/rest/v1/expenses"
        + f"?expense_date=gte.{since}&order=expense_date.desc"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)

    r.raise_for_status()

    return r.json()

def fetch_all_expenses():

    url = SUPABASE_URL + "/rest/v1/expenses?order=expense_date.asc"

    r = requests.get(url, headers=HEADERS, timeout=10)

    r.raise_for_status()

    return r.json()



def insert_fixed_expense(payload: dict):

    url = SUPABASE_URL + "/rest/v1/fixed_expenses"

    r = requests.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 FIXED EXPENSE INSERT:", r.status_code, r.text)

    r.raise_for_status()


async def expense_payment_chosen(update, context):

    query = update.callback_query
    await query.answer()

    method = "company" if query.data == "EXP_PAY_COMPANY" else "cash"

    exp = context.user_data["expense"]

    payload = {
        "amount": exp["amount"],
        "date": exp["date"],
        "category": exp["category"],
        "payment_method": method,
    }

    insert_expense(payload)

    await query.edit_message_text("✅ Расход сохранён.")

    await query.message.reply_text(
        "Главное меню:",
        reply_markup=start_keyboard(update.effective_user),
    )

    context.user_data.pop("expense", None)

    return FlowState.MENU


# ======================================================
# Bookings DB API
# ======================================================

def insert_booking(payload: dict):

    url = SUPABASE_URL + "/rest/v1/bookings"

    r = requests.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 BOOKING INSERT:", r.status_code, r.text)

    r.raise_for_status()


def fetch_active_bookings():

    url = (
        SUPABASE_URL
        + "/rest/v1/bookings"
        + "?status=eq.active"
        + "&order=flat_number.asc"
    )

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=10,
    )

    r.raise_for_status()

    return r.json()


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

        "max_people_day": int(data["MAX_PEOPLE_DAY"]),
        "max_people_night": int(data["MAX_PEOPLE_NIGHT"]),
        
        "price_per_day": int(data["PRICE_PER_DAY"]),
        "total_price": int(data["TOTAL_PRICE"]),
        "deposit": int(data["DEPOSIT"]),

        "checkout_time": data["CHECKOUT_TIME"],
        "is_closed": False,

        "payment_method": data.get("PAYMENT_METHOD"),
        "invoice_issued": data.get("INVOICE_ISSUED"),
        "invoice_number": data.get("INVOICE_NUMBER"),
        "fixed_per_booking": round(
            float(data.get("FIXED_PER_BOOKING", 10)),
            2,
        ),
    }

    r = requests.post(url, json=payload, headers=headers, timeout=10)

    print("🟡 Supabase INSERT status:", r.status_code)
    print("🟡 Supabase INSERT body:", r.text)
    
    if r.status_code not in (200, 201):
        raise RuntimeError("Supabase insert failed")

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

# ======================================================
# Close contract full logic (with early checkout + act)
# ======================================================

def calculate_close_preview(
    contract_code: str,
    actual_checkout_date: date,
    early_checkout: bool,
    initiator: str | None,
    early_reason: str | None,
    manual_refund: int | None,
):

    contract = get_contract_by_code(contract_code)

    violations = fetch_contract_violations(contract_code)
    penalties = sum(int(v["amount"]) for v in violations)

    start = datetime.fromisoformat(contract["start_date"]).date()
    actual_end = actual_checkout_date

    lived_nights = max(0, (actual_end - start).days)

    price = int(contract["price_per_day"])
    total_price = int(contract["total_price"])
    deposit = int(contract["deposit"])

    used_amount = lived_nights * price
    unused_amount = max(0, total_price - used_amount)

    refund = 0
    extra_due = 0

    if not early_checkout:

        refund = max(0, deposit - penalties)
        extra_due = max(0, penalties - deposit)

    else:

        if initiator == "tenant":

            refund = unused_amount + max(0, deposit - penalties)
            extra_due = max(0, penalties - deposit)

        elif initiator == "landlord":

            if manual_refund is not None:
                refund = manual_refund

                total_available = deposit + unused_amount
                extra_due = max(0, penalties - total_available + refund)

            else:
                refund = unused_amount + max(0, deposit - penalties)
                extra_due = max(0, penalties - (deposit + unused_amount))

    return {
        "used": used_amount,
        "unused": unused_amount,
        "penalties": penalties,
        "refund": refund,
        "extra_due": extra_due,
        "lived_nights": lived_nights,
        "unused_nights": max(0, contract["nights"] - lived_nights),
    }


def close_contract_full(
    contract_code: str,
    actual_checkout_date: date,
    early_checkout: bool,
    initiator: str | None,
    early_reason: str | None,
    manual_refund: int | None,
):

    contract = get_contract_by_code(contract_code)

    if not contract:
        raise ValueError("Contract not found")

    if contract["is_closed"]:
        raise ValueError("Contract already closed")

    # --- violations ---
    violations = fetch_contract_violations(contract_code)
    penalties = sum(int(v["amount"]) for v in violations)

    # --- dates ---
    start = datetime.fromisoformat(contract["start_date"]).date()
    actual_end = actual_checkout_date

    lived_nights = max(0, (actual_end - start).days)

    price = int(contract["price_per_day"])
    total_price = int(contract["total_price"])
    deposit = int(contract["deposit"])

    used_amount = lived_nights * price
    unused_amount = max(0, total_price - used_amount)

    # --- default calculations ---
    refund = 0
    extra_due = 0

    # =============================
    # NORMAL END
    # =============================
    if not early_checkout:

        refund = max(0, deposit - penalties)
        extra_due = max(0, penalties - deposit)

    # =============================
    # EARLY CHECKOUT
    # =============================
    else:

        # ---- tenant initiated ----
        if initiator == "tenant":

            refund = unused_amount + max(0, deposit - penalties)
            extra_due = max(0, penalties - deposit)

        # ---- landlord initiated ----
        elif initiator == "landlord":

            if manual_refund is not None:
                refund = manual_refund

                total_available = deposit + unused_amount
                extra_due = max(0, penalties - total_available + refund)

            else:
                refund = unused_amount + max(0, deposit - penalties)
                extra_due = max(0, penalties - (deposit + unused_amount))

    # --- save to contracts ---
    url = (
        SUPABASE_URL
        + f"/rest/v1/contracts?contract_code=eq.{contract_code}"
    )

    payload = {
        "actual_checkout_date": actual_checkout_date.isoformat(),
        "early_checkout": early_checkout,
        "early_initiator": initiator,
        "early_reason": early_reason,

        "refund_unused_amount": unused_amount,
        "final_refund_amount": refund,
        "extra_due_amount": extra_due,

        "is_closed": True,
    }

    r = requests.patch(
        url,
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 CLOSE FULL:", r.status_code, r.text)

    r.raise_for_status()

    return {
        "used": used_amount,
        "unused": unused_amount,
        "penalties": penalties,
        "refund": refund,
        "extra_due": extra_due,
        "lived_nights": lived_nights,
    }

# ======================================================
# Violations DB API
# ======================================================

def insert_violation(payload: dict):

    url = SUPABASE_URL + "/rest/v1/violations"

    r = requests.post(
        url,
        json=payload,
        headers=HEADERS,
        timeout=10,
    )

    print("🟡 VIOLATION INSERT:", r.status_code, r.text)

    r.raise_for_status()


def fetch_contract_violations(contract_code: str):

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + f"?contract_code=eq.{contract_code}"
        + "&resolved=eq.false"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    return r.json()


def fetch_flat_violations(flat_number: str):

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + f"?flat_number=eq.{flat_number}"
        + "&resolved=eq.false"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    return r.json()


def delete_violation(violation_id: str):

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + f"?id=eq.{violation_id}"
    )

    r = requests.delete(url, headers=HEADERS, timeout=10)

    print("🟡 VIOLATION DELETE:", r.status_code, r.text)

    r.raise_for_status()


def fetch_violations_between(start_date: str, end_date: str):

    url = (
        SUPABASE_URL
        + "/rest/v1/violations"
        + f"?created_at=gte.{start_date}"
        + f"&created_at=lte.{end_date}"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()

    return r.json()



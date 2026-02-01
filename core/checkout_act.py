from docx import Document
from datetime import datetime
from docx.shared import Pt


# ======================================================
# MAIN
# ======================================================

def build_checkout_act(
    template_path: str,
    output_path: str,
    contract: dict,
    violations: list,
):

    safe_code = contract["contract_code"].replace("/", "_")
    doc = Document(template_path)

    start = datetime.fromisoformat(contract["start_date"]).date()
    end_plan = datetime.fromisoformat(contract["end_date"]).date()
    actual = datetime.fromisoformat(contract["actual_checkout_date"]).date()

    lived_nights = max(0, (actual - start).days)
    total_nights = contract["nights"] or 0
    unused_nights = max(0, total_nights - lived_nights)

    price = contract["price_per_day"] or 0
    refund_unused = unused_nights * price

    penalties_total = sum(v["amount"] for v in violations)

    values = {
        "FLAT_NUMBER": contract["flat_number"],
        "CLIENT_NAME": contract["client_name"],
        "CLIENT_ID": contract["client_id"] or "",
        "CLIENT_NUMBER": contract["client_number"] or "",
        "CLIENT_MAIL": contract["client_mail"] or "",
        "CLIENT_ADDRESS": contract["client_address"] or "",

        "START_DATE": start.strftime("%d.%m.%Y"),
        "END_DATE": end_plan.strftime("%d.%m.%Y"),
        "ACTUAL_CHECKOUT_DATE": actual.strftime("%d.%m.%Y"),
        "CHECKOUT_TIME": contract.get("checkout_time") or "",

        "TOTAL_PRICE": str(contract["total_price"]),
        "DEPOSIT": str(contract["deposit"]),

        "EARLY_CHECKOUT": "Да" if contract["early_checkout"] else "Нет",
        "EARLY_INITIATOR": contract.get("early_initiator") or "-",
        "EARLY_REASON": contract.get("early_reason") or "-",

        "REFUND_UNUSED_AMOUNT": str(refund_unused),
        "FINAL_REFUND_AMOUNT": str(contract["final_refund_amount"]),
        "EXTRA_DUE_AMOUNT": str(contract["extra_due_amount"]),

        "LIVED_NIGHTS": str(lived_nights),
        "UNUSED_NIGHTS": str(unused_nights),

        "PENALTIES_TOTAL": str(penalties_total),
    }

    replace_everywhere(doc, values)
    insert_violations_table(doc, violations)

    doc.save(output_path)

    return output_path


# ======================================================
# HELPERS
# ======================================================

def replace_everywhere(doc: Document, data: dict):

    for p in doc.paragraphs:
        _process_paragraph(p, data)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _process_paragraph(p, data)


def _process_paragraph(p, data):

    text = p.text

    keys_used = [k for k in data if f"{{{{{k}}}}}" in text]

    if not keys_used:
        return

    for r in p.runs:
        r.text = ""

    i = 0
    while i < len(text):

        replaced = False

        for k in keys_used:

            ph = f"{{{{{k}}}}}"

            if text.startswith(ph, i):
                run = p.add_run(str(data[k]))
                run.font.size = Pt(11)
                i += len(ph)
                replaced = True
                break

        if not replaced:
            run = p.add_run(text[i])
            i += 1


def insert_violations_table(doc: Document, violations: list):

    marker = "{{VIOLATIONS_TABLE}}"

    for p in doc.paragraphs:

        if marker not in p.text:
            continue

        p.text = ""

        if not violations:
            p.add_run("Нарушений не зафиксировано.")
            return

        table = doc.add_table(rows=1, cols=3)

        hdr = table.rows[0].cells
        hdr[0].text = "Тип"
        hdr[1].text = "Сумма (€)"
        hdr[2].text = "Комментарий"

        for v in violations:
            row = table.add_row().cells
            row[0].text = v["violation_type"]
            row[1].text = str(v["amount"])
            row[2].text = v.get("description") or ""

        p._element.addnext(table._element)
        return

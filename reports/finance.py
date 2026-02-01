
from datetime import date, timedelta
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font
from calendar import monthrange


EXPENSE_PER_STAY = 10


def build_finance_report(contracts):

    wb = Workbook()
    wb.remove(wb.active)

    by_month = defaultdict(list)

    # --- разложим договора по месяцам ---
    for c in contracts:

        start = date.fromisoformat(c["start_date"])
        end = date.fromisoformat(
            c["actual_checkout_date"] or c["end_date"]
        )

        cur = start

        while cur <= end:
            key = f"{cur.year}-{cur.month:02d}"
            by_month[key].append(c)
            cur += timedelta(days=1)

    # --- строим листы ---
    for month, rows in sorted(by_month.items(), reverse=True):

        ws = wb.create_sheet(month)

        ws.append([
            "Квартира",
            "Ночей",
            "Доход",
            "Расходы",
            "Чистый доход",
            "Загрузка %",
        ])

        for cell in ws[1]:
            cell.font = Font(bold=True)

        stats = {}

        year, m = map(int, month.split("-"))
        days_in_month = monthrange(year, m)[1]

        for c in rows:

            flat = c["flat_number"]
            price = int(c["price_per_day"])

            stats.setdefault(flat, {
                "nights": 0,
                "income": 0,
                "stays": set(),
            })

            stats[flat]["nights"] += 1
            stats[flat]["income"] += price
            stats[flat]["stays"].add(c["contract_code"])

        for flat, d in stats.items():

            expenses = len(d["stays"]) * EXPENSE_PER_STAY
            net = d["income"] - expenses
            load = round(d["nights"] / days_in_month * 100, 1)

            ws.append([
                flat,
                d["nights"],
                d["income"],
                expenses,
                net,
                load,
            ])

    path = "/tmp/finance_report.xlsx"
    wb.save(path)

    return path

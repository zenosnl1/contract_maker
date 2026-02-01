from datetime import date, timedelta
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from calendar import monthrange

EXPENSE_PER_STAY = 10


THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


CENTER = Alignment(horizontal="center", vertical="center")


def style_sheet(ws):

    widths = [18, 14, 14, 14, 16, 14]

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    for row in ws.iter_rows():
        ws.row_dimensions[row[0].row].height = 22

        for cell in row:
            cell.alignment = CENTER
            cell.border = THIN_BORDER


def build_finance_report(contracts):

    wb = Workbook()
    wb.remove(wb.active)

    by_month = defaultdict(list)

    # -----------------------------
    # раскладываем по месяцам
    # -----------------------------

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

    # -----------------------------
    # строим листы
    # -----------------------------

    for month, rows in sorted(by_month.items(), reverse=True):

        ws = wb.create_sheet(month)

        ws.append([
            "Квартира",
            "Ночей",
            "Доход (€)",
            "Расходы (€)",
            "Чистый доход (€)",
            "Загрузка (%)",
        ])

        for c in ws[1]:
            c.font = Font(bold=True)

        year, m = map(int, month.split("-"))
        days_in_month = monthrange(year, m)[1]

        stats = {}

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

        # -----------------------------
        # сортировка по номеру квартиры
        # -----------------------------

        sorted_flats = sorted(stats.items(), key=lambda x: int(x[0]))

        total_nights = 0
        total_income = 0
        total_expenses = 0

        for flat, d in sorted_flats:

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

            total_nights += d["nights"]
            total_income += d["income"]
            total_expenses += expenses

        # -----------------------------
        # ИТОГО
        # -----------------------------

        avg_load = round(total_nights / (days_in_month * len(sorted_flats)) * 100, 1)

        ws.append([])
        ws.append([
            "ИТОГО",
            total_nights,
            total_income,
            total_expenses,
            total_income - total_expenses,
            avg_load,
        ])

        last_row = ws.max_row

        for cell in ws[last_row]:
            cell.font = Font(bold=True)

        style_sheet(ws)

    path = "/tmp/finance_report.xlsx"
    wb.save(path)

    return path

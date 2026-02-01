from datetime import date, timedelta
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from calendar import monthrange

EXPENSE_PER_STAY = 10


GRAY_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

CENTER = Alignment(horizontal="center", vertical="center")


def style_sheet(ws):

    widths = [16, 12, 14, 14, 16, 20, 22, 14]

    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    for row in ws.iter_rows():
        ws.row_dimensions[row[0].row].height = 22

        for cell in row:
            cell.alignment = CENTER
            cell.border = GRAY_BORDER


def build_finance_report(contracts):

    wb = Workbook()
    wb.remove(wb.active)

    by_month = defaultdict(list)

    # -----------------------------
    # раскладываем ночи по месяцам
    # -----------------------------

    for c in contracts:

        start = date.fromisoformat(c["start_date"])
        end = date.fromisoformat(
            c.get("actual_checkout_date") or c["end_date"]
        )

        cur = start

        while cur <= end:
            key = f"{cur.year}-{cur.month:02d}"
            by_month[key].append(c)
            cur += timedelta(days=1)

    # -----------------------------
    # считаем ОБЩУЮ прибыль
    # -----------------------------

    all_profit = 0
    all_nights = 0
    all_days = defaultdict(int)

    for c in contracts:
        nights = int(c["nights"])
        price = int(c["price_per_day"])
        all_profit += nights * price - EXPENSE_PER_STAY
        all_nights += nights

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
            "Потенциальная прибыль (€)",
            "Реализованная прибыль (€)",
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

        sorted_flats = sorted(stats.items(), key=lambda x: int(x[0]))

        total_nights = 0
        total_income = 0
        total_expenses = 0
        total_potential = 0

        for flat, d in sorted_flats:

            expenses = len(d["stays"]) * EXPENSE_PER_STAY
            net = d["income"] - expenses

            potential = days_in_month * (d["income"] // max(d["nights"], 1))

            load = round(d["nights"] / days_in_month * 100, 1)

            ws.append([
                flat,
                d["nights"],
                d["income"],
                expenses,
                net,
                potential,
                net,
                load,
            ])

            total_nights += d["nights"]
            total_income += d["income"]
            total_expenses += expenses
            total_potential += potential

        ws.append([])
        ws.append([
            "ИТОГО",
            total_nights,
            total_income,
            total_expenses,
            total_income - total_expenses,
            total_potential,
            total_income - total_expenses,
            round(total_nights / (days_in_month * len(sorted_flats)) * 100, 1),
        ])

        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)

        # -----------------------------
        # Доля месяца от общего
        # -----------------------------

        ws.append([])
        ws.append([
            "Доля месяца от общей прибыли",
            "",
            "",
            "",
            f"{round((total_income - total_expenses) / max(all_profit,1) * 100, 1)} %",
        ])

        ws.append([
            "Доля месяца от общей загрузки",
            "",
            "",
            "",
            f"{round(total_nights / max(all_nights,1) * 100, 1)} %",
        ])

        style_sheet(ws)

    path = "/tmp/finance_report.xlsx"
    wb.save(path)

    return path

from datetime import date, timedelta
from calendar import monthrange
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter


GRAY = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

CENTER = Alignment(horizontal="center", vertical="center")


# ---------- helpers ----------

def month_bounds(year: int, month: int):
    days = monthrange(year, month)[1]
    return (
        date(year, month, 1),
        date(year, month, days + 1),
        days,
    )


def nights_overlap(start, end, m_start, m_end):
    s = max(start, m_start)
    e = min(end, m_end)
    if s >= e:
        return 0
    return (e - s).days


def euro(val):
    return f"{int(val)} €"


def percent(val):
    return f"{round(val, 1)} %"


# ---------- MAIN BUILDER ----------

def build_financial_report(rows):

    wb = Workbook()
    wb.remove(wb.active)

    today = date.today()

    # группируем по месяцам заезда/выезда
    contracts_by_month = defaultdict(list)

    for r in rows:
        s = date.fromisoformat(r["start_date"])
        e = date.fromisoformat(r["end_date"])

        cur = date(s.year, s.month, 1)

        while cur <= e:
            contracts_by_month[(cur.year, cur.month)].append(r)

            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)

    grand_total_profit = 0
    grand_total_nights = 0

    for (year, month), contracts in sorted(contracts_by_month.items(), reverse=True):

        m_start, m_end, days_in_month = month_bounds(year, month)

        ws = wb.create_sheet(f"{month:02}.{year}")

        headers = [
            "Помещение",
            "Реализовано",
            "Потенциально",
            "Расходы",
            "Прибыль",
            "Загрузка",
            "",
            "Доля месяца",
        ]

        ws.append(headers)

        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22

        ws.column_dimensions["H"].width = 66  # доля месяца

        ws.row_dimensions[1].height = 26

        for c in range(1, 9):
            cell = ws.cell(row=1, column=c)
            cell.font = Font(bold=True)
            cell.alignment = CENTER
            cell.border = GRAY

        flats = defaultdict(list)

        for r in contracts:
            flats[r["flat_number"]].append(r)

        month_profit = 0
        month_realized = 0
        month_potential = 0
        month_cost = 0
        month_nights = 0

        for flat in sorted(flats.keys(), key=lambda x: int(x)):

            realized = 0
            potential = 0
            nights_total = 0

            for r in flats[flat]:

                start = date.fromisoformat(r["start_date"])
                planned_end = date.fromisoformat(r["end_date"])

                actual_end = (
                    date.fromisoformat(r["actual_checkout_date"])
                    if r.get("actual_checkout_date")
                    else planned_end
                )

                price = int(r["price_per_day"])

                # --- realized ---
                real_end = min(today, actual_end)

                realized_nights = nights_overlap(
                    start,
                    real_end,
                    m_start,
                    m_end,
                )

                realized += realized_nights * price

                # --- potential ---
                pot_nights = nights_overlap(
                    start,
                    planned_end,
                    m_start,
                    m_end,
                )

                potential += pot_nights * price

                nights_total += pot_nights

            costs = nights_total * 10
            profit = realized - costs

            load = (nights_total / days_in_month) * 100 if days_in_month else 0

            ws.append([
                flat,
                euro(realized),
                euro(potential),
                euro(costs),
                euro(profit),
                percent(load),
                "",
                f"{nights_total} ночей / {days_in_month}",
            ])

            row = ws.max_row

            ws.row_dimensions[row].height = 22

            for c in range(1, 9):
                cell = ws.cell(row=row, column=c)
                cell.alignment = CENTER
                cell.border = GRAY

            month_realized += realized
            month_potential += potential
            month_cost += costs
            month_profit += profit
            month_nights += nights_total

        # ----- TOTALS -----

        ws.append([])
        ws.append([])

        base = ws.max_row + 1

        totals = [
            ("Итого реализовано:", euro(month_realized)),
            ("Итого потенциально:", euro(month_potential)),
            ("Итого расходы:", euro(month_cost)),
            ("Итого прибыль:", euro(month_profit)),
            ("Средняя загрузка:", percent((month_nights / days_in_month) * 100 if days_in_month else 0)),
        ]

        for label, value in totals:
            ws.append([label, value])

            r = ws.max_row

            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)

            for c in range(1, 3):
                ws.cell(row=r, column=c).font = Font(bold=True)

        grand_total_profit += month_profit
        grand_total_nights += month_nights

        ws.append([])
        ws.append([
            "Доля месяца от всей прибыли:",
            percent((month_profit / grand_total_profit) * 100 if grand_total_profit else 0),
        ])

    path = "/tmp/financial_report.xlsx"
    wb.save(path)

    return path

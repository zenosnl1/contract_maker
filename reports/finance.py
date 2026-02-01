from datetime import date, datetime
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Side, Font
from openpyxl.utils import get_column_letter


EXPENSE_PER_BOOKING = 10


GRAY_BORDER = Border(
    left=Side(style="thin", color="CCCCCC"),
    right=Side(style="thin", color="CCCCCC"),
    top=Side(style="thin", color="CCCCCC"),
    bottom=Side(style="thin", color="CCCCCC"),
)

CENTER = Alignment(horizontal="center", vertical="center")


# -------------------------------------------------------


def month_range(year: int, month: int):
    start = date(year, month, 1)

    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    return start, end


def overlap_nights(a_start, a_end, b_start, b_end):
    start = max(a_start, b_start)
    end = min(a_end, b_end)

    if start >= end:
        return 0

    return (end - start).days


# -------------------------------------------------------


def build_finance_report(rows):

    wb = Workbook()
    ws = wb.active
    ws.title = "Финансы"

    headers = [
        "Месяц",
        "Помещение",

        "Ночей в месяце",

        "Реализовано €",
        "Потенциал €",

        "Расходы €",

        "Загрузка %",
    ]

    ws.append(headers)

    for col in range(1, len(headers) + 1):
        cell = ws.cell(1, col)
        cell.font = Font(bold=True)
        cell.border = GRAY_BORDER
        cell.alignment = CENTER
        ws.column_dimensions[get_column_letter(col)].width = 24

    ws.row_dimensions[1].height = 26

    # --------------------------------------------------
    # группировка: (year, month) -> flat -> data
    # --------------------------------------------------

    grouped = defaultdict(lambda: defaultdict(lambda: {
        "nights": 0,
        "realized": 0,
        "potential": 0,
        "expenses": 0,
    }))

    today = date.today()

    for r in rows:

        try:
            start = datetime.fromisoformat(r["start_date"]).date()
            end = datetime.fromisoformat(r["end_date"]).date()

            price = int(r["price_per_day"])
            flat = r["flat_number"]

        except Exception:
            continue

        cur = start.replace(day=1)

        while cur < end:

            m_start, m_end = month_range(cur.year, cur.month)

            nights = overlap_nights(start, end, m_start, m_end)

            if nights:

                bucket = grouped[(cur.year, cur.month)][flat]

                bucket["nights"] += nights

                bucket["potential"] += nights * price

                lived = overlap_nights(
                    start,
                    min(today, end),
                    m_start,
                    m_end,
                )

                bucket["realized"] += lived * price

                # фикс-расход на заезд
                bucket["expenses"] += EXPENSE_PER_BOOKING

            # следующий месяц
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)

    # --------------------------------------------------
    # вывод
    # --------------------------------------------------

    grand_total = 0

    for (year, month) in sorted(grouped.keys(), reverse=True):

        ws.append([])
        ws.append([f"{month:02}.{year}"])
        ws.merge_cells(
            start_row=ws.max_row,
            start_column=1,
            end_row=ws.max_row,
            end_column=len(headers),
        )

        title_cell = ws.cell(ws.max_row, 1)
        title_cell.font = Font(bold=True)
        title_cell.alignment = CENTER
        title_cell.border = GRAY_BORDER

        month_total = 0
        month_potential = 0
        month_nights = 0
        month_expenses = 0

        for flat in sorted(grouped[(year, month)]):

            b = grouped[(year, month)][flat]

            month_total += b["realized"]
            month_potential += b["potential"]
            month_nights += b["nights"]
            month_expenses += b["expenses"]

            ws.append([
                f"{month:02}.{year}",
                flat,

                b["nights"],

                f"{b['realized']} €",
                f"{b['potential']} €",

                f"{b['expenses']} €",

                f"{round(b['nights'] / 30 * 100, 1)} %",
            ])

        # ---- итог месяца ----

        ws.append([])

        days_in_month = (
            month_range(year, month)[1]
            - month_range(year, month)[0]
        ).days

        flats_count = len(grouped[(year, month)])

        total_possible_nights = days_in_month * flats_count

        month_load = round(
            month_nights / total_possible_nights * 100,
            1,
        ) if total_possible_nights else 0

        month_profit = month_total - month_expenses

        ws.append([
            "ИТОГО",
            f"{flats_count} квартир",

            month_nights,

            f"{month_total} €",
            f"{month_potential} €",

            f"{month_expenses} €",

            f"{month_load} %",
        ])

        grand_total += month_profit

    # --------------------------------------------------
    # форматирование всех ячеек
    # --------------------------------------------------

    for row in ws.iter_rows():
        ws.row_dimensions[row[0].row].height = 20

        for cell in row:
            if cell.value is not None:
                cell.alignment = CENTER
                cell.border = GRAY_BORDER

    path = "/tmp/financial_report.xlsx"
    wb.save(path)

    return path

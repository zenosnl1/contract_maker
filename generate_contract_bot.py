import os
from docx import Document
import threading
import http.server
import socketserver
import os
import asyncio
import requests
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from telegram.ext import ApplicationBuilder
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from datetime import date, timedelta, datetime
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH


TOKEN = os.environ["BOT_TOKEN"]

MENU = 0
FILLING = 1
CONFIRM_SAVE = 2

CONTRACT_TEMPLATE = "template_contract.docx"
ACT_TEMPLATE = "template_act.docx"

FIELDS = [
    "FLAT_NUMBER",
    "CLIENT_NAME",
    "CLIENT_ID",
"CLIENT_ADDRESS",
"CLIENT_MAIL",
"CLIENT_NUMBER",
    "START_DATE",
    "END_DATE",
"CHECKOUT_TIME",
"PRICE_PER_DAY",
    "DEPOSIT",
]

QUESTIONS = {
    "FLAT_NUMBER": "Номер помещения:",
    "CLIENT_NAME": "Имя клиента:",
    "CLIENT_ID": "Документ / персональный код:",
"CLIENT_ADDRESS": "Адрес клиента:",
"CLIENT_MAIL": "EMAIL клиента",
"CLIENT_NUMBER": "Номер телефона клиента",
    "START_DATE": "Дата заезда:",
    "END_DATE": "Дата выезда:",
"CHECKOUT_TIME": "Время выезда:",
"PRICE_PER_DAY": "Цена за ночь:",
    "DEPOSIT": "Депозит:",
}


# ===== Word replacement =====

async def date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    iso = query.data.split(":")[1]
    d = datetime.fromisoformat(iso)

    step = context.user_data["step"]
    if step >= len(FIELDS):
        return FILLING
    
    field = FIELDS[step]

    # сохраняем дату
    context.user_data[field] = d.strftime("%d.%m.%Y")

    step += 1
    context.user_data["step"] = step

    # после START_DATE — показываем END_DATE
    if field == "START_DATE":
        next_day = d + timedelta(days=1)
    
        await query.edit_message_text(
            "📅 Выберите дату выезда:",
            reply_markup=date_keyboard(start_from=next_day),
        )
        return FILLING


    # после END_DATE — просто спрашиваем следующий шаг (CHECKOUT_TIME)
    next_field = FIELDS[step]

    if next_field == "CHECKOUT_TIME":
        await query.edit_message_text(
            "⏰ Выберите время выезда:",
            reply_markup=checkout_keyboard(),
        )
        return FILLING
    
    await query.edit_message_text(QUESTIONS[next_field])
    return FILLING



def checkout_keyboard():
    buttons = [
        [
            InlineKeyboardButton("09:00", callback_data="CHECKOUT:09:00"),
            InlineKeyboardButton("12:00", callback_data="CHECKOUT:12:00"),
        ],
        [
            InlineKeyboardButton("15:00", callback_data="CHECKOUT:15:00"),
            InlineKeyboardButton("18:00", callback_data="CHECKOUT:18:00"),
        ],
    ]

    return InlineKeyboardMarkup(buttons)

def start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Начать оформление", callback_data="START_FLOW")],
        [InlineKeyboardButton("📥 Импорт договора", callback_data="MENU_IMPORT")],
        [InlineKeyboardButton("📊 Статистика", callback_data="MENU_STATS")],
        [InlineKeyboardButton("👥 Текущие жильцы", callback_data="MENU_ACTIVE")],
    ])

def date_keyboard(days=30, start_from=None):

    if start_from:
        base = start_from
    else:
        base = date.today()

    buttons = []

    for i in range(days):
        d = base + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(
                d.strftime("%d.%m.%Y"),
                callback_data=f"DATE:{d.isoformat()}",
            )
        ])

    return InlineKeyboardMarkup(buttons)

def skip_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⏭ Пропустить", callback_data="SKIP")]]
    )


def replace_everywhere(doc, data):
    for p in doc.paragraphs:
        process_paragraph(p, data)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    process_paragraph(p, data)


def process_paragraph(p, data):
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
                run = p.add_run(data[k])
                run.bold = True
                i += len(ph)
                replaced = True
                break

        if not replaced:
            run = p.add_run(text[i])
            i += 1


def add_page_numbers(doc):

    section = doc.sections[0]
    footer = section.footer

    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    run = p.add_run()

    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')

    instrText = OxmlElement('w:instrText')
    instrText.text = "PAGE"

    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'end')

    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)

async def import_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["step"] = 0
    context.user_data["mode"] = "import"

    await query.edit_message_text(
        "📥 Импорт договора.\n\n"
        "Введите номер помещения:"
    )

    return FILLING

def generate_docs(data):
    safe = data["CLIENT_NAME"].replace(" ", "_")

    outputs = []

    for tpl, prefix in [
        (CONTRACT_TEMPLATE, "contract"),
        (ACT_TEMPLATE, "act"),
    ]:
        doc = Document(tpl)
        replace_everywhere(doc, data)
        add_page_numbers(doc)

        fname = f"{prefix}_{safe}.docx"
        doc.save(fname)
        outputs.append(fname)

    return outputs

def build_stats_excel(rows):

    wb = Workbook()

    gray_border = Border(
        left=Side(style="thin", color="CCCCCC"),
        right=Side(style="thin", color="CCCCCC"),
        top=Side(style="thin", color="CCCCCC"),
        bottom=Side(style="thin", color="CCCCCC"),
    )

    center_align = Alignment(horizontal="center", vertical="center")

    # ====== СВОДКА ======

    ws1 = wb.active
    ws1.title = "Сводка"

    total_income = sum(r["total_price"] for r in rows)
    total_nights = sum(r["nights"] for r in rows)
    first_date = min(r["start_date"] for r in rows)

    ws1.append(["Общий доход (€)", total_income])
    ws1.append(["Всего ночей", total_nights])
    ws1.append(["Дата первого договора", first_date])

    for row in ws1.iter_rows():
        ws1.row_dimensions[row[0].row].height = 20

        for cell in row:
            cell.font = Font(bold=cell.column == 1)
            cell.alignment = center_align
            cell.border = gray_border

            ws1.column_dimensions[get_column_letter(cell.column)].width = 30

    # ====== ДОГОВОРЫ ======

    ws2 = wb.create_sheet("Договоры")

    if not rows:
        return None

    headers_map = {
        "flat_number": "Помещение",
        "client_name": "Имя клиента",
        "client_id": "Документ",
        "client_address": "Адрес",
        "client_mail": "Email",
        "client_number": "Телефон",
        "start_date": "Дата заезда",
        "end_date": "Дата выезда",
        "nights": "Ночей",
        "price_per_day": "Цена / ночь",
        "total_price": "Общая сумма",
        "deposit": "Депозит",
        "checkout_time": "Время выезда",
    }

    keys = list(headers_map.keys())

    ws2.append([headers_map[k] for k in keys])

    # ---- Заголовки ----

    for col in range(1, len(keys) + 1):

        cell = ws2.cell(row=1, column=col)

        cell.font = Font(bold=True)
        cell.alignment = center_align
        cell.border = gray_border

        ws2.column_dimensions[get_column_letter(col)].width = 26

    ws2.row_dimensions[1].height = 26

    # ---- Данные ----

    for r in rows:
        ws2.append([r.get(k) for k in keys])

    for row in ws2.iter_rows(min_row=2):

        ws2.row_dimensions[row[0].row].height = 18

        for cell in row:
            cell.alignment = center_align
            cell.border = gray_border

    path = "/tmp/contracts_stats.xlsx"
    wb.save(path)

    return path

# ===== Telegram flow =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Главное меню:",
        reply_markup=start_keyboard(),
    )

    return MENU



async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🛑 Процесс заполнения остановлен.",
        reply_markup=start_keyboard(),
    )
    return MENU

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step", 0)

    if step <= 0:
        await update.message.reply_text(
            "Вы уже в начале. Введите значение или используйте /stop."
        )
        return FILLING

    step -= 1
    context.user_data["step"] = step

    field = FIELDS[step]

    await update.message.reply_text(
        f"⬅️ Возврат назад.\n\n{QUESTIONS[field]}"
    )

    return FILLING

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data:
        await update.message.reply_text("Пока ничего не введено.")
        return FILLING

    lines = ["📋 Текущие данные:"]

    for f in FIELDS:
        if f in context.user_data:
            lines.append(f"• {f}: {context.user_data[f]}")

    await update.message.reply_text("\n".join(lines))
    return FILLING

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    try:
        rows = fetch_all_contracts()
    except Exception:
        await query.edit_message_text("⚠️ Ошибка получения данных.", reply_markup=None)
        return MENU

    if not rows:
        await query.edit_message_text("Пока нет договоров.", reply_markup=None)
        return MENU

    path = build_stats_excel(rows)

    await query.edit_message_text("📊 Формирую статистику…", reply_markup=None)

    await query.message.reply_document(open(path, "rb"))
    
    await query.message.reply_text(
        "Главное меню:",
        reply_markup=start_keyboard(),
    )

    return MENU

async def active_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    try:
        rows = fetch_active_contracts()
    except Exception:
        await query.edit_message_text("⚠️ Ошибка получения данных.", reply_markup=None)
        return MENU

    if not rows:
        await query.edit_message_text("Сейчас жильцов нет.", reply_markup=None)
        return MENU

    lines = ["👥 Текущие жильцы:\n"]

    for r in rows:
        lines.append(
            f"🏠 {r['flat_number']}\n"
            f"👤 {r['client_name']}\n"
            f"📞 {r['client_number']}\n"
            f"📅 {r['start_date']} → {r['end_date']}\n"
            f"💶 {r['total_price']} €\n"
            "—"
        )

    await query.edit_message_text("\n".join(lines), reply_markup=None)

    await query.message.reply_text(
        "Главное меню:",
        reply_markup=start_keyboard(),
    )

    return MENU

async def start_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = "normal"
    context.user_data.clear()
    context.user_data["step"] = 0

    await query.edit_message_text(
        "📄 Начинаем создание договора.\n\n"
        + QUESTIONS[FIELDS[0]]
    , reply_markup=None)

    return FILLING

async def checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    time_val = query.data.replace("CHECKOUT:", "")

    step = context.user_data["step"]
    field = FIELDS[step]  # CHECKOUT_TIME

    context.user_data[field] = time_val

    step += 1
    context.user_data["step"] = step

    next_field = FIELDS[step]

    await query.edit_message_text(QUESTIONS[next_field], reply_markup=None)
    return FILLING

async def skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    step = context.user_data["step"]
    field = FIELDS[step]

    context.user_data[field] = "-----"

    step += 1
    context.user_data["step"] = step

    next_field = FIELDS[step]

    if next_field in ["CLIENT_ADDRESS", "CLIENT_MAIL"]:
        await query.edit_message_text(
            QUESTIONS[next_field],
            reply_markup=skip_keyboard(),
        )
        return FILLING
    
    await query.edit_message_text(QUESTIONS[next_field], reply_markup=None)
    return FILLING

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mode = context.user_data.get("mode", "normal")
    step = context.user_data["step"]
    field = FIELDS[step]

    text = update.message.text.strip()

    # ---------- ВАЛИДАЦИЯ ----------

    mode = context.user_data.get("mode", "normal")
    
    if field in ["START_DATE", "END_DATE"] and mode == "import":
    
        try:
            datetime.strptime(text, "%d.%m.%Y")
        except ValueError:
            await update.message.reply_text(
                "❌ Формат даты должен быть ДД.ММ.ГГГГ"
            )
            return FILLING


    if field == "PRICE_PER_DAY":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Введите цену цифрами, например: 25"
            )
            return FILLING

    if field == "DEPOSIT":
        if not text.isdigit():
            await update.message.reply_text(
                "❌ Введите депозит цифрами, например: 80"
            )
            return FILLING

    # ---------- СОХРАНЯЕМ ----------

    context.user_data[field] = text

    # ---------- АВТОРАСЧЁТ СУММЫ ----------

    if field == "PRICE_PER_DAY":

        start = datetime.strptime(context.user_data["START_DATE"], "%d.%m.%Y")
        end = datetime.strptime(context.user_data["END_DATE"], "%d.%m.%Y")

        nights = (end - start).days
        total = nights * int(text)

        context.user_data["TOTAL_PRICE"] = str(total)

        await update.message.reply_text(
            f"💶 {nights} ночей × {text} € = {total} €"
        )

    # ---------- ДВИГАЕМСЯ ВПЕРЁД ----------

    step += 1
    context.user_data["step"] = step

    # ---------- ЕСЛИ ЕСТЬ СЛЕДУЮЩИЙ ШАГ ----------

    if step < len(FIELDS):

        next_field = FIELDS[step]

        if next_field == "START_DATE":
            if mode == "import":
                await update.message.reply_text(
                    "Введите дату заезда (ДД.ММ.ГГГГ):"
                )
            else:
                await update.message.reply_text(
                    "📅 Выберите дату заезда:",
                    reply_markup=date_keyboard(),
                )
        
            return FILLING

        if next_field == "END_DATE":
            if mode == "import":
                await update.message.reply_text(
                    "Введите дату выезда (ДД.ММ.ГГГГ):"
                )
            else:
                await update.message.reply_text(
                    "📅 Выберите дату выезда:",
                    reply_markup=date_keyboard(),
                )
        
            return FILLING


        if next_field == "CHECKOUT_TIME":
            await update.message.reply_text(
                "⏰ Выберите время выезда:",
                reply_markup=checkout_keyboard(),
            )
            return FILLING

        if next_field in ["CLIENT_ADDRESS", "CLIENT_MAIL"]:
            await update.message.reply_text(
                QUESTIONS[next_field],
                reply_markup=skip_keyboard(),
            )
            return FILLING

        await update.message.reply_text(QUESTIONS[next_field])
        return FILLING

    # ---------- ФИНАЛ: ГЕНЕРИРУЕМ ДОКУМЕНТЫ ----------

    files = generate_docs(context.user_data)

    context.user_data["_generated_files"] = files

    await update.message.reply_text(
        "📄 Документы готовы.\n\n"
        "Сохранить договор в базе данных?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💾 Да", callback_data="SAVE_DB"),
                InlineKeyboardButton("❌ Нет", callback_data="SKIP_DB"),
            ]
        ])
    )

    return CONFIRM_SAVE

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def fetch_all_contracts():

    url = os.environ["SUPABASE_URL"] + "/rest/v1/contracts?select=*"

    headers = {
        "apikey": os.environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_KEY']}",
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()

    return r.json()

def fetch_active_contracts():

    today = date.today().isoformat()

    url = (
        os.environ["SUPABASE_URL"]
        + f"/rest/v1/contracts?start_date=lte.{today}&end_date=gt.{today}"
    )

    headers = {
        "apikey": os.environ["SUPABASE_KEY"],
        "Authorization": f"Bearer {os.environ['SUPABASE_KEY']}",
    }

    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()

    return r.json()

async def save_db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    save_contract_to_db(
        context.user_data,
        context.user_data["_generated_files"],
    )

    for f in context.user_data["_generated_files"]:
        await query.message.reply_document(open(f, "rb"))

    await query.edit_message_text("💾 Сохранено.", reply_markup=None)
    await query.message.reply_text(
        "Главное меню:",
        reply_markup=start_keyboard(),
    )

    return MENU

async def skip_db_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    for f in context.user_data["_generated_files"]:
        await query.message.reply_document(open(f, "rb"))

    await query.edit_message_text("Не Сохранено.", reply_markup=None)
    await query.message.reply_text(
        "Главное меню:",
        reply_markup=start_keyboard(),
    )

    return MENU

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

    payload = {
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
    }

    r = requests.post(url, json=payload, headers=headers, timeout=10)

    print("🟡 Supabase INSERT status:", r.status_code)
    print("🟡 Supabase INSERT body:", r.text)
    
    if r.status_code not in (200, 201):
        raise RuntimeError("Supabase insert failed")

# ===== main =====

WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", 10000))
PUBLIC_URL = os.environ.get("PUBLIC_URL")  # будем задать в Render

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = Handler

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 Dummy server running on port {port}")
        httpd.serve_forever()

def main():
    port = int(os.environ.get("PORT", 10000))
    public_url = os.environ.get("PUBLIC_URL")

    if not public_url:
        raise RuntimeError("PUBLIC_URL env var is not set")

    webhook_url = public_url.rstrip("/") + WEBHOOK_PATH

    print("🌍 Webhook URL:", webhook_url)

    app = ApplicationBuilder().token(TOKEN).build()
    
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU: [
                CallbackQueryHandler(start_flow_callback, pattern="^START_FLOW$"),
                CallbackQueryHandler(import_flow_callback, pattern="^MENU_IMPORT$"),
                CallbackQueryHandler(stats_callback, pattern="^MENU_STATS$"),
                CallbackQueryHandler(active_callback, pattern="^MENU_ACTIVE$"),
            ],
    
            FILLING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
    
                CallbackQueryHandler(date_callback, pattern="^DATE:"),
                CallbackQueryHandler(checkout_callback, pattern="^CHECKOUT:"),
                CallbackQueryHandler(skip_callback, pattern="^SKIP$"),
    
                CommandHandler("back", back),
                CommandHandler("status", status),
                CommandHandler("stop", stop),
            ],
    
            CONFIRM_SAVE: [
                CallbackQueryHandler(save_db_callback, pattern="^SAVE_DB$"),
                CallbackQueryHandler(skip_db_callback, pattern="^SKIP_DB$"),
            ],
        },
        fallbacks=[CommandHandler("stop", stop)],
        allow_reentry=True,
    )

    app.add_handler(conv)

    # 🚀 Самый стабильный запуск webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=WEBHOOK_PATH,
        webhook_url=webhook_url,
    )

    async def error_handler(update, context):
        print("🔥 ERROR:", context.error)
    
    app.add_error_handler(error_handler)

if __name__ == "__main__":
    main()
























































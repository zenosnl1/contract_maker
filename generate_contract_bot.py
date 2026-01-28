import os
from docx import Document
import threading
import http.server
import socketserver
import os
import asyncio
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

TOKEN = os.environ["BOT_TOKEN"]

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
    field = FIELDS[step]

    # сохраняем дату
    context.user_data[field] = d.strftime("%d.%m.%Y")

    step += 1
    context.user_data["step"] = step

    # после START_DATE — показываем END_DATE
    if field == "START_DATE":
        await query.edit_message_text(
            "📅 Выберите дату выезда:",
            reply_markup=date_keyboard(),
        )
        return 0

    # после END_DATE — просто спрашиваем следующий шаг (CHECKOUT_TIME)
    next_field = FIELDS[step]

    if next_field == "CHECKOUT_TIME":
        await query.edit_message_text(
            "⏰ Выберите время выезда:",
            reply_markup=checkout_keyboard(),
        )
        return 0
    
    await query.edit_message_text(QUESTIONS[next_field])
    return 0



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
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("▶️ Начать оформление", callback_data="START_FLOW")]]
    )

def date_keyboard(days=30):
    today = date.today()
    buttons = []

    for i in range(days):
        d = today + timedelta(days=i)
        buttons.append([
            InlineKeyboardButton(
                d.strftime("%d.%m.%Y"),
                callback_data=f"DATE:{d.isoformat()}"
            )
        ])

    return InlineKeyboardMarkup(buttons)

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


def generate_docs(data):
    safe = data["CLIENT_NAME"].replace(" ", "_")

    outputs = []

    for tpl, prefix in [
        (CONTRACT_TEMPLATE, "contract"),
        (ACT_TEMPLATE, "act"),
    ]:
        doc = Document(tpl)
        replace_everywhere(doc, data)

        fname = f"{prefix}_{safe}.docx"
        doc.save(fname)
        outputs.append(fname)

    return outputs


# ===== Telegram flow =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Добро пожаловать!\n\n"
        "Нажмите кнопку ниже, чтобы начать оформление договора.",
        reply_markup=start_keyboard(),
    )

    return 0


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🛑 Процесс заполнения остановлен.",
        reply_markup=start_keyboard(),
    )
    return ConversationHandler.END

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step", 0)

    if step <= 0:
        await update.message.reply_text(
            "Вы уже в начале. Введите значение или используйте /stop."
        )
        return 0

    step -= 1
    context.user_data["step"] = step

    field = FIELDS[step]

    await update.message.reply_text(
        f"⬅️ Возврат назад.\n\n{QUESTIONS[field]}"
    )

    return 0

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data:
        await update.message.reply_text("Пока ничего не введено.")
        return 0

    lines = ["📋 Текущие данные:"]

    for f in FIELDS:
        if f in context.user_data:
            lines.append(f"• {f}: {context.user_data[f]}")

    await update.message.reply_text("\n".join(lines))
    return 0

async def start_flow_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    context.user_data.clear()
    context.user_data["step"] = 0

    await query.edit_message_text(
        "📄 Начинаем создание договора.\n\n"
        + QUESTIONS[FIELDS[0]]
    )

    return 0

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

    await query.edit_message_text(QUESTIONS[next_field])
    return 0


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    step = context.user_data["step"]
    field = FIELDS[step]

    context.user_data[field] = update.message.text.strip()

    # если только что ввели цену — считаем сумму
    if field == "PRICE_PER_DAY":

        start = datetime.strptime(context.user_data["START_DATE"], "%d.%m.%Y")
        end = datetime.strptime(context.user_data["END_DATE"], "%d.%m.%Y")

        nights = (end - start).days
        price = int(context.user_data["PRICE_PER_DAY"])

        context.user_data["TOTAL_PRICE"] = str(nights * price)

        await update.message.reply_text(
            f"💶 {nights} ночей × {price} € = {nights * price} €"
        )

    step += 1
    context.user_data["step"] = step

    if step < len(FIELDS):

        next_field = FIELDS[step]

        if next_field == "START_DATE":
            await update.message.reply_text(
                "📅 Выберите дату заезда:",
                reply_markup=date_keyboard(),
            )
            return 0

        if next_field == "END_DATE":
            await update.message.reply_text(
                "📅 Выберите дату выезда:",
                reply_markup=date_keyboard(),
            )
            return 0

        if next_field == "CHECKOUT_TIME":
            await update.message.reply_text(
                "⏰ Выберите время выезда:",
                reply_markup=checkout_keyboard(),
            )
            return 0

        await update.message.reply_text(QUESTIONS[next_field])
        return 0

    files = generate_docs(context.user_data)

    for f in files:
        await update.message.reply_document(document=open(f, "rb"))

    await update.message.reply_text(
        "✅ Готово! Договор и акт сформированы.\n\n"
        "Можете оформить следующий договор:",
        reply_markup=start_keyboard(),
    )

    return ConversationHandler.END

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


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

    app.add_handler(CallbackQueryHandler(start_flow_callback, pattern="^START_FLOW$"))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", stop))

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            0: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
                CallbackQueryHandler(date_callback, pattern="^DATE:"),
                CallbackQueryHandler(checkout_callback, pattern="^CHECKOUT:"),
                CommandHandler("back", back),
                CommandHandler("status", status),
                CommandHandler("stop", stop),
                CommandHandler("cancel", stop),
            ]
        },
        fallbacks=[
            CommandHandler("stop", stop),
            CommandHandler("cancel", stop),
        ],
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
























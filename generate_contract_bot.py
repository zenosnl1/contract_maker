import os
from docx import Document
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]

CONTRACT_TEMPLATE = "template_contract.docx"
ACT_TEMPLATE = "template_act.docx"

FIELDS = [
    "CONTRACT_NUMBER",
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
    "TOTAL_PRICE",
    "DEPOSIT",
]

QUESTIONS = {
    "CONTRACT_NUMBER": "Введите номер договора:",
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
    "TOTAL_PRICE": "Общая сумма:",
    "DEPOSIT": "Депозит:",
}


# ===== Word replacement =====

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
    context.user_data["step"] = 0
    await update.message.reply_text("📄 Начинаем создание договора.\n\n" + QUESTIONS[FIELDS[0]])
    return 0

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🛑 Процесс заполнения остановлен.\n\n"
        "Напишите /start чтобы начать заново."
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

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data["step"]
    field = FIELDS[step]

    context.user_data[field] = update.message.text.strip()

    step += 1
    context.user_data["step"] = step

    if step < len(FIELDS):
        await update.message.reply_text(QUESTIONS[FIELDS[step]])
        return 0

    files = generate_docs(context.user_data)

    for f in files:
        await update.message.reply_document(document=open(f, "rb"))

    await update.message.reply_text("✅ Готово! Договор и акт сформированы.")

    return ConversationHandler.END

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


# ===== main =====

import threading
import http.server
import socketserver
import os
import asyncio
from telegram.ext import ApplicationBuilder

WEBHOOK_PATH = "/webhook"
PORT = int(os.environ.get("PORT", 10000))
PUBLIC_URL = os.environ.get("PUBLIC_URL")  # будем задать в Render

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    handler = Handler

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🌐 Dummy server running on port {port}")
        httpd.serve_forever()

async def main():
    if not PUBLIC_URL:
        raise RuntimeError("PUBLIC_URL environment variable is not set")

    webhook_url = PUBLIC_URL.rstrip("/") + WEBHOOK_PATH

    print("🌍 Webhook URL:", webhook_url)

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            0: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer),
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
    )

    app.add_handler(conv)

    # --- webhook instead of polling ---
    await app.bot.set_webhook(webhook_url)

    await app.initialize()
    await app.start()

    await app.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
    )

    print("🤖 Bot is running via webhook")

    await asyncio.Event().wait()  # держим процесс живым


if __name__ == "__main__":
    asyncio.run(main())






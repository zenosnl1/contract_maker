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

TOKEN = "7718573173:AAFxvApNFCBhErPZOviJpTAHVkfShqQkUOM"

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


# ===== main =====

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]},
        fallbacks=[],
    )

    app.add_handler(conv)
    app.run_polling()


if __name__ == "__main__":
    main()

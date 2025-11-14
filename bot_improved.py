import fitz
from pptx import Presentation
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import os
from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN", "7935681061:AAG6zPjZ_0mifx_Mccijvjzzu_cFVFWrKaw")
WEBHOOK_PATH = f"/{BOT_TOKEN}"

# Flask app
app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "Bot is running on Render!"

@app_web.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "ok"

# --- تلخيص النص ---
def summarize_text_local(text, sentences_count=2):
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers import Tokenizer
    from sumy.summarizers.lsa import LsaSummarizer

    if not text.strip():
        return "لا يوجد نص للسلايد"

    parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
    summarizer = LsaSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count)
    summary = " ".join([str(sentence) for sentence in summary_sentences])
    return summary if summary else "لا يوجد محتوى كافي للتلخيص"

# --- معالجة الملفات ---
def process_ppt(file_path):
    prs = Presentation(file_path)
    summaries = []
    for i, slide in enumerate(prs.slides, start=1):
        text = " ".join([shape.text for shape in slide.shapes if hasattr(shape, "text")])
        summaries.append(f"📌 سلايد {i}:\n{summarize_text_local(text)}\n")
    return summaries

def process_pdf(file_path):
    doc = fitz.open(file_path)
    summaries = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        summaries.append(f"📌 صفحة {i}:\n{summarize_text_local(text)}\n")
    return summaries

# --- استقبال الملفات ---
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    file_name = document.file_name
    file_path = f"temp_{file_name}"

    file = await document.get_file()
    await file.download_to_drive(file_path)

    try:
        if file_name.endswith(".pptx"):
            summaries = process_ppt(file_path)
        elif file_name.endswith(".pdf"):
            summaries = process_pdf(file_path)
        else:
            await update.message.reply_text("❌ نوع الملف غير مدعوم، استخدم PDF أو PPTX.")
            return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    # إرسال الملخصات
    for summary in summaries:
        for i in range(0, len(summary), 4000):
            await update.message.reply_text(summary[i:i+4000])

    # حفظ الملف
    summary_file = f"summary_{file_name}.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        for s in summaries:
            f.write(s + "\n")

    await update.message.reply_document(open(summary_file, "rb"))
    os.remove(summary_file)

# --- إعداد البوت ---
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()
bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

# --- تشغيل Flask ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # عند رفعه على Render، يجب ضبط Webhook للبوت:
    # https://api.telegram.org/bot<TOCKEN>/setWebhook?url=https://boot-z9f1.onrender.com/<TOCKEN>
    app_web.run(host="0.0.0.0", port=port)

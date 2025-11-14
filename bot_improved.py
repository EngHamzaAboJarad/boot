import fitz  # PyMuPDF
from pptx import Presentation
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import os

# تلخيص محلي
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer  # يمكن تغييره إلى LuhnSummarizer أو LexRank

BOT_TOKEN = "7935681061:AAG6zPjZ_0mifx_Mccijvjzzu_cFVFWrKaw"

# --- دالة تلخيص النص ---
def summarize_text_local(text, sentences_count=2):
    if not text.strip():
        return "لا يوجد نص للسلايد"
    
    parser = PlaintextParser.from_string(text, Tokenizer("arabic"))
    summarizer = LsaSummarizer()
    summary_sentences = summarizer(parser.document, sentences_count)
    summary = " ".join([str(sentence) for sentence in summary_sentences])
    return summary if summary else "لا يوجد محتوى كافي للتلخيص"

# --- دوال معالجة PPT وPDF ---
def process_ppt(file_path):
    prs = Presentation(file_path)
    summaries = []
    for i, slide in enumerate(prs.slides, start=1):
        text = " ".join([shape.text for shape in slide.shapes if hasattr(shape, "text")])
        summary = summarize_text_local(text)
        summaries.append(f"📌 سلايد {i}:\n{summary}\n")
    return summaries

def process_pdf(file_path):
    doc = fitz.open(file_path)
    summaries = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        summary = summarize_text_local(text)
        summaries.append(f"📌 صفحة {i}:\n{summary}\n")
    return summaries

# --- دالة استقبال الملفات ---
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
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء معالجة الملف: {e}")
        return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    # --- إرسال كل سلايد/صفحة في رسالة منفصلة ---
    for summary in summaries:
        for i in range(0, len(summary), 4000):
            await update.message.reply_text(summary[i:i+4000])

    # --- إنشاء ملف TXT بالملخصات ---
    summary_file = f"summary_{file_name}.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        for s in summaries:
            f.write(s + "\n")

    # --- إرسال الملف للمستخدم ---
    await update.message.reply_document(open(summary_file, "rb"))
    os.remove(summary_file)

# --- تشغيل البوت ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

print("🚀 البوت جاهز للتلخيص محليًا بدون OpenAI!")
app.run_polling()

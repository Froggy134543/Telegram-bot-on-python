import json
import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)

TOKEN = "8712566181:AAEe4WHEgiNX6n_IPglfNBe-OjahorPtH_s"
DATA_FILE = Path("habits_data.json")


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "uk")  # за замовчуванням укр


def tr(key: str, lang: str) -> str:
    texts = {
        "start_uk": (
            "Привіт! Я бот-трекер звичок.\n\n"
            "Команди:\n"
            "/lang – вибір мови (укр/англ)\n"
            "/add назва_звички – додати звичку\n"
            "/list – показати звички\n"
            "/stats – статистика за звичками\n"
            "/remind N – нагадування через N секунд\n\n"
            "Наприклад: /add англійська\n/remind 10"
        ),
        "start_en": (
            "Hi! I am a habit tracker bot.\n\n"
            "Commands:\n"
            "/lang – choose language (ua/en)\n"
            "/add habit_name – add habit\n"
            "/list – show habits\n"
            "/stats – habits statistics\n"
            "/remind N – reminder in N seconds\n\n"
            "Example: /add english\n/remind 10"
        ),
        "choose_lang_uk": "Вибери мову:",
        "choose_lang_en": "Choose language:",
        "lang_set_uk": "Мову змінено на українську 🇺🇦",
        "lang_set_en": "Language changed to English 🇬🇧",

        "no_habit_name_uk": "Напиши назву звички після команди. Наприклад: /add математика",
        "no_habit_name_en": "Send habit name after command. Example: /add math",

        "habit_exists_uk": "Така звичка вже є у списку.",
        "habit_exists_en": "This habit is already in your list.",

        "habit_added_uk": "Я додав звичку: {habit}",
        "habit_added_en": "I added habit: {habit}",

        "no_habits_uk": "У тебе ще немає звичок. Додай за допомогою /add.",
        "no_habits_en": "You have no habits yet. Add one with /add.",

        "your_habits_uk": "Твої звички:\n{list}",
        "your_habits_en": "Your habits:\n{list}",

        "remind_usage_uk": "Використання: /remind N (N — секунд). Наприклад: /remind 10",
        "remind_usage_en": "Usage: /remind N (N = seconds). Example: /remind 10",

        "remind_bad_uk": "Напиши позитивне число секунд. Наприклад: /remind 10",
        "remind_bad_en": "Send a positive number of seconds. Example: /remind 10",

        "remind_ok_uk": "Ок! Я надішлю нагадування через {sec} секунд.",
        "remind_ok_en": "Ok! I will send reminder in {sec} seconds.",

        "no_habits_for_rem_uk": "У тебе ще немає звичок.",
        "no_habits_for_rem_en": "You have no habits yet.",

        "saved_done_uk": "Записав: ти виконав '{habit}' {date}.",
        "saved_done_en": "Saved: you did '{habit}' on {date}.",

        "saved_skip_uk": "Добре, відмітив, що ти не зробив '{habit}' {date}.",
        "saved_skip_en": "Okay, marked that you didn't do '{habit}' on {date}.",

        "no_stats_uk": "Поки що немає даних для статистики.",
        "no_stats_en": "No stats yet.",

        "no_week_stats_uk": "За останні 7 днів поки що немає записів.",
        "no_week_stats_en": "No entries for the last 7 days yet.",

        "stats_title_uk": "Статистика за останні 7 днів:",
        "stats_title_en": "Stats for last 7 days:",
    }
    return texts[f"{key}_{'uk' if lang == 'uk' else 'en'}"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(tr("start", lang))


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    keyboard = [
        [
            InlineKeyboardButton("Українська", callback_data="lang|uk"),
            InlineKeyboardButton("English", callback_data="lang|en"),
        ]
    ]
    await update.message.reply_text(
        tr("choose_lang", lang),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def add_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    user_id = str(update.effective_user.id)
    text = " ".join(context.args).strip()

    if not text:
        await update.message.reply_text(tr("no_habit_name", lang))
        return

    data = load_data()
    user_data = data.get(user_id, {"habits": [], "history": []})

    if text in user_data["habits"]:
        await update.message.reply_text(tr("habit_exists", lang))
        return

    user_data["habits"].append(text)
    data[user_id] = user_data
    save_data(data)

    await update.message.reply_text(tr("habit_added", lang).format(habit=text))


async def list_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = data.get(user_id)

    if not user_data or not user_data.get("habits"):
        await update.message.reply_text(tr("no_habits", lang))
        return

    habits_text = "\n".join(f"- {h}" for h in user_data["habits"])
    await update.message.reply_text(tr("your_habits", lang).format(list=habits_text))


async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.data["user_id"]
    lang = job.data.get("lang", "uk")

    data = load_data()
    user_data = data.get(user_id)
    if not user_data or not user_data.get("habits"):
        await context.bot.send_message(
            chat_id=job.chat_id,
            text=tr("no_habits_for_rem", lang),
        )
        return

    today = datetime.date.today().isoformat()

    for habit in user_data["habits"]:
        keyboard = [
            [
                InlineKeyboardButton("✅", callback_data=f"done|{habit}|{today}"),
                InlineKeyboardButton("❌", callback_data=f"skip|{habit}|{today}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=job.chat_id,
            text=f"Ти виконав сьогодні: *{habit}*?",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)

    if not context.args:
        await update.message.reply_text(tr("remind_usage", lang))
        return

    try:
        seconds = int(context.args[0])
        if seconds <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(tr("remind_bad", lang))
        return

    job_name = f"reminder_once_{user_id}"
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    for job in current_jobs:
        job.schedule_removal()

    context.job_queue.run_once(
        callback=send_reminder,
        when=seconds,
        chat_id=chat_id,
        name=job_name,
        data={"user_id": user_id, "lang": lang},
    )

    await update.message.reply_text(tr("remind_ok", lang).format(sec=seconds))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data_str = query.data

    # Вибір мови
    if data_str.startswith("lang|"):
        _, lang = data_str.split("|", 1)
        context.user_data["lang"] = lang
        await query.answer()
        if lang == "uk":
            await query.edit_message_text(tr("lang_set", "uk"))
        else:
            await query.edit_message_text(tr("lang_set", "en"))
        return

    await query.answer()

    # Кнопки done/skip
    try:
        action, habit, date_str = data_str.split("|", 2)
    except ValueError:
        return

    lang = get_lang(context)
    user_id = str(query.from_user.id)
    data = load_data()
    user_data = data.get(user_id, {"habits": [], "history": []})

    if action == "done":
        user_data["history"].append(
            {"habit": habit, "date": date_str, "status": "done"}
        )
        msg = tr("saved_done", lang).format(habit=habit, date=date_str)
    else:
        user_data["history"].append(
            {"habit": habit, "date": date_str, "status": "skip"}
        )
        msg = tr("saved_skip", lang).format(habit=habit, date=date_str)

    data[user_id] = user_data
    save_data(data)

    await query.edit_message_text(msg)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = data.get(user_id)

    if not user_data or not user_data.get("history"):
        await update.message.reply_text(tr("no_stats", lang))
        return

    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    counters = {}

    for rec in user_data["history"]:
        d = datetime.date.fromisoformat(rec["date"])
        if d < week_ago:
            continue
        habit = rec["habit"]
        status = rec["status"]
        done, total = counters.get(habit, (0, 0))
        total += 1
        if status == "done":
            done += 1
        counters[habit] = (done, total)

    if not counters:
        await update.message.reply_text(tr("no_week_stats", lang))
        return

    lines = [tr("stats_title", lang)]
    for habit, (done, total) in counters.items():
        percent = int(done / total * 100) if total > 0 else 0
        lines.append(f"- {habit}: {done}/{total} ({percent}%)")

    await update.message.reply_text("\n".join(lines))


def main():
    application: Application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", lang_cmd))
    application.add_handler(CommandHandler("add", add_habit))
    application.add_handler(CommandHandler("list", list_habits))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("remind", set_reminder))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущений...")
    application.run_polling()


if __name__ == "__main__":
    main()
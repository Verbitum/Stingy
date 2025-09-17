import json
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode
from config import API_TOKEN

DATA_FILE = "data.json"
FUTURE_FILE = "future.json"
HISTORY_FILE = "history.json"

# ======== Работа с балансом ========
def load_balance(user_id):
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(user_id), {}).get("balance", 0)
    except:
        return 0

def save_balance(user_id, balance):
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    if str(user_id) not in data:
        data[str(user_id)] = {}

    data[str(user_id)]["balance"] = balance
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

# ======== Работа с историей ========
def load_history(user_id):
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(user_id), [])
    except:
        return []

def save_history(user_id, history):
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    data[str(user_id)] = history
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

# ======== Работа с предстоящими операциями ========
def load_future(user_id):
    try:
        with open(FUTURE_FILE, "r") as f:
            data = json.load(f)
        return data.get(str(user_id), [])
    except:
        return []

def save_future(user_id, future):
    try:
        with open(FUTURE_FILE, "r") as f:
            data = json.load(f)
    except:
        data = {}

    data[str(user_id)] = future
    with open(FUTURE_FILE, "w") as f:
        json.dump(data, f)

# ======== Меню ========
def main_menu():
    keyboard = [
        ["📊 Баланс", "🗓 Прогноз баланса"],
        ["➕ Добавить операцию", "📋 История"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def add_operation_menu():
    keyboard = [
        ["➖ Добавить расход", "➕ Добавить доход"],
        ["⏳ Добавить предстоящую операцию", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def future_menu():
    keyboard = [
        ["➕ Предстоящий доход", "➖ Предстоящий расход"],
        ["📋 Список предстоящих", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def forecast_menu():
    keyboard = [
        ["📅 Через неделю", "📅 Через месяц"],
        ["📅 Через 3 месяца", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ======== Состояния ========
CHOOSING_INCOME, CHOOSING_EXPENSE, FUTURE_AMOUNT, FUTURE_DATE = range(4)

# ======== Календарь ========
def build_calendar(year=None, month=None):
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    keyboard = []
    # Заголовок
    keyboard.append([InlineKeyboardButton(f"{year}-{month:02d}", callback_data="ignore")])
    # Дни недели
    keyboard.append([InlineKeyboardButton(d, callback_data="ignore") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])

    month_calendar = []
    first_day = datetime(year, month, 1)
    start_day = first_day.weekday()
    days_in_month = (datetime(year if month < 12 else year + 1, (month % 12) + 1, 1) - timedelta(days=1)).day

    row = []
    for _ in range(start_day):
        row.append(InlineKeyboardButton(" ", callback_data="ignore"))

    for day in range(1, days_in_month + 1):
        row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}-{month:02d}-{day:02d}"))
        if len(row) == 7:
            month_calendar.append(row)
            row = []
    if row:
        month_calendar.append(row)

    keyboard.extend(month_calendar)
    # Управление месяцами
    keyboard.append([
        InlineKeyboardButton("<", callback_data=f"prev_{year}_{month}"),
        InlineKeyboardButton(">", callback_data=f"next_{year}_{month}")
    ])
    return InlineKeyboardMarkup(keyboard)

# ======== Команды ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name or ""
    welcome_text = (
        f"Привет, *{user_first_name}*! 👋\n\n"
        "Смотри, что я умею:\n\n"
        "📊 Показать текущий баланс\n"
        "🗓 Прогнозировать будущий баланс\n"
        "➕ Добавлять доходы и расходы / предстоящие операции\n"
        "📋 Смотреть историю операций\n\n"
        "*Просто нажми на нужную кнопку, чтобы начать!*"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=main_menu(),
        parse_mode=ParseMode.MARKDOWN
    )

# ======== Баланс и история ========
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    balance = load_balance(user_id)
    await update.message.reply_text(f"Ваш текущий баланс: {balance} ₽")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    history = load_history(user_id)
    if not history:
        await update.message.reply_text("История операций пуста.")
    else:
        text = "История операций:\n"
        for op in history:
            text += f"{op['type']}: {op['amount']} ₽\n"
        await update.message.reply_text(text)

# ======== Прогноз ========
async def forecast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите период прогноза:", reply_markup=forecast_menu())

async def handle_forecast_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    now = datetime.now()

    if text == "📅 Через неделю":
        target_date = now + timedelta(weeks=1)
    elif text == "📅 Через месяц":
        target_date = now + timedelta(days=30)
    elif text == "📅 Через 3 месяца":
        target_date = now + timedelta(days=120)
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return
    else:
        return

    balance = load_balance(user_id)
    future = load_future(user_id)
    for op in future:
        try:
            op_date = datetime.strptime(op["date"], "%Y-%m-%d")
            if op_date <= target_date:
                balance += op["amount"] if op["type"] == "доход" else -op["amount"]
        except:
            continue

    await update.message.reply_text(
        f"Прогнозируемый баланс на {target_date.strftime('%d.%m.%Y')}: {balance} ₽"
    )

# ======== Мгновенные операции ========
async def instant_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "➕ Добавить операцию":
        await update.message.reply_text("Выберите действие:", reply_markup=add_operation_menu())
        return ConversationHandler.END

    elif text == "➕ Добавить доход":
        await update.message.reply_text("Введите сумму дохода:")
        return CHOOSING_INCOME

    elif text == "➖ Добавить расход":
        await update.message.reply_text("Введите сумму расхода:")
        return CHOOSING_EXPENSE

    elif text == "⏳ Добавить предстоящую операцию":
        await update.message.reply_text("Меню предстоящих операций:", reply_markup=future_menu())
        return ConversationHandler.END

    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return ConversationHandler.END

# ======== Добавление мгновенного дохода/расхода ========
async def add_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = float(update.message.text)
        balance = load_balance(user_id)
        balance += amount
        save_balance(user_id, balance)
        history = load_history(user_id)
        history.append({"type": "доход", "amount": amount})
        save_history(user_id, history)
        await update.message.reply_text(f"Доход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_INCOME
    return ConversationHandler.END

async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = float(update.message.text)
        balance = load_balance(user_id)
        balance -= amount
        save_balance(user_id, balance)
        history = load_history(user_id)
        history.append({"type": "расход", "amount": amount})
        save_history(user_id, history)
        await update.message.reply_text(f"Расход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_EXPENSE
    return ConversationHandler.END

# ======== Предстоящие операции ========
async def handle_future_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text in ["➕ Предстоящий доход", "➖ Предстоящий расход"]:
        context.user_data["future_last_command"] = "доход" if "доход" in text else "расход"
        await update.message.reply_text("Введите сумму:")
        return FUTURE_AMOUNT

    elif text == "📋 Список предстоящих":
        future = load_future(user_id)
        if not future:
            await update.message.reply_text("Список предстоящих операций пуст.")
        else:
            text_list = "Список предстоящих операций:\n"
            for op in future:
                text_list += f"{op['type']}: {op['amount']} ₽ на {op['date']}\n"
            await update.message.reply_text(text_list)
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в меню 'Добавить операцию'", reply_markup=add_operation_menu())

async def future_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        context.user_data["future_amount"] = amount
        await update.message.reply_text("Выберите дату:", reply_markup=build_calendar())
        return FUTURE_DATE
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return FUTURE_AMOUNT

async def future_date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data.startswith("date_"):
        date_str = query.data.replace("date_", "")
        op_type = context.user_data.get("future_last_command")
        amount = context.user_data.get("future_amount")

        future = load_future(user_id)
        future.append({"type": op_type, "amount": amount, "date": date_str})
        save_future(user_id, future)

        await query.edit_message_text(f"Предстоящая операция добавлена: {op_type} {amount} ₽ на {date_str}")
        return ConversationHandler.END

    elif query.data.startswith("prev_") or query.data.startswith("next_"):
        parts = query.data.split("_")
        year, month = int(parts[1]), int(parts[2])
        if query.data.startswith("prev_"):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        else:
            month += 1
            if month == 13:
                month = 1
                year += 1
        await query.edit_message_reply_markup(reply_markup=build_calendar(year, month))
        return FUTURE_DATE

# ======== Настройка приложения ========
app = ApplicationBuilder().token(API_TOKEN).build()

# Основные команды
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("📊 Баланс"), show_balance))
app.add_handler(MessageHandler(filters.Regex("📋 История"), show_history))
app.add_handler(MessageHandler(filters.Regex("🗓 Прогноз баланса"), forecast_start))

# Мгновенные операции
app.add_handler(MessageHandler(filters.Regex("➕ Добавить операцию|⏳ Добавить предстоящую операцию|🔙 Назад"), instant_operation))

# ConversationHandlers для дохода/расхода
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("➕ Добавить доход"), instant_operation)],
    states={CHOOSING_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_amount)]},
    fallbacks=[]
))
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("➖ Добавить расход"), instant_operation)],
    states={CHOOSING_EXPENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)]},
    fallbacks=[]
))

# Предстоящие операции
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("➕ Предстоящий доход|➖ Предстоящий расход"), handle_future_buttons)],
    states={
        FUTURE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, future_amount)],
        FUTURE_DATE: [CallbackQueryHandler(future_date_handler)]
    },
    fallbacks=[]
))
app.add_handler(MessageHandler(filters.Regex("📋 Список предстоящих|🔙 Назад"), handle_future_buttons))

# Прогноз
app.add_handler(MessageHandler(filters.Regex("📅 Через неделю|📅 Через месяц|📅 Через 3 месяца|🔙 Назад"), handle_forecast_buttons))

# ======== Запуск ========
app.run_polling()

import json
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode
from config import API_TOKEN

DATA_FILE = "data.json"
FUTURE_FILE = "future.json"
HISTORY_FILE = "history.json"

# ======== Работа с балансом ========
def load_balance():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        return data.get("balance", 0)
    except:
        return 0

def save_balance(balance):
    with open(DATA_FILE, "w") as f:
        json.dump({"balance": balance}, f)

# ======== Работа с историей ========
def load_history():
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        return data.get("history", [])
    except:
        return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump({"history": history}, f)

# ======== Работа с предстоящими операциями ========
def load_future():
    try:
        with open(FUTURE_FILE, "r") as f:
            data = json.load(f)
        return data.get("future", [])
    except:
        return []

def save_future(future):
    with open(FUTURE_FILE, "w") as f:
        json.dump({"future": future}, f)

# ======== Меню ========
def main_menu():
    keyboard = [
        ["📊 Баланс", "🗓 Прогноз баланса"],
        ["➕ Добавить операцию", "📋 История"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

def add_operation_menu():
    keyboard = [
        ["➖ Добавить расход", "➕ Добавить доход"],
        ["⏳ Добавить предстоящую операцию", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

def future_menu():
    keyboard = [
        ["➕ Предстоящий доход", "➖ Предстоящий расход"],
        ["📋 Список предстоящих", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

def forecast_menu():
    keyboard = [
        ["📅 Через неделю", "📅 Через месяц"],
        ["📅 Через 4 месяца", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

# ======== Состояния ========
CHOOSING_INCOME, CHOOSING_EXPENSE, FUTURE_AMOUNT_DATE = range(3)

# ======== Команды ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
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
    balance = load_balance()
    await update.message.reply_text(f"Ваш текущий баланс: {balance} ₽")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history = load_history()
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
    text = update.message.text
    now = datetime.now()

    if text == "📅 Через неделю":
        target_date = now + timedelta(weeks=1)
    elif text == "📅 Через месяц":
        target_date = now + timedelta(days=30)
    elif text == "📅 Через 4 месяца":
        target_date = now + timedelta(days=120)
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return

    balance = load_balance()
    future = load_future()
    for op in future:
        try:
            op_date = datetime.strptime(op["date"], "%Y-%m-%d")
            if op_date <= target_date:
                balance += op["amount"] if op["type"] == "доход" else -op["amount"]
        except:
            continue

    await update.message.reply_text(f"Прогнозируемый баланс на {target_date.strftime('%d.%m.%Y')}: {balance} ₽")

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
    try:
        amount = float(update.message.text)
        balance = load_balance()
        balance += amount
        save_balance(balance)
        history = load_history()
        history.append({"type": "доход", "amount": amount})
        save_history(history)
        await update.message.reply_text(f"Доход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_INCOME
    return ConversationHandler.END

async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        balance = load_balance()
        balance -= amount
        save_balance(balance)
        history = load_history()
        history.append({"type": "расход", "amount": amount})
        save_history(history)
        await update.message.reply_text(f"Расход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_EXPENSE
    return ConversationHandler.END

# ======== Предстоящие операции ========
async def handle_future_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["➕ Предстоящий доход", "➖ Предстоящий расход"]:
        context.user_data["future_last_command"] = "доход" if "доход" in text else "расход"
        await update.message.reply_text("Введите сумму и дату в формате: сумма на YYYY-MM-DD")
        return FUTURE_AMOUNT_DATE
    elif text == "📋 Список предстоящих":
        future = load_future()
        if not future:
            await update.message.reply_text("Список предстоящих операций пуст.")
        else:
            text_list = "Список предстоящих операций:\n"
            for op in future:
                text_list += f"{op['type']}: {op['amount']} ₽ на {op['date']}\n"
            await update.message.reply_text(text_list)
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в меню 'Добавить операцию'", reply_markup=add_operation_menu())
    else:
        try:
            amount_str, date_str = text.split("на")
            amount = float(amount_str.strip())
            date = date_str.strip()
            op_type = context.user_data.get("future_last_command")
            future = load_future()
            future.append({"type": op_type, "amount": amount, "date": date})
            save_future(future)
            await update.message.reply_text(f"Предстоящая операция добавлена: {op_type} {amount} ₽ на {date}")
        except Exception:
            await update.message.reply_text("Неправильный формат. Используйте: сумма на YYYY-MM-DD")

# ======== Настройка приложения ========
app = ApplicationBuilder().token(API_TOKEN).build()

# Основные команды
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("📊 Баланс"), show_balance))
app.add_handler(MessageHandler(filters.Regex("📋 История"), show_history))
app.add_handler(MessageHandler(filters.Regex("🗓 Прогноз баланса"), forecast_start))

# Мгновенные операции (только меню)
app.add_handler(MessageHandler(filters.Regex(
    "➕ Добавить операцию|⏳ Добавить предстоящую операцию|🔙 Назад"
), instant_operation))

# ConversationHandlers для мгновенного дохода/расхода
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
app.add_handler(MessageHandler(filters.Regex(
    "➕ Предстоящий доход|➖ Предстоящий расход|📋 Список предстоящих|\\d+.*|🔙 Назад"
), handle_future_buttons))

# Прогноз
app.add_handler(MessageHandler(filters.Regex(
    "📅 Через неделю|📅 Через месяц|📅 Через 4 месяца|🔙 Назад"
), handle_forecast_buttons))

# ======== Запуск ========
app.run_polling()

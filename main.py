import json
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

# ======== Состояния ========
CHOOSING_ACTION, CHOOSING_INCOME, CHOOSING_EXPENSE, FUTURE_MENU, FUTURE_AMOUNT_DATE = range(5)

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
    return CHOOSING_ACTION

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
async def forecast_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = load_balance()
    future = load_future()
    for op in future:
        if op["type"] == "доход":
            balance += op["amount"]
        elif op["type"] == "расход":
            balance -= op["amount"]
    await update.message.reply_text(f"Прогнозируемый баланс: {balance} ₽")

# ======== Мгновенные операции ========
async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        balance = load_balance() + amount
        save_balance(balance)
        history = load_history()
        history.append({"type": "доход", "amount": amount})
        save_history(history)
        await update.message.reply_text(f"Доход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_INCOME
    return CHOOSING_ACTION

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        balance = load_balance() - amount
        save_balance(balance)
        history = load_history()
        history.append({"type": "расход", "amount": amount})
        save_history(history)
        await update.message.reply_text(f"Расход добавлен. Новый баланс: {balance} ₽", reply_markup=add_operation_menu())
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_EXPENSE
    return CHOOSING_ACTION

# ======== Предстоящие операции ========
async def handle_future_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["➕ Предстоящий доход", "➖ Предстоящий расход"]:
        context.user_data["future_type"] = "доход" if "доход" in text else "расход"
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
        return FUTURE_MENU
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в меню 'Добавить операцию'", reply_markup=add_operation_menu())
        return CHOOSING_ACTION

async def add_future_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount_str, date_str = update.message.text.split("на")
        amount = float(amount_str.strip())
        date = date_str.strip()
        op_type = context.user_data.get("future_type")
        future = load_future()
        future.append({"type": op_type, "amount": amount, "date": date})
        save_future(future)
        await update.message.reply_text(f"Предстоящая операция добавлена: {op_type} {amount} ₽ на {date}", reply_markup=future_menu())
    except Exception:
        await update.message.reply_text("Неправильный формат. Используйте: сумма на YYYY-MM-DD")
    return FUTURE_MENU

# ======== Основной ConversationHandler ========
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ Добавить операцию":
        await update.message.reply_text("Меню операций:", reply_markup=add_operation_menu())
        return CHOOSING_ACTION
    elif text == "➕ Добавить доход":
        await update.message.reply_text("Введите сумму дохода:")
        return CHOOSING_INCOME
    elif text == "➖ Добавить расход":
        await update.message.reply_text("Введите сумму расхода:")
        return CHOOSING_EXPENSE
    elif text == "⏳ Добавить предстоящую операцию":
        await update.message.reply_text("Меню предстоящих операций:", reply_markup=future_menu())
        return FUTURE_MENU
    elif text == "📊 Баланс":
        await show_balance(update, context)
        return CHOOSING_ACTION
    elif text == "📋 История":
        await show_history(update, context)
        return CHOOSING_ACTION
    elif text == "🗓 Прогноз баланса":
        await forecast_balance(update, context)
        return CHOOSING_ACTION
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return CHOOSING_ACTION
    return CHOOSING_ACTION

# ======== Настройка приложения ========
app = ApplicationBuilder().token(API_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_action)],
        CHOOSING_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income)],
        CHOOSING_EXPENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense)],
        FUTURE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_future_menu)],
        FUTURE_AMOUNT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_future_operation)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)
app.run_polling()

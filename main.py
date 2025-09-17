import json
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

DATA_FILE = "data.json"
FUTURE_FILE = "future.json"

# ======== Работа с текущим балансом ========
def load_balance():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        return data.get("balance", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def save_balance(balance):
    with open(DATA_FILE, "w") as f:
        json.dump({"balance": balance}, f)

# ======== Работа с предстоящими операциями ========
def load_future_operations():
    try:
        with open(FUTURE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_future_operations(operations):
    with open(FUTURE_FILE, "w") as f:
        json.dump(operations, f, ensure_ascii=False, indent=2)

# ======== Состояния ========
CHOOSING_INCOME, CHOOSING_EXPENSE = range(2)
CHOOSING_FUTURE_INCOME, CHOOSING_FUTURE_EXPENSE = range(2, 4)

# ======== Команды ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user_name = update.effective_user.first_name
    keyboard = [
        ["💸 Добавить расход", "💰 Добавить доход"],
        ["📊 Баланс", "➕ Добавить предстоящие операции"],
        ["📋 Список операций", "📅 Прогноз баланса"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=False, resize_keyboard=True)

    await update.message.reply_text(
        f"Привет, {user_name}! 👋\n\n"
        "Смотри, что я умею:\n"
        "💸 — Добавлять расходы\n"
        "💰 — Добавлять доходы\n"
        "📊 — Показывать баланс\n"
        "➕ — Добавлять предстоящие операции\n"
        "📋 — Показывать список операций\n"
        "📅 — Делать прогноз баланса",
        reply_markup=reply_markup
    )

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = load_balance()
    await update.message.reply_text(f"Ваш текущий баланс: {balance} ₽")

# ======== Добавление доходов/расходов ========
async def add_income_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите сумму дохода:")
    return CHOOSING_INCOME

async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите сумму расхода:")
    return CHOOSING_EXPENSE

async def add_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        balance = load_balance()
        balance += amount
        save_balance(balance)
        await update.message.reply_text(f"Доход добавлен ✅ Новый баланс: {balance} ₽")
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
        await update.message.reply_text(f"Расход добавлен ✅ Новый баланс: {balance} ₽")
    except ValueError:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_EXPENSE
    return ConversationHandler.END

# ======== Предстоящие операции ========
async def future_operation_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Предстоящий доход", "Предстоящий расход"], ["Отмена"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Выберите тип предстоящей операции:\n\n"
        "Введите в формате: СУММА;НАЗВАНИЕ;ГГГГ-ММ-ДД",
        reply_markup=reply_markup
    )

async def add_future_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите доход в формате: СУММА;НАЗВАНИЕ;ГГГГ-ММ-ДД")
    return CHOOSING_FUTURE_INCOME

async def add_future_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите расход в формате: СУММА;НАЗВАНИЕ;ГГГГ-ММ-ДД")
    return CHOOSING_FUTURE_EXPENSE

async def save_future_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount, name, date_str = update.message.text.split(";")
        amount = float(amount)
        date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        operations = load_future_operations()
        operations.append({"type": "income", "amount": amount, "name": name.strip(), "date": str(date)})
        save_future_operations(operations)
        await update.message.reply_text("Предстоящий доход добавлен ✅")
    except Exception:
        await update.message.reply_text("Ошибка! Введите в формате: СУММА;НАЗВАНИЕ;ГГГГ-ММ-ДД")
        return CHOOSING_FUTURE_INCOME
    return ConversationHandler.END

async def save_future_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount, name, date_str = update.message.text.split(";")
        amount = float(amount)
        date = datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        operations = load_future_operations()
        operations.append({"type": "expense", "amount": amount, "name": name.strip(), "date": str(date)})
        save_future_operations(operations)
        await update.message.reply_text("Предстоящий расход добавлен ✅")
    except Exception:
        await update.message.reply_text("Ошибка! Введите в формате: СУММА;НАЗВАНИЕ;ГГГГ-ММ-ДД")
        return CHOOSING_FUTURE_EXPENSE
    return ConversationHandler.END

# ======== Список предстоящих операций ========
async def list_operations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    operations = load_future_operations()
    if not operations:
        await update.message.reply_text("Список операций пуст.")
        return

    msg = "📋 Список операций:\n\n"
    for op in operations:
        emoji = "💰" if op["type"] == "income" else "💸"
        msg += f"{emoji} {op['name']} — {op['amount']} ₽ (дата: {op['date']})\n"
    await update.message.reply_text(msg)

# ======== Прогноз баланса ========
async def forecast_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    balance = load_balance()
    operations = load_future_operations()
    if not operations:
        await update.message.reply_text(f"📅 Прогнозируемый баланс: {balance} ₽ (операций нет)")
        return

    forecast = balance
    for op in operations:
        if op["type"] == "income":
            forecast += op["amount"]
        else:
            forecast -= op["amount"]

    await update.message.reply_text(f"📅 Прогнозируемый баланс: {forecast} ₽")

# ======== Отмена ========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# ======== Запуск приложения ========
app = ApplicationBuilder().token("8390399537:AAH3JU0sd35q-JmPn7pHTg1Z1vCTq6kdW4Y").build()

# Команды и кнопки
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Regex("📊 Баланс"), show_balance))
app.add_handler(MessageHandler(filters.Regex("📋 Список операций"), list_operations))
app.add_handler(MessageHandler(filters.Regex("📅 Прогноз баланса"), forecast_balance))
app.add_handler(MessageHandler(filters.Regex("➕ Добавить предстоящие операции"), future_operation_start))

# ConversationHandler для доходов
income_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("💰 Добавить доход"), add_income_start)],
    states={CHOOSING_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_amount)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

expense_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("💸 Добавить расход"), add_expense_start)],
    states={CHOOSING_EXPENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

future_income_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("Предстоящий доход"), add_future_income)],
    states={CHOOSING_FUTURE_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_future_income)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

future_expense_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("Предстоящий расход"), add_future_expense)],
    states={CHOOSING_FUTURE_EXPENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_future_expense)]},
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(income_handler)
app.add_handler(expense_handler)
app.add_handler(future_income_handler)
app.add_handler(future_expense_handler)

app.run_polling()

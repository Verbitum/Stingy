import json
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode
from config import API_TOKEN

USERS_FILE = "users.json"

# ======== Работа с данными пользователей ========
def load_user_data(user_id):
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id), {"balance": 0, "history": [], "future": []})
    except FileNotFoundError:
        return {"balance": 0, "history": [], "future": []}
    except json.JSONDecodeError:
        return {"balance": 0, "history": [], "future": []}

def save_user_data(user_id, user_data):
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[str(user_id)] = user_data
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        ["📅 Через 3 месяца", "🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

# ======== Состояния ========
CHOOSING_INCOME, CHOOSING_EXPENSE, FUTURE_AMOUNT_DATE = range(3)

# ======== Хэндлеры ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = (update.effective_user.first_name or "").strip()
    welcome_text = (
        f"Привет, *{user_first_name}*! 👋\n\n"
        "Смотри, что я умею:\n\n"
        "📊 Показать текущий баланс\n"
        "🗓 Прогнозировать будущий баланс\n"
        "➕ Добавлять доходы и расходы / предстоящие операции\n"
        "📋 Смотреть историю операций\n\n"
        "*Просто нажми на нужную кнопку, чтобы начать!*"
    )
    await update.message.reply_text(welcome_text, reply_markup=main_menu(), parse_mode=ParseMode.MARKDOWN)

# Баланс и история
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = load_user_data(user_id)
    await update.message.reply_text(f"Ваш текущий баланс: {user['balance']} ₽")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = load_user_data(user_id)
    history = user.get("history", [])
    if not history:
        await update.message.reply_text("История операций пуста.")
        return
    text = "История операций:\n"
    for op in history:
        # опционально можно добавить дату/время, если нужно
        text += f"{op['type']}: {op['amount']} ₽\n"
    await update.message.reply_text(text)

# Прогноз
async def forecast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите период прогноза:", reply_markup=forecast_menu())

async def handle_forecast_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    now = datetime.now()
    user_id = update.effective_user.id
    user = load_user_data(user_id)

    if text == "📅 Через неделю":
        target_date = now + timedelta(weeks=1)
    elif text == "📅 Через месяц":
        target_date = now + timedelta(days=30)
    elif text == "📅 Через 3 месяца":
        # можно заменить на точное прибавление 3 календарных месяцев через dateutil.relativedelta
        target_date = now + timedelta(days=90)
    elif text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return
    else:
        return  # не наша кнопка — игнорируем

    balance = user.get("balance", 0)
    future_ops = user.get("future", [])

    # Учитываем только валидные будущие операции с корректной датой
    for op in future_ops:
        try:
            op_date = datetime.strptime(op["date"], "%Y-%m-%d")
        except Exception:
            # пропускаем некорректную дату
            continue
        if op_date <= target_date:
            if op["type"] == "доход":
                balance += op["amount"]
            else:
                balance -= op["amount"]

    await update.message.reply_text(f"Прогнозируемый баланс на {target_date.strftime('%d.%m.%Y')}: {balance} ₽")

# Мгновенные операции — показываем подменю или запрашиваем сумму
async def instant_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "➕ Добавить операцию":
        await update.message.reply_text("Выберите действие:", reply_markup=add_operation_menu())
        return ConversationHandler.END

    if text == "➕ Добавить доход":
        await update.message.reply_text("Введите сумму дохода:")
        return CHOOSING_INCOME

    if text == "➖ Добавить расход":
        await update.message.reply_text("Введите сумму расхода:")
        return CHOOSING_EXPENSE

    if text == "⏳ Добавить предстоящую операцию":
        await update.message.reply_text("Меню предстоящих операций:", reply_markup=future_menu())
        return ConversationHandler.END

    if text == "🔙 Назад":
        await update.message.reply_text("Возврат в главное меню", reply_markup=main_menu())
        return ConversationHandler.END

# Добавление мгновенного дохода/расхода
async def add_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = load_user_data(user_id)
    text = update.message.text
    try:
        amount = float(text)
    except Exception:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_INCOME

    user["balance"] += amount
    user.setdefault("history", []).append({"type": "доход", "amount": amount, "ts": datetime.now().isoformat()})
    save_user_data(user_id, user)

    await update.message.reply_text(f"Доход добавлен. Новый баланс: {user['balance']} ₽", reply_markup=add_operation_menu())
    return ConversationHandler.END

async def add_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = load_user_data(user_id)
    text = update.message.text
    try:
        amount = float(text)
    except Exception:
        await update.message.reply_text("Введите корректное число.")
        return CHOOSING_EXPENSE

    user["balance"] -= amount
    user.setdefault("history", []).append({"type": "расход", "amount": amount, "ts": datetime.now().isoformat()})
    save_user_data(user_id, user)

    await update.message.reply_text(f"Расход добавлен. Новый баланс: {user['balance']} ₽", reply_markup=add_operation_menu())
    return ConversationHandler.END

# Предстоящие операции (теперь привязаны к пользователю)
async def handle_future_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user = load_user_data(user_id)

    if text in ["➕ Предстоящий доход", "➖ Предстоящий расход"]:
        # сохраняем тип в session для последующего ввода "сумма на дата"
        context.user_data["future_last_command"] = "доход" if "доход" in text else "расход"
        await update.message.reply_text("Введите сумму и дату в формате: сумма на YYYY-MM-DD (например: 1000 на 2025-10-01)")
        return FUTURE_AMOUNT_DATE

    if text == "📋 Список предстоящих":
        future = user.get("future", [])
        if not future:
            await update.message.reply_text("Список предстоящих операций пуст.")
            return
        text_list = "Список предстоящих операций:\n"
        for op in future:
            text_list += f"{op['type']}: {op['amount']} ₽ на {op['date']}\n"
        await update.message.reply_text(text_list)
        return

    if text == "🔙 Назад":
        await update.message.reply_text("Возврат в меню 'Добавить операцию'", reply_markup=add_operation_menu())
        return

    # Если сюда попали — возможно пользователь ввёл строку "сумма на YYYY-MM-DD"
    if "на" in text:
        try:
            amount_str, date_str = text.split("на", 1)
            amount = float(amount_str.strip())
            date = date_str.strip()
            # проверим формат даты
            datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            await update.message.reply_text("Неправильный формат. Используйте: сумма на YYYY-MM-DD (например: 1000 на 2025-10-01)")
            return

        op_type = context.user_data.get("future_last_command")
        if op_type is None:
            await update.message.reply_text("Сначала выберите тип операции (предстоящий доход или расход).")
            return

        user.setdefault("future", []).append({"type": op_type, "amount": amount, "date": date})
        save_user_data(user_id, user)
        await update.message.reply_text(f"Предстоящая операция добавлена: {op_type} {amount} ₽ на {date}", reply_markup=future_menu())
        return

    # Другие сообщения игнорируем
    return

# ======== Регистрация хэндлеров и запуск ========
app = ApplicationBuilder().token(API_TOKEN).build()

# Основные команды
app.add_handler(CommandHandler("start", start))

# ВАЖНО: регистрируем хэндлер прогнозов раньше хэндлера будущих операций,
# чтобы кнопки "📅 ..." не перехватывались обработчиком будущих операций.
app.add_handler(MessageHandler(filters.Regex(r"^📅 Через неделю$|^📅 Через месяц$|^📅 Через 3 месяца$|^🔙 Назад$"), handle_forecast_buttons))
app.add_handler(MessageHandler(filters.Regex("^🗓 Прогноз баланса$"), forecast_start))

# Основные кнопки / меню
app.add_handler(MessageHandler(filters.Regex("^📊 Баланс$"), show_balance))
app.add_handler(MessageHandler(filters.Regex("^📋 История$"), show_history))
app.add_handler(MessageHandler(filters.Regex("^➕ Добавить операцию$"), instant_operation))
app.add_handler(MessageHandler(filters.Regex("^⏳ Добавить предстоящую операцию$|^🔙 Назад$"), instant_operation))

# ConversationHandlers для мгновенных операций (вход — нажатие кнопки, затем ввод суммы)
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➕ Добавить доход$"), instant_operation)],
    states={CHOOSING_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_income_amount)]},
    fallbacks=[]
))
app.add_handler(ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^➖ Добавить расход$"), instant_operation)],
    states={CHOOSING_EXPENSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense_amount)]},
    fallbacks=[]
))

# Предстоящие операции: ловим кнопки и строки формата "сумма на дата"
# Добавляем негативную проверку на начало с "📅", но поскольку прогнозные хэндлеры зарегистрированы раньше — это дополнительная страховка.
future_pattern = r"^(➕ Предстоящий доход|➖ Предстоящий расход|📋 Список предстоящих|🔙 Назад|.*\bна\b.*)$"
app.add_handler(MessageHandler(filters.Regex(future_pattern), handle_future_buttons))

# Запуск
app.run_polling()

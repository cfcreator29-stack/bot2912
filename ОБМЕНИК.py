import telebot
from telebot import types
import sqlite3
from datetime import datetime

# токен бота
bot = telebot.TeleBot('8256987630:AAH5EHUrGxlY6TObhkDnZDkGCmeqX5fg3qw')

# ID админов
ADMINS = [8535260202]

conn = sqlite3.connect('exchange_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS exchanges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    direction TEXT,
    amount_from REAL,
    amount_to REAL,
    user_requisites TEXT,
    status TEXT DEFAULT 'в обработке',
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS directions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_currency TEXT,
    to_currency TEXT,
    rate REAL,
    commission REAL DEFAULT 0,
    min_amount REAL,
    reserve REAL,
    is_active BOOLEAN DEFAULT TRUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS direction_credentials(
    direction_id INTEGER,
    credentials TEXT,
    FOREIGN KEY (direction_id) REFERENCES directions (id),
    PRIMARY KEY (direction_id)
)
''')

directions_to_add = [
    ('М Банк', 'Payeer', 1.0, 2.0, 100, 50000),
    ('O!Деньги', 'Payeer', 0.5, 50.0, 50, 30000),
    ('Payeer', 'М Банк', 0.98, 2.0, 100, 40000),
    ('Касспи', 'Payeer', 1.01, 1.5, 500, 30000)
]

for from_cur, to_cur, rate, commission, min_amount, reserve in directions_to_add:
    cursor.execute("SELECT COUNT(*) FROM directions WHERE from_currency = ? AND to_currency = ?", (from_cur, to_cur))
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO directions (from_currency, to_currency, rate, commission, min_amount, reserve) VALUES (?, ?, ?, ?, ?, ?)",
            (from_cur, to_cur, rate, commission, min_amount, reserve)
        )

cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('chat_link', 'https://t.me/xogeman')")
conn.commit()

user_states = {}
admin_states = {}


def get_user_main_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('💱 Обмен')
    btn2 = types.KeyboardButton('📖 История')
    btn3 = types.KeyboardButton('ℹ️ Информация')
    markup.add(btn1, btn2, btn3)
    return markup


def get_admin_main_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('💱 Обмен')
    btn2 = types.KeyboardButton('📖 История')
    btn3 = types.KeyboardButton('ℹ️ Информация')
    btn4 = types.KeyboardButton('👨‍💻 Админ Панель')
    markup.add(btn1, btn2, btn3, btn4)
    return markup


def get_admin_panel_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📢 Рассылка')
    btn2 = types.KeyboardButton('➕ Добавить Направление')
    btn3 = types.KeyboardButton('➖ Удалить Направление')
    btn4 = types.KeyboardButton('🏦 Реквизиты')
    btn5 = types.KeyboardButton('🔗 Изменить Ссылку')
    btn6 = types.KeyboardButton('📊 Комиссия')
    btn7 = types.KeyboardButton('📋 Заявки')
    btn8 = types.KeyboardButton('📊 Статистика')
    btn9 = types.KeyboardButton('◶️ Назад')
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5, btn6)
    markup.row(btn7, btn8)
    markup.add(btn9)
    return markup


def get_directions_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    cursor.execute("SELECT id, from_currency, to_currency FROM directions WHERE is_active = TRUE")
    directions = cursor.fetchall()
    for dir_id, from_cur, to_cur in directions:
        btn = types.InlineKeyboardButton(f"{from_cur} → {to_cur}", callback_data=f"dir_{dir_id}")
        markup.add(btn)
    return markup


def get_directions_for_remove_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    cursor.execute("SELECT id, from_currency, to_currency FROM directions WHERE is_active = TRUE")
    directions = cursor.fetchall()
    for dir_id, from_cur, to_cur in directions:
        btn = types.InlineKeyboardButton(f"{from_cur} → {to_cur}", callback_data=f"remove_dir_{dir_id}")
        markup.add(btn)
    return markup


def get_directions_for_commission_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    cursor.execute("SELECT id, from_currency, to_currency FROM directions WHERE is_active = TRUE")
    directions = cursor.fetchall()
    for dir_id, from_cur, to_cur in directions:
        btn = types.InlineKeyboardButton(f"{from_cur} → {to_cur}", callback_data=f"com_dir_{dir_id}")
        markup.add(btn)
    return markup


def get_directions_for_credentials_kb():
    markup = types.InlineKeyboardMarkup(row_width=2)
    cursor.execute("SELECT id, from_currency, to_currency FROM directions WHERE is_active = TRUE")
    directions = cursor.fetchall()
    for dir_id, from_cur, to_cur in directions:
        btn = types.InlineKeyboardButton(f"{from_cur} → {to_cur}", callback_data=f"cred_dir_{dir_id}")
        markup.add(btn)
    return markup


def get_payment_confirmation_kb(user_id):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("💳 Оплатил", callback_data=f"confirm_payment_{user_id}")
    markup.add(btn)
    return markup


def get_back_to_menu_kb(is_admin=False):
    if is_admin:
        return get_admin_main_kb()
    else:
        return get_user_main_kb()


def get_order_approval_kb(order_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Одобрить", callback_data=f"admin_approve_{order_id}")
    btn2 = types.InlineKeyboardButton("❌ Отменить", callback_data=f"admin_reject_{order_id}")
    markup.add(btn1, btn2)
    return markup


def get_approved_kb():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("✅ Одобрено", callback_data="no_action")
    markup.add(btn)
    return markup


def get_rejected_kb():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("❌ Отменено", callback_data="no_action")
    markup.add(btn)
    return markup


@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.first_name
    if message.from_user.last_name:
        full_name += " " + message.from_user.last_name

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)",
                       (user_id, username, full_name))
        conn.commit()

    if user_id in user_states:
        del user_states[user_id]
    if user_id in admin_states:
        del admin_states[user_id]

    is_admin = user_id in ADMINS
    markup = get_admin_main_kb() if is_admin else get_user_main_kb()

    text = f"""👋 <b>Добро пожаловать, {full_name}!</b>

🚀 <i>Я — современный и надежный бот для обмена валют.</i>

💎 <b>Выберите действие:</b>"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == '💱 Обмен')
def process_exchange(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    text = """💎<b>Выберите направление обмена:</b>

⬇️ <i>Все доступные варианты представлены ниже.</i>"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_directions_kb())


@bot.message_handler(func=lambda message: message.text == '📖 История')
def process_history(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    user_id = message.from_user.id

    cursor.execute('''
    SELECT direction, amount_from, amount_to, status FROM exchanges WHERE user_id = ? ORDER BY date DESC LIMIT 5
    ''', (user_id,))
    history = cursor.fetchall()

    text = "<b>📖 Ваша история обменов (последние 5):</b>\n\n"
    if history:
        for i, (direction, am_from, am_to, status) in enumerate(history, 1):
            text += f"<b>{i}. {direction}</b>\nСумма: <code>{am_from} → {am_to}</code>\nСтатус: <b>{status}</b>\n\n"
    else:
        text += "❌ <b>История пуста</b>"
    bot.send_message(message.chat.id, text, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == 'ℹ️ Информация')
def process_info(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    cursor.execute("SELECT value FROM settings WHERE key = 'chat_link'")
    chat_link_row = cursor.fetchone()
    chat_link = chat_link_row[0] if chat_link_row else "https://t.me/xogeman"

    info_text = f"""🤖 <b>Информация о нашем сервисе</b>

💠 <b>Мы предлагаем:</b>
•Быстрый и безопасный обмен 🔒
•Конкурентные курсы 📊
•Поддержку 24/7 👨‍💻

⏱ <b>Время обработки заявок:</b>
•Обычно до 15 минут ⏰
•В пиковые часы — до 1 часа 🕐

👥 <b>Техническая поддержка:</b>
•Задать вопрос: {chat_link}

<i>Мы ценим каждого клиента!</i> 💎"""
    bot.send_message(message.chat.id, info_text, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '👨‍💻 Админ Панель' and message.from_user.id in ADMINS)
def admin_panel(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    text = """👨‍💻<b>Админ Панель</b>
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_admin_panel_kb())


@bot.message_handler(func=lambda message: message.text == '◶️ Назад' and message.from_user.id in ADMINS)
def back_to_main(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    bot.send_message(message.chat.id, "🔙 <b>Возврат в главное меню</b>", parse_mode='HTML',
                     reply_markup=get_admin_main_kb())


@bot.message_handler(func=lambda message: message.text == '📋 Заявки' and message.from_user.id in ADMINS)
def orders_management(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]

    cursor.execute("SELECT COUNT(*) FROM exchanges WHERE status = 'в обработке'")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exchanges")
    total_count = cursor.fetchone()[0]

    text = f"""📋 <b>Управление заявками</b>

📊 <b>Статистика:</b>
•Всего заявок: <b>{total_count}</b>
•Ожидают обработки: <b>{pending_count}</b>
"""

    bot.send_message(message.chat.id, text, parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📊 Статистика' and message.from_user.id in ADMINS)
def show_statistics(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM exchanges")
    total_exchanges = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount_from) FROM exchanges WHERE status = 'выполнено'")
    total_amount = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM exchanges WHERE status = 'в обработке'")
    pending_orders = cursor.fetchone()[0]

    text = f"""📊 <b>Общая статистика</b>

👥 <b>Всего пользователей:</b> {total_users}
💱 <b>Всего обменов:</b> {total_exchanges}
⏳ <b>Ожидают обработки:</b> {pending_orders}
💰 <b>Общая сумма обмена (выполнено):</b> {total_amount:.2f}"""

    bot.send_message(message.chat.id, text, parse_mode='HTML')


@bot.callback_query_handler(func=lambda call: call.data.startswith('dir_'))
def process_direction_selection(call):
    if call.from_user.id in user_states:
        del user_states[call.from_user.id]
    if call.from_user.id in admin_states:
        del admin_states[call.from_user.id]

    direction_id = call.data.split('_')[1]

    cursor.execute(
        "SELECT from_currency, to_currency, rate, commission, min_amount, reserve FROM directions WHERE id = ?",
        (direction_id,))
    from_cur, to_cur, rate, commission, min_amount, reserve = cursor.fetchone()

    final_rate = rate * (1 - commission / 100)

    text = f"""💱 <b>Направление: {from_cur} → {to_cur}</b>

📊 <b>Курс:</b> 1 {from_cur} = {final_rate:.2f} {to_cur}
💸<b>Комиссия:</b> {commission}%
💰<b>Минимальная сумма:</b> {min_amount} {from_cur}
🏦<b>Резерв:</b> {reserve} {to_cur}

💵 <b>Введите сумму в {from_cur}, которую хотите обменять:</b>"""

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    user_states[call.from_user.id] = {'direction_id': direction_id, 'waiting_for_amount': True}


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_payment_'))
def confirm_payment_callback(call):
    user_id = call.from_user.id
    if user_id not in user_states:
        bot.edit_message_text("❌ <b>Данные для заявки не найдены. Пожалуйста, начните обмен заново.</b>",
                              call.message.chat.id, call.message.message_id, parse_mode='HTML')
        return

    user_data = user_states[user_id]
    direction_id = user_data.get('direction_id')
    amount = user_data.get('amount')
    user_requisites = user_data.get('user_requisites')

    if not direction_id or not amount or not user_requisites:
        bot.edit_message_text("❌ <b>Неполные данные для заявки. Пожалуйста, начните обмен заново.</b>",
                              call.message.chat.id, call.message.message_id, parse_mode='HTML')
        return

    user_states[user_id]['waiting_for_receipt'] = True
    bot.edit_message_text("📎 <b>Пожалуйста, отправьте фото чека или подтверждения оплаты.</b>", call.message.chat.id,
                          call.message.message_id, parse_mode='HTML')


@bot.message_handler(content_types=['photo'],
                     func=lambda message: user_states.get(message.from_user.id, {}).get('waiting_for_receipt'))
def process_receipt(message):
    user_id = message.from_user.id
    user_data = user_states.get(user_id, {})
    direction_id = user_data.get('direction_id')
    amount = user_data.get('amount')
    user_requisites = user_data.get('user_requisites')

    if not direction_id or not amount or not user_requisites:
        bot.send_message(message.chat.id, "❌ <b>Неполные данные для заявки. Пожалуйста, начните обмен заново.</b>",
                         parse_mode='HTML')
        del user_states[user_id]
        return

    cursor.execute("SELECT from_currency, to_currency, rate, commission FROM directions WHERE id = ?", (direction_id,))
    from_cur, to_cur, rate, commission = cursor.fetchone()

    cursor.execute("SELECT credentials FROM direction_credentials WHERE direction_id = ?", (direction_id,))
    credentials_row = cursor.fetchone()
    credentials = credentials_row[0] if credentials_row else "Реквизиты для этого направления не указаны"

    amount_to = amount * rate * (1 - commission / 100)
    direction = f"{from_cur} → {to_cur}"

    cursor.execute(
        "INSERT INTO exchanges (user_id, direction, amount_from, amount_to, user_requisites) VALUES (?, ?, ?, ?, ?)",
        (user_id, direction, amount, amount_to, user_requisites))
    conn.commit()
    order_id = cursor.lastrowid

    user_text = f"""✅ <b>Заявка #{order_id} создана!</b>

💱 <b>Направление:</b> {from_cur} → {to_cur}
💵 <b>Сумма к отправке:</b> {amount:.2f} {from_cur}
💰 <b>Сумма к получению:</b> {amount_to:.2f} {to_cur}
💸 <b>Комиссия:</b> {commission}%
🏦 <b>Ваши реквизиты:</b> {user_requisites}
🏦 <b>Реквизиты для оплаты:</b>
<blockquote><code>{credentials}</code></blockquote>
⏳ <b>Статус:</b> в обработке
📌 <b>Ожидайте обработки заявки администратором.</b>"""

    bot.send_message(message.chat.id, user_text, parse_mode='HTML')

    cursor.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
    full_name = cursor.fetchone()[0]
    username = f"@{message.from_user.username}" if message.from_user.username else "нет"

    admin_text = f"""# GROM

👤 <b>Пользователь:</b> {full_name} ({username})
🆔 <b>ID:</b> {user_id}
💱 <b>Направление:</b> {direction}
💵 <b>Сумма:</b> {amount:.2f} {from_cur} → {amount_to:.2f} {to_cur}
🏦 <b>Реквизиты:</b> {user_requisites}
💸 <b>Комиссия:</b> {commission}%"""

    for admin_id in ADMINS:
        try:

            bot.send_photo(
                admin_id,
                message.photo[-1].file_id,
                caption=admin_text,
                parse_mode='HTML',
                reply_markup=get_order_approval_kb(order_id)
            )
        except Exception as e:
            print(f"Ошибка отправки фото админу: {e}")

            bot.send_message(
                admin_id,
                admin_text + "\n\n📸 <b>Фото чека приложено</b>",
                parse_mode='HTML',
                reply_markup=get_order_approval_kb(order_id)
            )

    del user_states[user_id]


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_approve_'))
def admin_approve_order(call):
    order_id = call.data.split('_')[2]

    cursor.execute("UPDATE exchanges SET status = 'выполнено' WHERE id = ?", (order_id,))
    conn.commit()

    cursor.execute('''
    SELECT e.user_id, e.direction, e.amount_from, e.amount_to, u.full_name 
    FROM exchanges e 
    JOIN users u ON e.user_id = u.id 
    WHERE e.id = ?
    ''', (order_id,))
    order_info = cursor.fetchone()

    if order_info:
        user_id, direction, amount_from, amount_to, full_name = order_info

        user_text = f"""✅ <b>Ваша заявка #{order_id} выполнена!</b>

💱 <b>Направление:</b> {direction}
💵 <b>Сумма:</b> {amount_from} → {amount_to}
💰 <b>Статус:</b> выполнено

🙏 <b>Пожалуйста, оставьте отзыв в нашем чате: @ccылка</b>
Ваше мнение очень важно для нас! 💎"""

        try:
            bot.send_message(user_id, user_text, parse_mode='HTML')
        except:
            pass

    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n✅ <b>ОДОБРЕНО</b>",
            parse_mode='HTML',
            reply_markup=get_approved_kb()
        )
    except:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n✅ <b>ОДОБРЕНО</b>",
            parse_mode='HTML',
            reply_markup=get_approved_kb()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_reject_'))
def admin_reject_order(call):
    order_id = call.data.split('_')[2]

    cursor.execute("UPDATE exchanges SET status = 'отклонено' WHERE id = ?", (order_id,))
    conn.commit()

    cursor.execute('''
    SELECT e.user_id, e.direction, e.amount_from, e.amount_to, u.full_name 
    FROM exchanges e 
    JOIN users u ON e.user_id = u.id 
    WHERE e.id = ?
    ''', (order_id,))
    order_info = cursor.fetchone()

    if order_info:
        user_id, direction, amount_from, amount_to, full_name = order_info

        user_text = f"""❌ <b>Ваша заявка #{order_id} отклонена</b>

💱 <b>Направление:</b> {direction}
💵 <b>Сумма:</b> {amount_from} → {amount_to}
💰 <b>Статус:</b> отклонено

📞 <b>По вопросам обращайтесь в поддержку: @ссылка</b>"""

        try:
            bot.send_message(user_id, user_text, parse_mode='HTML')
        except:
            pass

    try:
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n❌ <b>ОТМЕНЕНО</b>",
            parse_mode='HTML',
            reply_markup=get_rejected_kb()
        )
    except:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n❌ <b>ОТМЕНЕНО</b>",
            parse_mode='HTML',
            reply_markup=get_rejected_kb()
        )


@bot.callback_query_handler(func=lambda call: call.data == 'no_action')
def no_action(call):
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('waiting_for_amount'))
def process_amount(message):
    user_id = message.from_user.id
    user_data = user_states.get(user_id, {})
    direction_id = user_data.get('direction_id')

    if not direction_id:
        return

    try:
        amount = float(message.text.replace(',', '.'))
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Неверный формат суммы. Введите число.</b>", parse_mode='HTML')
        return

    cursor.execute(
        "SELECT from_currency, to_currency, rate, commission, min_amount, reserve FROM directions WHERE id = ?",
        (direction_id,))
    from_cur, to_cur, rate, commission, min_amount, reserve = cursor.fetchone()

    if amount < min_amount:
        bot.send_message(message.chat.id, f"❌ <b>Сумма меньше минимальной ({min_amount} {from_cur}).</b>",
                         parse_mode='HTML')
        return

    if amount * rate * (1 - commission / 100) > reserve:
        bot.send_message(message.chat.id, f"❌ <b>Недостаточно резерва ({reserve} {to_cur}).</b>", parse_mode='HTML')
        return

    user_states[user_id] = {'direction_id': direction_id, 'amount': amount, 'waiting_for_requisites': True}
    bot.send_message(message.chat.id, f"🏦 <b>Введите ваши реквизиты для получения {to_cur}:</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('waiting_for_requisites'))
def process_requisites(message):
    user_id = message.from_user.id
    user_data = user_states.get(user_id, {})
    direction_id = user_data.get('direction_id')
    amount = user_data.get('amount')

    if not direction_id or not amount:
        return

    user_requisites = message.text

    cursor.execute("SELECT from_currency, to_currency, rate, commission FROM directions WHERE id = ?", (direction_id,))
    from_cur, to_cur, rate, commission = cursor.fetchone()

    cursor.execute("SELECT credentials FROM direction_credentials WHERE direction_id = ?", (direction_id,))
    credentials_row = cursor.fetchone()
    credentials = credentials_row[0] if credentials_row else "Реквизиты для этого направления не указаны"

    amount_to = amount * rate * (1 - commission / 100)

    user_states[user_id] = {
        'direction_id': direction_id,
        'amount': amount,
        'user_requisites': user_requisites,
        'from_cur': from_cur,
        'to_cur': to_cur,
        'amount_to': amount_to,
        'commission': commission,
        'credentials': credentials
    }

    text = f"""✅ <b>Данные для обмена:</b>

💱 <b>Направление:</b> {from_cur} → {to_cur}
💵 <b>Сумма к отправке:</b> {amount:.2f} {from_cur}
💰 <b>Сумма к получению:</b> {amount_to:.2f} {to_cur}
💸 <b>Комиссия:</b> {commission}%
🏦 <b>Ваши реквизиты:</b> {user_requisites}
🏦 <b>Реквизиты для оплаты:</b>
<blockquote><code>{credentials}</code></blockquote>
📌 <b>После оплаты нажмите кнопку ниже для подтверждения.</b>"""

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_payment_confirmation_kb(user_id))


@bot.message_handler(func=lambda message: message.text == '📢 Рассылка' and message.from_user.id in ADMINS)
def start_broadcast(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    msg = bot.send_message(message.chat.id, "✍️ <b>Введите сообщение для рассылки:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_broadcast)


def process_broadcast(message):
    if message.text:
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()
        for (user_id,) in users:
            try:
                bot.send_message(user_id, message.text, parse_mode='HTML')
            except:
                pass
        bot.send_message(message.chat.id, "✅ <b>Рассылка завершена!</b>", parse_mode='HTML',
                         reply_markup=get_admin_panel_kb())


@bot.message_handler(func=lambda message: message.text == '➕ Добавить Направление' and message.from_user.id in ADMINS)
def add_direction(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    msg = bot.send_message(message.chat.id,
                           "📥 <b>Добавление нового направления:</b>\n\nВведите данные в формате:\n<code>Из_валюты В_валюту Курс Комиссия% Мин_сумма Резерв</code>\n\n<b>Пример:</b>\n<code>Касспи Payeer 1.0 1.5 500 30000</code>",
                           parse_mode='HTML')
    bot.register_next_step_handler(msg, process_new_direction)


def process_new_direction(message):
    try:
        parts = message.text.split()
        if len(parts) != 6:
            raise ValueError
        from_cur, to_cur, rate, commission, min_amount, reserve = parts[0], parts[1], float(parts[2]), float(
            parts[3]), float(parts[4]), float(parts[5])
        cursor.execute(
            "INSERT INTO directions (from_currency, to_currency, rate, commission, min_amount, reserve) VALUES (?, ?, ?, ?, ?, ?)",
            (from_cur, to_cur, rate, commission, min_amount, reserve))
        conn.commit()
        bot.send_message(message.chat.id, "✅ <b>Направление добавлено!</b>", parse_mode='HTML',
                         reply_markup=get_admin_panel_kb())
    except:
        bot.send_message(message.chat.id, "❌ <b>Неверный формат. Попробуйте снова.</b>", parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '➖ Удалить Направление' and message.from_user.id in ADMINS)
def remove_direction(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    bot.send_message(message.chat.id, "🗑️ <b>Выберите направление для удаления:</b>", parse_mode='HTML',
                     reply_markup=get_directions_for_remove_kb())


@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_dir_'))
def process_remove_direction(call):
    direction_id = call.data.split('_')[2]
    cursor.execute("UPDATE directions SET is_active = FALSE WHERE id = ?", (direction_id,))
    cursor.execute("DELETE FROM direction_credentials WHERE direction_id = ?", (direction_id,))
    conn.commit()
    bot.edit_message_text("✅ <b>Направление удалено!</b>", call.message.chat.id, call.message.message_id,
                          parse_mode='HTML')


@bot.message_handler(func=lambda message: message.text == '📊 Комиссия' and message.from_user.id in ADMINS)
def set_commission(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    bot.send_message(message.chat.id, "📊 <b>Выберите направление для изменения комиссии:</b>", parse_mode='HTML',
                     reply_markup=get_directions_for_commission_kb())


@bot.callback_query_handler(func=lambda call: call.data.startswith('com_dir_'))
def process_commission_selection(call):
    direction_id = call.data.split('_')[2]
    cursor.execute("SELECT from_currency, to_currency FROM directions WHERE id = ?", (direction_id,))
    from_cur, to_cur = cursor.fetchone()
    text = f"📊 <b>Текущее направление: {from_cur} → {to_cur}</b>\n\n✏️ <b>Введите новую комиссию (%):</b>"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    admin_states[call.from_user.id] = {'direction_id': direction_id, 'from_cur': from_cur, 'to_cur': to_cur}
    bot.register_next_step_handler(call.message, lambda m: process_new_commission(m, direction_id, from_cur, to_cur))


def process_new_commission(message, direction_id, from_cur, to_cur):
    try:
        new_commission = float(message.text.replace(',', '.'))
        cursor.execute("UPDATE directions SET commission = ? WHERE id = ?", (new_commission, direction_id))
        conn.commit()
        bot.send_message(message.chat.id,
                         f"✅ <b>Комиссия для {from_cur} → {to_cur} обновлена на {new_commission}%!</b>",
                         parse_mode='HTML', reply_markup=get_admin_panel_kb())
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Неверный формат. Введите число.</b>", parse_mode='HTML')
    finally:
        if message.from_user.id in admin_states:
            del admin_states[message.from_user.id]


@bot.message_handler(func=lambda message: message.text == '🔗 Изменить Ссылку' and message.from_user.id in ADMINS)
def change_chat_link(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    msg = bot.send_message(message.chat.id, "🔗 <b>Введите новую ссылку на чат:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, process_chat_link)


def process_chat_link(message):
    if message.text:
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'chat_link'", (message.text,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ <b>Ссылка на чат успешно обновлена!</b>", parse_mode='HTML',
                         reply_markup=get_admin_panel_kb())


@bot.message_handler(func=lambda message: message.text == '🏦 Реквизиты' and message.from_user.id in ADMINS)
def manage_credentials(message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]
    bot.send_message(message.chat.id, "🏦 <b>Выберите направление для изменения реквизитов:</b>", parse_mode='HTML',
                     reply_markup=get_directions_for_credentials_kb())


@bot.callback_query_handler(func=lambda call: call.data.startswith('cred_dir_'))
def process_credentials_selection(call):
    direction_id = call.data.split('_')[2]
    cursor.execute("SELECT from_currency, to_currency FROM directions WHERE id = ?", (direction_id,))
    from_cur, to_cur = cursor.fetchone()
    cursor.execute("SELECT credentials FROM direction_credentials WHERE direction_id = ?", (direction_id,))
    current_creds_row = cursor.fetchone()
    current_creds = current_creds_row[0] if current_creds_row else "Реквизиты не указаны"

    text = f"""🏦 <b>Текущее направление: {from_cur} → {to_cur}</b>
🏦 <b>Текущие реквизиты:</b>
<blockquote><code>{current_creds}</code></blockquote>

✏️ <b>Введите новые реквизиты:</b>"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
    admin_states[call.from_user.id] = {'direction_id': direction_id, 'from_cur': from_cur, 'to_cur': to_cur}
    bot.register_next_step_handler(call.message, lambda m: process_new_credentials(m, direction_id, from_cur, to_cur))


def process_new_credentials(message, direction_id, from_cur, to_cur):
    if message.text:
        cursor.execute("INSERT OR REPLACE INTO direction_credentials (direction_id, credentials) VALUES (?, ?)",
                       (direction_id, message.text))
        conn.commit()
        bot.send_message(message.chat.id,
                         f"✅ <b>Реквизиты для {from_cur} → {to_cur} успешно обновлены!</b>\n\n<blockquote><code>{message.text}</code></blockquote>",
                         parse_mode='HTML', reply_markup=get_admin_panel_kb())
    if message.from_user.id in admin_states:
        del admin_states[message.from_user.id]


if __name__ == '__main__':
    print("🤖 Бот запущен...")
    bot.infinity_polling()
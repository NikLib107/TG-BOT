import sqlite3
import logging
import config
import csv
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
import asyncio

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Шляхи до файлів
DATA_FILE = Path("shoes_data.csv")
DB_FILE = Path("shoes.db")

# Визначення станів
class UserInfo(StatesGroup):
    name = State()
    want_to_buy = State()
    size = State()
    style = State()
    shoe_type = State()
    confirm_order = State()
    more_shopping = State()

# Ініціалізація бази даних
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            size INTEGER NOT NULL,
            style TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            UNIQUE(brand, size, style, type)
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM shoes")
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_data = [
            ("Nike Air Max", 42, "sport", "sneakers", 3499),
            ("Adidas Ultraboost", 41, "sport", "sneakers", 3999),
            ("Puma RS-X", 40, "casual", "sneakers", 2799),
            ("Reebok Classic", 43, "casual", "sneakers", 2599),
            ("Ecco Soft 7", 44, "formal", "shoes", 4599),
            ("Geox Uomo", 42, "formal", "shoes", 3899),
            ("Timberland Premium", 45, "outdoor", "boots", 5999),
            ("Columbia Newton Ridge", 41, "outdoor", "boots", 4299),
            ("New Balance 574", 39, "casual", "sneakers", 3199),
            ("Skechers Go Walk", 40, "casual", "shoes", 2499),
            ("Clarks Desert Boot", 42, "formal", "boots", 3799),
            ("Salomon XA Pro", 43, "sport", "boots", 4999),
            ("Vans Old Skool", 38, "casual", "sneakers", 2299),
            ("Dr. Martens 1460", 44, "formal", "boots", 5499),
            ("Asics Gel-Kayano", 42, "sport", "sneakers", 4799)
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO shoes (brand, size, style, type, price)
            VALUES (?, ?, ?, ?, ?)
        """, sample_data)
        conn.commit()
        logging.info(f"Додано {len(sample_data)} записів до бази даних")
    
    conn.close()

init_db()

# Клавіатури для вибору
def get_base_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="↩️ На попередній крок"), KeyboardButton(text="🏠 На початок")]
        ],
        resize_keyboard=True
    )

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Так"), KeyboardButton(text="Ні")],
            [KeyboardButton(text="↩️ На попередній крок"), KeyboardButton(text="🏠 На початок")]
        ],
        resize_keyboard=True
    )

def get_style_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="sport"), KeyboardButton(text="casual")],
            [KeyboardButton(text="formal"), KeyboardButton(text="outdoor")],
            [KeyboardButton(text="↩️ На попередній крок"), KeyboardButton(text="🏠 На початок")]
        ],
        resize_keyboard=True
    )

def get_type_keyboard(style: str):
    if style == "sport":
        types = ["sneakers", "boots"]
    elif style == "casual":
        types = ["sneakers", "shoes"]
    elif style == "formal":
        types = ["shoes", "boots"]
    else:  # outdoor
        types = ["boots"]
    
    keyboard = []
    row = []
    for t in types:
        row.append(KeyboardButton(text=t))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([KeyboardButton(text="↩️ На попередній крок"), KeyboardButton(text="🏠 На початок")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Підтвердити замовлення", callback_data="confirm")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")]
    ])

# Отримання доступних розмірів з бази
def get_available_sizes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT size FROM shoes ORDER BY size")
    sizes = [str(size[0]) for size in cursor.fetchall()]
    conn.close()
    return sizes

# Обробка команди старт
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserInfo.name)
    await message.answer("Привіт! Як до вас звертатися?", reply_markup=ReplyKeyboardRemove())

# Обробка кнопок навігації
async def handle_navigation(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_data = await state.get_data()
    
    if message.text == "🏠 На початок":
        await start(message, state)
        return True
    
    elif message.text == "↩️ На попередній крок":
        if current_state == UserInfo.want_to_buy.state:
            await state.set_state(UserInfo.name)
            await message.answer("Як до вас звертатися?", reply_markup=ReplyKeyboardRemove())
        elif current_state == UserInfo.size.state:
            await state.set_state(UserInfo.want_to_buy)
            await message.answer(f"{user_data.get('name', '')}, хочете підібрати взуття?", reply_markup=get_yes_no_keyboard())
        elif current_state == UserInfo.style.state:
            await state.set_state(UserInfo.size)
            available_sizes = get_available_sizes()
            await message.answer(
                f"Доступні розміри: {', '.join(available_sizes)}\n"
                "Будь ласка, введіть ваш розмір взуття:",
                reply_markup=get_base_keyboard()
            )
        elif current_state == UserInfo.shoe_type.state:
            await state.set_state(UserInfo.style)
            await message.answer("Оберіть стиль взуття:", reply_markup=get_style_keyboard())
        elif current_state == UserInfo.confirm_order.state:
            await state.set_state(UserInfo.shoe_type)
            await message.answer("Оберіть тип взуття:", 
                               reply_markup=get_type_keyboard(user_data.get('style', '')))
        elif current_state == UserInfo.more_shopping.state:
            await state.set_state(UserInfo.want_to_buy)
            await message.answer("Хочете підібрати взуття?", reply_markup=get_yes_no_keyboard())
        return True
    return False

# Отримання імені
@dp.message(UserInfo.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(UserInfo.want_to_buy)
    await message.answer(f"Приємно познайомитися, {message.text}! Хочете підібрати взуття?", 
                        reply_markup=get_yes_no_keyboard())

# Обробка відповіді про покупку
@dp.message(UserInfo.want_to_buy)
async def process_want_to_buy(message: types.Message, state: FSMContext):
    if await handle_navigation(message, state):
        return
    
    if message.text not in ["Так", "Ні"]:
        await message.answer("Будь ласка, виберіть 'Так' або 'Ні'", reply_markup=get_yes_no_keyboard())
        return
    
    if message.text == "Ні":
        await message.answer("Добре, звертайтеся будь-коли! Щоб почати знову, напишіть /start", 
                           reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        available_sizes = get_available_sizes()
        await state.set_state(UserInfo.size)
        await message.answer(
            f"Доступні розміри: {', '.join(available_sizes)}\n"
            "Будь ласка, введіть ваш розмір взуття:",
            reply_markup=get_base_keyboard()
        )

# Отримання розміру
@dp.message(UserInfo.size)
async def get_size(message: types.Message, state: FSMContext):
    if await handle_navigation(message, state):
        return
    
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть число (наприклад, 42)", reply_markup=get_base_keyboard())
        return
    
    size = int(message.text)
    available_sizes = [int(s) for s in get_available_sizes()]
    
    if size not in available_sizes:
        await message.answer(f"На жаль, розміру {size} немає в наявності. Оберіть будь ласка інший розмір.", 
                           reply_markup=get_base_keyboard())
        return
    
    await state.update_data(size=size)
    await state.set_state(UserInfo.style)
    await message.answer("Оберіть стиль взуття:", reply_markup=get_style_keyboard())

# Отримання стилю
@dp.message(UserInfo.style)
async def get_style(message: types.Message, state: FSMContext):
    if await handle_navigation(message, state):
        return
    
    if message.text not in ["sport", "casual", "formal", "outdoor"]:
        await message.answer("Будь ласка, оберіть стиль з клавіатури", reply_markup=get_style_keyboard())
        return
    
    await state.update_data(style=message.text)
    await state.set_state(UserInfo.shoe_type)
    await message.answer("Оберіть тип взуття:", reply_markup=get_type_keyboard(message.text))

# Отримання типу і пошук взуття
@dp.message(UserInfo.shoe_type)
async def get_shoes_type(message: types.Message, state: FSMContext):
    if await handle_navigation(message, state):
        return
    
    user_data = await state.get_data()
    style = user_data.get('style', '')
    available_types = {
        "sport": ["sneakers", "boots"],
        "casual": ["sneakers", "shoes"],
        "formal": ["shoes", "boots"],
        "outdoor": ["boots"]
    }.get(style, [])
    
    if message.text not in available_types:
        await message.answer("Будь ласка, оберіть тип з клавіатури", 
                           reply_markup=get_type_keyboard(style))
        return
    
    await state.update_data(shoe_type=message.text)
    shoe = find_shoe(user_data['size'], style, message.text)
    
    if shoe:
        await state.update_data(current_shoe=shoe)
        response = (
            f"{user_data.get('name', '')}, ми підібрали для вас:\n\n"
            f"🏷 Бренд: {shoe[1]}\n"
            f"📏 Розмір: {shoe[2]}\n"
            f"🎨 Стиль: {shoe[3]}\n"
            f"👟 Тип: {shoe[4]}\n"
            f"💵 Ціна: {shoe[5]} UAH\n\n"
            f"Підтвердіть, будь ласка, ваше замовлення:"
        )
        await message.answer(response, reply_markup=ReplyKeyboardRemove())
        await message.answer("Підтвердити замовлення?", reply_markup=get_confirm_keyboard())
        await state.set_state(UserInfo.confirm_order)
    else:
        await message.answer("На жаль, немає взуття, що відповідає вашим критеріям.")
        await state.set_state(UserInfo.more_shopping)
        await message.answer("Чи бажаєте спробувати інші параметри?", reply_markup=get_yes_no_keyboard())

# Обробка підтвердження замовлення
@dp.callback_query(UserInfo.confirm_order, F.data.in_(["confirm", "cancel"]))
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    name = user_data.get('name', '')
    
    if callback.data == "confirm":
        shoe = user_data['current_shoe']
        order_details = (
            f"✅ Ваше замовлення прийнято!\n\n"
            f"Деталі замовлення:\n"
            f"Бренд: {shoe[1]}\n"
            f"Розмір: {shoe[2]}\n"
            f"Стиль: {shoe[3]}\n"
            f"Тип: {shoe[4]}\n"
            f"Ціна: {shoe[5]} UAH\n\n"
            f"Дякуємо за покупку, {name}! 🎉"
        )
        await callback.message.answer(order_details)
    else:
        await callback.message.answer("Замовлення скасовано.")
    
    await callback.answer()
    await state.set_state(UserInfo.more_shopping)
    await callback.message.answer("Чи бажаєте ще щось замовити?", reply_markup=get_yes_no_keyboard())

# Обробка запиту на додаткові покупки
@dp.message(UserInfo.more_shopping)
async def more_shopping(message: types.Message, state: FSMContext):
    if await handle_navigation(message, state):
        return
    
    if message.text not in ["Так", "Ні"]:
        await message.answer("Будь ласка, виберіть 'Так' або 'Ні'", reply_markup=get_yes_no_keyboard())
        return
    
    if message.text == "Ні":
        await message.answer("Дякуємо за покупки! 🛍️ Звертайтеся будь-коли. Щоб почати знову, напишіть /start", 
                           reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        available_sizes = get_available_sizes()
        await state.set_state(UserInfo.size)
        await message.answer(
            f"Доступні розміри: {', '.join(available_sizes)}\n"
            "Будь ласка, введіть ваш розмір взуття:",
            reply_markup=get_base_keyboard()
        )

# Функція пошуку однієї пари взуття
def find_shoe(size, style, shoe_type):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, brand, size, style, type, price FROM shoes
        WHERE size = ? AND style = ? AND type = ?
        LIMIT 1
    """, (size, style, shoe_type))
    
    result = cursor.fetchone()
    conn.close()
    return result

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
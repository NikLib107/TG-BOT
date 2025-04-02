import sqlite3
import logging
import config
import aiohttp
import json
import random
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove,
    InputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
import asyncio
import urllib.parse

# Налаштування логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота
bot = Bot(token=config.TOKEN)
dp = Dispatcher()

# Шляхи до файлів
DB_FILE = Path("shoes.db")
GIST_URL = "https://gist.githubusercontent.com/kykylib/83d6ccc3228a6473e073a0c8b95eb746/raw/a48107987aa73ab76945c005d1a60581260beb8a/gistfile1.txt"

# Визначення станів
class UserInfo(StatesGroup):
    name = State()
    want_to_buy = State()
    size = State()
    style = State()
    shoe_type = State()
    confirm_order = State()
    more_shopping = State()

async def init_db():
    """Ініціалізація БД з використанням даних з Gist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Видаляємо існуючу таблицю, якщо вона є
    cursor.execute("DROP TABLE IF EXISTS shoes")
    
    # Створюємо нову таблицю з правильною структурою
    cursor.execute("""
        CREATE TABLE shoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            size INTEGER NOT NULL,
            style TEXT NOT NULL,
            type TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT,
            UNIQUE(brand, model, size)
        )
    """)
    
    # Перевіряємо, чи таблиця порожня
    cursor.execute("SELECT COUNT(*) FROM shoes")
    count = cursor.fetchone()[0]
    
    if count == 0:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GIST_URL) as response:
                    if response.status == 200:
                        raw_text = await response.text()
                        data = json.loads(raw_text)
                        shoes_data = [
                            (
                                item['brand'],
                                item['model'],
                                item['size'],
                                item['style'],
                                item['type'],
                                item['price'],
                                item.get('image_url', '')
                            ) for item in data
                        ]
                        
                        cursor.executemany("""
                            INSERT OR IGNORE INTO shoes 
                            (brand, model, size, style, type, price, image_url)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, shoes_data)
                        conn.commit()
                        logging.info(f"Додано {len(shoes_data)} записів з Gist")
                        
                    else:
                        raise Exception(f"HTTP Error: {response.status}")
                        
        except Exception as e:
            logging.error(f"Помилка завантаження даних: {e}")
            # Використовуємо резервні дані з правильними URL зображень
            backup_data = [
                ("Nike", "Air Max 270", 42, "sport", "sneakers", 3499, "https://static.nike.com/a/images/t_PDP_1280_v1/f_auto,q_auto:eco/skwgyqrbfzhu6uyeh0gg/air-max-270-mens-shoes-KkLcGR.png"),
                ("Adidas", "Ultraboost 22", 41, "sport", "sneakers", 3999, "https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/8a5bf7ac7dcd4898a9b1af1800f5a1a3_9366/Ultraboost_22_Shoes_Black_GZ0127_01_standard.jpg"),
                ("Puma", "RS-X3 Puzzle", 40, "casual", "sneakers", 2799, "https://images.puma.com/image/upload/f_auto,q_auto,b_rgb:fafafa,w_2000,h_2000/global/376220/02/sv01/fnd/EEA/fmt/png/RS-X3-Puzzle-Unisex-Sneakers"),
                ("Timberland", "Premium Boot", 43, "outdoor", "boots", 5999, "https://images.timberland.com/is/image/TimberlandEU/10061713-hero?wid=720&hei=720&fit=constrain,1&qlt=85,1&op_usm=1,1,6,0"),
                ("Clarks", "Desert Trek", 44, "formal", "boots", 4599, "https://www.clarksusa.com/dw/image/v2/BDWJ_PRD/on/demandware.static/-/Sites-clarks-master-catalog/default/dw5a1a9b9c/images/large/26175754_A.jpg"),
                ("Vans", "Old Skool Pro", 39, "casual", "sneakers", 2299, "https://images.vans.com/is/image/VansEU/VN0A38G1P8O-HERO?$VFDP-VIEWER-ZOOMVIEW-HERO$")
            ]
            cursor.executemany("""
                INSERT OR IGNORE INTO shoes 
                (brand, model, size, style, type, price, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, backup_data)
            conn.commit()
    
    conn.close()

# Клавіатури
def get_base_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="↩️ Назад"), 
            KeyboardButton(text="🏠 Додому")
        ]],
        resize_keyboard=True
    )

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Так"), KeyboardButton(text="❌ Ні")],
            [KeyboardButton(text="↩️ Назад"), KeyboardButton(text="🏠 Додому")]
        ],
        resize_keyboard=True
    )

def get_style_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏃 Спорт"), KeyboardButton(text="👖 Кежуал")],
            [KeyboardButton(text="👔 Офіційний"), KeyboardButton(text="🌳 На вулицю")],
            [KeyboardButton(text="↩️ Назад"), KeyboardButton(text="🏠 Додому")]
        ],
        resize_keyboard=True
    )

def get_type_keyboard(style: str):
    style_map = {
        "🏃 Спорт": ["👟 Кросівки", "🥾 Черевики"],
        "👖 Кежуал": ["👟 Кросівки", "👞 Туфлі"],
        "👔 Офіційний": ["👞 Туфлі", "🥾 Черевики"],
        "🌳 На вулицю": ["🥾 Черевики"]
    }
    
    types = style_map.get(style, [])
    keyboard = []
    row = []
    for t in types:
        row.append(KeyboardButton(text=t))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([KeyboardButton(text="↩️ Назад"), KeyboardButton(text="🏠 Додому")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_confirm_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Підтвердити", callback_data="confirm")],
        [InlineKeyboardButton(text="🗑️ Скасувати", callback_data="cancel")]
    ])

def get_available_sizes():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT size FROM shoes ORDER BY size")
    sizes = [str(size[0]) for size in cursor.fetchall()]
    conn.close()
    return sizes

def is_valid_image_url(url):
    """Перевіряє, чи URL вказує на зображення"""
    if not url:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        return any(parsed.path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
    except:
        return False

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(UserInfo.name)
    await message.answer("👋 Вітаю! Як до вас звертатися?", reply_markup=ReplyKeyboardRemove())

@dp.message(UserInfo.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(UserInfo.want_to_buy)
    await message.answer(
        f"Приємно познайомитися, {message.text}! Хочете підібрати взуття?",
        reply_markup=get_yes_no_keyboard()
    )

@dp.message(UserInfo.want_to_buy)
async def process_want_to_buy(message: types.Message, state: FSMContext):
    if message.text == "✅ Так":
        available_sizes = get_available_sizes()
        await state.set_state(UserInfo.size)
        await message.answer(
            f"Доступні розміри: {', '.join(available_sizes)}\n"
            "Введіть ваш розмір:",
            reply_markup=get_base_keyboard()
        )
    elif message.text == "❌ Ні":
        await message.answer("Дякуємо! Звертайтеся будь-коли 😊")
        await state.clear()
    else:
        await message.answer("Оберіть варіант з клавіатури ⬇️", reply_markup=get_yes_no_keyboard())

@dp.message(UserInfo.size)
async def get_size(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введіть числовий розмір (наприклад: 42)", reply_markup=get_base_keyboard())
        return
    
    size = int(message.text)
    available_sizes = [int(s) for s in get_available_sizes()]
    
    if size not in available_sizes:
        await message.answer("Цього розміру немає в наявності. Оберіть інший.", reply_markup=get_base_keyboard())
        return
    
    await state.update_data(size=size)
    await state.set_state(UserInfo.style)
    await message.answer("Оберіть стиль:", reply_markup=get_style_keyboard())

@dp.message(UserInfo.style)
async def get_style(message: types.Message, state: FSMContext):
    valid_styles = ["🏃 Спорт", "👖 Кежуал", "👔 Офіційний", "🌳 На вулицю"]
    if message.text not in valid_styles:
        await message.answer("Оберіть стиль з клавіатури ⬇️", reply_markup=get_style_keyboard())
        return
    
    await state.update_data(style=message.text)
    await state.set_state(UserInfo.shoe_type)
    await message.answer("Оберіть тип взуття:", reply_markup=get_type_keyboard(message.text))

@dp.message(UserInfo.shoe_type)
async def get_shoe_type(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    style = user_data.get('style', '')
    
    # Відображення стилів з інтерфейсу на значення в БД
    style_mapping = {
        "🏃 Спорт": "sport",
        "👖 Кежуал": "casual",
        "👔 Офіційний": "formal",
        "🌳 На вулицю": "outdoor"
    }
    
    # Відображення типів з інтерфейсу на значення в БД
    type_mapping = {
        "👟 Кросівки": "sneakers",
        "🥾 Черевики": "boots",
        "👞 Туфлі": "shoes"
    }
    
    db_style = style_mapping.get(style)
    db_type = type_mapping.get(message.text)
    
    if not db_style or not db_type:
        await message.answer("Оберіть тип з клавіатури ⬇️", reply_markup=get_type_keyboard(style))
        return
    
    await state.update_data(shoe_type=message.text)
    
    # Пошук взуття в БД
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT brand, model, price, image_url 
        FROM shoes 
        WHERE size = ? AND style = ? AND type = ?
        LIMIT 1
    """, (user_data['size'], db_style, db_type))
    
    shoe = cursor.fetchone()
    conn.close()
    
    if shoe:
        await state.update_data(current_shoe=shoe)
        response = (
            f"Знайдено для вас:\n\n"
            f"🏷 Бренд: {shoe[0]}\n"
            f"👟 Модель: {shoe[1]}\n"
            f"💵 Ціна: {shoe[2]} UAH\n\n"
            f"Підтвердити замовлення?"
        )
        
        # Перевіряємо URL зображення перед відправкою
        if shoe[3] and is_valid_image_url(shoe[3]):
            try:
                await message.answer_photo(shoe[3], caption=response, reply_markup=get_confirm_keyboard())
            except Exception as e:
                logging.error(f"Помилка відправки фото: {e}")
                await message.answer(response, reply_markup=get_confirm_keyboard())
        else:
            await message.answer(response, reply_markup=get_confirm_keyboard())
        
        await state.set_state(UserInfo.confirm_order)
    else:
        await message.answer("На жаль, немає в наявності 😔", reply_markup=get_base_keyboard())
        await state.set_state(UserInfo.more_shopping)
        await message.answer("Бажаєте спробувати інші параметри?", reply_markup=get_yes_no_keyboard())

@dp.callback_query(UserInfo.confirm_order, F.data.in_(["confirm", "cancel"]))
async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm":
        user_data = await state.get_data()
        await callback.message.answer(
            "✅ Замовлення оформлено!\n"
            f"Дякуємо, {user_data.get('name', '')}!\n"
            "Очікуйте доставку 🚚"
        )
    else:
        await callback.message.answer("❌ Замовлення скасовано")
    
    await callback.answer()
    await state.set_state(UserInfo.more_shopping)
    await callback.message.answer("Бажаєте щось ще?", reply_markup=get_yes_no_keyboard())

@dp.message(UserInfo.more_shopping)
async def more_shopping(message: types.Message, state: FSMContext):
    if message.text == "✅ Так":
        await state.set_state(UserInfo.size)
        available_sizes = get_available_sizes()
        await message.answer(
            f"Доступні розміри: {', '.join(available_sizes)}\n"
            "Введіть ваш розмір:",
            reply_markup=get_base_keyboard()
        )
    else:
        await message.answer("Дякуємо за покупки! 🛍️", reply_markup=ReplyKeyboardRemove())
        await state.clear()

async def main():
    await init_db()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
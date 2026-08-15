import os
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

db = sqlite3.connect("santexnika.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    qty REAL DEFAULT 0,
    unit TEXT DEFAULT 'dona',
    price REAL DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    qty REAL,
    total REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 SANTEXNIKA DO'KONI BOTI\n\n"
        "Mahsulot qo'shish:\n"
        "/qoshish kran 20 dona 85000\n\n"
        "Mahsulotlarni ko'rish:\n"
        "/mahsulotlar\n\n"
        "Sotuv kiritish:\n"
        "/sotuv kran 2\n\n"
        "Hisobot:\n"
        "/hisobot"
    )


async def qoshish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 4:
        await update.message.reply_text(
            "Namuna:\n/qoshish kran 20 dona 85000"
        )
        return

    name = context.args[0]
    qty = float(context.args[1])
    unit = context.args[2]
    price = float(context.args[3])

    cur.execute("""
        INSERT INTO products(name, qty, unit, price)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
        qty = qty + excluded.qty,
        unit = excluded.unit,
        price = excluded.price
    """, (name, qty, unit, price))

    db.commit()

    await update.message.reply_text(
        f"✅ Mahsulot qo'shildi!\n\n"
        f"📦 {name}\n"
        f"📊 Miqdor: {qty:g} {unit}\n"
        f"💰 Narx: {price:,.0f} so'm"
    )


async def mahsulotlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = cur.execute(
        "SELECT name, qty, unit, price FROM products ORDER BY name"
    ).fetchall()

    if not rows:
        await update.message.reply_text("📦 Hali mahsulot yo'q.")
        return

    text = "📦 MAHSULOTLAR:\n\n"

    for name, qty, unit, price in rows:
        text += (
            f"🔹 {name}\n"
            f"   Qoldiq: {qty:g} {unit}\n"
            f"   Narx: {price:,.0f} so'm\n\n"
        )

    await update.message.reply_text(text)


async def sotuv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Namuna:\n/sotuv kran 2"
        )
        return

    name = context.args[0]
    qty = float(context.args[1])

    row = cur.execute(
        "SELECT qty, price FROM products WHERE name=?",
        (name,)
    ).fetchone()

    if not row:
        await update.message.reply_text(
            "❌ Bunday mahsulot topilmadi."
        )
        return

    stock, price = row

    if qty > stock:
        await update.message.reply_text(
            f"❌ Omborda yetarli mahsulot yo'q.\n"
            f"Qoldiq: {stock:g}"
        )
        return

    total = qty * price

    cur.execute(
        "UPDATE products SET qty = qty - ? WHERE name=?",
        (qty, name)
    )

    cur.execute(
        "INSERT INTO sales(product, qty, total) VALUES (?, ?, ?)",
        (name, qty, total)
    )

    db.commit()

    await update.message.reply_text(
        f"✅ SOTUV YOZILDI\n\n"
        f"📦 Mahsulot: {name}\n"
        f"📊 Miqdor: {qty:g}\n"
        f"💰 Jami: {total:,.0f} so'm\n"
        f"📦 Qoldiq: {stock - qty:g}"
    )


async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sales = cur.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales"
    ).fetchone()[0]

    count = cur.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    await update.message.reply_text(
        f"📊 UMUMIY HISOBOT\n\n"
        f"📦 Mahsulot turlari: {count}\n"
        f"💰 Jami sotuv: {sales:,.0f} so'm"
    )


def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("qoshish", qoshish))
    app.add_handler(CommandHandler("mahsulotlar", mahsulotlar))
    app.add_handler(CommandHandler("sotuv", sotuv))
    app.add_handler(CommandHandler("hisobot", hisobot))

    app.run_polling()


if __name__ == "__main__":
    main()

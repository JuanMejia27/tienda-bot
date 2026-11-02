import os
import re
import sqlite3

import telebot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

# Token del bot
API_TOKEN = os.environ.get('API_TOKEN', 'YOUR_API_TOKEN_HERE')#Reemplaza 'YOUR_API_TOKEN_HERE' con tu token
bot = telebot.TeleBot(API_TOKEN)

# Diccionario de categorias y productos
catalogo = {
    "camisas": ["Camisa Polo - $200", "Camisa casual - $150", "Camisa formal - $300"],
    "pantalones": ["Pantalón de vestir - $400", "Jeans - $350"],
    "accesorios": ["Reloj - $500", "Cinturón - $180", "Gorra - $200"]
}


def get_product_price(product):
    match = re.search(r"\$(\d+)", product)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)", product)
    if match:
        return int(match.group(1))
    raise ValueError(f"No se pudo obtener el precio del producto: {product}")


# Base de datos SQLite
def setup_database():
    conn = sqlite3.connect('tienda_ropa.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente INTEGER,
        producto TEXT,
        cantidad INTEGER,
        total REAL,
        estado TEXT
    )
    ''')
    conn.commit()
    conn.close()


setup_database()


# Funcion para confirmar el pedido
def confirm_order(message, product, quantity, total):
    confirmation = (message.text or '').strip().lower()
    valid_yes = ['si', 'sí', 's']
    valid_no = ['no', 'n']

    if confirmation in valid_yes:
        conn = sqlite3.connect('tienda_ropa.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO pedidos (id_cliente, producto, cantidad, total, estado) VALUES (?, ?, ?, ?, ?)",
            (message.chat.id, product, quantity, total, 'Pendiente')
        )
        conn.commit()
        conn.close()

        bot.send_message(
            message.chat.id,
            f"¡Pedido confirmado! Gracias por tu compra.\n\n"
            f"Certificado de pedido:\n"
            f"Producto: {product}\n"
            f"Cantidad: {quantity}\n"
            f"Total: ${total}\n\n"
            f"Por favor, realiza el pago en la cuenta bancaria: \n"
            f"Cuenta bancaria: 1234-5678-9101-1121\n"
            f"Después del pago, un asesor se pondrá en contacto contigo para coordinar la entrega.\n\n"
            f"Para regresar al menú principal, escribe /menu"
        )
    elif confirmation in valid_no:
        bot.send_message(message.chat.id, "Pedido cancelado. Para regresar al menú principal, escribe /menu")
    else:
        bot.send_message(message.chat.id, "Por favor, responde con 'sí' o 'no'.")
        bot.register_next_step_handler(message, confirm_order, product, quantity, total)


# Funcion para enviar el menu principal
def send_menu(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("/catálogo"), KeyboardButton("/mis_pedidos"))
    markup.add(KeyboardButton("volver al menú principal"))
    bot.send_message(
        message.chat.id,
        "¡Bienvenido al bot de la tienda de ropa! Por favor, elige una opción:",
        reply_markup=markup
    )


# Manejador del comando /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("/catálogo"), KeyboardButton("/mis_pedidos"))
    bot.send_message(
        message.chat.id,
        "¡Hola! Bienvenido al bot de la tienda de ropa. Para consultar el catálogo, realizar pedidos y más.\n\n"
        "Comandos disponibles:\n"
        "/catálogo - Ver el catálogo de productos\n"
        "/mis_pedidos - Ver mis pedidos\n"
        "/menu - Volver al menú principal",
        reply_markup=markup
    )


# Manejador para el comando /catálogo
@bot.message_handler(commands=['catalogo'])
def send_catalogo(message):
    categories = "\n".join([f"- {cat.title()}" for cat in catalogo.keys()])
    bot.send_message(
        message.chat.id,
        f"Catálogo de productos:\n\n{categories}\n\n"
        "Para ver los productos de una categoría, escribe el nombre de la categoría.\n\n"
        "Para regresar al menú principal, escribe /menu"
    )
    bot.register_next_step_handler(message, show_products)


# Funcion para mostrar los productos de una categoria
def show_products(message):
    if message.text is None:
        return
    category = message.text.strip().lower()
    if category == '/menu':
        send_menu(message)
        return
    if category in catalogo:
        products = "\n".join([f"{index}. {product}" for index, product in enumerate(catalogo[category], start=1)])
        bot.send_message(
            message.chat.id,
            f"Productos en la categoría '{category.title()}':\n\n{products}\n\n"
            "Para realizar un pedido, escribe el número del producto.\n\n"
            "Para regresar al menú principal, escribe /menu"
        )
        bot.register_next_step_handler(message, select_product, category)
    else:
        bot.send_message(
            message.chat.id,
            "Categoría no válida. Por favor, intenta de nuevo o escribe /menu para regresar al menú principal."
        )
        bot.register_next_step_handler(message, show_products)


# Funcion para seleccionar un producto y cantidad
def select_product(message, category):
    if message.text is None:
        return
    if message.text.lower() == "/menu":
        send_menu(message)
        return
    try:
        product_index = int(message.text.strip()) - 1
        if 0 <= product_index < len(catalogo[category]):
            product = catalogo[category][product_index]
            bot.send_message(
                message.chat.id,
                f"Has seleccionado: {product}\n\n"
                "Por favor, indica la cantidad que deseas comprar (por ejemplo: '2').\n\n"
                "Para regresar al menú principal, escribe /menu"
            )
            bot.register_next_step_handler(message, confirm_quantity, product)
        else:
            bot.send_message(
                message.chat.id,
                "Producto no válido. Por favor, intenta de nuevo o escribe /menu para regresar al menú principal."
            )
            bot.register_next_step_handler(message, select_product, category)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Producto no válido. Por favor, intenta de nuevo o escribe /menu para regresar al menú principal."
        )
        bot.register_next_step_handler(message, select_product, category)


# Funcion para confirmar la cantidad del producto
def confirm_quantity(message, product):
    if message.text is None:
        return
    if message.text.lower() == "/menu":
        send_menu(message)
        return
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError
        price = get_product_price(product)
        total = price * quantity
        bot.send_message(
            message.chat.id,
            f"Has seleccionado {quantity} unidades de {product}. El total es: ${total}\n\n"
            "¿Deseas confirmar tu pedido? (sí/no)\n\n"
            "Para regresar al menú principal, escribe /menu"
        )
        bot.register_next_step_handler(message, confirm_order, product, quantity, total)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Cantidad no válida. Por favor, intenta de nuevo o escribe /menu para regresar al menú principal."
        )
        bot.register_next_step_handler(message, confirm_quantity, product)


# Historial de pedidos
@bot.message_handler(commands=['mis_pedidos'])
def show_orders(message):
    conn = sqlite3.connect('tienda_ropa.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos WHERE id_cliente = ?", (message.chat.id,))
    orders = cursor.fetchall()
    conn.close()

    if orders:
        order_list = "\n".join(
            [f"Pedido {order[0]}: {order[2]} x{order[3]} - ${order[4]}" for order in orders]
        )
        bot.send_message(
            message.chat.id,
            f"Tus pedidos:\n{order_list}\n"
            "Para regresar al menú principal, escribe /menu"
        )
    else:
        bot.send_message(message.chat.id, "No tienes pedidos registrados. Para regresar al menú principal, escribe /menu")


# Manejador para el boton de volver al menú principal
@bot.message_handler(func=lambda message: message.text and message.text.lower() == "volver al menú principal")
def back_to_menu(message):
    send_menu(message)


@bot.message_handler(commands=['menu'])
def menu_command(message):
    send_menu(message)


# Ejecucion del bot
bot.polling(none_stop=True)
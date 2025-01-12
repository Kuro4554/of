import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest
import os
import time
from telegram.constants import ParseMode
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio




# --- Configuración de Google Drive ---
def autenticar_google_drive():
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]
    credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return build("drive", "v3", credentials=credentials)

def subir_a_google_drive(file_path, folder_id="1fi3BlBq-T_fKwtRLb7R7ZhlaDcwXri1F"):
    """Sube un archivo a Google Drive y retorna el enlace público."""
    drive_service = autenticar_google_drive()
    file_metadata = {"name": os.path.basename(file_path), "parents": [folder_id]}
    media = MediaFileUpload(file_path, mimetype="image/jpeg")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
    print(f"Archivo subido a Google Drive: {file.get('webViewLink')}")
    return file.get("webViewLink")







# --- Configuración de Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(credentials)
sheet = client.open("Suscripciones").sheet1  # Hoja principal


# --- Configuración del bot ---
TOKEN = "8088624985:AAGRMvD7kiUS0LNNN2_fhUvU0sxIxk0mqj8"
ADMIN_IDS = [7786874724,6380669463,7130814268,5453322412]  # Lista de administradores (puedes añadir más IDs)
GRUPO_EXCLUSIVO = -1002322290251  # ID del grupo/canal privado
CANAL_ID = -1002442455901  # Cambia esto por el username del canal
BOT_USERNAME = "lilit_rousebot"  # Bot al que redirigirá el botón



# --- Funciones para Google Sheets ---
def agregar_usuario(user_id, username):
    usuarios = sheet.get_all_records()
    for usuario in usuarios:
        if str(usuario["user_id"]) == str(user_id):
            return  # El usuario ya existe
    sheet.append_row([user_id, username, "pending", 0])

def actualizar_estado(user_id, status, subscription_end=None):
    usuarios = sheet.get_all_records()
    for idx, usuario in enumerate(usuarios):
        if str(usuario["user_id"]) == str(user_id):
            fila = idx + 2  # Ajustar índice para la fila en Sheets (la fila 1 es encabezado)
            sheet.update(values=[[status]], range_name=f"C{fila}")  # Actualizar estado
            if subscription_end:
                sheet.update(values=[[subscription_end]], range_name=f"D{fila}")  # Actualizar fecha
            return

def obtener_usuarios_por_estado(status):
    usuarios = sheet.get_all_records()
    return [u for u in usuarios if u["payment_status"] == status]



# --- Función para enviar mensaje al canal ---
async def enviar_mensaje_diario(context: ContextTypes.DEFAULT_TYPE):
    try:
        # Crear botón con enlace para iniciar el bot
        botones = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "Quiero unirme",
                url=f"https://t.me/{BOT_USERNAME}?start=1"  # Enlace al bot
            )]
        ])
        # Ruta de la imagen que se enviará
        ruta_imagen = "bienvenida.jpg"  # Cambia esto al nombre de tu imagen
        texto = (
            "🌟 ¡Únete a nuestro Grupo VIP de Telegram! 🌟\n\n"
            "Realiza tu pago por Yape, Plin o PayPal y disfruta de contenido exclusivo 🎉\n\n"
            "✅ Contenido único y beneficios increíbles.\n\n"
            "¡Haz clic en el botón de abajo para más información! 👇"
        )

        # Enviar mensaje con imagen al canal
        with open(ruta_imagen, "rb") as imagen:
            await context.bot.send_photo(
                chat_id=CANAL_ID,
                photo=imagen,
                caption=texto,
                reply_markup=botones,
                parse_mode="Markdown"
            )
        print("Mensaje enviado al canal.")
    except Exception as e:
        print(f"Error al enviar el mensaje al canal: {e}")



 # --- Función para manejar el comando manual ---
async def enviar_mensaje_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Verificar si el usuario es administrador
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return
# Llamar a la función que envía el mensaje al canal
    # Llamar a la función que envía el mensaje al canal
    await enviar_mensaje_diario(context)
    await update.message.reply_text("✅ El mensaje se ha enviado manualmente al canal.")       


# Función para manejar el clic en el botón "Quiero unirme"
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    # Responder al clic del botón
    await query.answer()
    await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"¡Hola, {user.first_name}! 🎉\n\n"
            "Estos son los precios para unirte a nuestro Grupo VIP de Telegram:\n\n"
            "💎 1 Mes - S/ 40\n"
            "✨ 3 Meses - S/ 100\n"
            "🎉 6 Meses - S/ 180\n\n"
            "💰 Métodos de pago:\n"
            "1️⃣ *Yape*: 999-999-999\n"
            "2️⃣ *Plin*: 888-888-888\n"
            "3️⃣ *PayPal*: [Tu enlace de PayPal](https://paypal.me/tulink)\n\n"
            "📸 Envía tu comprobante de pago para procesarlo y unirte al Grupo VIP."
        ),
        parse_mode="Markdown"
    )
    print(f"Información enviada a {user.id} ({user.username})")





async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username

    # Enviar mensaje de bienvenida
    with open("bienvenida.jpg", "rb") as photo:
        await update.message.reply_photo(photo, caption=(
            f"¡Hola, {username}! 🌸 Bienvenid@ a nuestro procesador de pagos.\n\n"
            "🔔 *Canal público:* [Contenido Gratuito y Actualizaciones](https://t.me/Lilit_R0se).\n\n"
            "🎀 *Accede al contenido exclusivo suscribiéndote*\n"
            "💎 1 Mes - S/ 30\n"
            "✨ 3 Meses - S/ 80\n"
            "🎉 12 Meses - S/ 260\n\n"
            "🎉 VITALICIO - S/ 500\n\n"
            "💰 Métodos de pago para PERU:\n"
            "1️⃣ *Yape*: 988133711\n"
            "2️⃣ *Plin*: 988133711\n"
            ), parse_mode="Markdown")

    # Enviar la imagen adicional
    with open("imagen_final.jpg", "rb") as imagen_final:
        await update.message.reply_photo(imagen_final)


     # Esperar un momento antes de enviar las opciones de PayPal
    import asyncio
    await asyncio.sleep(1)  # Espera de 1 segundo


    # Crear botones de pago con PayPal
    botones_paypal = InlineKeyboardMarkup([
        [InlineKeyboardButton("Mensual - $10", url="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-0LY583665W194821XM6B4ZEA")],
        [InlineKeyboardButton("3 Meses - $22", url="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-0UV30168C76716028M6B42ZY")],
        [InlineKeyboardButton("Anual - $70", url="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-7PL63532BL645082FM6B435I")],
        [InlineKeyboardButton("Vitalicio - $135", url="https://www.paypal.com/webapps/billing/plans/subscribe?plan_id=P-15P67236JF6512136M6B4X7Q")],
    ])

    # Esperar un momento antes de enviar las opciones de PayPal
    import asyncio
    await asyncio.sleep(1)  # Espera de 1 segundo

    # Enviar los botones de pago con PayPal
    await update.message.reply_text(
        "💳 *Opciones de Pago con PayPal*:\n\n"
        "RECUERDA ENVIAR UNA CAPTURA UNA VEZ REALIZADO TU PAGO:\n\n"
        "Elige el plan que más te convenga 👇",
        reply_markup=botones_paypal,
        parse_mode="Markdown"
    )
     # Esperar un momento antes de enviar las opciones de PayPal
    import asyncio
    await asyncio.sleep(1)  # Espera de 1 segundo


    # Enviar el mensaje final sobre el comprobante
    await update.message.reply_text(
        "📸 Envíame tu comprobante de pago para procesarlo."
    )









async def recibir_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Verificar que el usuario no sea None
    if user is None:
        await update.message.reply_text("❌ Error: No se pudo identificar al usuario.")
        return

    user_id = user.id
    username = user.username if user.username else "SinUsername"

    if update.message.photo:
        # Crear la carpeta 'comprobantes/' si no existe
        folder_path = "comprobantes"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Guardar la imagen enviada
        photo_file = await update.message.photo[-1].get_file()
        file_path = f"{folder_path}/{user_id}_comprobante.jpg"
        await photo_file.download_to_drive(file_path)

        # Confirmar recepción al usuario
        await update.message.reply_text(
            "📩 ¡Comprobante recibido! El administrador lo verificará pronto."
        )

        # Notificar a los administradores
        for admin_id in ADMIN_IDS:  # Lista de administradores
            try:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=open(file_path, "rb"),
                    caption=(
                        f"📤 *Nuevo comprobante recibido*\n\n"
                        f"👤 Usuario: @{username} (ID: {user_id})\n"
                        "Estado: Pendiente de verificación."
                        "⚠️ Usa:  /confirmar "
                        "para aprobar este pago."
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                print(f"Error al notificar al administrador: {e}")
    else:
        await update.message.reply_text("❌ Por favor, envía una foto del comprobante de pago.")







async def verificar_pagos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Verificar si el usuario es administrador
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return

    # Obtener usuarios pendientes de verificación
    usuarios_pendientes = obtener_usuarios_por_estado("pending_verification")

    if not usuarios_pendientes:
        await update.message.reply_text("✅ No hay pagos pendientes.")
        return

    # Función para escapar caracteres especiales en HTML
    def escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
        )

    # Enviar detalles de los usuarios pendientes
    for usuario in usuarios_pendientes:
        file_path = f"comprobantes/{usuario['user_id']}_comprobante.jpg"

        # Escapar valores dinámicos
        escaped_username = escape_html(usuario['username'])
        escaped_user_id = escape_html(str(usuario['user_id']))
        escaped_status = escape_html(usuario['payment_status'])

        # Construir mensaje
        caption = (
            f"👤 Usuario: @{escaped_username} (ID: {escaped_user_id})\n"
            f"Estado: {escaped_status}\n\n"
            "⚠️ Usa /confirmar &lt;ID&gt; &lt;DÍAS&gt; para aprobar este pago."
        )

        # Debug: Imprimir el texto generado
        print(f"Texto enviado al administrador:\n{caption}")

        if os.path.exists(file_path):  # Verificar si el archivo existe
            try:
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=open(file_path, "rb"),
                    caption=caption,
                    parse_mode=ParseMode.HTML  # Usar HTML
                )
            except Exception as e:
                print(f"Error al enviar la imagen al administrador: {e}")
        else:
            await update.message.reply_text(
                f"❌ No se encontró el comprobante para el usuario @{escaped_username} (ID: {usuario['user_id']})."
            )


                    


# --- Actualización de la función `confirmar_suscripcion` ---
async def confirmar_suscripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or len(args) != 2:
        await update.message.reply_text("❌ Uso: /confirmar ID DÍAS")
        return

    user_id, dias = map(int, args)
    subscription_end = int(time.time()) + dias * 86400  # Tiempo de expiración en segundos
    actualizar_estado(user_id, "active", subscription_end)

    try:
        # Generar un enlace de invitación único
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=GRUPO_EXCLUSIVO,
            member_limit=1,  # Solo una persona puede usarlo
            expire_date=subscription_end  # Fecha de expiración
        )
        # Enviar el enlace al usuario
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Suscripción confirmada. Aquí está tu enlace de acceso:\n{invite_link.invite_link}\n\n"
                 "⚠️ *Este enlace es personal y solo se puede usar una vez.* No lo compartas con nadie.",
            parse_mode="Markdown"
        )
        await update.message.reply_text(f"✅ Suscripción confirmada para el usuario {user_id}.")

        # Subir comprobante a Google Drive y eliminar archivo local
        file_path = f"comprobantes/{user_id}_comprobante.jpg"
        if os.path.exists(file_path):
            enlace_drive = subir_a_google_drive(file_path)  # Subir la imagen a Drive
            print(f"Enlace de Drive: {enlace_drive}")

            # Actualizar Google Sheets con el enlace al comprobante en Drive
            actualizar_estado(user_id, "active", enlace_drive)

            # Eliminar el archivo local
            os.remove(file_path)
            print(f"Archivo local eliminado: {file_path}")
        else:
            print(f"No se encontró el archivo local: {file_path}")

    except BadRequest as e:
        await update.message.reply_text(f"❌ No se pudo generar el enlace. Verifica los permisos del bot.\nError: {e}")


async def verificar_suscripciones(context: ContextTypes.DEFAULT_TYPE):
    usuarios_activos = obtener_usuarios_por_estado("active")
    for usuario in usuarios_activos:
        user_id = usuario["user_id"]
        subscription_end = int(usuario["subscription_end"])
        time_left = subscription_end - int(time.time())

        if time_left <= 86400 * 2:  # Enviar recordatorio si quedan 2 días o menos
            try:
                await context.bot.send_message(chat_id=user_id, text="⏳ Tu suscripción vence pronto. ¡Renueva ahora para no perder acceso!")
            except:
                pass

        if time_left <= 0:  # Cambiar estado si la suscripción ha vencido
            actualizar_estado(user_id, "expired")

# --- Configuración del bot ---
def main():
    app = Application.builder().token(TOKEN).build()

    # Arrancar el JobQueue
    app.job_queue.run_repeating(verificar_suscripciones, interval=3600)



    # Programar mensajes diarios al canal a las 8 PM
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: app.job_queue.run_once(enviar_mensaje_diario, when=0),
        trigger="cron",
        hour=20,  # Hora de envío (8 PM)
        minute=0,
        second=0,
    )
    scheduler.start()

    # Agregar manejadores
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("verificar", verificar_pagos))
    app.add_handler(CommandHandler("confirmar", confirmar_suscripcion))
    app.add_handler(MessageHandler(filters.PHOTO, recibir_comprobante))
    app.add_handler(CommandHandler("send_message", enviar_mensaje_comando))

    app.run_polling()

if __name__ == "__main__":
    main()

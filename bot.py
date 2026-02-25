import requests
import time
import json
import os
from datetime import datetime, date

# ===============================
# CONFIGURACIÓN
# ===============================

TOKEN = os.environ.get("TOKEN")  # ahora viene desde Render
if not TOKEN:
    raise ValueError("No se encontró la variable de entorno TOKEN")

URL = f"https://api.telegram.org/bot{TOKEN}"
TURNOS_FILE = "turnos.json"

# ===============================
# ASEGURAR ARCHIVO JSON
# ===============================
if not os.path.exists(TURNOS_FILE):
    with open(TURNOS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# ===============================
# ESTADOS
# ===============================
INICIO = "INICIO"
MENU = "MENU"
FECHA_TURNO = "FECHA_TURNO"
ADMIN_MENU = "ADMIN_MENU"
ADMIN_FECHA = "ADMIN_FECHA"
ADMIN_CANCELAR = "ADMIN_CANCELAR"

estado = {}
last_update_id = 0

# ===============================
# UTILIDADES
# ===============================
def enviar(chat_id, texto):
    try:
        requests.post(
            f"{URL}/sendMessage",
            data={"chat_id": chat_id, "text": texto},
            timeout=10
        )
    except Exception as e:
        print("Error enviando mensaje:", e)

def fecha_valida(txt):
    try:
        datetime.strptime(txt, "%d/%m/%Y")
        return True
    except:
        return False

def cargar_turnos():
    try:
        with open(TURNOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def guardar_turnos(turnos):
    try:
        with open(TURNOS_FILE, "w", encoding="utf-8") as f:
            json.dump(turnos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error guardando turnos:", e)

# ===============================
# MENÚS
# ===============================
MENU_TXT = (
    "🦷 Dental Assistant Demo\n\n"
    "1️⃣ Solicitar turno\n"
    "2️⃣ Urgencias\n"
    "3️⃣ Información odontológica\n"
    "4️⃣ Salir\n\n"
    "✍️ Escriba el número:"
)

ADMIN_TXT = (
    "🛠️ Panel de Administración\n\n"
    "1️⃣ Turnos del día\n"
    "2️⃣ Agenda semanal\n"
    "3️⃣ Agregar nuevo turno\n"
    "4️⃣ Cancelar turno\n"
    "5️⃣ Pacientes en espera\n"
    "9️⃣ Volver al menú principal\n\n"
    "✍️ Elegí una opción:"
)

print("🤖 Bot iniciado en Render...")

# ===============================
# LOOP PRINCIPAL
# ===============================
while True:
    try:
        response = requests.get(
            f"{URL}/getUpdates",
            params={
                "offset": last_update_id + 1,
                "timeout": 10
            },
            timeout=15
        )

        data = response.json()

        for u in data.get("result", []):
            last_update_id = u["update_id"]

            msg = u.get("message")
            if not msg:
                continue

            chat = msg["chat"]["id"]
            txt = msg.get("text", "").strip()
            est = estado.get(chat, INICIO)

            print(f"📩 {chat} | {txt} | Estado: {est}")

            if txt.lower() == "/start":
                estado[chat] = MENU
                enviar(chat, "✅ Start recibido.")
                enviar(chat, MENU_TXT)
                continue

            if est == INICIO:
                enviar(chat, "⚠️ Enviá /start para comenzar.")
                continue

            if est == MENU:

                if txt.lower() == "admin":
                    estado[chat] = ADMIN_MENU
                    enviar(chat, "🔐 Acceso administrador concedido")
                    enviar(chat, ADMIN_TXT)
                    continue

                if txt == "1":
                    estado[chat] = FECHA_TURNO
                    enviar(chat, "📆 Ingrese la fecha del turno (dd/mm/yyyy):")
                    continue

                if txt == "2":
                    enviar(chat, "🚨 En caso de urgencia, llame al 123-456-789")
                    enviar(chat, MENU_TXT)
                    continue

                if txt == "3":
                    enviar(chat,
                           "🤖 Información odontológica:\n"
                           "- Limpieza dental lun-vie 9–17\n"
                           "- Extracciones y urgencias\n"
                           "- Control cada 6 meses")
                    enviar(chat, MENU_TXT)
                    continue

                if txt == "4":
                    enviar(chat, "👋 Hasta luego.")
                    estado[chat] = INICIO
                    continue

                enviar(chat, "❌ Opción no válida.")
                enviar(chat, MENU_TXT)
                continue

            if est == FECHA_TURNO:
                if fecha_valida(txt):
                    turnos = cargar_turnos()
                    turnos.append({"fecha": txt, "origen": "usuario"})
                    guardar_turnos(turnos)

                    enviar(chat, f"✅ Turno solicitado para {txt}")
                    estado[chat] = MENU
                    enviar(chat, MENU_TXT)
                else:
                    enviar(chat, "❌ Fecha inválida. Usá dd/mm/yyyy")
                continue

        time.sleep(1)

    except Exception as e:
        print("⚠️ Error general:", e)
        time.sleep(5)

import requests
import time
import json
from datetime import datetime, date

# ===============================
# CONFIGURACIÓN
# ===============================
TOKEN = "8572312796:AAH7Mjynp72pNfRg-T8ZJP3Sbg9I9rFP_Pw"  # JuanBot token
URL = f"https://api.telegram.org/bot{TOKEN}"
TURNOS_FILE = "turnos.json"

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
            if isinstance(data, list):
                return data
            else:
                return []
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

# ===============================
# INICIO
# ===============================
print("🤖 Dental Assistant Demo iniciado...")
print("⏳ Limpiando mensajes viejos...")

try:
    r = requests.get(f"{URL}/getUpdates", params={"timeout": 1}, timeout=5).json()
    if "result" in r and r["result"]:
        last_update_id = r["result"][-1]["update_id"]
except:
    last_update_id = 0

print("✅ Listo. Offset:", last_update_id)

# ===============================
# LOOP PRINCIPAL
# ===============================
while True:
    try:
        response = requests.get(
            f"{URL}/getUpdates",
            params={
                "offset": last_update_id + 1,
                "timeout": 5
            },
            timeout=10
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

            # START
            if txt.lower() == "/start":
                estado[chat] = MENU
                enviar(chat, "✅ Start recibido. Bienvenido al Dental Assistant Demo")
                enviar(chat, MENU_TXT)
                continue

            # BLOQUEO SIN START
            if est == INICIO:
                enviar(chat, "⚠️ Enviá /start para comenzar.")
                continue

            # MENÚ PRINCIPAL
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
                    enviar(chat, "👋 Gracias por usar Dental Assistant Demo. ¡Hasta luego!")
                    estado[chat] = INICIO
                    continue

                enviar(chat, "❌ Opción no válida.")
                enviar(chat, MENU_TXT)
                continue

            # TURNO USUARIO
            if est == FECHA_TURNO:

                if fecha_valida(txt):
                    turnos = cargar_turnos()
                    turnos.append({"fecha": txt, "origen": "usuario"})
                    guardar_turnos(turnos)

                    enviar(chat, f"✅ Turno solicitado para el {txt}")
                    estado[chat] = MENU
                    enviar(chat, MENU_TXT)
                else:
                    enviar(chat, "❌ Fecha inválida. Usá dd/mm/yyyy")

                continue

            # ADMIN MENU
            if est == ADMIN_MENU:

                turnos = cargar_turnos()

                if txt == "1":
                    hoy = date.today().strftime("%d/%m/%Y")
                    lista = [t for t in turnos if t["fecha"] == hoy]

                    if not lista:
                        enviar(chat, "📭 No hay turnos hoy.")
                    else:
                        msg = "📋 Turnos del día:\n"
                        for i, t in enumerate(lista, 1):
                            msg += f"{i}. {t['fecha']} ({t['origen']})\n"
                        enviar(chat, msg)

                    enviar(chat, ADMIN_TXT)
                    continue

                if txt == "2":
                    if not turnos:
                        enviar(chat, "📭 No hay turnos cargados.")
                    else:
                        msg = "🗓️ Agenda:\n"
                        for i, t in enumerate(turnos, 1):
                            msg += f"{i}. {t['fecha']} ({t['origen']})\n"
                        enviar(chat, msg)

                    enviar(chat, ADMIN_TXT)
                    continue

                if txt == "3":
                    estado[chat] = ADMIN_FECHA
                    enviar(chat, "📆 Ingrese la fecha del nuevo turno (dd/mm/yyyy):")
                    continue

                if txt == "4":
                    if not turnos:
                        enviar(chat, "📭 No hay turnos para cancelar.")
                        enviar(chat, ADMIN_TXT)
                    else:
                        msg = "❌ Turnos:\n"
                        for i, t in enumerate(turnos, 1):
                            msg += f"{i}. {t['fecha']} ({t['origen']})\n"
                        msg += "\nIngrese el número a cancelar:"
                        estado[chat] = ADMIN_CANCELAR
                        enviar(chat, msg)
                    continue

                if txt == "5":
                    enviar(chat, "👥 Pacientes en espera: (función futura)")
                    enviar(chat, ADMIN_TXT)
                    continue

                if txt == "9":
                    estado[chat] = MENU
                    enviar(chat, "🔓 Sesión admin cerrada.")
                    enviar(chat, MENU_TXT)
                    continue

                enviar(chat, "❌ Opción inválida.")
                enviar(chat, ADMIN_TXT)
                continue

            # ADMIN FECHA
            if est == ADMIN_FECHA:
                if fecha_valida(txt):
                    turnos = cargar_turnos()
                    turnos.append({"fecha": txt, "origen": "admin"})
                    guardar_turnos(turnos)

                    enviar(chat, f"✅ Turno agregado para {txt}")
                    estado[chat] = ADMIN_MENU
                    enviar(chat, ADMIN_TXT)
                else:
                    enviar(chat, "❌ Fecha inválida. Usá dd/mm/yyyy")
                continue

            # ADMIN CANCELAR
            if est == ADMIN_CANCELAR:
                turnos = cargar_turnos()
                if txt.isdigit() and 1 <= int(txt) <= len(turnos):
                    eliminado = turnos.pop(int(txt) - 1)
                    guardar_turnos(turnos)
                    enviar(chat, f"🗑️ Turno {eliminado['fecha']} cancelado.")
                else:
                    enviar(chat, "❌ Número inválido.")

                estado[chat] = ADMIN_MENU
                enviar(chat, ADMIN_TXT)
                continue

        time.sleep(0.5)

    except Exception as e:
        print("⚠️ Error general:", e)
        time.sleep(3)
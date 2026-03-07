import json
import os
from flask import Flask, request
from datetime import datetime, timedelta
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

TURNOS_FILE = "turnos.json"
MENSAJES_FILE = "mensajes.json"

# estados en memoria (pruebas)
estado = {}

# administradores (prueba)
ADMINS = [
    "whatsapp:+5493515645624"
]

# MENÚS (no se tocan)
MENU_PACIENTE = """
🦙 E-Bot Lite
1 Turno
2 Consultar mi turno
3 Mensaje 📩
4 Urgencia 🚑
5 Informes
6 Salir
"""

MENU_ADMIN = """
🛠 ADMIN

1 Turnos del día
2 Próximos turnos
3 Ver mensajes
4 Ingresar turno
5 Cancelar turno
6 Bloquear agenda
7 Salir
"""

# HELPERS JSON
def cargar_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def guardar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# HORARIOS
def generar_horarios():
    horarios = []
    inicio = datetime.strptime("09:00", "%H:%M")
    fin = datetime.strptime("19:00", "%H:%M")
    actual = inicio
    while actual <= fin:
        horarios.append(actual.strftime("%H:%M"))
        actual += timedelta(minutes=30)
    return horarios

def obtener_turnos_futuros():
    hoy = datetime.now().date()
    turnos = cargar_json(TURNOS_FILE)
    futuros = [
        t for t in turnos
        if datetime.strptime(t["fecha"], "%d/%m/%Y").date() >= hoy
    ]
    return sorted(futuros, key=lambda x: (x["fecha"], x["hora"]))

# MENÚ PACIENTE
def manejar_menu(numero, body, resp):
    msg = resp.message()

    if body == "1":
        estado[numero] = "TURNO_NOMBRE"
        msg.body("Ingrese nombre y apellido")
        return str(resp)

    if body == "2":
        turnos = cargar_json(TURNOS_FILE)
        lista = [t for t in turnos if t["telefono"] == numero]
        if not lista:
            msg.body("No se encontraron turnos para su número")
        else:
            salida = "\n".join([f"{t['fecha']} {t['hora']}" for t in lista])
            msg.body(f"📅 Sus turnos:\n{salida}")
        return str(resp)

    if body == "3":
        estado[numero] = "MENSAJE_NOMBRE"
        msg.body("Nombre y apellido")
        return str(resp)

    if body == "4":
        msg.body("Urgencias 🚑: +549000000000")
        return str(resp)

    if body == "5":
        msg.body("""
📄 Informes

🕒 Horario: 08:00 – 18:00
🏥 Obras sociales: Sí
""")
        return str(resp)

    if body == "6":
        msg.body("Hasta pronto. Escriba MENU para volver")
        return str(resp)

    msg.body(MENU_PACIENTE)
    return str(resp)

# MENÚ ADMIN
def manejar_admin(numero, body, resp):
    msg = resp.message()
    turnos = cargar_json(TURNOS_FILE)
    mensajes = cargar_json(MENSAJES_FILE)

    if body == "1":
        hoy = datetime.now().strftime("%d/%m/%Y")
        lista = [t for t in turnos if t["fecha"] == hoy]
        msg.body("No hay turnos hoy" if not lista else "\n".join([
            f"{t['hora']} {t['nombre']} {t['telefono']}" for t in lista
        ]))
        return str(resp)

    if body == "2":
        lista = obtener_turnos_futuros()
        msg.body("No hay próximos turnos" if not lista else "\n".join([
            f"{t['fecha']} {t['hora']} {t['nombre']}" for t in lista
        ]))
        return str(resp)

    if body == "3":
        msg.body("Sin mensajes" if not mensajes else "\n".join([
            f"{m['nombre']} {m['telefono']}\n{m['mensaje']}" for m in mensajes
        ]))
        return str(resp)

    if body == "4":
        estado[numero] = "TURNO_NOMBRE"
        msg.body("Ingrese nombre y apellido para ingresar turno")
        return str(resp)

    if body == "5":
        msg.body("Función cancelar turno en desarrollo")
        return str(resp)

    if body == "6":
        msg.body("Función bloquear agenda en desarrollo")
        return str(resp)

    if body == "7":
        estado[numero] = "MENU"
        msg.body("Saliendo admin")
        return str(resp)

    msg.body(MENU_ADMIN)
    return str(resp)

# WEBHOOK (GET y POST)
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "OK"

    numero = request.values.get("From")
    body = request.values.get("Body", "").strip()
    texto = body.lower()

    resp = MessagingResponse()
    msg = resp.message()

    estado.setdefault(numero, "MENU")
    estado_actual = estado[numero]

    # menú siempre responde
    if estado_actual == "MENU":
        return manejar_menu(numero, body, resp)

    # admin por palabra secreta
    if texto in ["adm", "admin"]:
        estado[numero] = "ADMIN"
        msg.body(MENU_ADMIN)
        return str(resp)

    # admin real
    if estado_actual == "ADMIN" and numero in ADMINS:
        return manejar_admin(numero, body, resp)

    # turno nombre
    if estado_actual == "TURNO_NOMBRE":
        estado[numero + "_nombre"] = body
        estado[numero] = "TURNO_FECHA"
        msg.body("Ingrese fecha (dd/mm/yyyy)")
        return str(resp)

    # turno fecha
    if estado_actual == "TURNO_FECHA":
        try:
            fecha = datetime.strptime(body, "%d/%m/%Y").date()
        except:
            msg.body("Formato inválido. Use dd/mm/yyyy")
            return str(resp)

        if fecha < datetime.now().date():
            msg.body("Fecha pasada. Elija otra")
            return str(resp)

        estado[numero + "_fecha"] = body
        estado[numero] = "TURNO_HORA"

        horarios = generar_horarios()
        turnos = cargar_json(TURNOS_FILE)
        ocupados = [t["hora"] for t in turnos if t["fecha"] == body]
        libres = [h for h in horarios if h not in ocupados]

        if not libres:
            msg.body("No hay horarios disponibles")
            estado[numero] = "MENU"
            return str(resp)

        msg.body("Elija hora:\n" + "\n".join(libres))
        return str(resp)

    # turno hora
    if estado_actual == "TURNO_HORA":
        hora = body.strip()
        horarios = generar_horarios()

        if hora not in horarios:
            msg.body("Hora inválida")
            return str(resp)

        fecha = estado.get(numero + "_fecha")
        if not fecha:
            msg.body("Error. Vuelva a iniciar turno")
            estado[numero] = "MENU"
            return str(resp)

        turnos = cargar_json(TURNOS_FILE)

        if any(t["fecha"] == fecha and t["hora"] == hora for t in turnos):
            msg.body("Hora ocupada")
            return str(resp)

        turnos.append({
            "nombre": estado[numero + "_nombre"],
            "telefono": numero,
            "fecha": fecha,
            "hora": hora
        })
        guardar_json(TURNOS_FILE, turnos)

        estado[numero] = "MENU"
        msg.body(f"✅ Turno confirmado\n{estado[numero + '_nombre']}\n{fecha} {hora}")
        return str(resp)

    # mensajes
    if estado_actual == "MENSAJE_NOMBRE":
        estado[numero + "_nombre"] = body
        estado[numero] = "MENSAJE_TEXTO"
        msg.body("Escriba su mensaje")
        return str(resp)

    if estado_actual == "MENSAJE_TEXTO":
        mensajes = cargar_json(MENSAJES_FILE)
        mensajes.append({
            "nombre": estado[numero + "_nombre"],
            "telefono": numero,
            "mensaje": body,
            "fecha": datetime.now().isoformat(),
            "leido": False
        })
        guardar_json(MENSAJES_FILE, mensajes)

        estado[numero] = "MENU"
        msg.body("Mensaje recibido")
        return str(resp)

    # fallback
    msg.body(MENU_PACIENTE)
    return str(resp)

# HEALTHCHECK
@app.route("/")
def home():
    return "E-Bot activo"

# RUN LOCAL
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

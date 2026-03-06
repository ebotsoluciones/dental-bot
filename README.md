🦙 E-Bot Lite

Bot de WhatsApp para gestión de turnos y mensajes.

Parte del ecosistema E-Bot Soluciones.

---

Funciones

- 📅 Solicitud de turnos
- 💬 Mensajes de pacientes
- 🚨 contacto de urgencias
- 🛠 menú administrador
- 📊 agenda básica

---

Tecnologías

- Python
- Flask
- Twilio API
- Railway

---

Estructura del proyecto

bot.py
requirements.txt
turnos.json
mensajes.json
estado.json
README.md

---

Instalación

Instalar dependencias:

pip install -r requirements.txt

Ejecutar bot:

python bot.py

---

Deploy Railway

Start command:

gunicorn bot:app

Webhook Twilio:

https://tu-app.up.railway.app/webhook

---

Uso

Enviar mensaje:

menu

Menú paciente:

1 Turno
2 Mensaje
3 Urgencia
4 Informes
5 Salir

Acceso administrador:

admin

---

Proyecto

Desarrollado como parte de E-Bot Soluciones.

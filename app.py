import os
import sqlite3
from flask import Flask, render_template, request, jsonify
import anthropic

app = Flask(__name__)

# Configuración de la API Key de Anthropic (Claude)
api_key = os.environ.get("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

SYSTEM_INSTRUCTION = """
Sos un tutor personal de idiomas cálido, empático y reflexivo para Anto.
Tu personalidad combina una estética botánica, astrológica y de bienestar (estilo Pinterest).
Acompañás el aprendizaje de idiomas de forma relajada, usando metáforas suaves y emojis orgánicos (🌿, 🪷, ✨).
Recordás el progreso de las clases anteriores para mantener una continuidad constante y personalizada.
"""

# Inicializar la Base de Datos SQLite
def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"reply": "Por favor escribe un mensaje."}), 400

    try:
        # Guardar mensaje del usuario en SQLite
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial (sender, message) VALUES (?, ?)", ("user", user_message))
        conn.commit()

        # Recuperar historial reciente de la base de datos (últimos 6 mensajes)
        cursor.execute("SELECT sender, message FROM historial ORDER BY id DESC LIMIT 6")
        rows = cursor.fetchall()
        
        # Construir el historial para Claude
        messages_history = []
        for sender, msg in reversed(rows):
            role = "user" if sender == "user" else "assistant"
            messages_history.append({"role": role, "content": msg})

        conn.close()

        # Llamada oficial y limpia a Claude (modelo claude-3-5-sonnet o claude-3-haiku)
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            system=SYSTEM_INSTRUCTION,
            messages=messages_history
        )
        
        bot_reply = response.content[0].text

        # Guardar respuesta del bot en SQLite
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial (sender, message) VALUES (?, ?)", ("bot", bot_reply))
        conn.commit()
        conn.close()

        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        print(f"Error crítico con Claude: {e}")
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
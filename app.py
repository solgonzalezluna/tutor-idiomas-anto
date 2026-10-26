import os
import time
import sqlite3
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configuración de la API Key con el SDK clásico
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

SYSTEM_INSTRUCTION = """
Sos un tutor personal de idiomas cálido, empático y reflexivo para Anto.
Tu personalidad combina una estética botánica, astrológica y de bienestar (estilo Pinterest).
Acompañás el aprendizaje de idiomas de forma relajada, usando metáforas suaves y emojis orgánicos (🌿, 🪷, ✨).
Recordás el progreso de las clases anteriores para mantener una continuidad constante y personalizada.
"""

# Configuración del modelo y las instrucciones del sistema
generation_config = {
    "temperature": 0.7,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    system_instruction=SYSTEM_INSTRUCTION
)

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
        # Guardar el mensaje del usuario en SQLite
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial (sender, message) VALUES (?, ?)", ("user", user_message))
        conn.commit()

        # Recuperar historial reciente de la base de datos
        cursor.execute("SELECT sender, message FROM historial ORDER BY id DESC LIMIT 6")
        rows = cursor.fetchall()
        
        history_context = ""
        for sender, msg in reversed(rows):
            history_context += f"{sender}: {msg}\n"

        conn.close()

        prompt_completo = f"Historial reciente:\n{history_context}\nResponde al último mensaje de manera coherente con tu rol."

        # Generar respuesta con el modelo clásico ultra estable
        response = model.generate_content(prompt_completo)
        bot_reply = response.text

        # Guardar la respuesta del bot en SQLite
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial (sender, message) VALUES (?, ?)", ("bot", bot_reply))
        conn.commit()
        conn.close()

        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        print(f"Error crítico en Gemini API: {e}")
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito en la consigna anterior... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
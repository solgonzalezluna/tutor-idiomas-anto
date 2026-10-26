import os
import time
import sqlite3
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Configuración de la API Key
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

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

        # Sistema de reintento automático (Fallback inteligente)
        response = None
        max_intentos = 3
        
        for intento in range(max_intentos):
            try:
                response = client.models.generate_content(
                    model='gemini-1.5-pro',
                    contents=prompt_completo,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.7,
                    )
                )
                break # Si sale bien, rompemos el ciclo y seguimos
            except Exception as api_err:
                if intento == max_intentos - 1:
                    raise api_err # Si fallan todos los intentos, pasa al except general
                time.sleep(1) # Espera 1 segundo antes de reintentar

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
        # Respuesta elegante por si todo falla, sin mencionar fallas técnicas feas
        return jsonify({"reply": "Ay Anto, me quedé pensando un segundito en la consigna anterior... ¿Me lo repetirías de otra forma, por favor? 🌿✨"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
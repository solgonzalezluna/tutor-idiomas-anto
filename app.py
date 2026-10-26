import os
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

# Ejecutamos la creación de la tabla al arrancar
init_db()

@app.route("/")
def index():
    # Opcional: podrías cargar los mensajes anteriores de la BD si querés mostrarlos en pantalla
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

        # Recuperar un poco de historial reciente de la base de datos para darle contexto al modelo
        cursor.execute("SELECT sender, message FROM historial ORDER BY id DESC LIMIT 6")
        rows = cursor.fetchall()
        
        # Armamos el historial conversacional para pasárselo a Gemini
        history_context = ""
        for sender, msg in reversed(rows):
            history_context += f"{sender}: {msg}\n"

        conn.close()

        # Generar respuesta con Gemini usando el contexto acumulado
        prompt_completo = f"Historial reciente:\n{history_context}\nResponde al último mensaje de manera coherente con tu rol."

        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt_completo,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
        )
        
        bot_reply = response.text

        # Guardar la respuesta del bot en SQLite
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO historial (sender, message) VALUES (?, ?)", ("bot", bot_reply))
        conn.commit()
        conn.close()

        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        print(f"Error en Gemini API: {e}")
        return jsonify({"reply": "Ay Anto, mercurio retrógrado nos dio una pequeña pausa en la energía. Probá de nuevo en un segundito. 🪐💫"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
import os
from flask import Flask, request
import requests
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()
app = Flask(__name__)

# --- Config ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "romulo123") # inventa uno
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN") # te lo da Meta
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID") # te lo da Meta
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("Cargando modelo...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def buscar_en_supabase(pregunta):
    emb = model.encode(pregunta).tolist()
    res = supabase.rpc("match_documents", {
        "query_embedding": emb,
        "match_count": 5
    }).execute()
    if not res.data:
        return "No encontré eso en los Códigos y Acordadas cargadas. ¿Podés reformular?"

    # Deduplicar
    vistos = {}
    for doc in res.data:
        texto = doc.get('contenido') or doc.get('content') or ""
        fuente = doc.get('metadata',{}).get('fuente','Ley')
        key = f"{fuente}_{texto[:80]}"
        if key not in vistos:
            vistos[key] = doc

    top = sorted(vistos.values(), key=lambda x: x['similarity'], reverse=True)[:3]
    respuesta = f"Encontré esto sobre *{pregunta}*:\n\n"
    for i, d in enumerate(top, 1):
        meta = d.get('metadata',{})
        texto = (d.get('contenido') or d.get('content') or "")[:400]
        respuesta += f"*{i}. {meta.get('fuente','')} - {meta.get('articulo','')}*\n{texto}...\n\n"

    respuesta += "¿Querés agendar consulta con el estudio? Escribí *SI* y te paso horarios."
    return respuesta

def enviar_whatsapp(to, mensaje):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": mensaje}
    }
    r = requests.post(url, headers=headers, json=data)
    print(f"Enviado a {to}: {r.status_code} {r.text}")

# --- Webhooks de Meta ---
@app.route("/webhook", methods=["GET"])
def verify():
    # Meta te verifica con esto
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Token invalido", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' in entry:
            msg = entry['messages'][0]
            from_number = msg['from']
            texto_cliente = msg['text']['body']

            print(f"[{from_number}]: {texto_cliente}")

            if texto_cliente.upper() == "SI":
                enviar_whatsapp(from_number, "Perfecto 👨‍⚖️ El Dr Rómulo te puede atender mañana 9am o 3pm. ¿Cuál preferís? Escribime y te agendo. Estudio Echeverría - Capiatá")
            else:
                respuesta_ia = buscar_en_supabase(texto_cliente)
                enviar_whatsapp(from_number, respuesta_ia)
    except Exception as e:
        print(f"Error webhook: {e}")
    return "OK", 200

@app.route("/")
def home():
    return "AbogadoIA bot activo 🤖"

if __name__ == "__main__":
    app.run(port=5000)
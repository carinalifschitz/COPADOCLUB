import asyncio
import json
import os
import requests
import random
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE CREDENCIALES ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")

# --- BANCO DE RESPALDO ---
BANCO_RESPALDO = [
    {"pregunta": "¿Cuál fue el resultado final tras los 120 minutos en la final de Qatar 2022?", "opciones": ["3-3", "2-2", "4-4"], "correcta": "3-3"},
    {"pregunta": "¿Qué jugador argentino anotó el primer gol de penal?", "opciones": ["Lionel Messi", "Ángel Di María", "Julián Álvarez"], "correcta": "Lionel Messi"},
    {"pregunta": "¿En qué estadio se jugó la final de Qatar 2022?", "opciones": ["Lusail Iconic Stadium", "Al Bayt Stadium", "974 Stadium"], "correcta": "Lusail Iconic Stadium"}
]

def obtener_datos_final_mundo():
    fixture_id = 1137021
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
        "User-Agent": "Mozilla/5.0"
    }
    datos_partido = {"detalles": {}, "eventos": []}
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            datos_json = res.json()
            if "response" in datos_json and len(datos_json["response"]) > 0:
                partido = datos_json["response"][0]
                datos_partido["detalles"] = {
                    "local": partido["teams"]["home"]["name"],
                    "visitante": partido["teams"]["away"]["name"],
                    "goles_local": partido["goals"]["home"],
                    "goles_visitante": partido["goals"]["away"]
                }
                for evento in partido.get("events", [])[:20]:
                    datos_partido["eventos"].append({
                        "tiempo": evento["time"]["elapsed"],
                        "jugador": evento["player"]["name"] if evento.get("player") else "Desconocido",
                        "tipo": evento["type"]
                    })
    except:
        pass
    return datos_partido

@app.get("/", response_class=HTMLResponse)
async def obtener_interfaz():
    ruta_html = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(ruta_html, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Error: No se encontró index.html</h1>"

@app.get("/api/test")
async def probar_apis():
    reporte = {
        "api_futbol": "OK" if FOOTBALL_API_KEY else "Falta Key",
        "api_grok": "OK" if GROK_API_KEY else "Falta Key",
        "datos_recuperados": obtener_datos_final_mundo()
    }
    return reporte

@app.get("/api/trivias")
async def obtener_trivias():
    if not GROK_API_KEY:
        random.shuffle(BANCO_RESPALDO)
        return {"preguntas": BANCO_RESPALDO}

    contexto = obtener_datos_final_mundo()
    try:
        url_grok = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        
        # Modelo ajustado a 'grok-beta'
        payload = {
            "model": "grok-beta",
            "messages": [
                {"role": "system", "content": "Genera un JSON con clave 'preguntas' y 12 objetos: 'pregunta', 'opciones' (3), 'correcta'."},
                {"role": "user", "content": f"Trivia sobre: {json.dumps(contexto)}"}
            ],
            "temperature": 0.7
        }

        res = requests.post(url_grok, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
    except:
        pass
    
    random.shuffle(BANCO_RESPALDO)
    return {"preguntas": BANCO_RESPALDO}

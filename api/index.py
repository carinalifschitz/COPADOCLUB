import json
import os
import requests
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Definición de la instancia 'app' en el nivel superior para Vercel
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN ---
GROK_API_KEY = os.environ.get("GROK_API_KEY")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")

def obtener_datos_final_mundo():
    fixture_id = 1137021
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
        "User-Agent": "Mozilla/5.0"
    }
    datos_partido = {"detalles": {}, "jugadores": []}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            datos_json = res.json()
            if "response" in datos_json and len(datos_json["response"]) > 0:
                partido = datos_json["response"][0]
                datos_partido["detalles"] = {
                    "local": partido["teams"]["home"]["name"],
                    "visitante": partido["teams"]["away"]["name"]
                }
                for team in partido.get("players", []):
                    for player in team.get("players", []):
                        stats = player.get("statistics", [{}])[0]
                        datos_partido["jugadores"].append({
                            "nombre": player["player"]["name"],
                            "goles": stats.get("goals", {}).get("total", 0),
                            "faltas": stats.get("fouls", {}).get("committed", 0),
                            "atajadas": stats.get("goalkeeper", {}).get("saves", 0),
                            "goles_recibidos": stats.get("goalkeeper", {}).get("conceded", 0)
                        })
    except Exception as e:
        datos_partido["error"] = str(e)
    return datos_partido

@app.get("/")
async def home():
    return HTMLResponse("<h1>Servidor Activo</h1>")

@app.get("/api/test")
async def probar_apis():
    # Devuelve el objeto completo para verificar el funcionamiento
    return obtener_datos_final_mundo()

@app.get("/api/trivias")
async def obtener_trivias():
    if not GROK_API_KEY:
        return {"error": "API Key no configurada"}

    contexto = obtener_datos_final_mundo()
    
    try:
        url_grok = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        # Modelo corregido a grok-beta
        payload = {
            "model": "grok-beta", 
            "messages": [
                {"role": "system", "content": "Sos experto en fútbol. Responde solo con JSON: {'preguntas': [{'pregunta': '', 'opciones': [], 'correcta': ''}]}"},
                {"role": "user", "content": f"Trivia detallada sobre los datos: {json.dumps(contexto)}"}
            ],
            "temperature": 0.7
        }
        res = requests.post(url_grok, json=payload, headers=headers, timeout=10)
        
        if res.status_code == 200:
            # Estructura corregida: choices[0]
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
        else:
            return {"error": f"Error API Grok: {res.text}"}
    except Exception as e:
        return {"error": f"Error generando trivia: {str(e)}"}

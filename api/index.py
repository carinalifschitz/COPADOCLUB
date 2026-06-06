import json
import os
import requests
import random
from fastapi import FastAPI
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
    datos_partido = {"detalles": {}, "jugadores": [], "eventos": []}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            datos_json = res.json()
            if "response" in datos_json and len(datos_json["response"]) > 0:
                p = datos_json["response"][0]
                datos_partido["detalles"] = {
                    "local": p["teams"]["home"]["name"],
                    "visitante": p["teams"]["away"]["name"]
                }
                # --- EXTRACCIÓN DE JUGADORES Y ESTADÍSTICAS ---
                for team in p.get("players", []):
                    for player in team.get("players", []):
                        stats = player.get("statistics", [{}])[0]
                        datos_partido["jugadores"].append({
                            "nombre": player["player"]["name"],
                            "goles": stats.get("goals", {}).get("total", 0),
                            "faltas": stats.get("fouls", {}).get("committed", 0),
                            "atajadas": stats.get("goalkeeper", {}).get("saves", 0),
                            "goles_recibidos": stats.get("goalkeeper", {}).get("conceded", 0)
                        })
                # Eventos básicos
                for evento in p.get("events", [])[:10]:
                    datos_partido["eventos"].append({"tipo": evento["type"], "jugador": evento["player"]["name"]})
    except:
        pass
    return datos_partido

@app.get("/api/test")
async def probar_apis():
    # Devuelve el XML/JSON completo para verificar datos y Grok
    datos = obtener_datos_final_mundo()
    grok_status = "No configurado"
    if GROK_API_KEY:
        try:
            url_grok = "https://api.x.ai/v1/chat/completions"
            payload = {"model": "grok-beta", "messages": [{"role": "user", "content": "Hola"}]}
            res = requests.post(url_grok, json=payload, headers={"Authorization": f"Bearer {GROK_API_KEY}"}, timeout=5)
            grok_status = f"HTTP {res.status_code}"
        except Exception as e:
            grok_status = str(e)
    return {"grok_status": grok_status, "datos_futbol": datos}

@app.get("/api/trivias")
async def obtener_trivias():
    contexto = obtener_datos_final_mundo()
    try:
        url_grok = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-beta", 
            "messages": [
                {"role": "system", "content": "Genera un JSON con clave 'preguntas' y 12 objetos: 'pregunta', 'opciones' (3), 'correcta'."},
                {"role": "user", "content": f"Usa estos datos de jugadores y partido para crear trivia: {json.dumps(contexto)}"}
            ],
            "temperature": 0.7
        }
        res = requests.post(url_grok, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
    except:
        pass
    return {"error": "Error al contactar con Grok o datos insuficientes"}

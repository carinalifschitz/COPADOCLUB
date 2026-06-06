import json
import os
import requests
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# 1. Definición obligatoria al inicio para Vercel
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            data = res.json()
            if "response" in data and len(data["response"]) > 0:
                p = data["response"][0]
                datos_partido["detalles"] = {"local": p["teams"]["home"]["name"], "visitante": p["teams"]["away"]["name"]}
                # Extraer jugadores correctamente
                for team in p.get("players", []):
                    for player in team.get("players", []):
                        stats = player.get("statistics", [{}])[0]
                        datos_partido["jugadores"].append({
                            "nombre": player["player"]["name"],
                            "goles": stats.get("goals", {}).get("total", 0),
                            "faltas": stats.get("fouls", {}).get("committed", 0),
                            "atajadas": stats.get("goalkeeper", {}).get("saves", 0)
                        })
    except: pass
    return datos_partido

@app.get("/")
async def root():
    ruta_html = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(ruta_html, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<h1>Error: No se pudo cargar el archivo index.html. Detalle: {str(e)}</h1>"

@app.get("/api/test")
async def probar_apis():
    return {"status": "ok", "datos": obtener_datos_final_mundo()}

@app.get("/api/trivias")
async def obtener_trivias():
    contexto = obtener_datos_final_mundo()
    url_grok = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "grok-beta",
        "messages": [
            {"role": "system", "content": "Responde solo con JSON: {'preguntas': [{'pregunta': '', 'opciones': [], 'correcta': ''}]}"},
            {"role": "user", "content": f"Trivia sobre: {json.dumps(contexto)}"}
        ]
    }
    try:
        res = requests.post(url_grok, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            # CORRECCIÓN: Acceso a index 0
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
    except: pass
    return {"error": "Fallo en IA"}

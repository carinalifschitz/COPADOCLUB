import json
import os
import requests
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

GROK_API_KEY = os.environ.get("GROK_API_KEY")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")

def obtener_datos_final_mundo():
    fixture_id = 1137021
    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    headers = {"x-apisports-key": FOOTBALL_API_KEY or "", "User-Agent": "Mozilla/5.0"}
    datos_partido = {"detalles": {}, "jugadores": []}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "response" in data and len(data["response"]) > 0:
                p = data["response"][0]
                datos_partido["detalles"] = {"local": p["teams"]["home"]["name"], "visitante": p["teams"]["away"]["name"]}
                
                # Buscamos jugadores en 'players' (la estructura estándar)
                for team in p.get("players", []):
                    for player in team.get("players", []):
                        stats = player.get("statistics", [{}])[0]
                        datos_partido["jugadores"].append({
                            "nombre": player["player"]["name"],
                            "goles": stats.get("goals", {}).get("total", 0),
                            "atajadas": stats.get("goalkeeper", {}).get("saves", 0)
                        })
    except Exception as e:
        datos_partido["error_api_futbol"] = str(e)
    return datos_partido

@app.get("/", response_class=HTMLResponse)
async def root():
    ruta_html = os.path.join(os.path.dirname(__file__), "index.html")
    with open(ruta_html, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/test")
async def probar_apis():
    datos_futbol = obtener_datos_final_mundo()
    estado_grok = "No probado"
    
    # Test real de Grok
    if GROK_API_KEY:
        try:
            url_grok = "https://api.x.ai/v1/chat/completions"
            payload = {"model": "grok-beta", "messages": [{"role": "user", "content": "Hola, ¿funcionas?"}]}
            res = requests.post(url_grok, json=payload, headers={"Authorization": f"Bearer {GROK_API_KEY}"}, timeout=10)
            estado_grok = f"HTTP {res.status_code} - {res.text[:50]}"
        except Exception as e:
            estado_grok = str(e)
    
    return {"grok_status": estado_grok, "datos_futbol": datos_futbol}

@app.get("/api/trivias")
async def obtener_trivias():
    contexto = obtener_datos_final_mundo()
    
    # Si la lista de jugadores está vacía, forzamos un aviso para debuggear
    if not contexto.get("jugadores"):
        return {"error": "No se pudieron obtener jugadores de la API de fútbol"}

    try:
        url_grok = "https://api.x.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "grok-beta",
            "messages": [
                {"role": "system", "content": "Responde solo JSON: {'preguntas': [{'pregunta': '', 'opciones': [], 'correcta': ''}]}"},
                {"role": "user", "content": f"Crea 12 preguntas de trivia con estos datos: {json.dumps(contexto)}"}
            ]
        }
        res = requests.post(url_grok, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
        return {"error": f"Error Grok {res.status_code}: {res.text}"}
    except Exception as e:
        return {"error": f"Excepción IA: {str(e)}"}

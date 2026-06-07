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
    # ID de la final Qatar 2022
    url = "https://v3.football.api-sports.io/fixtures?id=1137021"
    headers = {"x-apisports-key": FOOTBALL_API_KEY or "", "User-Agent": "Mozilla/5.0"}
    
    resultado = {"detalles": {}, "jugadores": []}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "response" in data and data["response"]:
                p = data["response"][0]
                resultado["detalles"] = {
                    "local": p["teams"]["home"]["name"], 
                    "visitante": p["teams"]["away"]["name"]
                }
                
                # Extracción detallada de jugadores
                if "players" in p:
                    for team in p["players"]:
                        for player in team.get("players", []):
                            stats = player.get("statistics", [{}])[0]
                            resultado["jugadores"].append({
                                "nombre": player["player"]["name"],
                                "goles": stats.get("goals", {}).get("total", 0),
                                "faltas": stats.get("fouls", {}).get("committed", 0),
                                "atajadas": stats.get("goalkeeper", {}).get("saves", 0)
                            })
    except Exception as e:
        resultado["error_api"] = str(e)
    return resultado

@app.get("/", response_class=HTMLResponse)
async def root():
    ruta_html = os.path.join(os.path.dirname(__file__), "index.html")
    with open(ruta_html, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/test")
async def probar_apis():
    datos = obtener_datos_final_mundo()
    grok_res = {"status": "No configurado"}
    
    if GROK_API_KEY:
        try:
            # CORRECCIÓN: Cambiado modelo a "grok-2"
            res = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "grok-4.3", 
                    "messages": [{"role": "user", "content": "Hola"}]
                },
                timeout=10
            )
            grok_res = {"status": res.status_code, "body": res.text}
        except Exception as e:
            grok_res = {"error": str(e)}
            
    return {"grok": grok_res, "datos_futbol": datos}

@app.get("/api/trivias")
async def obtener_trivias():
    datos = obtener_datos_final_mundo()
    
    info_jugadores = datos.get('jugadores', [])[:15]
    prompt_contenido = f"Crea 5 preguntas de trivia basadas en estos jugadores: {json.dumps(info_jugadores)}"
    
    payload = {
        "model": "grok-4.3",
        "messages": [
            {"role": "user", "content": "Genera un JSON con 15 preguntas de trivia sobre fútbol. Formato: {'preguntas': [{'pregunta': '...', 'opciones': ['A','B','C'], 'correcta': '...'}]}"}
        ]
    }
    
    try:
        res = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        if res.status_code == 200:
            texto = res.json()["choices"][0]["message"]["content"].replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
        return {"error": f"Grok falló {res.status_code}", "detalle": res.text}
    except Exception as e:
        return {"error": str(e)}

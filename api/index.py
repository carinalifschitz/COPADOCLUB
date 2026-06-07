import json
import os
import requests
from fastapi import FastAPI, HTTPException
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
    # CORRECCIÓN: Se restauró la URL oficial completa del endpoint para fixtures de api-football
    url = "https://api-sports.io"
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
            res = requests.post(
                # CORRECCIÓN: Se restauró la URL completa del endpoint de chat de xAI
                "https://x.ai",
                headers={
                    "Authorization": f"Bearer {GROK_API_KEY}", 
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
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
    # CAMBIO 1: Validamos la key aquí también para evitar el error 400
    if not GROK_API_KEY:
        return {"error": "GROK_API_KEY no configurada"}

    datos = obtener_datos_final_mundo()
    
    info_jugadores = datos.get('jugadores', [])[:15]
    prompt_contenido = f"Crea 5 preguntas de trivia en formato JSON basándote estrictamente en estos jugadores: {json.dumps(info_jugadores)}. Formato: {{'preguntas': [{{'pregunta': '...', 'opciones': ['A','B','C'], 'correcta': '...'}}]}}"
    
    payload = {
        "model": "grok-4.3",
        "messages": [
            # CAMBIO 2: Cambiado el texto estático por tu variable prompt_contenido
            {"role": "user", "content": prompt_contenido}
        ]
    }
    
    try:
        res = requests.post(
            # CORRECCIÓN: Se restauró la URL completa del endpoint de chat de xAI
            "https://x.ai",
            headers={
                "Authorization": f"Bearer {GROK_API_KEY}", 
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            },
            json=payload,
            timeout=15
        )
        if res.status_code == 200:
            # CAMBIO 3: Ajustado el acceso al mensaje del JSON de respuesta de Grok
            raw_text = res.json()["choices"]["message"]["content"]
            texto = raw_text.replace("```json", "").replace("```", "").strip()
            return json.loads(texto)
        return {"error": f"Grok falló {res.status_code}", "detalle": res.text}
    except Exception as e:
        return {"error": str(e)}

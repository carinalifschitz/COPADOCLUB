import json
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from openai import OpenAI

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

# Inicialización segura apuntando al motor gratuito de Groq
grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(
        api_key=GROK_API_KEY,
        # CAMBIO: URL base oficial para conectar con la API de Groq
        base_url="https://groq.com"
    )

def obtener_datos_final_mundo():
    url = "https://api-sports.io"
    headers = {"x-apisports-key": FOOTBALL_API_KEY or "", "User-Agent": "Mozilla/5.0"}
    
    resultado = {"detalles": {}, "jugadores": []}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if "response" in data and data["response"]:
                p = data["response"]
                resultado["detalles"] = {
                    "local": p["teams"]["home"]["name"], 
                    "visitante": p["teams"]["away"]["name"]
                }
                
                if "players" in p:
                    for team in p["players"]:
                        for player in team.get("players", []):
                            stats = player.get("statistics", [{}])
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
    
    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                # CAMBIO: Usamos uno de los modelos gratuitos más potentes de Groq
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Hola"}]
            )
            grok_res = {"status": 200, "body": response.choices.message.content}
        except Exception as e:
            grok_res = {"error": str(e)}
            
    return {"grok": grok_res, "datos_futbol": datos}

@app.get("/api/trivias")
async def obtener_trivias():
    if not grok_client:
        return {"error": "GROK_API_KEY no configurada"}

    datos = obtener_datos_final_mundo()
    info_jugadores = datos.get('jugadores', [])[:15]
    prompt_contenido = f"Crea 5 preguntas de trivia en formato JSON basándote estrictamente en estos jugadores: {json.dumps(info_jugadores)}. Formato: {{'preguntas': [{{'pregunta': '...', 'opciones': ['A','B','C'], 'correcta': '...'}}]}}"
    
    try:
        response = grok_client.chat.completions.create(
            # CAMBIO: Usamos uno de los modelos gratuitos más potentes de Groq
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_contenido}],
            timeout=15
        )
        raw_text = response.choices.message.content
        texto = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        return {"error": str(e)}

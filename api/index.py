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

# Inicialización corregida con la URL base correcta para el cliente de Groq
grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

def obtener_datos_final_mundo():
    # 1. Primero obtenemos el fixture para confirmar que el partido existe
    base_url = "https://v3.football.api-sports.io"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY or "",
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    # ID del partido
    fixture_id = "1035570"
    resultado = {"detalles": {}, "jugadores": []}
    
    try:
        # AQUI ESTÁ EL CAMBIO: Llamamos al endpoint de jugadores
        res = requests.get(f"{base_url}/fixtures/players", headers=headers, params={"fixture": fixture_id}, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if "response" in data and data["response"]:
                # La estructura de /fixtures/players devuelve una lista de equipos
                for team_data in data["response"]:
                    for player in team_data.get("players", []):
                        stats = player.get("statistics", [{}])[0]
                        resultado["jugadores"].append({
                            "nombre": player["player"]["name"],
                            "goles": stats.get("games", {}).get("minutes", 0), # Ejemplo
                            "posicion": player.get("statistics", [{}])[0].get("games", {}).get("position", "N/A"),
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
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Hola"}]
            )
            grok_res = {"status": 200, "body": response.choices[0].message.content}
        except Exception as e:
            grok_res = {"error": str(e)}
            
    return {"grok": grok_res, "datos_futbol": datos}

@app.get("/api/trivias")
async def obtener_trivias():
    if not grok_client:
        return {"error": "GROK_API_KEY no configurada"}

    datos = obtener_datos_final_mundo()
    info_jugadores = datos.get('jugadores', [])[:15]
    prompt_contenido = f"Crea 10 preguntas de trivia en formato JSON basándote estrictamente en estos jugadores: {json.dumps(info_jugadores)}. Formato: {{'preguntas': [{{'pregunta': '...', 'opciones': ['A','B','C'], 'correcta': '...'}}]}}"
    
    try:
        response = grok_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt_contenido}],
            timeout=15
        )
        raw_text = response.choices[0].message.content
        texto = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto)
    except Exception as e:
        return {"error": str(e)}

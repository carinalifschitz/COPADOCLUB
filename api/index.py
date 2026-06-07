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

grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(
        api_key=GROK_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

def obtener_datos_final_mundo():
    base_url = "https://v3.football.api-sports.io"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY or "",
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    resultado = {"detalles": {}, "jugadores": []}
    
    try:
        # CAMBIO: Buscamos el último partido jugado en la Premier League (ID 39)
        # Esto asegura que el ID sea reciente y tenga estadísticas disponibles
        url_search = f"{base_url}/fixtures?league=39&season=2025&last=1"
        res_search = requests.get(url_search, headers=headers, timeout=10)
        
        if res_search.status_code == 200:
            data_search = res_search.json()
            if data_search.get("response"):
                fixture_id = data_search["response"][0]["fixture"]["id"]
                resultado["detalles"] = {
                    "local": data_search["response"][0]["teams"]["home"]["name"],
                    "visitante": data_search["response"][0]["teams"]["away"]["name"]
                }
                
                # Ahora consultamos los jugadores con el ID obtenido dinámicamente
                url_players = f"{base_url}/fixtures/players?fixture={fixture_id}"
                res_players = requests.get(url_players, headers=headers, timeout=10)
                
                if res_players.status_code == 200:
                    data_players = res_players.json()
                    for team in data_players.get("response", []):
                        for player in team.get("players", []):
                            stats = player.get("statistics", [{}])[0]
                            resultado["jugadores"].append({
                                "nombre": player["player"]["name"],
                                "posicion": stats.get("games", {}).get("position", "N/A"),
                                "minutos": stats.get("games", {}).get("minutes", 0),
                                "calificacion": stats.get("games", {}).get("rating", "N/A"),
                                "goles": stats.get("goals", {}).get("total", 0),
                                "asistencias": stats.get("goals", {}).get("assists", 0),
                                "tiros_total": stats.get("shots", {}).get("total", 0),
                                "tiros_al_arco": stats.get("shots", {}).get("on", 0),
                                "pases_completados": stats.get("passes", {}).get("accuracy", "0%"),
                                "faltas_cometidas": stats.get("fouls", {}).get("committed", 0),
                                "faltas_recibidas": stats.get("fouls", {}).get("drawn", 0),
                                "tarjetas_amarillas": stats.get("cards", {}).get("yellow", 0),
                                "tarjetas_rojas": stats.get("cards", {}).get("red", 0),
                                "atajadas": stats.get("goalkeeper", {}).get("saves", 0)
                            })
    except Exception as e:
        resultado["error"] = str(e)
        
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

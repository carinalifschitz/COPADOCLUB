import asyncio
import json
import os
import requests
import random
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

# --- BANCO DE RESPALDO INTEGRADO ---
BANCO_RESPALDO = [
    {"pregunta": "¿Cuál fue el resultado final tras los 120 minutos en la final de Qatar 2022?", "opciones": ["3-3", "2-2", "4-4"], "correcta": "3-3"},
    {"pregunta": "¿Qué jugador argentino anotó el primer gol de penal?", "opciones": ["Lionel Messi", "Ángel Di María", "Julián Álvarez"], "correcta": "Lionel Messi"},
    {"pregunta": "¿En qué estadio se jugó la final de Qatar 2022?", "opciones": ["Lusail Iconic Stadium", "Al Bayt Stadium", "974 Stadium"], "correcta": "Lusail Iconic Stadium"}
]

def obtener_datos_final_mundo():
    url_base = "https://api-sports.io"
    headers = {
        "x-rapidapi-host": "v3.football.api-sports.io",
        "x-rapidapi-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
        "x-apisports-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
    }
    datos_partido = {"detalles": {}, "eventos": []}
    
    try:
        url_fixture = f"{url_base}/fixtures?id=970030"
        res = requests.get(url_fixture, headers=headers, timeout=4)
        
        if res.status_code == 200:
            datos_json = res.json()
            if "response" in datos_json and len(datos_json["response"]) > 0:
                partido = datos_json["response"][0]
                
                datos_partido["detalles"] = {
                    "local": partido["teams"]["home"]["name"],
                    "visitante": partido["teams"]["away"]["name"],
                    "goles_local": partido["goals"]["home"],
                    "goles_visitante": partido["goals"]["away"],
                    "estadio": partido["fixture"]["venue"]["name"],
                    "arbitro": partido["fixture"]["referee"]
                }
                
                for evento in partido.get("events", [])[:15]:
                    datos_partido["eventos"].append({
                        "tiempo": evento["time"]["elapsed"],
                        "equipo": evento["team"]["name"],
                        "jugador": evento["player"]["name"] if evento.get("player") else "Desconocido",
                        "tipo": evento["type"],
                        "detalle": evento["detail"]
                    })
    except Exception:
        pass
        
    return datos_partido

# --- ENDPOINT DE CONSULTA ---
@app.get("/api/trivias")
async def obtener_trivias_http():
    if not GROK_API_KEY:
        return {"preguntas": random.sample(BANCO_RESPALDO, len(BANCO_RESPALDO))}

    contexto_mundial = obtener_datos_final_mundo()
    
    if not contexto_mundial.get("detalles"):
        contexto_mundial = {
            "detalles": {"local": "Argentina", "visitante": "Francia", "goles_local": 3, "goles_visitante": 3, "estadio": "Lusail Iconic Stadium"},
            "eventos": [
                {"tiempo": 23, "equipo": "Argentina", "jugador": "Lionel Messi", "tipo": "Goal"},
                {"tiempo": 36, "equipo": "Argentina", "jugador": "Ángel Di María", "tipo": "Goal"},
                {"tiempo": 80, "equipo": "Francia", "jugador": "Kylian Mbappé", "tipo": "Goal"}
            ]
        }

    try:
        url_grok = "https://api.x.ai/v1/chat/completions"  # <-- Endpoint oficial corregido
        headers_grok = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt_sistema = (
            "Sos un historiador deportivo experto en Copas del Mundo. Tu única tarea es responder con un objeto JSON válido. "
            "Este JSON debe tener una clave única llamada 'preguntas' que contenga un array de objetos. "
            "No devuelvas bloques Markdown ni texto explicativo extra."
        )
        
        prompt_usuario = (
            f"Basándote estrictamente en este JSON con datos reales de la Final de Qatar 2022 extraídos de la API: {json.dumps(contexto_mundial)}. "
            "Generá un array de exactamente 12 preguntas de trivia variadas sobre este partido. "
            "Estructura requerida por objeto del array: pregunta, opciones (array de 3 strings), correcta (debe coincidir exactamente con una opción)."
        )

        payload = {
            "model": "grok-2", 
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            "temperature": 0.7
        }

        res = requests.post(url_grok, json=payload, headers=headers_grok, timeout=6)
        
        if res.status_code == 200:
            datos_api = res.json()
            texto_json = datos_api["choices"]["message"]["content"]
            datos_finales = json.loads(texto_json)
            
            if "preguntas" in datos_finales and len(datos_finales["preguntas"]) > 0:
                preguntas_mezcladas = datos_finales["preguntas"]
                random.shuffle(preguntas_mezcladas)
                return {"preguntas": preguntas_mezcladas}
                
    except Exception:
        pass
    
    copia_respaldo = list(BANCO_RESPALDO)
    random.shuffle(copia_respaldo)
    return {"preguntas": copia_respaldo}

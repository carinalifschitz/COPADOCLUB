import asyncio
import json
import os
import requests
import random
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse # <-- Importante para devolver el HTML

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
    # ID Corregido para la Final de Qatar 2022 (Argentina vs Francia)
    url = "https://v3.football.api-sports.io/fixtures?id=970031"
    
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
        "x-rapidapi-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    # ... (el resto de la función queda exactamente igual)
    
    datos_partido = {"detalles": {}, "eventos": []}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            content_type = res.headers.get("Content-Type", "")
            if "application/json" in content_type:
                datos_json = res.json()
                
                # Verificamos si la respuesta contiene datos reales del partido
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
                    
                    # Guardamos las incidencias principales del partido
                    for evento in partido.get("events", [])[:15]:
                        datos_partido["eventos"].append({
                            "tiempo": evento["time"]["elapsed"],
                            "equipo": evento["team"]["name"],
                            "jugador": evento["player"]["name"] if evento.get("player") else "Desconocido",
                            "tipo": evento["type"],
                            "detalle": evento["detail"]
                        })
                        
                    return datos_partido
    except Exception:
        pass
        
    return datos_partido
# --- NUEVO: ENDPOINT PARA MOSTRAR LA WEB ---
@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
async def obtener_interfaz():
    # Lee el archivo index.html que pusimos dentro de la misma carpeta api/
    ruta_html = os.path.join(os.path.dirname(__file__), "index.html")
    try:
        with open(ruta_html, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Error: No se encontró el archivo index.html dentro de la carpeta api/</h1>"
# --- ENDPOINT DE DIAGNÓSTICO (Para saber qué falla) ---
@app.get("/api/test")
# --- ENDPOINT DE DIAGNÓSTICO DEFINITIVO ---
@app.get("/api/test")
async def probar_apis():
    reporte = {
        "estado_credenciales": {
            "grok_key_detectada": GROK_API_KEY is not None and GROK_API_KEY != "",
            "football_key_detectada": FOOTBALL_API_KEY is not None and FOOTBALL_API_KEY != ""
        },
        "prueba_api_futbol_partido": {"estado": "Sin probar", "datos_recuperados": None, "error": None},
        "prueba_grok_ia": {"estado": "Sin probar", "respuesta_grok": None, "error": None}
    }

    # 1. Probar la consulta del partido real (Final Qatar ID: 970030)
    try:
        url = "https://v3.football.api-sports.io/fixtures?id=970031"
        headers = {
            "x-apisports-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
            "x-rapidapi-key": FOOTBALL_API_KEY if FOOTBALL_API_KEY else "",
            "User-Agent": "Mozilla/5.0"
        }
        res = requests.get(url, headers=headers, timeout=6)
        reporte["prueba_api_futbol_partido"]["estado"] = f"HTTP {res.status_code}"
        
        if res.status_code == 200:
            datos_json = res.json()
            # Si la API devuelve un error interno en su JSON (ej. límite de cuota superado)
            if "errors" in datos_json and datos_json["errors"]:
                reporte["prueba_api_futbol_partido"]["error"] = datos_json["errors"]
            elif "response" in datos_json and len(datos_json["response"]) > 0:
                # Si encuentra el partido, guardamos un resumen de lo que capturó
                partido = datos_json["response"][0]
                reporte["prueba_api_futbol_partido"]["datos_recuperados"] = {
                    "partido": f"{partido['teams']['home']['name']} vs {partido['teams']['away']['name']}",
                    "goles": f"{partido['goals']['home']}-{partido['goals']['away']}",
                    "cantidad_eventos": len(partido.get("events", []))
                }
            else:
                reporte["prueba_api_futbol_partido"]["error"] = "La API respondió bien, pero el array 'response' vino vacío. ¿El ID 970030 está disponible en tu plan?"
    except Exception as e:
        reporte["prueba_api_futbol_partido"]["estado"] = "Error de ejecución en Python"
        reporte["prueba_api_futbol_partido"]["error"] = str(e)

    # 2. Probar Grok IA
    if not GROK_API_KEY:
        reporte["prueba_grok_ia"]["estado"] = "Falta la clave en Vercel"
    else:
        try:
            url_grok = "https://api.x.ai/v1/chat/completions"
            headers_grok = {
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "grok-2-1212", 
                "messages": [{"role": "user", "content": "Responde con la palabra OK"}],
                "max_tokens": 5
            }
            res = requests.post(url_grok, json=payload, headers=headers_grok, timeout=6)
            reporte["prueba_grok_ia"]["estado"] = f"HTTP {res.status_code}"
            if res.status_code == 200:
                reporte["prueba_grok_ia"]["respuesta_grok"] = res.json()["choices"][0]["message"]["content"].strip()
            else:
                reporte["prueba_grok_ia"]["error"] = res.json()
        except Exception as e:
            reporte["prueba_grok_ia"]["estado"] = "Error de conexión con X.AI"
            reporte["prueba_grok_ia"]["error"] = str(e)

    return reporte
# --- ENDPOINT DE DATOS DE LA TRIVIA ---
@app.get("/api/trivias")
@app.get("/trivias")
async def obtener_trivias_http():
    # Si falta la clave de Grok, usamos el respaldo pero extendido para que no sea aburrido
    if not GROK_API_KEY:
        copia_respaldo = list(BANCO_RESPALDO)
        random.shuffle(copia_respaldo)
        return {"preguntas": copia_respaldo}

    contexto_mundial = obtener_datos_final_mundo()
    
    # Si la API de fútbol falla o se agotan los créditos, usamos un contexto real hardcodeado
    if not contexto_mundial.get("detalles") or len(contexto_mundial.get("eventos", [])) == 0:
        contexto_mundial = {
            "detalles": {
                "local": "Argentina", 
                "visitante": "Francia", 
                "goles_local": 3, 
                "goles_visitante": 3, 
                "estadio": "Lusail Iconic Stadium",
                "arbitro": "Szymon Marciniak"
            },
            "eventos": [
                {"tiempo": 23, "equipo": "Argentina", "jugador": "Lionel Messi", "tipo": "Goal", "detalle": "Penalty"},
                {"tiempo": 36, "equipo": "Argentina", "jugador": "Ángel Di María", "tipo": "Goal", "detalle": "Normal Goal"},
                {"tiempo": 80, "equipo": "Francia", "jugador": "Kylian Mbappé", "tipo": "Goal", "detalle": "Penalty"},
                {"tiempo": 81, "equipo": "Francia", "jugador": "Kylian Mbappé", "tipo": "Goal", "detalle": "Normal Goal"},
                {"tiempo": 108, "equipo": "Argentina", "jugador": "Lionel Messi", "tipo": "Goal", "detalle": "Normal Goal"},
                {"tiempo": 118, "equipo": "Francia", "jugador": "Kylian Mbappé", "tipo": "Goal", "detalle": "Penalty"}
            ]
        }

    try:
        url_grok = "https://api.x.ai/v1/chat/completions"
        headers_grok = {
            "Authorization": f"Bearer {GROK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt_sistema = (
            "Sos un historiador deportivo experto en la Copa del Mundo Qatar 2022. Tu única tarea es responder con un objeto JSON válido. "
            "El JSON debe tener una estructura exacta con una clave llamada 'preguntas' que contenga un array de objetos. "
            "Cada objeto debe tener: 'pregunta', 'opciones' (un array de exactamente 3 strings) y 'correcta' (un string que coincida exactamente con una de las opciones). "
            "No incluyas texto fuera del JSON, ni bloques de código markdown."
        )
        
        prompt_usuario = (
            f"Basándote en estos datos históricos reales del partido: {json.dumps(contexto_mundial)}. "
            "Generá exactamente 12 preguntas de trivia variadas sobre las incidencias, goles, tiempos, jugadores y detalles del partido. "
            "Asegurate de cambiar el orden de la opción correcta en las respuestas para que no siempre sea la primera."
        )

        payload = {
            "model": "grok-2", 
            "messages": [
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            "temperature": 0.7
        }

        res = requests.post(url_grok, json=payload, headers=headers_grok, timeout=8)
        
        if res.status_code == 200:
            datos_api = res.json()
            texto_json = datos_api["choices"]["message"]["content"].strip()
            
            # --- LIMPIADOR DE MARKDOWN EMERGENCIAL ---
            # Si Grok devuelve el JSON envuelto en ```json ... ``` lo limpiamos manualmente
            if texto_json.startswith("```"):
                lineas = texto_json.split("\n")
                if lineas[0].startswith("```"):
                    lineas = lineas[1:]
                if lineas[-1].startswith("```"):
                    lineas = lineas[:-1]
                texto_json = "\n".join(lineas).strip()
            
            datos_finales = json.loads(texto_json)
            
            if "preguntas" in datos_finales and len(datos_finales["preguntas"]) > 0:
                preguntas_mezcladas = datos_finales["preguntas"]
                random.shuffle(preguntas_mezcladas)
                return {"preguntas": preguntas_mezcladas}
                
    except Exception as e:
        print(f"Error detectado en la generación: {str(e)}")
        pass
    
    # Banco de respaldo barajado por si ocurre algún fallo de conexión con las APIs externas
    copia_respaldo = list(BANCO_RESPALDO)
    random.shuffle(copia_respaldo)
    return {"preguntas": copia_respaldo}

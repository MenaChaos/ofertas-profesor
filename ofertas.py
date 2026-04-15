import requests
import os
import time
import random

# --- CONFIGURACIÓN DE PERSONALIDAD ---
FRASES_COOP = [
    "¡Buenas noticias, Jenkins! He encontrado un experimento grupal. Es casi tan peligroso como aquella vez que envié a la tripulación anterior a una avispa gigante... ¡Casi!",
    "¡Atención, tripulación! Este juego requiere trabajar en equipo. Si logran cooperar mejor que Fry y Bender cuando encuentran una moneda, ¡podrían sobrevivir!",
    "¡Grandes noticias! Si juegan esto juntos en el servidor, sus posibilidades de supervivencia aumentan un 0.004%. ¡A celebrar!",
    "¡Por el dulce néctar de Slurm! He hallado un juego cooperativo. ¡Intenten no matarse entre ustedes antes de que los enemigos lo hagan!"
]

FRASES_SOLO = [
    "¡Buenas noticias! He encontrado un juego para jugar en soledad absoluta. ¡Justo como paso mis noches en el laboratorio de clones prohibidos!",
    "¡Ah, el dulce aislamiento! Este juego es perfecto para ignorar al resto del universo. ¡Es como meterse en mi propia Cámara de la Muerte!",
    "¡Por la gloria de la ciencia! Un juego para un solo sujeto de prueba. Si las cosas salen mal, siempre puedo reemplazarlos con un clon llamado Cubert.",
    "¡Buenas noticias! Este juego es individual porque nadie más soportaría sus tácticas de juego, Jenkins."
]

FRASES_DESPEDIDA = [
    "Los acompañaría a jugar, pero ya me puse la pijama.",
    "Me gustaría ver cómo fallan en este experimento, pero tengo que ir a organizar mi colección de cables de distintas longitudes.",
    "¡En fin, me voy a dormir! Si el laboratorio explota, no me despierten.",
    "¡Ya hice suficiente por hoy! Mañana enviaré a alguien más a una misión suicida."
]

def obtener_datos_steam(app_id):
    """Obtiene datos directamente de Steam usando región Chile (cc=cl)."""
    try:
        # cc=cl fuerza precios en CLP, l=spanish para categorías en español
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res = requests.get(url, timeout=10).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            
            # Extraemos géneros para que la IA sepa de qué trata el juego
            generos = [g['description'] for g in data.get('genres', [])]
            generos_str = ", ".join(generos) if generos else "Desconocido"
            
            # Extraemos el precio formateado directamente (ej: CLP$ 3.725)
            precio_clp = data.get('price_overview', {}).get('final_formatted', 'Gratis o N/A')
            
            # Clasificación multijugador
            categorias = [cat['id'] for cat in data.get('categories', [])]
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            
            return es_multi, generos_str, precio_clp
        return None, "", ""
    except:
        return None, "", ""

def profesor_habla(nombre, generos, score, modo):
    """Usa Gemini para inventar una reseña basada en datos, no en traducciones."""
    frase_base = random.choice(FRASES_COOP if modo == "COOPERATIVA" else FRASES_SOLO)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # El secreto: Le pedimos que use su conocimiento del juego basándose en el nombre y géneros
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Usa OBLIGATORIAMENTE esta frase inicial: '{frase_base}'. "
        f"Escribe una reseña corta (máximo 3 líneas), sarcástica y graciosa sobre el juego '{nombre}'. "
        f"Contexto científico: Géneros: {generos}. Calificación Metacritic: {score}/100. "
        f"Habla directamente a 'los Jenkins'. No menciones que eres una IA. Responde en español."
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=12)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    # Si la IA falla, un mensaje genérico del profesor para no romper el estilo
    return f"{frase_base}\n\n¡Rayos! Mi detector de reseñas se quedó sin Slurm para '{nombre}', pero mi instinto científico dice que por ese precio vale la pena el riesgo."

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi = []
    candidatos_solo = []
    
    # Análisis de ofertas (CheapShark nos da la lista inicial y el Metacritic Score)
    for pagina in range(5):
        url_ofertas = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url_ofertas).json()
            if not ofertas: break
            for o in ofertas:
                if not o.get('steamAppID'): continue
                
                # Obtener datos reales de Chile
                es_multi, generos, precio_clp = obtener_datos_steam(o['steamAppID'])
                
                if es_multi is not None:
                    o['generos'] = generos
                    o['precio_clp'] = precio_clp
                    o['score'] = int(o.get('metacriticScore', 0))
                    o['ahorro'] = float(o.get('savings', 0))
                    
                    if es_multi: candidatos_multi.append(o)
                    else: candidatos_solo.append(o)
                time.sleep(1.1) # Respetar límites de API
        except: continue

    # Ordenar por puntaje y ahorro
    candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
    candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

    # --- INICIO DE ENVÍOS SEPARADOS ---

    # 1. Recomendación Cooperativa (Mensaje 1)
    if candidatos_multi:
        best = candidatos_multi[0]
        resena = profesor_habla(best['title'], best['generos'], best['score'], "COOPERATIVA")
        m_coop = (
            f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n---\n"
            f"{resena}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Costo:** 💰 {best['precio_clp']}\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_coop})
        time.sleep(2)

    # 2. Experimento de Aislamiento (Mensaje 2)
    if candidatos_solo:
        best = candidatos_solo[0]
        resena = profesor_habla(best['title'], best['generos'], best['score'], "INDIVIDUAL")
        m_solo = (
            f"🧬 **EXPERIMENTO DE AISLAMIENTO DEL PROFESOR** 🧬\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n---\n"
            f"{resena}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Costo:** 💰 {best['precio_clp']}\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_solo})
        time.sleep(2)

    # 3. Menciones Deshonrosas (Mensaje 3)
    final_info = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    final_info += "He detectado otros especímenes con ofertas excelentes para Chile. Échenles un ojo antes de que yo olvide por qué estamos aquí.\n\n"
    
    if len(candidatos_multi) > 1:
        final_info += "**📡 Otros sujetos grupales:**\n"
        final_info += "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_multi[1:5]])
        final_info += "\n\n"
    
    if len(candidatos_solo) > 1:
        final_info += "**🧬 Otros sujetos solitarios:**\n"
        final_info += "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_solo[1:5]])
        final_info += "\n\n"

    final_info += f"*{random.choice(FRASES_DESPEDIDA)}*"
    requests.post(webhook_url, json={"content": final_info})

if __name__ == "__main__":
    enviar_mensaje()

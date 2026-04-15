import requests
import os
import time
import random
from deep_translator import GoogleTranslator

def obtener_datos_steam(app_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Sin descripción.')
            categorias = [cat['id'] for cat in data.get('categories', [])]
            # 1: Multi, 9: Co-op, 38: Online Co-op
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            return es_multi, desc
        return None, ""
    except: return None, ""

def traducir_emergencia(texto):
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

def profesor_habla(nombre, descripcion, modo):
    saludos = [
        "¡Buenas noticias!",
        "¡Por todos los circuitos de un robot!",
        "¡Atención, tripulación!",
        "¡Grandes noticias, a menos que mueran!",
        "¡He inventado un dispositivo de ofertas!",
        "¡Increíble! He encontrado algo digno de mi genio:"
    ]
    saludo_elegido = random.choice(saludos)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    contexto = "para jugar con amigos" if modo == "COOPERATIVA" else "para jugar en total aislamiento"
    
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Escribe una reseña corta y sarcástica para el juego '{nombre}'. "
        f"Es una recomendación {contexto}. "
        f"Empieza con: '{saludo_elegido}'. Traduce/resume esto al español: {descripcion}"
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    return f"{saludo_elegido} Mi cerebro falló, pero traduje esto: {traducir_emergencia(descripcion)}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    # Pedimos 30 ofertas para tener de dónde elegir
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    try:
        ofertas = requests.get(url_ofertas).json()
        candidatos_multi = []
        candidatos_solo = []
        
        # Fase 1: Análisis y Clasificación (Revisamos los primeros 30)
        for o in ofertas[:30]:
            es_multi, desc_steam = obtener_datos_steam(o['steamAppID'])
            if es_multi is not None:
                o['descripcion_limpia'] = desc_steam
                o['score_int'] = int(o['metacriticScore'])
                if es_multi:
                    candidatos_multi.append(o)
                else:
                    candidatos_solo.append(o)
            time.sleep(0.6) # Un poco de calma para no enojar a Steam

        # Fase 2: Selección del Mejor (Ordenamos por nota)
        candidatos_multi.sort(key=lambda x: x['score_int'], reverse=True)
        candidatos_solo.sort(key=lambda x: x['score_int'], reverse=True)

        # Fase 3: Envío de Resultados
        if candidatos_multi:
            best = candidatos_multi[0]
            resena = profesor_habla(best['title'], best['descripcion_limpia'], "COOPERATIVA")
            mensaje = (
                f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n---\n"
                f"{resena}\n\n"
                f"**Tipo de experimento:** 🧪 Multijugador / Cooperativo\n"
                f"**Calibración crítica:** ⚡ {best['metacriticScore']}/100\n"
                f"**Costo:** 💰 ${best['salePrice']} USD\n"
                f"**Link:** https://store.steampowered.com/app/{best['steamAppID']}"
            )
            requests.post(webhook_url, json={"content": mensaje})

        if candidatos_solo:
            best_solo = candidatos_solo[0]
            resena_solo = profesor_habla(best_solo['title'], best_solo['descripcion_limpia'], "INDIVIDUAL")
            mensaje_solo = (
                f"🧬 **EXPERIMENTO DE AISLAMIENTO DEL PROFESOR** 🧬\n---\n"
                f"{resena_solo}\n\n"
                f"**Tipo de experimento:** 👤 Un solo jugador\n"
                f"**Calibración crítica:** ⚡ {best_solo['metacriticScore']}/100\n"
                f"**Costo:** 💰 ${best_solo['salePrice']} USD\n"
                f"**Link:** https://store.steampowered.com/app/{best_solo['steamAppID']}"
            )
            requests.post(webhook_url, json={"content": mensaje_solo})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enviar_mensaje()

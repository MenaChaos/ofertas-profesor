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
        "¡Increíble! He encontrado algo digno de mi genio:"
    ]
    saludo_elegido = random.choice(saludos)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    contexto_modo = "para jugar con amigos" if modo == "COOPERATIVA" else "para jugar en total aislamiento"
    
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Escribe una reseña corta y sarcástica para el juego '{nombre}'. "
        f"Es una recomendación {contexto_modo}. "
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
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    try:
        ofertas = requests.get(url_ofertas).json()
        encontrado_multi = False
        encontrado_solo = False
        
        for o in ofertas[:20]:
            if encontrado_multi and encontrado_solo: break
            
            es_multi, desc_steam = obtener_datos_steam(o['steamAppID'])
            
            # Caso 1: Buscamos el multijugador si aún no lo tenemos
            if es_multi and not encontrado_multi:
                resena = profesor_habla(o['title'], desc_steam, "COOPERATIVA")
                mensaje = (
                    f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n---\n"
                    f"{resena}\n\n"
                    f"**Tipo de experimento:** 🧪 Multijugador / Cooperativo\n"
                    f"**Calibración crítica:** ⚡ {o['metacriticScore']}/100\n"
                    f"**Costo:** 💰 ${o['salePrice']} USD\n"
                    f"**Link:** https://store.steampowered.com/app/{o['steamAppID']}"
                )
                requests.post(webhook_url, json={"content": mensaje})
                encontrado_multi = True
                
            # Caso 2: Buscamos el Single Player si aún no lo tenemos
            elif es_multi == False and not encontrado_solo:
                resena = profesor_habla(o['title'], desc_steam, "INDIVIDUAL")
                mensaje = (
                    f"🧬 **EXPERIMENTO DE AISLAMIENTO DEL PROFESOR** 🧬\n---\n"
                    f"{resena}\n\n"
                    f"**Tipo de experimento:** 👤 Un solo jugador\n"
                    f"**Calibración crítica:** ⚡ {o['metacriticScore']}/100\n"
                    f"**Costo:** 💰 ${o['salePrice']} USD\n"
                    f"**Link:** https://store.steampowered.com/app/{o['steamAppID']}"
                )
                requests.post(webhook_url, json={"content": mensaje})
                encontrado_solo = True
                
            time.sleep(1.5)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enviar_mensaje()

import requests
import os
import time
from deep_translator import GoogleTranslator

def obtener_datos_steam(app_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Sin descripción.')
            categorias = [cat['id'] for cat in data.get('categories', [])]
            # Categorías: 1 (Multiplayer), 9 (Co-op), 38 (Online Co-op)
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            return es_multi, desc
        return False, ""
    except: return False, ""

def traducir_emergencia(texto):
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

def profesor_habla(nombre, descripcion):
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Prompt ajustado para que el Profesor sepa que es una recomendación cooperativa
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Escribe una reseña corta y sarcástica para el juego '{nombre}'. "
        f"Es un juego cooperativo/multijugador para jugar con amigos. "
        f"Traduce o resume esta descripción al español: {descripcion}"
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    desc_es = traducir_emergencia(descripcion)
    return f"¡Buenas noticias! Mi cerebro falló, pero traduje esto para ustedes: {desc_es}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    ofertas = requests.get(url_ofertas).json()
    for o in ofertas[:10]:
        es_multi, desc_steam = obtener_datos_steam(o['steamAppID'])
        if es_multi:
            resena = profesor_habla(o['title'], desc_steam)
            
            # Formateo del mensaje con etiquetas claras
            mensaje = (
                f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n"
                f"---"
                f"\n{resena}\n\n"
                f"**Tipo de experimento:** 🎮 Multijugador / Cooperativo\n"
                f"**Nota de los críticos:** ⭐ {o['metacriticScore']}/100\n"
                f"**Costo de los materiales:** ${o['salePrice']} USD\n"
                f"**Enlace al vicio:** https://store.steampowered.com/app/{o['steamAppID']}"
            )
            requests.post(webhook_url, json={"content": mensaje})
            return 

if __name__ == "__main__":
    enviar_mensaje()

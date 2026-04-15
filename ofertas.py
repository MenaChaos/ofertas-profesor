import requests
import os
import random
import time

def obtener_datos_steam(app_id):
    """ Obtiene descripción y categorías de Steam """
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Un juego misterioso.')
            cats = [cat['id'] for cat in data.get('categories', [])]
            es_multi = any(id_m in cats for id_m in [1, 9, 38])
            return es_multi, desc
        return False, ""
    except: return False, ""

def profesor_traductor(nombre, descripcion_steam):
    """ Usa la IA para traducir la descripción de Steam al estilo Farnsworth """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key: return descripcion_steam

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = (
        f"Eres el Profesor Farnsworth de Futurama. Traduce la siguiente descripción al ESPAÑOL "
        f"con tu estilo sarcástico y loco. Empieza con '¡Buenas noticias!'. "
        f"Sé breve. Juego: {nombre}. Descripción a traducir: {descripcion_steam}"
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload, timeout=15)
        res = response.json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        # Si la IA falla, devolvemos la descripción de Steam para no quedar en blanco
        return f"¡Buenas noticias! Mi cerebro falló, pero Steam dice esto: {descripcion_steam}"

def buscar_mejor_oferta():
    url = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    ofertas = requests.get(url).json()
    candidatos = []
    
    for o in ofertas[:15]:
        es_multi, desc = obtener_datos_steam(o['steamAppID'])
        if es_multi:
            o['descripcion'] = desc
            o['score'] = float(o['metacriticScore'])
            candidatos.append(o)
        time.sleep(0.5)
    
    if not candidatos: return None
    candidatos.sort(key=lambda x: x['score'], reverse=True)
    return candidatos[0]

def enviar_mensaje():
    webhook = os.getenv('WEBHOOK_PROFESOR')
    juego = buscar_mejor_oferta()
    
    if juego:
        # El Profesor traduce la descripción real
        resena = profesor_traductor(juego['title'], juego['descripcion'])
        
        mensaje = (
            f"{resena}\n\n"
            f"**Nota:** ⭐ {juego['metacriticScore']}/100\n"
            f"**Precio:** ${juego['salePrice']} USD\n"
            f"**Link:** https://store.steampowered.com/app/{juego['steamAppID']}"
        )
        requests.post(webhook, json={"content": mensaje})

if __name__ == "__main__":
    enviar_mensaje()

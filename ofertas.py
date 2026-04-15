import requests
import os
import random
import time

def generar_resena_ia(nombre_juego):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return "¡Es un buen juego, estúpidos! Compren la cuestión."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = {
        "contents": [{
            "parts": [{
                "text": f"Actúa como el Profesor Farnsworth de Futurama. Dame una reseña extremadamente corta (máximo 2 frases) sobre el juego '{nombre_juego}'. Usa su frase '¡Buenas noticias!' y menciona por qué es bueno jugarlo con amigos o por qué es una joya. Sé sarcástico y gracioso."
            }]
        }]
    }

    try:
        response = requests.post(url, json=prompt)
        res = response.json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        return "¡Buenas noticias! He encontrado un juego que mi demencia senil me impide describir, ¡pero comprenlo!"

def es_multijugador(app_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url)
        data = response.json()
        if data and data[str(app_id)]['success']:
            info = data[str(app_id)]['data']
            categorias = [cat['id'] for cat in info.get('categories', [])]
            return any(id_multi in categorias for id_multi in [1, 9, 38])
        return False
    except: return False

def buscar_la_mejor_evaluada():
    url_api = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    try:
        response = requests.get(url_api)
        ofertas = response.json()
        candidatos_multi = []
        for juego in ofertas[:20]:
            if es_multijugador(juego['steamAppID']):
                juego['score_float'] = float(juego['metacriticScore'])
                candidatos_multi.append(juego)
            time.sleep(0.6)
        
        if not candidatos_multi: return None
        candidatos_multi.sort(key=lambda x: x['score_float'], reverse=True)
        return candidatos_multi[0]
    except: return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    juego = buscar_la_mejor_evaluada()
    
    if juego:
        resena = generar_resena_ia(juego['title'])
        link = f"https://store.steampowered.com/app/{juego['steamAppID']}"
        precio = juego['salePrice']
        
        # Formato elegante con la reseña de la IA
        mensaje = f"{resena}\n\n**Precio:** ${precio} (Oferta de Steam)\n**Link:** {link}"
        
        requests.post(webhook_url, json=mensaje)
        print(f"Reseña enviada para {juego['title']}")

if __name__ == "__main__":
    enviar_mensaje()

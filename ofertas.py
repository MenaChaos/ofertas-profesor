import requests
import os
import random
import time

def generar_resena_ia(nombre_juego):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return "¡Buenas noticias! He encontrado un juego, pero he olvidado mi llave API en mi otra bata."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    
    prompt_text = (
        f"Eres el Profesor Hubert J. Farnsworth de Futurama. "
        f"Danos una 'Buena Noticia' sobre el juego '{nombre_juego}'. "
        f"Explica brevemente por qué es una joya para jugar con amigos (multijugador). "
        f"Sé sarcástico, usa tus frases icónicas y no te pases de 3 líneas."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        res = response.json()
        # Verificamos si la respuesta tiene el contenido esperado
        if 'candidates' in res and res['candidates'][0]['content']['parts'][0]['text']:
            return res['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Respuesta inesperada de la IA: {res}")
            return "¡Buenas noticias! El juego es magnífico, pero mi cerebro está en un frasco y no puede describirlo ahora."
    except Exception as e:
        print(f"Error en la IA: {e}")
        return "¡Buenas noticias! He encontrado un juego que mi demencia senil me impide describir, ¡pero cómprenlo!"

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
        
        # El mensaje debe ir dentro de un diccionario para ser un JSON válido
        mensaje_final = f"{resena}\n\n**Precio:** ${precio} (Oferta de Steam)\n**Link:** {link}"
        payload = {"content": mensaje_final}
        
        requests.post(webhook_url, json=payload)
        print(f"Reseña enviada para {juego['title']}")

if __name__ == "__main__":
    enviar_mensaje()

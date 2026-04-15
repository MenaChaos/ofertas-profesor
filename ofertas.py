import requests
import os
import random
import time

def generar_resena_ia(nombre_juego):
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Instrucción ultra-directa
    prompt_text = f"Escribe un mensaje corto como el Profesor Farnsworth de Futurama sobre el juego {nombre_juego}. Empieza con '¡Buenas noticias!'. Explica por qué es divertido jugar con amigos. Máximo 50 palabras."
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }],
        "safetySettings": [ # Esto desactiva filtros que podrían estar bloqueando la respuesta
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        res = response.json()
        
        # Imprimimos la respuesta en el log de GitHub por si vuelve a fallar
        print(f"Respuesta IA: {res}") 
        
        if 'candidates' in res and len(res['candidates']) > 0:
            return res['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Error crítico: {e}")
        
    return "¡Buenas noticias! He encontrado un juego excelente, pero mi transmisor interplanetario está fallando. ¡Confíen en mi intelecto y jueguen esto!"

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
    # El Profesor se toma su tiempo para analizar
    juego = buscar_la_mejor_evaluada()
    
    if juego:
        print(f"Juego encontrado: {juego['title']}. Generando reseña de alta calidad...")
        resena = generar_resena_ia(juego['title'])
        
        link = f"https://store.steampowered.com/app/{juego['steamAppID']}"
        precio = juego['salePrice']
        nota = juego['metacriticScore']
        
        mensaje_final = (
            f"{resena}\n\n"
            f"**Calificación Crítica:** ⭐ {nota}/100\n"
            f"**Precio de Ganga:** ${precio} USD\n"
            f"**Link para el vicio:** {link}"
        )
        
        payload = {"content": mensaje_final}
        requests.post(webhook_url, json=payload)
    else:
        print("Hoy no encontré nada digno de mi intelecto.")

if __name__ == "__main__":
    enviar_mensaje()

import requests
import os
import time

def obtener_datos_steam(app_id):
    try:
        # Forzamos español con l=spanish
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Un juego que mi intelecto no puede describir.')
            categorias = [cat['id'] for cat in data.get('categories', [])]
            # 1: Multi, 9: Co-op, 38: Online Co-op
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            return es_multi, desc
        return False, "Sin descripción disponible."
    except:
        return False, "Error al conectar con Steam."

def profesor_habla_espanol(nombre, descripcion):
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Escribe una reseña corta en ESPAÑOL sobre el juego '{nombre}'. "
        f"Usa esta descripción como base: {descripcion}. "
        f"Empieza con '¡Buenas noticias!' y sé sarcástico. Máximo 3 frases."
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        # Si la IA falla, el Profesor se queja en español y da la descripción de Steam
        return f"¡Buenas noticias! Mi cerebro está en un frasco, pero Steam dice: {descripcion}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    # Buscamos ofertas de Steam con Metacritic > 80
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    try:
        ofertas = requests.get(url_ofertas).json()
        for o in ofertas[:15]: # Revisamos los primeros 15
            es_multi, desc_steam = obtener_datos_steam(o['steamAppID'])
            
            if es_multi:
                resena = profesor_habla_espanol(o['title'], desc_steam)
                
                mensaje = (
                    f"{resena}\n\n"
                    f"**Nota:** ⭐ {o['metacriticScore']}/100\n"
                    f"**Precio:** ${o['salePrice']} USD\n"
                    f"**Link:** https://store.steampowered.com/app/{o['steamAppID']}"
                )
                
                requests.post(webhook_url, json={"content": mensaje})
                return # Solo enviamos el mejor juego encontrado
            time.sleep(1) # Pausa para no saturar Steam
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    enviar_mensaje()

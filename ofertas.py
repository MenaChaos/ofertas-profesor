import requests
import os
import time

def obtener_datos_steam(app_id):
    try:
        # Forzamos l=spanish para que Steam nos dé todo en nuestro idioma
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Un juego que mi intelecto no puede describir.')
            categorias = [cat['id'] for cat in data.get('categories', [])]
            # 1: Multi, 9: Co-op, 38: Online Co-op
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            return es_multi, desc
        return False, "Sin descripción."
    except:
        return False, "Error de conexión."

def profesor_habla_espanol(nombre, descripcion):
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Prompt ultra simplificado para evitar bloqueos
    prompt = f"Como el Profesor Farnsworth de Futurama, dime en 2 frases por qué jugar '{nombre}' en español. Usa: {descripcion}"
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        # Si la IA responde, genial
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except:
        pass
    
    # RESPALDO TOTAL EN ESPAÑOL: Si la IA falla, el bot traduce solo
    return f"¡Buenas noticias! Mi cerebro biónico se sobrecalentó, pero Steam dice que este juego es una joya: {descripcion}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    try:
        ofertas = requests.get(url_ofertas).json()
        for o in ofertas[:10]:
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
                return 
            time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    enviar_mensaje()

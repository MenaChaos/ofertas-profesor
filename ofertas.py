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
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            
            # Extraemos el trailer si existe
            video_url = ""
            movies = data.get('movies', [])
            if movies:
                # Obtenemos el video en formato mp4 de alta calidad
                video_url = movies[0].get('mp4', {}).get('max', "")
            
            return es_multi, desc, video_url
        return None, "", ""
    except: return None, "", ""

def traducir_emergencia(texto):
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

def profesor_habla(nombre, descripcion, modo):
    saludos = ["¡Buenas noticias!", "¡Por todos los circuitos!", "¡Tripulación!", "¡Increíble!", "¡Atención!"]
    saludo = random.choice(saludos)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    contexto = "para jugar con amigos" if modo == "COOPERATIVA" else "para jugar en soledad absoluta"
    prompt = (f"Actúa como el Profesor Farnsworth. Escribe una reseña corta y sarcástica sobre '{nombre}' "
              f"que es {contexto}. Usa este texto base en español: {descripcion}")
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        return res['candidates'][0]['content']['parts'][0]['text']
    except:
        return f"{saludo} Mi cerebro falló, pero traduje esto: {traducir_emergencia(descripcion)}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    url_ofertas = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80"
    
    try:
        ofertas = requests.get(url_ofertas).json()
        candidatos_multi = []
        candidatos_solo = []
        
        for o in ofertas[:100]:
            es_multi, desc_steam, trailer = obtener_datos_steam(o['steamAppID'])
            if es_multi is not None:
                o['desc'] = desc_steam
                o['video'] = trailer
                o['score'] = int(o['metacriticScore'])
                o['ahorro'] = float(o['savings'])
                
                if es_multi: candidatos_multi.append(o)
                else: candidatos_solo.append(o)
            time.sleep(1)

        candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
        candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

        for lista, modo, titulo_bloque, emoji in [
            (candidatos_multi, "COOPERATIVA", "RECOMENDACIÓN COOPERATIVA", "📡"),
            (candidatos_solo, "INDIVIDUAL", "EXPERIMENTO DE AISLAMIENTO", "🧬")
        ]:
            if lista:
                best = lista[0]
                resena = profesor_habla(best['title'], best['desc'], modo)
                
                # Añadimos el trailer al final del mensaje si existe
                link_trailer = f"\n🎬 **Tráiler del experimento:** {best['video']}" if best['video'] else ""
                
                mensaje = (
                    f"{emoji} **{titulo_bloque} DEL PROFESOR** {emoji}\n---\n"
                    f"{resena}\n\n"
                    f"**Calibración:** ⚡ {best['score']}/100\n"
                    f"**Descuento:** 📉 {int(best['ahorro'])}%\n"
                    f"**Costo:** 💰 ${best['salePrice']} USD\n"
                    f"**Link:** https://store.steampowered.com/app/{best['steamAppID']}"
                    f"{link_trailer}"
                )
                requests.post(webhook_url, json={"content": mensaje})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    enviar_mensaje()

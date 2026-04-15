import requests
import os
import time
import random
from deep_translator import GoogleTranslator

def obtener_datos_steam(app_id):
    try:
        # Forzamos l=spanish para intentar traer la descripción en nuestro idioma desde el inicio
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
    saludos = ["¡Buenas noticias!", "¡Por todos los circuitos!", "¡Atención, tripulación!", "¡He inventado un sensor de gangas!", "¡Increíble!"]
    saludo = random.choice(saludos)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    contexto = "para jugar con amigos" if modo == "COOPERATIVA" else "para jugar en soledad absoluta"
    prompt = (f"Actúa como el Profesor Farnsworth de Futurama. Escribe una reseña corta y sarcástica sobre '{nombre}' "
              f"que es {contexto}. Usa este texto base: {descripcion}. Responde en español.")
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=10)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    return f"{saludo} Mi cerebro falló, pero traduje esto para ustedes: {traducir_emergencia(descripcion)}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi = []
    candidatos_solo = []
    
    print("Iniciando escaneo ultra-masivo de 5 páginas (300 juegos)...")

    # Escaneamos 5 páginas de resultados (60 juegos por página)
    for pagina in range(5):
        url_ofertas = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url_ofertas).json()
            if not ofertas: break
            
            for o in ofertas:
                if not o.get('steamAppID'): continue
                
                es_multi, desc_steam = obtener_datos_steam(o['steamAppID'])
                if es_multi is not None:
                    o['desc'] = desc_steam
                    o['score'] = int(o.get('metacriticScore', 0))
                    o['ahorro'] = float(o.get('savings', 0))
                    
                    if es_multi: candidatos_multi.append(o)
                    else: candidatos_solo.append(o)
                
                # Pausa necesaria para no ser bloqueados por Steam
                time.sleep(1.1)
        except: continue

    # Ordenamos por Calificación (Metacritic) y luego por Descuento
    candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
    candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

    # Envío de los dos campeones
    for lista, modo, titulo_bloque, emoji in [
        (candidatos_multi, "COOPERATIVA", "RECOMENDACIÓN COOPERATIVA", "📡"),
        (candidatos_solo, "INDIVIDUAL", "EXPERIMENTO DE AISLAMIENTO", "🧬")
    ]:
        if lista:
            best = lista[0]
            resena = profesor_habla(best['title'], best['desc'], modo)
            mensaje = (
                f"{emoji} **{titulo_bloque} DEL PROFESOR** {emoji}\n---\n"
                f"{resena}\n\n"
                f"**Calibración:** ⚡ {best['score']}/100\n"
                f"**Descuento:** 📉 {int(best['ahorro'])}%\n"
                f"**Costo:** 💰 ${best['salePrice']} USD\n"
                f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
            )
            requests.post(webhook_url, json={"content": mensaje})

if __name__ == "__main__":
    enviar_mensaje()

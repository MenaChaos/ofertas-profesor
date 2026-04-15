import requests
import os
import time
import random

# --- PERSONALIDAD DEL PROFESOR ---
FRASES_COOP = [
    "¡Buenas noticias, Jenkins! He encontrado un experimento grupal. ¡Casi tan peligroso como la tripulación anterior!",
    "¡Atención, tripulación! Si logran cooperar mejor que Fry y Bender, podrían sobrevivir."
]

FRASES_SOLO = [
    "¡Ah, el dulce aislamiento! Perfecto para ignorar al resto del universo.",
    "¡Buenas noticias! Este juego es individual porque nadie más soportaría sus tácticas, Jenkins."
]

FRASES_DESPEDIDA = [
    "¡En fin, me voy a dormir! Si el laboratorio explota, no me despierten.",
    "Ya hice suficiente por hoy. Me voy a organizar mi colección de cables."
]

def obtener_datos_steam(app_id):
    """
    Filtro de Seguridad 3.0: Valida ofertas reales en Chile y 
    evita confundir packs caros con el juego base.
    """
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res = requests.get(url, timeout=12).json()
        
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            
            # Verificamos que tenga datos de precio y no sea gratis
            if data.get('is_free') or 'price_overview' not in data:
                return None, None, None

            price_data = data['price_overview']
            
            # --- VALIDACIÓN DE OFERTA REAL EN CHILE ---
            # Comparamos estrictamente que el porcentaje de descuento sea > 0
            if price_data.get('discount_percent', 0) <= 0:
                return None, None, None
            
            # Comparamos que el precio final sea menor al inicial (seguridad extra)
            if price_data.get('final', 0) >= price_data.get('initial', 0):
                return None, None, None

            precio_clp = price_data.get('final_formatted', 'N/A')
            desc = data.get('short_description', 'Sin descripción disponible.')
            
            # Clasificación Multijugador
            categorias = [cat['id'] for cat in data.get('categories', [])]
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            
            return es_multi, desc, precio_clp
        return None, None, None
    except:
        return None, None, None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi, candidatos_solo = [], []
    
    # Escaneamos 5 páginas de CheapShark (aprox 300 juegos)
    for pagina in range(5):
        url_ofertas = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url_ofertas).json()
            for o in ofertas:
                if not o.get('steamAppID'): continue
                
                # Validamos el precio REAL en Chile antes de considerar el juego
                es_multi, desc, p_clp = obtener_datos_steam(o['steamAppID'])
                
                if p_clp: # Si pasó el filtro de oferta real
                    o.update({
                        'desc': desc,
                        'precio_clp': p_clp,
                        'score': int(o.get('metacriticScore', 0)),
                        'ahorro': float(o.get('savings', 0))
                    })
                    if es_multi: candidatos_multi.append(o)
                    else: candidatos_solo.append(o)
                time.sleep(1.2) # Pausa para no ser bloqueados por Steam
        except: continue

    # Ordenamos por nota de Metacritic y luego por porcentaje de ahorro
    candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
    candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

    # --- ENVÍO DE MENSAJES CON FORMATO CORREGIDO ---
    for lista, modo, titulo, emoji in [
        (candidatos_multi, "COOP", "RECOMENDACIÓN COOPERATIVA", "📡"),
        (candidatos_solo, "SOLO", "EXPERIMENTO DE AISLAMIENTO", "🧬")
    ]:
        if lista:
            best = lista[0]
            # Título con '#' para hacerlo grande en Discord y separadores claros
            msg = (
                f"# {emoji} {titulo} {emoji}\n"
                f"----------------------------------------------------------\n"
                f"{random.choice(FRASES_COOP if modo == 'COOP' else FRASES_SOLO)}\n\n"
                f"**Descripción:** {best['desc']}\n\n"
                f"**Calibración:** ⚡ {best['score']}/100\n"
                f"**Descuento:** 📉 {best['ahorro']:.0f}%\n"
                f"**Costo:** 💰 {best['precio_clp']}\n"
                f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}\n"
                f"----------------------------------------------------------"
            )
            requests.post(webhook_url, json={"content": msg})
            time.sleep(2)

    # 3. Mensaje de Menciones Finales
    final_info = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    if candidatos_multi:
        final_info += "**📡 Otros sujetos grupales:**\n" + "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_multi[1:5]]) + "\n\n"
    if candidatos_solo:
        final_info += "**🧬 Otros sujetos solitarios:**\n" + "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_solo[1:5]]) + "\n\n"
    
    final_info += f"*{random.choice(FRASES_DESPEDIDA)}*"
    requests.post(webhook_url, json={"content": final_info})

if __name__ == "__main__":
    enviar_mensaje()

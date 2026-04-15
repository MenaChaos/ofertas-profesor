import requests
import os
import time
import random

# --- CONFIGURACIÓN DE PERSONALIDAD ---
FRASES_COOP = ["¡Atención, tripulación! Si logran cooperar mejor que Fry y Bender, podrían sobrevivir."]
FRASES_SOLO = ["¡Ah, el dulce aislamiento! Perfecto para ignorar al resto del universo."]
FRASES_DESPEDIDA = ["Ya hice suficiente por hoy. Me voy a organizar mi colección de cables."]

def obtener_precios_regionales(app_id):
    """Consulta precios en Chile y Argentina para comparar."""
    try:
        # Consulta Chile
        url_cl = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res_cl = requests.get(url_cl, timeout=10).json()
        
        # Consulta Argentina
        url_ar = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=ar&l=spanish"
        res_ar = requests.get(url_ar, timeout=10).json()

        if res_cl and res_cl[str(app_id)]['success']:
            data_cl = res_cl[str(app_id)]['data']
            if data_cl.get('is_free') or 'price_overview' not in data_cl:
                return None
            
            p_cl = data_cl['price_overview']
            
            # FILTRO DE SEGURIDAD CHILE: ¿Hay oferta real?
            if p_cl.get('discount_percent', 0) <= 0:
                return None

            # Obtener precio Argentina si está disponible
            precio_ar = "N/A"
            if res_ar and res_ar[str(app_id)]['success']:
                p_ar = res_ar[str(app_id)]['data'].get('price_overview', {})
                precio_ar = p_ar.get('final_formatted', 'N/A')

            return {
                'es_multi': any(c['id'] in [1, 9, 38] for c in data_cl.get('categories', [])),
                'desc': data_cl.get('short_description', 'Sin descripción.'),
                'clp': p_cl.get('final_formatted'),
                'ars_usd': precio_ar,
                'descuento': p_cl.get('discount_percent')
            }
        return None
    except: return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi, candidatos_solo = [], []
    
    # Análisis de juegos (5 páginas)
    for pagina in range(5):
        url = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url).json()
            for o in ofertas:
                if not o.get('steamAppID'): continue
                datos = obtener_precios_regionales(o['steamAppID'])
                if datos:
                    o.update(datos)
                    o['score'] = int(o.get('metacriticScore', 0))
                    if datos['es_multi']: candidatos_multi.append(o)
                    else: candidatos_solo.append(o)
                time.sleep(1.2)
        except: continue

    for lista in [candidatos_multi, candidatos_solo]:
        lista.sort(key=lambda x: (x['score'], x['descuento']), reverse=True)

    # --- ENVÍO CON ESTÉTICA FINAL ---
    for lista, titulo, emoji, frase in [
        (candidatos_multi, "RECOMENDACIÓN COOPERATIVA", "📡", FRASES_COOP[0]),
        (candidatos_solo, "EXPERIMENTO DE AISLAMIENTO", "🧬", FRASES_SOLO[0])
    ]:
        if lista:
            best = lista[0]
            msg = (
                f"# {emoji} {titulo} {emoji}\n"
                f"----------------------------------------------------------\n"
                f"{frase}\n\n"
                f"**Descripción:** {best['desc']}\n\n"
                f"**Calibración:** ⚡ {best['score']}/100\n"
                f"**Descuento:** 📉 {best['descuento']}%\n"
                f"**Costo:** 💰 {best['clp']}\n"
                f"**Ref. Argentina:** 🇦🇷 {best['ars_usd']}\n"
                f"**Enlace:** https://store.steampowered.com/app/{best['steamAppID']}\n"
                f"----------------------------------------------------------"
            )
            requests.post(webhook_url, json={"content": msg})
            time.sleep(2)

    # Menciones Deshonrosas
    final = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    for cat, l in [("📡 Otros grupales", candidatos_multi), ("🧬 Otros solitarios", candidatos_solo)]:
        if l:
            final += f"**{cat}:**\n"
            final += "\n".join([f"• {s['title']}: {s['clp']} (Arg: {s['ars_usd']}) -{s['descuento']}%" for s in l[1:5]]) + "\n\n"
    
    final += f"*{FRASES_DESPEDIDA[0]}*"
    requests.post(webhook_url, json={"content": final})

if __name__ == "__main__":
    enviar_mensaje()

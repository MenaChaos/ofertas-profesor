import requests
import os
import time
import random
import google.generativeai as genai

# --- CONFIGURACIÓN DE IA (GEMINI) ---
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CONFIGURACIÓN DE PERSONALIDAD ---
FRASES_DESPEDIDA = ["Ya hice suficiente por hoy. Me voy a organizar mi colección de cables."]

def generar_resena_profesor(titulo, descripcion, modo):
    """Usa IA para generar una reseña con la personalidad del Profesor Farnsworth."""
    contexto = "cooperativo" if modo == "COOP" else "individual de aislamiento"
    prompt = (
        f"Actúa como el Profesor Hubert J. Farnsworth de Futurama. "
        f"Escribe una reseña muy breve (máximo 3 frases) y sarcástica para el juego '{titulo}'. "
        f"Menciona que es un experimento {contexto}. Usa sus frases típicas como '¡Buenas noticias!' o '¡Por todos los...'."
        f"La descripción original es: {descripcion}. Escribe SIEMPRE en español, incluso si la descripción está en inglés."
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return f"¡Rayos! Mi detector de reseñas se quedó sin Slurm para '{titulo}', pero mi instinto dice que es un experimento aceptable."

def obtener_precios_regionales(app_id):
    try:
        url_cl = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res_cl = requests.get(url_cl, timeout=10).json()
        url_ar = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=ar&l=spanish"
        res_ar = requests.get(url_ar, timeout=10).json()

        if res_cl and res_cl[str(app_id)]['success']:
            data_cl = res_cl[str(app_id)]['data']
            if data_cl.get('is_free') or 'price_overview' not in data_cl: return None
            p_cl = data_cl['price_overview']
            
            if p_cl.get('discount_percent', 0) <= 0: return None

            precio_ar = "N/A"
            if res_ar and res_ar[str(app_id)]['success']:
                p_ar = res_ar[str(app_id)]['data'].get('price_overview', {})
                precio_ar = p_ar.get('final_formatted', 'N/A')

            return {
                'title': data_cl.get('name'),
                'es_multi': any(c['id'] in [1, 9, 38] for c in data_cl.get('categories', [])),
                'desc_original': data_cl.get('short_description', 'Sin datos.'),
                'clp': p_cl.get('final_formatted'),
                'ars_usd': precio_ar,
                'descuento': p_cl.get('discount_percent')
            }
        return None
    except: return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi, candidatos_solo = [], []
    
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

    # --- ENVÍO CON IA ACTIVADA ---
    for lista, titulo_msg, emoji, modo_ia in [
        (candidatos_multi, "RECOMENDACIÓN COOPERATIVA", "📡", "COOP"),
        (candidatos_solo, "EXPERIMENTO DE AISLAMIENTO", "🧬", "SOLO")
    ]:
        if lista:
            best = lista[0]
            # La IA genera la descripción con personalidad
            resena_profesor = generar_resena_profesor(best['title'], best['desc_original'], modo_ia)
            
            msg = (
                f"# {emoji} {titulo_msg} {emoji}\n"
                f"----------------------------------------------------------\n"
                f"{resena_profesor}\n\n"
                f"**Calibración:** ⚡ {best['score']}/100\n"
                f"**Descuento:** 📉 {best['descuento']}%\n"
                f"**Costo:** 💰 {best['clp']}\n"
                f"**Ref. Argentina:** 🇦🇷 {best['ars_usd']}\n"
                f"**Enlace:** https://store.steampowered.com/app/{best['steamAppID']}\n"
                f"----------------------------------------------------------"
            )
            requests.post(webhook_url, json={"content": msg})
            time.sleep(2)

    # Menciones Finales
    final_info = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    for cat, l in [("📡 Otros grupales", candidatos_multi), ("🧬 Otros solitarios", candidatos_solo)]:
        if l:
            final_info += f"**{cat}:**\n"
            final_info += "\n".join([f"• {s['title']}: {s['clp']} (Arg: {s['ars_usd']}) -{s['descuento']}%" for s in l[1:5]]) + "\n\n"
    
    final_info += f"*{FRASES_DESPEDIDA[0]}*"
    requests.post(webhook_url, json={"content": final_info})

if __name__ == "__main__":
    enviar_mensaje()

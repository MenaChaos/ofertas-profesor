import requests
import os
import time
import random
from deep_translator import GoogleTranslator

# --- BANCO DE DATOS MAESTRO DEL PROFESOR ---
FRASES_COOP = [
    "¡Buenas noticias, Jenkins! He encontrado un experimento grupal. Es casi tan peligroso como aquella vez que envié a la tripulación anterior a una avispa gigante... ¡Casi!",
    "¡Atención, tripulación! Este juego requiere trabajar en equipo. Si logran cooperar mejor que Fry y Bender cuando encuentran una moneda, ¡podrían sobrevivir!",
    "¡Grandes noticias! Si juegan esto juntos en el servidor, sus posibilidades de supervivencia aumentan un 0.004%. ¡A celebrar!",
    "¡Por el dulce néctar de Slurm! He hallado un juego cooperativo. ¡Intenten no matarse entre ustedes antes de que los enemigos lo hagan!"
]

FRASES_SOLO = [
    "¡Buenas noticias! He encontrado un juego para jugar en soledad absoluta. ¡Justo como paso mis noches en el laboratorio de clones prohibidos!",
    "¡Ah, el dulce aislamiento! Este juego es perfecto para ignorar al resto del universo. ¡Es como meterse en mi propia Cámara de la Muerte!",
    "¡Por la gloria de la ciencia! Un juego para un solo sujeto de prueba. Si las cosas salen mal, siempre puedo reemplazarlos con un clon llamado Cubert.",
    "¡Buenas noticias! Este juego es individual porque nadie más soportaría sus tácticas de juego, Jenkins."
]

FRASES_DESPEDIDA = [
    "Los acompañaría a jugar, pero ya me puse la pijama.",
    "Me gustaría ver cómo fallan en este experimento, pero tengo que ir a organizar mi colección de cables de distintas longitudes.",
    "¡En fin, me voy a dormir! Si el laboratorio explota, no me despierten.",
    "¡Ya hice suficiente por hoy! Mañana enviaré a alguien más a una misión suicida."
]

def obtener_datos_steam(app_id):
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=spanish"
        res = requests.get(url).json()
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            desc = data.get('short_description', 'Sin descripción.')
            categorias = [cat['id'] for cat in data.get('categories', [])]
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            return es_multi, desc
        return None, ""
    except: return None, ""

def traducir_emergencia(texto):
    try:
        return GoogleTranslator(source='auto', target='es').translate(texto)
    except: return texto

def profesor_habla(nombre, descripcion, modo):
    frase_base = random.choice(FRASES_COOP if modo == "COOPERATIVA" else FRASES_SOLO)
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Usa OBLIGATORIAMENTE esta frase inicial: '{frase_base}'. "
        f"Escribe una reseña corta y sarcástica sobre '{nombre}' para los Jenkins. "
        f"Base: {descripcion}. Responde en español."
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=12)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    return f"{frase_base}\n\n[Cerebro fallando...] Traducción: {traducir_emergencia(descripcion)}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi = []
    candidatos_solo = []
    
    # Análisis masivo de 300 juegos
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
                time.sleep(1.1)
        except: continue

    candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
    candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

    # --- ENVÍO DIVIDIDO PARA FORMATO IMPECABLE ---

    # 1. Mensaje Cooperativo
    if candidatos_multi:
        best = candidatos_multi[0]
        resena = profesor_habla(best['title'], best['desc'], "COOPERATIVA")
        m_coop = (
            f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n---\n"
            f"{resena}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n"
            f"**Costo:** 💰 ${best['salePrice']} USD\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_coop})
        time.sleep(2) # Pausa para asegurar el orden en Discord

    # 2. Mensaje de Aislamiento
    if candidatos_solo:
        best = candidatos_solo[0]
        resena = profesor_habla(best['title'], best['desc'], "INDIVIDUAL")
        m_solo = (
            f"🧬 **EXPERIMENTO DE AISLAMIENTO DEL PROFESOR** 🧬\n---\n"
            f"{resena}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n"
            f"**Costo:** 💰 ${best['salePrice']} USD\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_solo})
        time.sleep(2)

    # 3. Menciones Deshonrosas y Despedida
    final_info = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    
    if len(candidatos_multi) > 1:
        sec_m = ", ".join([f"{s['title']} ({s['score']}/100)" for s in candidatos_multi[1:5]])
        final_info += f"*Otros especímenes grupales:* {sec_m}\n"
    
    if len(candidatos_solo) > 1:
        sec_s = ", ".join([f"{s['title']} ({s['score']}/100)" for s in candidatos_solo[1:5]])
        final_info += f"*Otros especímenes solitarios:* {sec_s}\n"

    final_info += f"\n*{random.choice(FRASES_DESPEDIDA)}*"
    requests.post(webhook_url, json={"content": final_info})

if __name__ == "__main__":
    enviar_mensaje()

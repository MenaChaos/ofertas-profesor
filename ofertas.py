import requests
import os
import time
import random
from deep_translator import GoogleTranslator

# --- BANCO DE DATOS DEL PROFESOR (REFERENCIAS A FUTURAMA) ---
FRASES_COOP = [
    "¡Buenas noticias! He encontrado un experimento grupal. Es casi tan peligroso como aquella vez que envié a la tripulación anterior a una avispa gigante... ¡Casi!",
    "¡Atención, tripulación! Este juego requiere trabajar en equipo. Si logran cooperar mejor que Fry y Bender cuando encuentran una moneda, ¡podrían sobrevivir!",
    "¡Por todos los circuitos! Reúnan a sus amigos. He calibrado este juego para que sea más divertido que una visita al parque de diversiones lunar. ¡Cuidado con las ballenas!",
    "¡Tripulación! Este juego multijugador es la solución a sus problemas. O al menos lo será hasta que Zoidberg arruine todo con sus pinzas.",
    "¡Increíble! Un juego para jugar juntos. Me recuerda a cuando fusioné las mentes de todos en un solo cuerpo. ¡Fue un desastre pegajoso, pero muy educativo!",
    "¡Sálvense quienes puedan! Pero háganlo en modo cooperativo. ¡Es como ser digerido por una ballena espacial, pero con descuento!",
    "¡Atención! He encontrado un experimento donde sus vidas dependen de la incompetencia de sus amigos... ¡Qué emoción!",
    "He inventado un dispositivo para jugar en red. ¡Es como el Internet, pero con más gritos y menos control de esfínteres!",
    "¡Grandes noticias! Si juegan esto juntos, sus posibilidades de supervivencia aumentan un 0.004%. ¡A celebrar!"
]

FRASES_SOLO = [
    "¡Buenas noticias! He encontrado un juego para jugar en soledad absoluta. ¡Justo como paso mis noches en el laboratorio de clones prohibidos!",
    "¡Ah, el dulce aislamiento! Este juego es perfecto para ignorar al resto del universo. ¡Es como meterse en mi propia Cámara de la Muerte!",
    "¡Por la gloria de la ciencia! Un juego para un solo sujeto de prueba. Si las cosas salen mal, siempre puedo reemplazarlos con un clon llamado Cubert.",
    "He inventado un dispositivo para jugar solo. Es casi tan eficiente como mi 'Olioscopio', pero en lugar de oler el espacio, verán ofertas.",
    "¿Compañía humana? ¡Puaj! Este juego es para genios solitarios. Me recuerda a cuando me exilié a un asteroide para construir robots que sintieran amor.",
    "¡Miren esto! Un experimento de aislamiento puro. Es como viajar al final del universo y ver que solo hay otra pizzería de Panucci.",
    "¡Increíble! Un mundo entero para explorar sin que nadie les pida dinero o les robe el botín. ¡El sueño de todo genio misántropo!",
    "He calibrado este juego para un solo sujeto de prueba. ¡No se preocupen, las posibilidades de fallo cerebral son de apenas el 97%!",
    "¡Por todos los circuitos de un robot! Un juego individual para cuando la tripulación me tiene harto. ¡O sea, siempre!"
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
    # Elegimos la frase base según el modo
    frase_base = random.choice(FRASES_COOP if modo == "COOPERATIVA" else FRASES_SOLO)
    
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    contexto = "para jugar con amigos" if modo == "COOPERATIVA" else "para jugar en soledad absoluta"
    
    prompt = (
        f"Actúa como el Profesor Farnsworth de Futurama. "
        f"Usa OBLIGATORIAMENTE esta frase inicial: '{frase_base}'. "
        f"Luego, escribe una reseña corta, loca y sarcástica sobre el juego '{nombre}' que es {contexto}. "
        f"Usa esta descripción como base: {descripcion}. Responde siempre en español."
    )
    
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        response = requests.post(url, json=payload, timeout=12)
        res = response.json()
        if 'candidates' in res:
            return res['candidates'][0]['content']['parts'][0]['text']
    except: pass
    
    # Si la IA falla, usamos la frase base + traducción
    return f"{frase_base}\n\nMi cerebro falló, pero traduje esto: {traducir_emergencia(descripcion)}"

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi = []
    candidatos_solo = []
    
    print("Iniciando análisis masivo de 300 juegos...")

    for pagina in range(5): # 5 páginas = 300 juegos
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

    for lista, modo, titulo, emoji in [
        (candidatos_multi, "COOPERATIVA", "RECOMENDACIÓN COOPERATIVA", "📡"),
        (candidatos_solo, "INDIVIDUAL", "EXPERIMENTO DE AISLAMIENTO", "🧬")
    ]:
        if lista:
            best = lista[0]
            resena = profesor_habla(best['title'], best['desc'], modo)
            mensaje = (
                f"{emoji} **{titulo} DEL PROFESOR** {emoji}\n---\n"
                f"{resena}\n\n"
                f"**Calibración crítica:** ⚡ {best['score']}/100\n"
                f"**Descuento de locura:** 📉 {int(best['ahorro'])}%\n"
                f"**Costo de materiales:** 💰 ${best['salePrice']} USD\n"
                f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
            )
            requests.post(webhook_url, json={"content": mensaje})

if __name__ == "__main__":
    enviar_mensaje()

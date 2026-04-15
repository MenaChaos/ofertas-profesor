import requests
import os
import time
import random

# --- CATÁLOGO DE PERSONALIDAD DEL PROFESOR ---
FRASES_COOP = [
    "¡Atención, tripulación! Si logran cooperar mejor que Fry y Bender, podrían sobrevivir.",
    "He encontrado una simulación grupal. Intenten no matarse entre ustedes, al menos hasta que termine el experimento.",
    "¡Buenas noticias! Un software para compartir con otros sacos de carne a un precio insignificante.",
    "¡Abran paso! He diseñado este protocolo cooperativo para que dejen de estorbar individualmente."
]

FRASES_SOLO = [
    "¡Ah, el dulce aislamiento! Perfecto para ignorar al resto del universo.",
    "Un experimento diseñado para un solo individuo. Ideal para quienes odian el contacto humano tanto como yo.",
    "He calibrado este juego para que nadie los moleste. ¡Váyanse de mi laboratorio!",
    "¿Quién necesita amigos cuando tienes una simulación computarizada y un frasco de ojos de repuesto?"
]

FRASES_INGLES = [
    "¡Por las barbas de un decápodo! La descripción está en inglés. Si no la entienden, culpen al sistema educativo de este cuadrante.",
    "Mis disculpas, la base de datos está en un idioma primitivo llamado inglés. ¡Usen sus traductores cerebrales!",
    "Reseña en inglés detectada. Espero que sus implantes de lenguaje funcionen, porque no pienso traducirlo.",
    "¡Maldición! El reporte viene en inglés. ¡Leela tú, que eres joven y tu cerebro aún no es gelatina!"
]

FRASES_DESPEDIDA = [
    "Ya hice suficiente por hoy. Me voy a organizar mi colección de cables.",
    "No me busquen en las próximas horas, estaré en la cámara de sueños o ignorándolos activamente.",
    "¡Adiós a todos! Me voy a mi pijama de una sola pieza.",
    "Los acompañaría a jugar, pero ya me puse la pijama.",
    "¡Arreglen sus propios problemas! Me voy a mi cámara de gritos."
]

def detectar_ingles(texto):
    """Detecta si el texto está mayormente en inglés basándose en palabras comunes."""
    palabras_en = {'the', 'and', 'with', 'from', 'this', 'your', 'about'}
    texto_set = set(texto.lower().split())
    return len(texto_set.intersection(palabras_en)) >= 2

def obtener_precios_regionales(app_id):
    """Consulta precios y extrae el nombre exacto del producto en Steam."""
    try:
        url_cl = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res_cl = requests.get(url_cl, timeout=10).json()
        
        url_ar = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=ar&l=spanish"
        res_ar = requests.get(url_ar, timeout=10).json()

        if res_cl and res_cl[str(app_id)]['success']:
            data_cl = res_cl[str(app_id)]['data']
            if data_cl.get('is_free'): return None
            
            p_cl = data_cl.get('price_overview')
            if not p_cl or p_cl.get('discount_percent', 0) <= 0: return None

            precio_ar = "N/A"
            if res_ar and res_ar[str(app_id)]['success']:
                p_ar = res_ar[str(app_id)]['data'].get('price_overview', {})
                precio_ar = p_ar.get('final_formatted', 'N/A')

            return {
                'es_multi': any(c['id'] in [1, 9, 38] for c in data_cl.get('categories', [])),
                'desc': data_cl.get('short_description', 'Sin descripción.'),
                'clp': p_cl.get('final_formatted'),
                'ars_usd': precio_ar,
                'descuento': p_cl.get('discount_percent'),
                'title': data_cl.get('name', 'Sujeto de Prueba'),
                'id': app_id
            }
        return None
    except: return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi, candidatos_solo = [], []
    ids_vistos = set() 
    
    # EXPLORACIÓN AMPLIADA: 10 páginas = ~600 juegos
    for pagina in range(10):
        url = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url).json()
            for o in ofertas:
                s_id = o.get('steamAppID')
                if not s_id or s_id in ids_vistos: continue
                
                datos = obtener_precios_regionales(s_id)
                if datos:
                    # Filtro de duplicados por nombre base
                    nombre_base = datos['title'].split(':')[0].lower()
                    if nombre_base in ids_vistos: continue
                    
                    datos['score'] = int(o.get('metacriticScore', 0))
                    if datos['es_multi']: candidatos_multi.append(datos)
                    else: candidatos_solo.append(datos)
                    
                    ids_vistos.add(s_id)
                    ids_vistos.add(nombre_base)
                
                # Respeto a la API de Steam (Crucial al subir el volumen)
                time.sleep(1.2)
        except: continue

    # Ordenar por puntaje de Metacritic
    for lista in [candidatos_multi, candidatos_solo]:
        lista.sort(key=lambda x: (x['score'], x['descuento']), reverse=True)

    # --- ENVÍO DE RECOMENDACIONES ---
    for lista, tipo_label, emoji, frases_tipo in [
        (candidatos_multi, "RECOMENDACIÓN COOPERATIVA", "📡", FRASES_COOP),
        (candidatos_solo, "EXPERIMENTO DE AISLAMIENTO", "🧬", FRASES_SOLO)
    ]:
        if lista:
            best = lista[0]
            prefijo = "UNA" if "RECOMENDACIÓN" in tipo_label else "UN"
            
            frase_intro = random.choice(frases_tipo)
            if detectar_ingles(best['desc']):
                frase_intro = f"{frase_intro}\n\n⚠️ *{random.choice(FRASES_INGLES)}*"

            msg = (
                f"# 🧪 EL PROFESOR TIENE {prefijo} {tipo_label}\n"
                f"----------------------------------------------------------\n"
                f"## {emoji} {best['title']} {emoji}\n"
                f"----\n"
                f"{frase_intro}\n\n"
                f"**Descripción:** {best['desc']}\n\n"
                f"**Calibración:** ⚡ {best['score']}/100\n"
                f"**Descuento:** 📉 {best['descuento']}%\n"
                f"**Costo:** 💰 {best['clp']}\n"
                f"**Ref. Argentina:** 🇦🇷 {best['ars_usd']}\n"
                f"**Enlace:** https://store.steampowered.com/app/{best['id']}\n"
                f"----------------------------------------------------------"
            )
            requests.post(webhook_url, json={"content": msg})
            time.sleep(2)

    # --- MENCIONES DESHONROSAS ---
    final = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n"
    final += "----------------------------------------------------------\n"
    for cat, l in [("📡 Otros grupales", candidatos_multi), ("🧬 Otros solitarios", candidatos_solo)]:
        if l:
            final += f"### {cat}:\n"
            # Mostramos los 4 siguientes mejores después del principal
            for s in l[1:5]:
                final += f"• **{s['title']}**\n  💰 {s['clp']}  |  🇦🇷 {s['ars_usd']}  |  📉 -{s['descuento']}%\n\n"
    
    final += "----------------------------------------------------------\n"
    final += f"*{random.choice(FRASES_DESPEDIDA)}*"
    requests.post(webhook_url, json={"content": final})

if __name__ == "__main__":
    enviar_mensaje()

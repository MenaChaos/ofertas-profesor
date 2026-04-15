import requests
import os
import time
import random

# --- CONFIGURACIÓN DE PERSONALIDAD ---
FRASES_COOP = [
    "¡Buenas noticias, Jenkins! He encontrado un experimento grupal. Es casi tan peligroso como aquella vez que envié a la tripulación anterior a una avispa gigante... ¡Casi!",
    "¡Atención, tripulación! Este juego requiere trabajar en equipo. Si logran cooperar mejor que Fry y Bender cuando encuentran una moneda, ¡podrían sobrevivir!"
]

FRASES_SOLO = [
    "¡Ah, el dulce aislamiento! Este juego es perfecto para ignorar al resto del universo. ¡Es como meterse en mi propia Cámara de la Muerte!",
    "¡Buenas noticias! Este juego es individual porque nadie más soportaría sus tácticas de juego, Jenkins."
]

FRASES_DESPEDIDA = [
    "Los acompañaría a jugar, pero ya me puse la pijama.",
    "¡En fin, me voy a dormir! Si el laboratorio explota, no me despierten."
]

def obtener_datos_steam(app_id):
    """
    Obtiene datos de Steam Chile y aplica un triple filtro de seguridad
    para garantizar que el descuento sea REAL en la región.
    """
    try:
        # cc=cl garantiza que consultamos la base de datos de Chile directamente
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res = requests.get(url, timeout=12).json()
        
        if res and res[str(app_id)]['success']:
            data = res[str(app_id)]['data']
            
            # 1. Verificamos que el juego no sea gratuito y tenga información de precio
            if data.get('is_free') or 'price_overview' not in data:
                return None, None, None

            price_data = data['price_overview']
            
            # --- TRIPLE FILTRO DE SEGURIDAD ---
            # A. ¿Hay un porcentaje de descuento reportado por Steam Chile?
            descuento_steam = price_data.get('discount_percent', 0)
            # B. ¿El precio final es realmente menor al inicial? (en centavos)
            precio_final = price_data.get('final', 0)
            precio_inicial = price_data.get('initial', 0)

            if descuento_steam <= 0 or precio_final >= precio_inicial:
                # Si no hay descuento real en Chile, el experimento se cancela
                return None, None, None
            # ----------------------------------

            precio_clp = price_data.get('final_formatted', 'N/A')
            desc = data.get('short_description', 'Sin descripción disponible para este espécimen.')
            
            # Clasificación Multijugador
            categorias = [cat['id'] for cat in data.get('categories', [])]
            es_multi = any(id_m in categorias for id_m in [1, 9, 38])
            
            return es_multi, desc, precio_clp
        return None, None, None
    except Exception as e:
        print(f"Error en el sensor: {e}")
        return None, None, None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi = []
    candidatos_solo = []
    
    # Escaneo de 300 juegos (5 páginas de CheapShark)
    for pagina in range(5):
        url_ofertas = f"https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=20&onSale=1&metacritic=80&pageNumber={pagina}"
        try:
            ofertas = requests.get(url_ofertas).json()
            if not ofertas: break
            for o in ofertas:
                if not o.get('steamAppID'): continue
                
                # Obtener datos con el nuevo filtro de seguridad regional
                es_multi, desc, p_clp = obtener_datos_steam(o['steamAppID'])
                
                if p_clp: # Solo si pasó los filtros de seguridad
                    o['desc'] = desc
                    o['precio_clp'] = p_clp
                    o['score'] = int(o.get('metacriticScore', 0))
                    o['ahorro'] = float(o.get('savings', 0))
                    
                    if es_multi: candidatos_multi.append(o)
                    else: candidatos_solo.append(o)
                
                # Pequeña pausa para no saturar la API de Steam
                time.sleep(1.2)
        except: continue

    # Ordenar por calidad científica (Metacritic)
    candidatos_multi.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)
    candidatos_solo.sort(key=lambda x: (x['score'], x['ahorro']), reverse=True)

    # --- ENVÍOS SEPARADOS ---

    # 1. Recomendación Cooperativa
    if candidatos_multi:
        best = candidatos_multi[0]
        frase = random.choice(FRASES_COOP)
        m_coop = (
            f"📡 **RECOMENDACIÓN COOPERATIVA DEL PROFESOR** 📡\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n---\n"
            f"{frase}\n\n"
            f"**Descripción:** {best['desc']}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Costo:** 💰 {best['precio_clp']}\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_coop})
        time.sleep(2)

    # 2. Experimento de Aislamiento
    if candidatos_solo:
        best = candidatos_solo[0]
        frase = random.choice(FRASES_SOLO)
        m_solo = (
            f"🧬 **EXPERIMENTO DE AISLAMIENTO DEL PROFESOR** 🧬\n"
            f"**Descuento:** 📉 {best['ahorro']:.0f}%\n---\n"
            f"{frase}\n\n"
            f"**Descripción:** {best['desc']}\n\n"
            f"**Calibración:** ⚡ {best['score']}/100\n"
            f"**Costo:** 💰 {best['precio_clp']}\n"
            f"**Enlace al vicio:** https://store.steampowered.com/app/{best['steamAppID']}"
        )
        requests.post(webhook_url, json={"content": m_solo})
        time.sleep(2)

    # 3. Menciones Deshonrosas
    final_info = "🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n---\n"
    final_info += "He detectado otros especímenes con ofertas reales en el territorio chileno. Échenles un ojo antes de que el universo colapse.\n\n"
    
    if len(candidatos_multi) > 1:
        final_info += "**📡 Otros sujetos grupales:**\n"
        final_info += "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_multi[1:5]])
        final_info += "\n\n"
    
    if len(candidatos_solo) > 1:
        final_info += "**🧬 Otros sujetos solitarios:**\n"
        final_info += "\n".join([f"• {s['title']}: {s['precio_clp']} (-{s['ahorro']:.0f}%)" for s in candidatos_solo[1:5]])
        final_info += "\n\n"

    final_info += f"*{random.choice(FRASES_DESPEDIDA)}*"
    requests.post(webhook_url, json={"content": final_info})

if __name__ == "__main__":
    enviar_mensaje()

import requests
import os
import time
import random
from datetime import datetime, timedelta
from functools import cmp_to_key  # Importado para la nueva lógica de ordenamiento

# --- CATÁLOGO DE PERSONALIDAD DEL PROFESOR ---
FRASES_COOP = [
    "¡Atención, tripulación! Si logran cooperar mejor que Fry y Bender, podrían sobrevivir.",
    "He encontrado una simulación grupal. Intenten no matarse entre ustedes.",
    "¡Buenas noticias! Un software para compartir con otros sacos de carne.",
    "¡Abran paso! Protocolo cooperativo activado para que dejen de estorbar.",
    "¿Cooperación? ¡Qué concepto tan primitivo! Pero aquí tienen algo para perder el tiempo.",
    "He detectado que necesitan interacción social. Aquí tienen su medicina.",
    "¡Miren esto! Un juego donde pueden fracasar juntos. ¡Como mi laboratorio!"
]

FRASES_SOLO = [
    "¡Ah, el dulce aislamiento! Perfecto para ignorar al resto del universo.",
    "Experimento para un solo individuo. Ideal para quienes odian el contacto humano.",
    "He calibrado este juego para que nadie los moleste. ¡Váyanse de mi laboratorio!",
    "¿Quién necesita amigos cuando tienes una simulación y un frasco de ojos de repuesto?",
    "¡Excelente! Un juego para personas que disfrutan de su propia compañía.",
    "He analizado este software y garantiza cero contacto con otros seres vivos.",
    "Si van a estar solos, al menos asegúrense de que el software sea de alta calidad."
]

FRASES_INGLES = [
    "¡Por las barbas de un decápodo! La descripción está en inglés. Culpen al sistema educativo.",
    "Mis disculpas, la base de datos está en un idioma primitivo llamado inglés.",
    "Reseña en inglés detectada. Espero que sus implantes de lenguaje funcionen.",
    "¡Maldición! El reporte viene en inglés. ¡Léela tú, que tu cerebro aún no es gelatina!",
    "¿Inglés? Mi traductor universal está en mantenimiento, usen su imaginación.",
    "¡Indignante! Una descripción sin traducir. Es como si esperaran que yo hiciera todo.",
    "Advertencia: Texto en dialecto anglosajón. No me miren a mí, yo hablo ciencia."
]

FRASES_DESPEDIDA = [
    "Ya hice suficiente por hoy. Me voy a organizar mi colección de cables.",
    "No me busquen, estaré en la cámara de sueños o ignorándolos activamente.",
    "¡Adiós a todos! Me voy a mi pijama de una sola pieza.",
    "¡Los acompañaría a jugar, pero ya me puse la pijama.",
    "¡Arreglen sus propios problemas! Me voy a mi cámara de gritos.",
    "Me retiro. Tengo que alimentar a mis experimentos... y a Mordelón.",
    "¡Basta de ciencia por hoy! Me voy a ver mis novelas holográficas.",
    "Si me necesitan, estaré en el año 3000. ¡O sea, en mi cama!",
    "¿Todavía están aquí? ¡Fuera! ¡Fuera de mi laboratorio!",
    "Ya me cansé de buscar ofertas para sus billeteras vacías. ¡Hasta nunca!"
]

# --- LÓGICA DE MEMORIA (14 DÍAS) ---
HISTORIAL_FILE = "historial.txt"

def gestionar_historial(nuevos_ids=[]):
    ahora = datetime.now()
    limite = ahora - timedelta(days=14)
    registros_validos = []
    ids_en_historial = set()

    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            for linea in f:
                try:
                    app_id, fecha_str = linea.strip().split(",")
                    fecha_reg = datetime.strptime(fecha_str, "%Y-%m-%d")
                    if fecha_reg > limite:
                        registros_validos.append(linea.strip())
                        ids_en_historial.add(app_id)
                except: continue

    if not nuevos_ids:
        return ids_en_historial

    fecha_hoy = ahora.strftime("%Y-%m-%d")
    for nid in nuevos_ids:
        if str(nid) not in ids_en_historial:
            registros_validos.append(f"{nid},{fecha_hoy}")
    
    with open(HISTORIAL_FILE, "w") as f:
        f.write("\n".join(registros_validos) + "\n")

def detectar_ingles(texto):
    palabras_en = {'the', 'and', 'with', 'from', 'this', 'your', 'about', 'world', 'game'}
    texto_set = set(texto.lower().split())
    return len(texto_set.intersection(palabras_en)) >= 2

def obtener_precios_regionales(app_id):
    try:
        url_cl = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cl&l=spanish"
        res_cl = requests.get(url_cl, timeout=10).json()
        
        if res_cl and res_cl[str(app_id)]['success']:
            data_cl = res_cl[str(app_id)]['data']
            
            # FILTRO DE FECHA (MÁXIMO 6 AÑOS)
            release_info = data_cl.get('release_date', {})
            date_str = release_info.get('date', '')
            if date_str:
                try:
                    year_release = int(date_str.split()[-1])
                    current_year = datetime.now().year
                    if (current_year - year_release) > 6:
                        return None
                except: pass

            if data_cl.get('is_free'): return None
            p_cl = data_cl.get('price_overview')
            if not p_cl or p_cl.get('discount_percent', 0) <= 0: return None

            url_ar = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=ar&l=spanish"
            res_ar = requests.get(url_ar, timeout=10).json()
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

def comparar_ofertas(a, b):
    # Si la diferencia de puntaje es de 5 puntos o menos, decide el descuento
    if abs(a['score'] - b['score']) <= 5:
        if b['descuento'] != a['descuento']:
            return b['descuento'] - a['descuento']
    # Si la diferencia es mayor a 5 o descuentos iguales, el de mayor puntaje gana
    return b['score'] - a['score']

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    candidatos_multi, candidatos_solo = [], []
    ids_vistos = set()
    
    bloqueados_historial = gestionar_historial()

    print(f"🚀 INICIANDO ESCANEO DE LARGO ALCANCE (900 JUEGOS)...")

    # Encabezado para identificarnos como navegador y evitar bloqueos
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for pagina in range(15):
        url = "https://www.cheapshark.com/api/1.0/deals"
        params = {
            "storeID": "1",
            "upperPrice": "20",
            "onSale": "1",
            "pageNumber": str(pagina)
        }
        
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"🔎 Probando página {pagina} - Respuesta HTTP: {res.status_code}")
            
            if res.status_code != 200:
                print(f"⚠️ Detalle del error {res.status_code}: {res.text}")
                continue

            ofertas = res.json()
            if not ofertas: 
                print("ℹ️ No hay más ofertas disponibles.")
                break

            for o in ofertas:
                # Filtrar la nota de Metacritic (80 o superior) directamente en Python
                score = int(o.get('metacriticScore') or 0)
                if score < 80:
                    continue

                s_id = o.get('steamAppID')
                if not s_id or s_id in ids_vistos or str(s_id) in bloqueados_historial:
                    continue

                datos = obtener_precios_regionales(s_id)
                if datos:
                    nombre_base = datos['title'].split(':')[0].lower()
                    if nombre_base in ids_vistos: continue

                    datos['score'] = score
                    if datos['es_multi']: candidatos_multi.append(datos)
                    else: candidatos_solo.append(datos)

                    ids_vistos.add(s_id)
                    ids_vistos.add(nombre_base)
                
                time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error en página {pagina}: {e}")
            continue

    # Aplicar nueva lógica de ordenamiento con el rango de 5 puntos
    for lista in [candidatos_multi, candidatos_solo]:
        lista.sort(key=cmp_to_key(comparar_ofertas))

    ids_a_registrar = []

    for lista, tipo_label, emoji, frases_tipo in [
        (candidatos_multi, "RECOMENDACIÓN COOPERATIVA", "🐀", FRASES_COOP),
        (candidatos_solo, "EXPERIMENTO DE AISLAMIENTO", "🚀", FRASES_SOLO)
    ]:
        if lista:
            best = lista[0]
            ids_a_registrar.append(best['id'])
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
                f"**Costo:** 🇨🇱 {best['clp']}\n"
                f"**Ref. Argentina:** 🇦🇷 {best['ars_usd']}\n"
                f"**Enlace:** https://store.steampowered.com/app/{best['id']}\n"
                f"----------------------------------------------------------"
            )
            requests.post(webhook_url, json={"content": msg})
            time.sleep(2)

    final = "# 🧪 **MENCIONES DESHONROSAS (SUJETOS SECUNDARIOS)**\n"
    final += "----------------------------------------------------------\n"
    hay_menciones = False
    
    for cat, l, cat_emoji in [("Otros grupales", candidatos_multi, "👥"), ("Otros solitarios", candidatos_solo, "🚀")]:
        if len(l) > 1:
            hay_menciones = True
            final += f"### {cat_emoji} {cat}:\n"
            for s in l[1:5]:
                final += f"• **{s['title']}** | 🇨🇱 {s['clp']} | 🇦🇷 {s['ars_usd']} | 📉 -{s['descuento']}%\n"
                ids_a_registrar.append(s['id'])
    
    if hay_menciones:
        final += "----------------------------------------------------------\n"
        final += f"*{random.choice(FRASES_DESPEDIDA)}*"
        requests.post(webhook_url, json={"content": final})

    if ids_a_registrar:
        gestionar_historial(ids_a_registrar)

if __name__ == "__main__":
    enviar_mensaje()

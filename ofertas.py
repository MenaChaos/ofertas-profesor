import requests
import os
import random
import time

def obtener_calificacion_steam(app_id):
    """ Obtiene las categorías y la calificación (si es posible) de Steam """
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url)
        data = response.json()
        
        if data and data[str(app_id)]['success']:
            info = data[str(app_id)]['data']
            # Verificamos si es Multi-player (1), Co-op (9) u Online Co-op (38)
            categorias = [cat['id'] for cat in info.get('categories', [])]
            es_multi = any(id_multi in categorias for id_multi in [1, 9, 38])
            
            # Si no es multi, devolvemos 0 para descartarlo
            if not es_multi:
                return 0
            
            # Devolvemos el porcentaje de ahorro de CheapShark como puntaje
            return es_multi
        return False
    except:
        return False

def buscar_la_mejor_oferta():
    # Buscamos ofertas potentes (descuento > 70% y nota Metacritic > 70)
    url_api = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=15&onSale=1&metacritic=70"
    
    try:
        response = requests.get(url_api)
        ofertas = response.json()
        
        candidatos_multi = []
        
        print("Analizando ofertas para encontrar la mejor opción multijugador...")
        
        # Revisamos los primeros 25 resultados para no demorar horas
        for juego in ofertas[:25]:
            if obtener_calificacion_steam(juego['steamAppID']):
                # Guardamos el juego junto con su porcentaje de ahorro (savings) para comparar
                juego['savings_float'] = float(juego['savings'])
                candidatos_multi.append(juego)
                print(f"Candidato encontrado: {juego['title']} ({juego['savings']}% ahorro)")
            
            time.sleep(0.6) # Respiro para la API de Steam

        if not candidatos_multi:
            return None

        # ORDENAR: El que tenga mayor porcentaje de ahorro (savings) va primero
        candidatos_multi.sort(key=lambda x: x['savings_float'], reverse=True)
        
        # Devolvemos el número 1 de la lista (la mejor oferta)
        return candidatos_multi[0]

    except Exception as e:
        print(f"Error: {e}")
        return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    if not webhook_url: return

    juego = buscar_la_mejor_oferta()
    
    if juego:
        nombre = juego['title']
        precio_oferta = juego['salePrice']
        ahorro = round(juego['savings_float'])
        link = f"https://store.steampowered.com/app/{juego['steamAppID']}"
        
        frases = [
            f"¡Buenas noticias! He analizado todas las ofertas y la ganadora absoluta es **{nombre}**. ¡Un ahorro del **{ahorro}%**! Solo ${precio_oferta} por un gran cooperativo.",
            f"¡Grandes noticias! Después de descartar juegos mediocres, he hallado esta joya multi: **{nombre}**. Bajó un **{ahorro}%**, ¡quedó a solo ${precio_oferta}!",
            f"¡Atención, carnes con ojos! He optimizado mi búsqueda y **{nombre}** es la oferta más eficiente del día. **{ahorro}%** de descuento. ¡Cómprelo antes de que me arrepienta!"
        ]
        
        data = {"content": f"{random.choice(frases)}\n{link}"}
        requests.post(webhook_url, json=data)
        print(f"Mejor oferta enviada: {nombre} con {ahorro}% de ahorro.")
    else:
        print("No se encontró ninguna oferta multijugador que valga la pena hoy.")

if __name__ == "__main__":
    enviar_mensaje()

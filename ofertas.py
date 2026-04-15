import requests
import os
import random
import time

def es_multijugador(app_id):
    """ Verifica en la API de Steam si el juego tiene etiquetas de multijugador o coop """
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url)
        data = response.json()
        
        if data and data[str(app_id)]['success']:
            info = data[str(app_id)]['data']
            # Categorías de Steam: 1 es Multi-player, 9 es Co-op, 38 es Online Co-op
            categorias = [cat['id'] for cat in info.get('categories', [])]
            # Si tiene alguna de estas IDs, nos sirve
            if any(id_multi in categorias for id_multi in [1, 9, 38]):
                return True
        return False
    except:
        return False

def buscar_oferta_multi():
    # Buscamos ofertas con buen descuento y nota Metacritic > 70
    url_api = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=15&onSale=1&metacritic=70"
    
    try:
        response = requests.get(url_api)
        ofertas = response.json()
        random.shuffle(ofertas) # Desordenamos para no ver siempre los mismos
        
        # El Profesor buscará entre los primeros 20 resultados uno que sea Multi
        for juego in ofertas[:20]:
            if es_multijugador(juego['steamAppID']):
                return juego
            time.sleep(0.5) # Un pequeño respiro para no saturar a Steam
            
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    if not webhook_url: return

    juego = buscar_oferta_multi()
    
    if juego:
        nombre = juego['title']
        precio_oferta = juego['salePrice']
        ahorro = round(float(juego['savings']))
        link = f"https://store.steampowered.com/app/{juego['steamAppID']}" # Link directo a Steam
        
        frases = [
            f"¡Buenas noticias! He encontrado **{nombre}** con un **{ahorro}%** de descuento. ¡Es multijugador, ideal para que manqueen juntos por solo ${precio_oferta}!",
            f"¡Grandes noticias! El juego cooperativo **{nombre}** está a precio de huevo: ${precio_oferta}. ¡Prendan el PC, estúpidos!",
            f"¡Atención! Si quieren gastar poco, **{nombre}** está en oferta. Tiene multi, así que no hay excusa para no jugar hoy."
        ]
        
        data = {"content": f"{random.choice(frases)}\n{link}"}
        requests.post(webhook_url, json=data)
        print(f"Oferta enviada: {nombre}")
    else:
        print("No pillé ni una oferta multi buena hoy.")

if __name__ == "__main__":
    enviar_mensaje()

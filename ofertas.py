import requests
import os
import random
import time

def es_multijugador(app_id):
    """ Verifica en la API de Steam si el juego tiene categorías de multijugador """
    try:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url)
        data = response.json()
        
        if data and data[str(app_id)]['success']:
            info = data[str(app_id)]['data']
            categorias = [cat['id'] for cat in info.get('categories', [])]
            # 1: Multi-player, 9: Co-op, 38: Online Co-op
            return any(id_multi in categorias for id_multi in [1, 9, 38])
        return False
    except:
        return False

def buscar_la_mejor_evaluada():
    # Buscamos ofertas (descuento > 50% y nota Metacritic > 75 para asegurar calidad)
    url_api = "https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=15&onSale=1&metacritic=75"
    
    try:
        response = requests.get(url_api)
        ofertas = response.json()
        
        candidatos_multi = []
        print("Buscando la joya multijugador con mejor crítica...")
        
        # Analizamos los primeros 25 resultados
        for juego in ofertas[:25]:
            if es_multijugador(juego['steamAppID']):
                # Guardamos el puntaje de Metacritic para comparar
                juego['score_float'] = float(juego['metacriticScore'])
                candidatos_multi.append(juego)
                print(f"Analizado: {juego['title']} - Nota: {juego['metacriticScore']}")
            
            time.sleep(0.6) # Evitar bloqueo de Steam

        if not candidatos_multi:
            return None

        # ORDENAR: El que tenga mayor Metascore (nota) va primero
        candidatos_multi.sort(key=lambda x: x['score_float'], reverse=True)
        
        return candidatos_multi[0]

    except Exception as e:
        print(f"Error: {e}")
        return None

def enviar_mensaje():
    webhook_url = os.getenv('WEBHOOK_PROFESOR')
    if not webhook_url: return

    juego = buscar_la_mejor_evaluada()
    
    if juego:
        nombre = juego['title']
        precio = juego['salePrice']
        nota = juego['metacriticScore']
        link = f"https://store.steampowered.com/app/{juego['steamAppID']}"
        
        frases = [
            f"¡Buenas noticias! He encontrado una obra maestra: **{nombre}**. Tiene una nota de **{nota}** en Metacritic y está a solo ${precio}. ¡Es multijugador!",
            f"¡Grandes noticias! Si buscan calidad, **{nombre}** es el mejor evaluado hoy (Nota: **{nota}**). ¡Un regalo por ${precio}!",
            f"¡Atención! He ignorado la basura barata y me quedé con esto: **{nombre}**. Nota: **{nota}**. Ideal para gente de gusto refinado como Los Jenkins."
        ]
        
        data = {"content": f"{random.choice(frases)}\n{link}"}
        requests.post(webhook_url, json=data)
        print(f"Enviado el mejor evaluado: {nombre} (Nota: {nota})")
    else:
        print("No pillé nada de alta calidad hoy.")

if __name__ == "__main__":
    enviar_mensaje()

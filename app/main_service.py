from openai import OpenAI
import threading
from datetime import datetime, timedelta
from fastapi import Request
from dotenv import load_dotenv
import os
import PyPDF2

# Cargamos el archivo .env
load_dotenv()

# Traemos las variables de entorno
API_TOKEN = os.getenv("OPENROUTER_API_TOKEN")
TIEMPO_EXPIRACION = os.getenv("TIEMPO_EXPIRACION")
TIEMPO_EXPIRACION = int(TIEMPO_EXPIRACION)  # Convertimos a entero
TIEMPO_REPETICION = os.getenv("TIEMPO_REPETICION")
TIEMPO_REPETICION = int(TIEMPO_REPETICION)  # Convertimos a entero

# Creamos el cliente con la API Key de OpenRouter
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_TOKEN)

# Obtenemos la configuración del modelo de un pdf
def extraer_texto_pdf(ruta_pdf):
    with open(ruta_pdf, 'rb') as archivo_pdf:
        # Crear un objeto de lectura de PDF
        lector_pdf = PyPDF2.PdfReader(archivo_pdf)
        
        # Extraer texto de cada página
        texto = ""
        for pagina in range(len(lector_pdf.pages)):
            pagina_objeto = lector_pdf.pages[pagina]
            texto += pagina_objeto.extract_text()
    return texto

texto_pdf = extraer_texto_pdf(os.path.join(os.path.dirname(__file__), 'files', 'model_config.pdf'))

# Creamos la memoria base
memoria = [
    {
        "role": "system",
        "content": texto_pdf,
    }
]

# Creamos un diccionario de memorias que almacenará cada una de la memoria de los usuarios
diccionario_memorias = {}
# Tiempos de última actividad
tiempo_actividad = {}

def obtener_ip_real(request: Request) -> str:
    """
    Función para obtener la IP real del usuario que hace la consulta a la API en FastAPI.

    Args:
        request (Request): Objeto de solicitud de FastAPI.

    Returns:
        str: IP del usuario que ha hecho la consulta.
    """
    if "X-Forwarded-For" in request.headers:
        ip = request.headers["X-Forwarded-For"].split(",")[0].strip()
    else:
        ip = request.client.host
    return ip

def consultar_ia(usuario, prompt)-> str:
    """
    Función que nos permite consultar el modelo mediante un prompt. Creará una memoria por cada uno de los usuarios que le consulte.

    Args:
        usuario (str): id del usuario que consulta al modelo.
        prompt (str): prompt con el que consultaremos al modelo.

    Returns:
        str: devuelve la respuesta del modelo a la consulta del usuario.
    """
    # Comprobamos si el usuario ya ha interactuado con el chat
    try:
        if usuario not in diccionario_memorias:
            diccionario_memorias[usuario] = memoria.copy()
            print(f"🟢 Nueva memoria para el usuario: {usuario}")
        # Actualizamos tiempo de actividad
        print(f"🟡: {prompt}")
        tiempo_actividad[usuario] = datetime.now()
        # Añadimos el prompt a la memoria
        diccionario_memorias[usuario].append({"role": "user", "content": prompt})
        # Realizamos la solicitud al modelo Quasar-alpha con el prompt proporcionado
        completion = client.chat.completions.create(
            extra_headers={},
            model="openrouter/quasar-alpha",  # Asegúrate de que este sea el modelo correcto
            messages=diccionario_memorias[usuario],
        )
        # Extraemos la respuesta de la IA
        respuesta = completion.choices[0].message.content
        print(f"🟣: {prompt}")
        # Guardamos la respuesta en la memoria
        diccionario_memorias[usuario].append({"role": "assistant", "content": respuesta})
        # Ejecutamos el método
        limpiar_memorias_inactivas(TIEMPO_EXPIRACION, TIEMPO_REPETICION)
        return respuesta
    except Exception as e:
        print(f"Error al consultar IA: {e}")
        print(f"TOKEN: {API_TOKEN}")
        return "Lo siento, ha habido un error al procesar tu solicitud. Pongase en contacto con el desarrollador."


def limpiar_memorias_inactivas(tiempo_expiracion, tiempo_repeticion):
    """
    Función que se ejecuta cada X número de segundos que borra la memoria de los usuarios que no han interactuado con el chat en X minutos

    Args:
        tiempo_expiracion int: cantidad de minutos en los que el usuario tiene que interactuar el chat para evitar que se borre su memoria.
        tiempo_repeticion int: cantidad de segundos que tarda esta función en volver a ejecutarse.
    """
    print("🔵 Comprobando memorias inactivas...")
    # Creamos una lista de usuarios a eliminar
    usuarios_a_eliminar = []
    # Para cada usuario que tengamos en tiempo_actividad, haremos:
    for usuario, ultima_interaccion in tiempo_actividad.items():
        # Comprobamos si ha pasado el tiempo de expiración
        if datetime.now() - ultima_interaccion > timedelta(minutes=tiempo_expiracion):
            # Añadimos el usuario a la lista de usuarios a eliminar
            usuarios_a_eliminar.append(usuario)
    for usuario in usuarios_a_eliminar:
        # Eliminamos la memória del usuario y su ultima actividad
        del diccionario_memorias[usuario]
        del tiempo_actividad[usuario]
        print(f"🟠 Memoria eliminada para el usuario: {usuario}")
    # Hacemos que despues de X segundos, se vuelva a ejecutar el método
    if len(diccionario_memorias) > 0:
        threading.Timer(
            tiempo_repeticion,
            limpiar_memorias_inactivas,
            args=[tiempo_expiracion, tiempo_repeticion],
        ).start()
    else: 
        print("🔴 Ya no hay memorias que eliminar.")

# # Ejemplo de uso
# prompt = "¿Hay leopardos en la albufera?"
# respuesta = consultar_ia("yo", prompt)
# print(respuesta)

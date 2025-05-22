#Downloaded libraries: langchain and langchain-community
from langchain.document_loaders import PyPDFLoader
import os
from langchain.document_loaders import PyPDFLoader
import requests
import re
from datetime import datetime
import json
import logging

# Configuración básica del logger
logging.basicConfig(
    level=logging.INFO,  
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',  # Opcional: guarda en archivo
    filemode='w' 
)

#Directorio para recoger periódico
carpeta = "newspaper"
pdfs = []

#Identificado carpeta y recorriendo archivos
for archivo in os.listdir(carpeta):
    if archivo.endswith(".pdf"):
        pdfs.append(os.path.join(carpeta, archivo))

print("PDFs encontrados:")
for pdf in pdfs:
    print(pdf)

logging.info("************************INICIO EXTRACCIÓN DE TEXTO************************")

# Cargar PDF y extraer texto
loader = PyPDFLoader('periodico.pdf')
pages = loader.load()

# Número de páginas por bloque
bloque_tamaño = 2
total_paginas = len(pages)

# Lista para almacenar texto por bloque. 
bloques_texto = []
structured_text = []

#Llamada a LLM para reorganización de texto.
def gemma(text: str) -> str:
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""Reorganiza el siguiente texto para asegurar que tenga coherencia semántica y fluya de forma lógica, mantén el idioma original (español) y NO agregués, eliminés o resumas el contenido; únicamente debes reordenar las partes del texto según sea necesario para mejorar su coherencia, no des explicaciones de cómo lo hiciste.
    Texto: {text}
"""

    payload = {
        "model": "gemma2:9b",  
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

logging.info("************************PROCESANDO TEXTO BLOQUE POR BLOQUE************************")
for i in range(0, total_paginas, bloque_tamaño):
    bloque = pages[i:i + bloque_tamaño]
    texto_bloque = '\n\n'.join([p.page_content for p in bloque])
    bloques_texto.append(texto_bloque)
    
    if __name__ == "__main__":
        result = gemma(bloques_texto[-1])
        structured_text.append(result)
        print("Texto reorganizado:\n")
        print(result)

logging.info("************************EXTRACCIÓN TEXTO BLOQUE POR BLOQUE FINALIZADO************************")
logging.info("************************EXTRACCIÓN FECHA************************")

#Obteniendo primer chunk de texto extraido
texto = structured_text[0]

# Expresión regular para buscar fechas tipo
pattern = r"(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de (\d{4})"

match = re.search(pattern, texto, re.IGNORECASE)
if match:
    dia = int(match.group(1))
    mes_texto = match.group(2).lower()
    anio = int(match.group(3))

    # Diccionario para convertir mes en texto a número
    meses = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12
    }

    mes = meses[mes_texto]

    fecha = datetime(anio, mes, dia)
    strdate = fecha.strftime("%Y-%m-%d")
    print("Fecha extraída:", strdate)
else:
    print("No se encontró ninguna fecha.")

logging.info("************************INICIO PROCESAR TEXTO Y OBTENER JSON************************")

#Obteniendo parámetros para el manejo del arreglo del texto estructurado
total_pages = len(structured_text)
size = 2

#Creación de arrays
json_news = []
bloques_news = []

#Función: llamada al LLM
def gemma_news(text: str) -> str:
    url = "http://localhost:11434/api/generate"
    
    prompt = f"""
Separa el texto en cada noticia. La salida debe ser un arreglo JSON, donde cada noticia contenga un "Titular" y un "Contenido". NO repitas ninguna noticia.
Text: {text}
"""

    payload = {
        "model": "gemma2:9b",  
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return response.json()["response"]
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    for i in range(0, total_pages, size):
        #Extraer bloque para enviarlo a la llamada de la API
        bloque = structured_text[i:i + size]
        texto_bloque = '\n\n'.join([p for p in bloque])
        bloques_news.append(texto_bloque)

        response = gemma_news(texto_bloque)

        #Conservar el formato json
        start_index = response.find("[")
        end_index = response.rfind("]") + 1
        json_message = response[start_index:end_index]
        json_news.append(json_message)
        print(json_message)

logging.info("************************PROCESAMIENTO DE TEXTO FINALIZADO************************")
logging.info("************************CREACIÓN DE ARCHIVO JSON************************")


# Traer fecha definida y crear arreglo de las noticias parseadas
fecha_str = strdate
parsed_news = []

for item in json_news:
    try:
        noticias = json.loads(item) 
        for noticia in noticias:
            if isinstance(noticia, dict):
                noticia["fecha"] = fecha_str
        parsed_news.extend(noticias)
    except json.JSONDecodeError as e:
        print("Error al decodificar este item, será omitido:\n", item)
        continue

# Guardar los datos válidos con fecha en un archivo
with open("noticias.json", "w", encoding="utf-8") as file:
    json.dump(parsed_news, file, ensure_ascii=False, indent=2)


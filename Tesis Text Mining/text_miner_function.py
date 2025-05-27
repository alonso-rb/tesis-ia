#Downloaded libraries: langchain and langchain-community
from langchain.document_loaders import PyPDFLoader
import os
import re
import requests
import socket
import subprocess
import time
from datetime import datetime
import json
from typing import List, Dict, Any
import logging

DIRECTORIO_NOTICIAS = "newspaper"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
MODEL_NAME = "gemma2:9b"

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f'logs/app-{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'
)

def leer_pdf(folder_name: str) -> List[str]:
    logging.info("************************LEYENDO PDFS************************")
    pdfs = []

    for archivo in os.listdir(folder_name):
        if archivo.endswith(".pdf"):
            pdfs.append(os.path.join(folder_name, archivo))

    logging.info("************************FINALIZANDO PDFS************************")
    return pdfs

def construir_prompts_extraer(instructions: str, text: str) -> str:
    prompt = f"""{instructions}: {text}"""
    return prompt

def esta_ollama_levantado(host=OLLAMA_HOST, port=OLLAMA_PORT):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False

def verificar_y_levantar_ollama():
    if not esta_ollama_levantado():
        print("🟡 Ollama no está corriendo. Intentando levantarlo...")
        try:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(10):
                if esta_ollama_levantado():
                    print("✅ Ollama levantado correctamente.")
                    return True
                time.sleep(1)
            print("❌ No se pudo levantar Ollama después de varios intentos.")
            return False
        except Exception as e:
            print("❌ Error al intentar levantar Ollama:", e)
            return False
    else:
        print("✅ Ollama ya está corriendo.")
        return True

def gemma_extraer_texo(prompt: str) -> str:
    if not verificar_y_levantar_ollama():
        return "[]"

    payload = {"model": MODEL_NAME, "prompt": prompt, "temperature": 0, "top_p": 1, "stop" : ["\n\n"], "stream": False}
    response = requests.post(OLLAMA_API_URL, json=payload)

    if response.status_code == 200:
        try:
            return response.json()["response"]
        except json.JSONDecodeError:
            print("⚠️ Respuesta contiene múltiples objetos JSON. Procesando por líneas...")
            # Intenta parsear línea por línea
            lines = response.text.strip().splitlines()
            results = []
            for line in lines:
                try:
                    parsed = json.loads(line)
                    if "response" in parsed:
                        results.append(parsed["response"])
                except json.JSONDecodeError:
                    continue
            return "\n".join(results)
    else:
        raise Exception(f"Error {response.status_code}: {response.text}")

def extraer_texto_pdf(pdfs: List) -> str:
    logging.info("************************INICIO EXTRACCIÓN DE TEXTO************************")
    j=0
    loader = PyPDFLoader(pdfs[0])
    pages = loader.load()
    bloque_tamaño = 2
    total_paginas = len(pages)
    structured_text = []
    instructions_extract = '''
    Reorganiza el siguiente texto para asegurar coherencia semántica y lógica. \n\n
    No traduzcas, no resumas, no expliques, y no agregues ni elimines contenido. \n\n
    Solo cambia el orden de las partes del texto para que tenga más sentido. \n\n
    Texto:'''

    logging.info("************************PROCESANDO TEXTO BLOQUE POR BLOQUE************************")
    for i in range(0, total_paginas, bloque_tamaño):
        j = j +1
        logging.info(f"************************Procesando bloque {j}************************")
        bloque = pages[i:i + bloque_tamaño]
        texto_bloque = '\n\n'.join([p.page_content for p in bloque])
        logging.info(f"************************COMIENZA LLAMADA A GEMMA PARA BLOQUE {j}************************")
        logging.info(f"************************CONSTRUCCIÓN DE PROMPT************************")    
        prompt_extraer = construir_prompts_extraer(instructions_extract, texto_bloque)
        logging.info(f"************************INICIO EJECUCIÓN DE LA LLAMADA************************")  
        result = gemma_extraer_texo(prompt_extraer)
        logging.info(f"************************TERMINA LLAMADA A GEMMA PARA BLOQUE {j}************************")
        structured_text.append(result)
        print("\nTexto reorganizado:\n")
        print(result)

    logging.info("************************EXTRACCIÓN TEXTO BLOQUE POR BLOQUE FINALIZADO************************")
    return structured_text

def extraer_fecha_pdf(text : str) -> str:
    logging.info("************************INICIA EXTRACCIÓN FECHA************************")
    pattern = r"(\d{1,2}) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) de (\d{4})"

    match = re.search(pattern, text, re.IGNORECASE)
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
        logging.info("************************FINALIZA EXTRACCIÓN FECHA************************")
        return strdate
    else:
        print("No se encontró ninguna fecha.")
        return ''

def separar_noticias(news : List[str]) -> List[str]:
    h=0
    logging.info("************************INICIO SEPARACIÓN DE NOTICIAS************************")
    total_pages = len(news)
    size = 2
    json_news = []
    instructions_separate = '''
    Separa el texto en cada noticia.\n\n 
    La salida debe ser un arreglo JSON, donde cada noticia contenga un "Titular" y un "Contenido". \n\n
    NO repitas ninguna noticia.\n\n
    Texto: '''

    logging.info("************************PROCESANDO TEXTO BLOQUE POR BLOQUE************************")
    for i in range(0, total_pages, size):
        h = h + 1
        bloque = news[i:i + size]
        texto_bloque = '\n\n'.join([p for p in bloque])
        logging.info(f"************************COMIENZA LLAMADA A GEMMA PARA BLOQUE {h}************************")
        logging.info(f"************************CONSTRUCCIÓN DE PROMPT************************")    
        prompt_separate = construir_prompts_extraer(instructions_separate, texto_bloque)
        logging.info(f"************************INICIO EJECUCIÓN DE LA LLAMADA************************")  
        response = gemma_extraer_texo(prompt_separate)
        logging.info(f"************************TERMINA LLAMADA A GEMMA PARA BLOQUE {h}************************")
        start_index = response.find("[")
        end_index = response.rfind("]") + 1
        json_message = response[start_index:end_index]
        json_news.append(json_message)
        print(json_message)

    logging.info("************************SEPARACIÓN TEXTO BLOQUE POR BLOQUE FINALIZADO************************")
    return json_news

def formatear_json(strdate: str, json_news: List[str]) -> List[Dict[str, Any]]:
    logging.info("************************FORMATEO JSON INICIADO************************")
    fecha_str = strdate
    parsed_news = []

    for item in json_news:
        try:
            noticias = json.loads(item) 
            for noticia in noticias:
                if isinstance(noticia, dict):
                    noticia["fecha"] = fecha_str
                    if "contenido" in noticia and isinstance(noticia["contenido"], str):
                        noticia["contenido"] = noticia["contenido"].replace('"', '')
            parsed_news.extend(noticias)
        except json.JSONDecodeError as e:
            print("Error al decodificar este item, será omitido:\n", item)
            continue
    logging.info("************************FORMATEO JSON FINALIZADO************************")
    return parsed_news

def procesar_derechos(folder_name : str):
    
    pdf_files = leer_pdf(folder_name)
    text_extracted = extraer_texto_pdf(pdfs=pdf_files)
    fecha = extraer_fecha_pdf(text_extracted[0])
    news_separated = separar_noticias(text_extracted)
    json_output = formatear_json(fecha, news_separated)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"noticias.json-{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(json_output, file, ensure_ascii=False, indent=2)


procesar_derechos(DIRECTORIO_NOTICIAS)



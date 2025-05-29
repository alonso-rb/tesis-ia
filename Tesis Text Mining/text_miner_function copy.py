#Downloaded libraries: langchain and langchain-community
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
import ollama
from tika import parser
from bs4 import BeautifulSoup

DIRECTORIO_NOTICIAS = "newspaper"
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434
MODEL_NAME = "gemma3:12B"

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f'logs/app-{timestamp}.log'

logging.basicConfig(
    level=logging.DEBUG,  
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
    prompt = f"""{instructions}\n: 
    {text}"""
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

def gemma_extraer_texo(prompt: str, text: str) -> str:
    response = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            'role': 'user',
            'content': prompt
        }, {
            'role': 'user',
            'content': text
        }]
    )
    return response.message.content


def extraer_texto_pdf(pdfs: List[str]) -> List[str]:
    logging.info("************************INICIA EXTRACCIÓN TEXTO************************")
    structured_text = []

    parsed = parser.from_file(pdfs[0], xmlContent=True)
    xml = parsed['content']
    soup = BeautifulSoup(xml, 'lxml')
    pages = soup.find_all('div', {'class': 'page'})

    for i, page in enumerate(pages):
        text = page.get_text(separator='\n', strip=True)
        structured_text.append(text)

    logging.info("************************FINALIZA EXTRACCIÓN TEXTO************************")
    return structured_text

def limpiar_texto(texto: str) -> str:
    texto = re.sub(r'[-=~_*]{3,}', '', texto)  
    texto = re.sub(r'\n{2,}', '\n', texto)     
    texto = re.sub(r'[ \t]+', ' ', texto)   
    texto = re.sub(r'\n\s+', '\n', texto)    
    texto = texto.strip()
    texto = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9.,;:\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

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
        logging.debug(f"Fecha extraída:\n{strdate}")
        logging.info("************************FINALIZA EXTRACCIÓN FECHA************************")
        return strdate
    else:
        print("No se encontró ninguna fecha.")
        return ''

def separar_noticias(news : List[str]) -> List[str]:
    h=0
    logging.info("************************INICIO SEPARACIÓN DE NOTICIAS************************")
    total_pages = len(news)
    size = 3
    json_news = []
    instructions_separate = '''
Este es el texto de un conjunto de publicaciones periodísticas. 
Identifica todas las piezas informativas, ya sean noticias, artículos de análisis o reportajes.
Devuelve cada una en un arreglo JSON con esta estructura:

[
  {
    "titular": "Aquí va el titular completo",
    "contenido": "Aquí va el texto completo, respetando espacios y saltos de línea"
  }
]

TODO debe ir en español. NO omitas texto. NO agregues explicaciones. SOLO devuelve el JSON. No tengas prejuicios con reportajes objetivos sobre violencia.
Texto:
'''


    logging.info("************************PROCESANDO TEXTO BLOQUE POR BLOQUE************************")
    for i in range(0, total_pages, size):
        h = h + 1
        bloque = news[i:i + size]
        texto_bloque = '\n\n'.join([f'Página #{i+1}\n{p}' for i, p in enumerate(bloque)])
        texto_bloque_clean = limpiar_texto(texto_bloque)
        logging.info(f"************************COMIENZA LLAMADA A GEMMA PARA BLOQUE {h}************************")
        logging.info(f"************************CONSTRUCCIÓN DE PROMPT************************")    
        prompt_separate = construir_prompts_extraer(instructions_separate, texto_bloque_clean)
        logging.debug(f"Prompt enviado al modelo (bloque {h}):\n{prompt_separate}")
        logging.info(f"************************INICIO EJECUCIÓN DE LA LLAMADA************************")  
        response = gemma_extraer_texo(instructions_separate, texto_bloque_clean)
        logging.debug(f"Respuesta recibida por el modelo (bloque {h}):\n{response}")
        print(response)
        logging.info(f"************************TERMINA LLAMADA A GEMMA PARA BLOQUE {h}************************")
        start_index = response.find("[")
        end_index = response.rfind("]") + 1
        json_message = response[start_index:end_index]
        json_news.append(json_message)

    logging.info("************************SEPARACIÓN TEXTO BLOQUE POR BLOQUE FINALIZADO************************")
    return json_news

def formatear_json(strdate: str, json_news: List[str]) -> List[Dict[str, Any]]:
    logging.info("************************FORMATEO JSON INICIADO************************")
    fecha_str = strdate
    parsed_news = []
    ommited_items = []

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
            ommited_items.append(item)
            continue
    
    logging.debug(f"Noticias omitidas por no cumplir con el formato:\n{ommited_items}")
    logging.debug(f"Noticias en formato JSON completas:\n{parsed_news}")
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



from pdf2image import convert_from_path
import os
import ollama
import time
import psutil

pdf_path = "periodico.pdf"
poppler_path = r"C:\poppler-24.08.0\Library\bin" 


def get_total_pages(pdf_path, poppler_path):
    try:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path)
        total_pages = len(images) 
        return total_pages
    except Exception as e:
        print(f"Error al obtener el número de páginas: {e}")
        return 0

def convert_pdf_to_images(pdf_path, poppler_path, start_page, end_page):
    try:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_path, first_page=start_page, last_page=end_page)
        image_paths = []  
        for i, image in enumerate(images):
            image_path = f"page_{start_page + i}.jpg"
            image.save(image_path, "JPEG")
            image_paths.append(image_path)
        
        return image_paths
    except Exception as e:
        print(f"Error al convertir el PDF a imágenes: {e}")
        return []

def process_pdf_in_chunks(pdf_path, poppler_path, pages_per_chunk=4):
    total_pages = get_total_pages(pdf_path, poppler_path)  # Obtener el número total de páginas automáticamente
    if total_pages == 0:
        print("Error al obtener el número de páginas. Verifique el archivo PDF.")
        return
    
    for start_page in range(1, total_pages + 1, pages_per_chunk):
        end_page = min(start_page + pages_per_chunk - 1, total_pages)
        
        print(f"Procesando páginas {start_page} a {end_page}...")
        
        # Convertir las páginas actuales a imágenes
        image_paths = convert_pdf_to_images(pdf_path, poppler_path, start_page, end_page)
        
        # Si se generaron imágenes, procesarlas una por una con Ollama
        if image_paths:
            for image_path in image_paths:
                ai_response = run_ai_query(image_path)  # Pasar solo una imagen por vez a la IA
                # Después de procesar la imagen, eliminarla
                delete_images([image_path])  # Eliminar imagen individualmente
        else:
            print(f"No se generaron imágenes para las páginas {start_page} a {end_page}. Verifique el archivo PDF.")

        char = "["


# Modificación de la función `run_ai_query` para aceptar una sola imagen por mensaje
def run_ai_query(image_path):
    start_time = time.time()

    # Llamada a Ollama con la imagen
    response = ollama.chat(
        model='llama3.2-vision',
        messages=[{
            'role': 'user',
            'content': """Por favor, extrae todas las noticias contenidas en la imagen sin resumir, omitir ni alterar ningún detalle.
        
        El formato de salida debe ser un JSON con las siguientes claves para cada noticia:
        
        1. **Titular**: El título completo y exacto de la noticia, tal como aparece en la imagen.
        2. **Contenido**: El cuerpo completo de la noticia, sin omitir ni modificar ninguna palabra o estructura. Incluye subtítulos si los hay.
        
        La salida debe ser en formato JSON como sigue:
        
        [
            {
                "titular": "Titular completo de la noticia",
                "contenido": "Texto completo de la noticia tal como aparece en la imagen, con subtítulos si los hay."
            },
            ...
        ]
        
        No realices resúmenes ni simplificaciones. Mantén todos los detalles que aparecen en la imagen (nombres, fechas, lugares, etc.). No agregues ni elimines información. El formato de salida debe reflejar exactamente lo que aparece en la imagen.
        
        - Usa solo el texto que aparece en la imagen, sin cambios.
        - Si la noticia tiene subtítulos, inclúyelos dentro del contenido.
        - Asegúrate de que el texto del "titular" esté completo y coincida exactamente con lo que aparece en la imagen.
        """,
            'images': [image_path]  # Solo una imagen por mensaje
        }]
    )

    print(response)

    execution_time = time.time() - start_time
    print("\n--- AI Query Execution Done ---")
    print(f"Execution Time: {execution_time:.4f} seconds")
    return response

def get_gpu_info():
    try:
        import GPUtil
        
        gpus = GPUtil.getGPUs()
        return [{
            "gpu_name": gpu.name,
            "gpu_memory_used": gpu.memoryUsed,  
            "gpu_memory_total": gpu.memoryTotal,  
            "gpu_load": gpu.load * 100,  
            "gpu_temperature": gpu.temperature
        } for gpu in gpus]
    except Exception as e:
        print(f"Error al obtener información de la GPU: {e}")
        return None

def get_system_info():
    return {
        "cpu_usage": psutil.cpu_percent(interval=1),  
        "memory_used": psutil.virtual_memory().used / (1024 ** 3),  
        "memory_total": psutil.virtual_memory().total / (1024 ** 3)
    }

def monitor_system():
    system_info = get_system_info()
    gpu_info = get_gpu_info()

    print("Sistema")
    print(f"CPU Usage: {system_info['cpu_usage']}%")
    print(f"Memory Used: {system_info['memory_used']:.2f} GB / {system_info['memory_total']:.2f} GB")

    if gpu_info:
        for i, gpu in enumerate(gpu_info):
            print(f"\n--- GPU {i+1} ({gpu['gpu_name']}) ---")
            print(f"GPU Load: {gpu['gpu_load']:.2f}%")
            print(f"GPU Memory Used: {gpu['gpu_memory_used']} MB / {gpu['gpu_memory_total']} MB")
    else:
        print("\nNo GPU detected.")

monitor_system()



# Función para eliminar las imágenes procesadas
def delete_images(image_paths):
    for image_path in image_paths:
        try:
            os.remove(image_path)
            print(f"Imagen {image_path} eliminada exitosamente.")
        except Exception as e:
            print(f"Error al eliminar la imagen {image_path}: {e}")

# Llamada a la función para procesar el PDF
process_pdf_in_chunks(pdf_path, poppler_path)



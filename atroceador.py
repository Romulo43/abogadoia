import os
import json
import re
import fitz # pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

def leer_pdf(ruta_pdf):
    """Lee un PDF y saca texto + metadata"""
    try:
        doc = fitz.open(ruta_pdf)
        texto_completo = ""
        for page in doc:
            texto_completo += page.get_text()
        doc.close()
        return texto_completo
    except Exception as e:
        print(f"[ERROR LEYENDO] {ruta_pdf}: {e}")
        return ""

def sacar_articulo(texto_chunk):
    """Intenta adivinar el Articulo. Busca 'Art. 85' o 'Artículo 1'"""
    match = re.search(r'(Art\.|Artículo)\s*(\d+)', texto_chunk, re.IGNORECASE)
    if match:
        return f"Art {match.group(2)}"
    return "General"

def trocear_carpeta(carpeta_entrada, archivo_salida):
    """Procesa todos los PDFs de una carpeta"""
    
    # 1. Configurar el troceador: 800 tokens = ~500 palabras
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,      # tokens
        chunk_overlap=100,   # ~50 palabras de overlap para no perder contexto
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    todos_los_chunks = []
    chunk_id_global = 0
    
    print(f"[INICIANDO] Procesando carpeta: {carpeta_entrada}")
    
    for nombre_archivo in os.listdir(carpeta_entrada):
        if not nombre_archivo.lower().endswith('.pdf'):
            continue
            
        ruta_pdf = os.path.join(carpeta_entrada, nombre_archivo)
        print(f"\n[PROCESANDO] {nombre_archivo}")
        
        texto = leer_pdf(ruta_pdf)
        if not texto:
            continue
            
        # 2. Trocear
        chunks_texto = splitter.split_text(texto)
        print(f"  -> Generados {len(chunks_texto)} chunks")
        
        # 3. Guardar cada chunk con metadata
        for chunk in chunks_texto:
            todos_los_chunks.append({
                "chunk_id": chunk_id_global,
                "texto": chunk,
                "fuente": nombre_archivo,
                "articulo": sacar_articulo(chunk),
                "longitud_tokens": len(chunk) // 4 # estimacion rapida
            })
            chunk_id_global += 1
    
    # 4. Guardar todo en 1 JSONL para subir a Supabase
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        for chunk in todos_los_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
            
    print(f"\n[LISTO] Total: {len(todos_los_chunks)} chunks guardados en {archivo_salida}")

if __name__ == "__main__":
    print("=== TROCEADOR.PY - PARTE PDFs EN 500 PALABRAS ===")
    
    carpeta = input("Pega la carpeta con los PDFs: ")
    salida = input("Nombre del archivo de salida .jsonl: ")
    
    trocear_carpeta(carpeta, salida)
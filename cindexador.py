import os
import re
import uuid
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer
from PyPDF2 import PdfReader

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def limpiar_texto(texto):
    texto = re.sub(r'(\w+)-\n(\w+)', r'\1\2', texto) # Une palabras cortadas
    texto = re.sub(r'(?<!\n)\n(?!\n)', ' ', texto)
    texto = re.sub(r'^[ \t]+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r' +', ' ', texto)
    texto = re.sub(r'\n{2,}', '\n\n', texto)
    return texto.strip()

def extraer_articulo(texto):
    match = re.search(r'(Art\.?\s*(\d+)[°º]?)', texto, re.IGNORECASE)
    if match:
        return f"Art_{match.group(2)}"
    return f"Parrafo_{uuid.uuid4().hex[:6]}" # Si no hay art, le pone ID único

def cortar_en_chunks(texto, max_len=1200):
    chunks = []
    while len(texto) > max_len:
        corte = texto.rfind('. ', 0, max_len)
        if corte == -1: corte = texto.rfind(' ', 0, max_len)
        if corte == -1: corte = max_len
        chunks.append(texto[:corte+1].strip())
        texto = texto[corte+1:].strip()
    if texto: chunks.append(texto)
    return chunks

def procesar_pdf(ruta_pdf):
    reader = PdfReader(ruta_pdf)
    texto_completo = ""
    for pagina in reader.pages:
        txt = pagina.extract_text()
        if txt: texto_completo += txt + "\n"
    
    texto_limpio = limpiar_texto(texto_completo)
    articulos = re.split(r'(?=Art\.?\s*\d+[°º]?)', texto_limpio)
    
    datos = []
    nombre_pdf = os.path.basename(ruta_pdf)
    for i, art in enumerate(articulos):
        if len(art.strip()) < 50: continue
            
        base_art = extraer_articulo(art)
        
        if len(art) > 1200:
            partes = cortar_en_chunks(art)
            for j, parte in enumerate(partes):
                embedding = model.encode(parte).tolist()
                datos.append({
                    "id": f"{nombre_pdf}_{base_art}_p{j}_{uuid.uuid4().hex[:4]}", # ID 100% único
                    "contenido": parte,
                    "metadata": {"fuente": nombre_pdf, "articulo": base_art},
                    "embedding": embedding
                })
        else:
            embedding = model.encode(art).tolist()
            datos.append({
                "id": f"{nombre_pdf}_{base_art}_{uuid.uuid4().hex[:4]}", # ID 100% único
                "contenido": art,
                "metadata": {"fuente": nombre_pdf, "articulo": base_art},
                "embedding": embedding
            })
    return datos

print("Empezando a indexar...")
total_subidos = 0
for archivo in os.listdir("pdfs_nuevos"):
    if archivo.endswith(".pdf"):
        print(f"Procesando {archivo}...")
        datos = procesar_pdf(f"pdfs_nuevos/{archivo}")
        
        for j in range(0, len(datos), 100):
            lote = datos[j:j+100]
            supabase.table("documentos").upsert(lote).execute() # UPSERT = actualiza si existe
            
        total_subidos += len(datos)
        print(f"Subidos {len(datos)} fragmentos")

print(f"Listo! Total: {total_subidos} fragmentos indexados")
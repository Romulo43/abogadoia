import os
from dotenv import load_dotenv
from supabase import create_client
from sentence_transformers import SentenceTransformer

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Cargando modelo de IA...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Listo! Ya puedes preguntar.\n")

def buscar(pregunta, top_k=10):
    embedding_pregunta = model.encode(pregunta).tolist()

    respuesta = supabase.rpc("match_documents", {
        "query_embedding": embedding_pregunta,
        "match_count": top_k * 3
    }).execute()

    resultados = respuesta.data
    if not resultados:
        return "No encontré información sobre eso en los códigos y acordadas cargados."

    docs_unicos = {}
    for doc in resultados:
        texto = doc.get('contenido') or doc.get('content') or ""
        meta = doc.get('metadata', {})
        fuente = meta.get('fuente', 'Desconocido')
        
        if not texto:
            continue

        llave = f"{fuente}_{texto[:100]}"

        if llave not in docs_unicos or doc['similarity'] > docs_unicos[llave]['similarity']:
            docs_unicos[llave] = doc
            docs_unicos[llave]['texto_limpio'] = texto

    resultados_finales = sorted(docs_unicos.values(), key=lambda x: x['similarity'], reverse=True)[:5]

    respuesta_texto = f"Encontré esto sobre: '{pregunta}'\n\n"
    for i, doc in enumerate(resultados_finales, 1):
        meta = doc.get('metadata', {})
        fuente = meta.get('fuente', 'Ley')
        pagina = meta.get('pagina', '?')
        sim = round(doc['similarity'] * 100, 1)
        texto = doc['texto_limpio']

        respuesta_texto += f"**{i}. {fuente} - Pág {pagina}** | Relevancia: {sim}%\n"
        respuesta_texto += f"{texto[:500]}...\n\n"

    return respuesta_texto


def main():
    print("="*50)
    print(" 🤖 IA ABOGADO - CODIGO CIVIL, PROCESAL Y ACORDADAS")
    print("="*50)
    print("Escribe tu pregunta legal. Escribe 'salir' para terminar.\n")

    while True:
        pregunta = input("Que ley quieres buscar? > ")

        if pregunta.lower() in ['salir', 'exit', 'q']:
            print("\nHasta luego! 👋")
            break

        if pregunta.strip() == "":
            continue

        print("\nBuscando...\n")
        respuesta = buscar(pregunta)
        print(respuesta)
        print("-"*50 + "\n")


if __name__ == "__main__": # <-- ESTA LINEA ES LA QUE FALTABA
    main()
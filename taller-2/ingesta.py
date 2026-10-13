# Ingesta: lee los documentos, los divide en chunks, calcula sus embeddings y los
# guarda en una base Chroma persistente. Se ejecuta una vez (o cuando cambian los
# documentos); la consulta después solo abre el índice ya construido.
#
# Uso:  python ingesta.py --modelo bge-m3
import argparse
import time
from pathlib import Path

from langchain_chroma import Chroma

from cargadores import cargar_base
from embeddings import MODELOS, EmbeddingsLocal

RUTA_INDICE = str(Path(__file__).parent / "chroma_db")


def abrir_indice(clave, embeddings=None, nombre=None):
    """Abre (o crea) la colección de Chroma. La métrica es coseno."""
    return Chroma(
        collection_name=nombre or f"ecomarket_{clave}",
        embedding_function=embeddings or EmbeddingsLocal(clave),
        persist_directory=RUTA_INDICE,
        collection_metadata={"hnsw:space": "cosine"},
    )


def construir_indice(clave, chunks, embeddings=None, nombre=None):
    """Borra la colección si existía y la reconstruye con los chunks dados."""
    vs = abrir_indice(clave, embeddings, nombre)
    vs.delete_collection()
    vs = abrir_indice(clave, vs._embedding_function, nombre)
    vs.add_documents(chunks)
    return vs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", choices=MODELOS, default="bge-m3")
    clave = ap.parse_args().modelo

    chunks = cargar_base()
    print(f"{len(chunks)} chunks de {len({c.metadata['fuente'] for c in chunks})} documentos")
    t = time.time()
    construir_indice(clave, chunks)
    print(f"Índice 'ecomarket_{clave}' guardado en {RUTA_INDICE} ({time.time() - t:.1f} s)")

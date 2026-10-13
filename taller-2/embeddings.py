# Modelos de embeddings candidatos. Todos son open source (Hugging Face), multilingües
# y corren en CPU. Se cargan con sentence-transformers.
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

# clave -> (nombre en Hugging Face, prefijo de consulta, prefijo de documento)
# Los modelos E5 fueron entrenados con los prefijos "query: " y "passage: ";
# sin ellos pierden calidad. Los otros dos no usan prefijos.
MODELOS = {
    "minilm": ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", ""),
    "e5-small": ("intfloat/multilingual-e5-small", "query: ", "passage: "),
    "e5-base": ("intfloat/multilingual-e5-base", "query: ", "passage: "),
    "bge-m3": ("BAAI/bge-m3", "", ""),
}


class EmbeddingsLocal(Embeddings):
    """Convierte texto en vectores normalizados (norma 1), de modo que la
    similitud coseno es el producto punto."""

    def __init__(self, clave: str):
        nombre, self.prefijo_consulta, self.prefijo_doc = MODELOS[clave]
        self.modelo = SentenceTransformer(nombre)
        # bge-m3 admite 8192 tokens; con 512 sobra para nuestros fragmentos y es más rápido.
        self.modelo.max_seq_length = min(self.modelo.max_seq_length or 512, 512)

    def embed_documents(self, textos):
        textos = [self.prefijo_doc + t for t in textos]
        return self.modelo.encode(textos, normalize_embeddings=True, batch_size=16).tolist()

    def embed_query(self, texto):
        return self.modelo.encode(self.prefijo_consulta + texto, normalize_embeddings=True).tolist()

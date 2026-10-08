# Línea base del Taller 2: el mismo flujo de rag_ejemplo.py, actualizado a LangChain 1.x.
# Cambios frente al ejemplo del profesor:
#   - Embeddings de Hugging Face (multilingües, locales) en vez de llama2 vía Ollama.
#   - LLM de Groq (el del Taller 1) en vez de Ollama.
#   - Cadena con operadores | (LCEL) y prompt propio, en vez de RetrievalQA.
# Sigue usando un solo documento; los demás se agregan en las fases siguientes.
import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

DOCUMENTO_ECO_MARKET = """
Política de Devoluciones de EcoMarket:

Nuestra política de devoluciones permite a los clientes devolver productos dentro de los 30 días posteriores a la fecha de compra. Para ser elegible para una devolución, el artículo debe estar sin usar, en su embalaje original y en las mismas condiciones en que lo recibió. Los productos perecederos, como alimentos y flores, no son elegibles para devolución. Las devoluciones de ropa de segunda mano también están sujetas a una revisión estricta para garantizar que el artículo no haya sido usado después de la compra. Para iniciar una devolución, visite nuestra sección de ayuda en el sitio web y siga los pasos.
"""

# 1. Chunking
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = splitter.create_documents([DOCUMENTO_ECO_MARKET])

# 2. Embeddings: texto -> vector
embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")

# 3. Base vectorial (en memoria, igual que el ejemplo original)
vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# 4. LLM: Groq expone una API compatible con OpenAI
llm = ChatOpenAI(
    model="openai/gpt-oss-120b",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY", ""),
    temperature=0.3,
)

# 5. Prompt: el contexto recuperado entra como texto delimitado
prompt = ChatPromptTemplate.from_template(
    """Eres un agente de servicio al cliente de EcoMarket.
Responde SOLO con la información del CONTEXTO. Si el contexto no alcanza para
responder, dilo y ofrece comunicar al cliente con un agente humano.

--- CONTEXTO ---
{contexto}
--- FIN DEL CONTEXTO ---

Pregunta del cliente: {pregunta}"""
)


def formatear(documentos):
    return "\n\n".join(d.page_content for d in documentos)


# 6. Cadena: pregunta -> retrieval -> prompt -> LLM -> texto
chain = (
    {"contexto": retriever | formatear, "pregunta": lambda x: x}
    | prompt
    | llm
    | StrOutputParser()
)

if __name__ == "__main__":
    print("Sistema RAG base de EcoMarket. Escribe 'salir' para terminar.")
    while True:
        pregunta = input("\nTu pregunta: ")
        if pregunta.lower() == "salir":
            break
        for d in retriever.invoke(pregunta):
            print(f"[chunk recuperado] {d.page_content[:80]}...")
        print("\n" + chain.invoke(pregunta))

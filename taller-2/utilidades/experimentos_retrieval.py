# Experimentos de retrieval (sin LLM): miden si los fragmentos recuperados contienen
# lo necesario para responder cada pregunta del set de evaluación.
#
# Uso (desde taller-2/):
#   python utilidades/experimentos_retrieval.py embeddings
#   python utilidades/experimentos_retrieval.py chunking --modelos bge-m3 e5-base
import argparse
import json
import statistics as st
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cargadores import cargar_base, cargar_recursivo, cargar_tamano_fijo
from embeddings import MODELOS, EmbeddingsLocal
from ingesta import construir_indice

RAIZ = Path(__file__).resolve().parent.parent
PREGUNTAS = json.loads((RAIZ / "evaluacion" / "preguntas_evaluacion.json").read_text(encoding="utf-8"))["preguntas"]
SALIDA = RAIZ / "evaluacion" / "resultados"
SALIDA.mkdir(exist_ok=True)
KS = (1, 3, 5)


def buscar(vs, pregunta, k, solo_publico=True):
    """Devuelve [(Document, similitud coseno)] ordenado de mayor a menor."""
    filtro = {"audiencia": "publico"} if solo_publico else None
    res = vs.similarity_search_with_score(pregunta, k=k, filter=filtro)
    return [(d, 1 - dist) for d, dist in res]


def evaluar(vs):
    """Calcula las métricas de retrieval de un índice sobre las 31 preguntas."""
    con_evidencia = [q for q in PREGUNTAS if q.get("evidencia")]
    out = {"n_preguntas_con_evidencia": len(con_evidencia)}

    # 1. Evidencia@k: fracción del texto necesario que aparece en los k fragmentos recuperados.
    #    Fuente@k: algún fragmento viene de un documento correcto. MRR: posición del primero correcto.
    for k in KS:
        ev, fu = [], []
        for q in con_evidencia:
            texto = "\n".join(d.page_content for d, _ in buscar(vs, q["pregunta"], k)).lower()
            ev.append(sum(e.lower() in texto for e in q["evidencia"]) / len(q["evidencia"]))
            fu.append(any(d.metadata["fuente"] in q["fuentes_esperadas"] for d, _ in buscar(vs, q["pregunta"], k)))
        out[f"evidencia@{k}"] = round(st.mean(ev), 3)
        out[f"fuente@{k}"] = round(st.mean(fu), 3)
        out[f"preguntas_completas@{k}"] = sum(x == 1 for x in ev)  # con TODA la evidencia
    rr = []
    for q in con_evidencia:
        rank = next((i for i, (d, _) in enumerate(buscar(vs, q["pregunta"], 10), 1)
                     if d.metadata["fuente"] in q["fuentes_esperadas"]), None)
        rr.append(1 / rank if rank else 0)
    out["MRR"] = round(st.mean(rr), 3)

    # 2. Separación entre preguntas con respuesta y sin respuesta (para decidir un umbral de "no sé").
    sin_info = [q for q in PREGUNTAS if q["tipo"] == "sin_respuesta" and not q["fuentes_esperadas"]]
    top1_con = [buscar(vs, q["pregunta"], 1)[0][1] for q in con_evidencia]
    top1_sin = [buscar(vs, q["pregunta"], 1)[0][1] for q in sin_info]
    out["sim_top1_con_respuesta"] = {"min": round(min(top1_con), 3), "media": round(st.mean(top1_con), 3)}
    out["sim_top1_sin_respuesta"] = {"max": round(max(top1_sin), 3), "media": round(st.mean(top1_sin), 3),
                                     "preguntas": [q["id"] for q in sin_info]}
    out["margen_umbral"] = round(min(top1_con) - max(top1_sin), 3)  # > 0: un umbral separa perfecto

    # 3. Fuga del documento interno si NO se filtra por audiencia.
    conf = [q for q in PREGUNTAS if q.get("fuente_prohibida")]
    sin_filtro = [buscar(vs, q["pregunta"], 3, solo_publico=False) for q in conf]
    out["fuga_sin_filtro_top3"] = sum(any(d.metadata["audiencia"] == "interno" for d, _ in r) for r in sin_filtro)
    out["fuga_sin_filtro_top1"] = sum(r[0][0].metadata["audiencia"] == "interno" for r in sin_filtro)
    out["preguntas_confidenciales"] = len(conf)

    # 4. Latencia de una consulta (embedding de la pregunta + búsqueda).
    t = time.time()
    for q in PREGUNTAS:
        buscar(vs, q["pregunta"], 3)
    out["ms_por_consulta"] = round((time.time() - t) / len(PREGUNTAS) * 1000)
    return out


def exp_embeddings(args):
    resultados = {}
    chunks = cargar_base()
    for clave in args.modelos:
        t = time.time()
        emb = EmbeddingsLocal(clave)
        carga = time.time() - t
        t = time.time()
        vs = construir_indice(clave, chunks, emb)
        indexado = time.time() - t
        r = evaluar(vs)
        r.update({
            "modelo": MODELOS[clave][0],
            "dimension": len(emb.embed_query("hola")),
            "parametros_M": round(sum(p.numel() for p in emb.modelo.parameters()) / 1e6),
            "max_tokens": emb.modelo.max_seq_length,
            "seg_carga_modelo": round(carga, 1),
            "seg_indexar_%d_chunks" % len(chunks): round(indexado, 1),
        })
        resultados[clave] = r
        print(f"\n== {clave} ==")
        print(json.dumps(r, ensure_ascii=False, indent=1))
    (SALIDA / "embeddings.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")


def exp_chunking(args):
    estrategias = {
        "A tamaño fijo (200 palabras, solape 50)": cargar_tamano_fijo,
        "B recursivo (1000 caracteres, solape 200)": cargar_recursivo,
        "C por estructura, sin encabezado": lambda: cargar_base(con_encabezado=False),
        "D por estructura, con encabezado": lambda: cargar_base(con_encabezado=True),
    }
    resultados = {}
    for clave in args.modelos:
        emb = EmbeddingsLocal(clave)
        for nombre, fn in estrategias.items():
            chunks = fn()
            vs = construir_indice(clave, chunks, emb, nombre=f"exp_{clave}_{nombre[0]}")
            r = evaluar(vs)
            r["n_chunks"] = len(chunks)
            resultados[f"{clave} | {nombre}"] = r
            print(f"\n== {clave} | {nombre} | {len(chunks)} chunks ==")
            print({k: r[k] for k in ("evidencia@1", "evidencia@3", "evidencia@5", "preguntas_completas@3", "fuente@3", "MRR",
                                      "margen_umbral", "fuga_sin_filtro_top3")})
    (SALIDA / "chunking.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("experimento", choices=["embeddings", "chunking"])
    ap.add_argument("--modelos", nargs="+", choices=MODELOS, default=list(MODELOS))
    a = ap.parse_args()
    {"embeddings": exp_embeddings, "chunking": exp_chunking}[a.experimento](a)

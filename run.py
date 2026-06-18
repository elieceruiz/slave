# run.py

from time import perf_counter

from gmail_reader import obtener_correos
from parser import parsear_correos
from db import insertar_documentos, crear_indice


class PipelineStageError(Exception):
    def __init__(self, stage, original_error):
        self.stage = stage
        self.original_error = original_error
        super().__init__(str(original_error))


def _duracion(inicio):
    return f"{perf_counter() - inicio:.2f}s"


# ==========================================================
# NUEVA FUNCIÓN (ENVOLTORIO)
# ==========================================================
def ejecutar_pipeline():
    main()


# ==========================================================
# TU LÓGICA ORIGINAL (INTACTA)
# ==========================================================
def main():

    inicio_total = perf_counter()

    print("[RUN] inicio")
    print("\n==============================")
    print("INICIANDO PIPELINE SLAVE")
    print("==============================\n")

    # ----------------------------
    # 1. Índice (seguro)
    # ----------------------------
    print("Verificando indice...")

    inicio = perf_counter()
    try:
        crear_indice()
        print(f"[RUN] crear_indice OK en {_duracion(inicio)}")
    except Exception as e:
        print(
            f"[RUN] crear_indice ERROR en {_duracion(inicio)} "
            f"| {e} | continuando=True"
        )

    # ----------------------------
    # 2. OBTENER CORREOS (🔥 NUEVO)
    # ----------------------------
    print("\nObteniendo correos...")
    print("[RUN] obtener_correos inicio")

    inicio = perf_counter()
    try:
        correos = obtener_correos()
        print(
            f"[RUN] obtener_correos OK en {_duracion(inicio)} "
            f"| correos={len(correos)}"
        )
    except Exception as e:
        print(f"[RUN] obtener_correos ERROR en {_duracion(inicio)} | {e}")
        raise PipelineStageError("obtener_correos", e) from e

    # ----------------------------
    # 3. Parser
    # ----------------------------
    print("\nParseando correos...")

    inicio = perf_counter()
    try:
        datos = parsear_correos(correos)
        print(
            f"[RUN] parsear_correos OK en {_duracion(inicio)} "
            f"| docs={len(datos)}"
        )
    except Exception as e:
        print(f"[RUN] parsear_correos ERROR en {_duracion(inicio)} | {e}")
        raise PipelineStageError("parsear_correos", e) from e

    print(f"Documentos generados: {len(datos)}")

    if not datos:
        print("No hay datos para insertar")
        print(f"[RUN] insertar_documentos omitido | docs=0")
        print(f"[RUN] completo en {_duracion(inicio_total)}")
        return

    # ----------------------------
    # 4. Mongo
    # ----------------------------
    print("\nInsertando en Mongo...")

    inicio = perf_counter()
    try:
        insertar_documentos(datos)
        print(f"[RUN] insertar_documentos OK en {_duracion(inicio)}")
    except Exception as e:
        print(f"[RUN] insertar_documentos ERROR en {_duracion(inicio)} | {e}")
        raise PipelineStageError("insertar_documentos", e) from e

    print(f"[RUN] completo en {_duracion(inicio_total)}")
    print("\n==============================")
    print("PIPELINE COMPLETO")
    print("==============================\n")


if __name__ == "__main__":
    main()

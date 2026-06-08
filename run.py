# run.py

from gmail_reader import correos_procesados
from parser import parsear_correos
from db import insertar_documentos, crear_indice


def main():

    print("\n==============================")
    print("🚀 INICIANDO PIPELINE SLAVE")
    print("==============================\n")

    # ----------------------------
    # 1. Índice (seguro)
    # ----------------------------
    print("🔧 Verificando índice...")

    try:
        crear_indice()
    except Exception as e:
        print(f"⚠️ Índice: {e} (continuando...)")

    # ----------------------------
    # 2. Parser
    # ----------------------------
    print("\n📥 Parseando correos...")

    datos = parsear_correos(correos_procesados)

    print(f"✓ Documentos generados: {len(datos)}")

    if not datos:
        print("⚠️ No hay datos para insertar")
        return

    # ----------------------------
    # 3. Mongo
    # ----------------------------
    print("\n💾 Insertando en Mongo...")

    insertar_documentos(datos)

    print("\n==============================")
    print("✅ PIPELINE COMPLETO")
    print("==============================\n")


if __name__ == "__main__":
    main()
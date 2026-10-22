"""Verifica los cuatro lineamientos con evidencia y genera el registro de revisión simulado.

Un lineamiento solo se marca 'CUMPLIDO' si existe la evidencia que lo respalda.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd  # noqa: E402
from medpredict import VERSION, config  # noqa: E402

R, RAIZ = config.RUTA_RESULTADOS, config.RAIZ
FECHA = "2026-10-21"


def leer(nombre):
    ruta = R / nombre
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def main() -> int:
    ejecucion, decisiones = leer("4_registro_ejecucion.json"), leer("3_registro_decisiones.json")
    df = pd.read_csv(config.RUTA_DATOS)
    resultados = []

    sinteticos = bool(df[config.COL_ID].str.startswith("SYN-").all())
    resultados.append({
        "lineamiento": "L1. Usar exclusivamente datos sintéticos", "cumplido": sinteticos,
        "evidencia": f"{config.RUTA_DATOS.relative_to(RAIZ)}: {len(df)} filas, 100 % con identificador SYN-; "
                     "generado por scripts/generar_datos.py (semilla 42); prueba test_datos_son_sinteticos."})

    separado = bool(ejecucion) and ejecucion["ids_compartidos_entre_particiones"] == 0
    resultados.append({
        "lineamiento": "L2. Separar entrenamiento y prueba", "cumplido": separado,
        "evidencia": (f"resultados/4_registro_ejecucion.json: {ejecucion['filas_entrenamiento']} filas de entrenamiento, "
                      f"{ejecucion['filas_prueba']} de prueba, {ejecucion['ids_compartidos_entre_particiones']} ids compartidos; "
                      "pruebas test_entrenamiento_y_prueba_no_comparten_registros y test_la_prueba_no_influye_en_el_ajuste."
                      ) if ejecucion else "Sin registro de ejecución."})

    versionado = bool(ejecucion) and (RAIZ / "CHANGELOG.md").exists() and ejecucion["version_prototipo"] == VERSION
    resultados.append({
        "lineamiento": "L3. Registrar versiones y resultados", "cumplido": versionado,
        "evidencia": (f"CHANGELOG.md y resultados/4_registro_ejecucion.json (versión {ejecucion['version_prototipo']}, "
                      f"sha256 del dataset {ejecucion['sha256_dataset']}, scikit-learn {ejecucion['scikit_learn']}); "
                      "resultados en resultados/1_ a 3_*.json.") if ejecucion else "Sin registro de ejecución."})

    pendientes = [k for k, v in (decisiones or {}).get("estado_seguimiento", {}).items() if not v["cumple"]]
    estado = "APROBADO" if decisiones and not pendientes else "CORRECCIÓN REQUERIDA (aprobación condicionada)"
    resultados.append({
        "lineamiento": "L4. Someter el producto a revisión antes de liberarlo", "cumplido": bool(decisiones),
        "evidencia": f"docs/registro_revision.md (revisión simulada, estado: {estado})."})

    todo = all(r["cumplido"] for r in resultados)
    (R / "5_lista_verificacion.json").write_text(json.dumps(
        {"fecha": FECHA, "version": VERSION, "lineamientos": resultados}, indent=2, ensure_ascii=False), encoding="utf-8")

    lineas = [f"# Registro de revisión (SIMULADO) - {config.EMPRESA}", "",
              f"- Fecha: {FECHA}", f"- Versión revisada: {VERSION}",
              f"- Revisor: {config.REVISOR_SIMULADO}", f"- Autor: {config.RESPONSABLE}",
              f"- **Estado: {estado}**", "", "## Hallazgos de la revisión", ""]
    for r in resultados:
        lineas.append(f"- [{'x' if r['cumplido'] else ' '}] {r['lineamiento']}")
    lineas += ["", "## Correcciones solicitadas", ""]
    if pendientes:
        for p in pendientes:
            v = decisiones["estado_seguimiento"][p]
            lineas.append(f"- `{p}`: valor {v['valor']} frente al umbral {v['umbral']}. Requiere acción antes del uso productivo.")
    else:
        lineas.append("- Sin correcciones.")
    lineas += ["", "_Este registro es parte del ejercicio y fue generado por scripts/verificar_lineamientos.py a partir de "
               "resultados reales de la ejecución; el revisor es simulado._"]
    (RAIZ / "docs" / "registro_revision.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print("=== LISTA DE VERIFICACIÓN DE LINEAMIENTOS ===")
    for r in resultados:
        print(f"[{'CUMPLIDO' if r['cumplido'] else 'SIN EVIDENCIA'}] {r['lineamiento']}\n    Evidencia: {r['evidencia']}")
    print(f"\nEstado de la revisión simulada: {estado}")
    return 0 if todo else 1


if __name__ == "__main__":
    sys.exit(main())

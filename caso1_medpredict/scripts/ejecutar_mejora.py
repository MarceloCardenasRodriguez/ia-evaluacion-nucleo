"""Ejecuta el flujo de mejora completo y escribe la evidencia en resultados/."""
import hashlib
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import sklearn  # noqa: E402
from medpredict import VERSION, config, mejora  # noqa: E402

R = config.RUTA_RESULTADOS
COLUMNAS = ["n", "positivos", "recall", "precision", "f1", "exactitud_balanceada", "auc"]


def tabla(titulo, metricas):
    print(f"\n{titulo}")
    print(f"{'grupo':<10}" + "".join(f"{c:>22}" for c in COLUMNAS))
    for g in ("global",) + config.GRUPOS:
        print(f"{g:<10}" + "".join(f"{metricas[g][c]:>22}" for c in COLUMNAS))
    print(f"brecha de recall entre grupos: {metricas['brecha_recall']} | umbral de decisión: {metricas['umbral_decision']}")


def main():
    df = mejora.cargar_datos()
    entrenamiento, prueba = mejora.separar(df)
    print(f"Entrenamiento: {len(entrenamiento)} filas | Prueba (aislada): {len(prueba)} filas")

    # 1) Diagnóstico inicial (modelo base, métricas por grupo)
    diag = mejora.diagnostico_datos(entrenamiento)
    base = mejora.entrenar_base(entrenamiento)
    m_base = mejora.evaluar_por_grupo(base, prueba)
    mejora.guardar_json({"datos_entrenamiento": diag, "metricas_prueba_modelo_base": m_base},
                        R / "1_diagnostico_inicial.json")
    print("\n== 1. DIAGNÓSTICO INICIAL ==")
    for g in config.GRUPOS:
        d = diag[g]
        print(f"Grupo {g}: n={d['n']} positivos={d['positivos']} prevalencia={d['prevalencia']} "
              f"faltantes(pcr)={d['faltantes_por_variable']['pcr_mg_l']} "
              f"faltantes(opacidad)={d['faltantes_por_variable']['indice_opacidad_imagen']}")
    tabla("Modelo base (media, sin ponderación, umbral 0,5) sobre PRUEBA:", m_base)

    # 2) Intervención: ajuste solo con entrenamiento
    mejorado = mejora.entrenar_mejorado(entrenamiento)
    m_mej = mejora.evaluar_por_grupo(mejorado, prueba)
    print("\n== 2. INTERVENCIÓN (imputación + indicadores de faltante, ponderación grupo x clase, "
          "umbral por validación cruzada en entrenamiento) ==")
    tabla("Modelo mejorado sobre PRUEBA:", m_mej)

    # 3) Comparación antes/después
    comparacion = {"antes": m_base, "despues": m_mej, "delta": {}}
    print("\n== 3. COMPARACIÓN ANTES -> DESPUÉS (prueba) ==")
    print(f"{'grupo':<8}{'métrica':<22}{'antes':>10}{'después':>10}{'delta':>10}")
    for g in ("global",) + config.GRUPOS:
        comparacion["delta"][g] = {}
        for c in ("recall", "precision", "f1", "exactitud_balanceada", "auc"):
            d = round(m_mej[g][c] - m_base[g][c], 4)
            comparacion["delta"][g][c] = d
            print(f"{g:<8}{c:<22}{m_base[g][c]:>10}{m_mej[g][c]:>10}{d:>+10.4f}")
    comparacion["delta"]["brecha_recall"] = round(m_mej["brecha_recall"] - m_base["brecha_recall"], 4)
    mejora.guardar_json(comparacion, R / "2_comparacion_metricas.json")

    # 4) Seguimiento
    seguimiento = mejora.evaluar_seguimiento(m_mej, diag)
    print("\n== 4. UMBRALES DE SEGUIMIENTO (modelo mejorado) ==")
    for regla, v in seguimiento.items():
        print(f"{'CUMPLE ' if v['cumple'] else 'NO CUMPLE'}  {regla}: valor={v['valor']} umbral={v['umbral']}")
    requiere_revision = not all(v["cumple"] for v in seguimiento.values())
    print("Estado:", "REQUIERE NUEVA REVISIÓN" if requiere_revision else "dentro de los umbrales")

    decisiones = {
        "version": VERSION,
        "decisiones": [
            {"id": "D1", "decision": "Separar prueba (25 %) estratificada por grupo y clase antes de cualquier ajuste.",
             "motivo": "Evitar contaminación: la prueba solo mide."},
            {"id": "D2", "decision": "Imputar con mediana y agregar indicadores de dato faltante, ajustados solo con entrenamiento.",
             "motivo": "El centro B tiene hasta 38 % de faltantes en PCR; la ausencia es informativa."},
            {"id": "D3", "decision": "Ponderar cada celda grupo x clase de forma inversa a su frecuencia.",
             "motivo": "Clase positiva rara y centro B con pocos datos."},
            {"id": "D4", "decision": "Agregar indicador de centro e interacciones centro x variable.",
             "motivo": "El equipo de imagen del centro B tiene otra calibración."},
            {"id": "D5", "decision": f"Umbral de decisión {m_mej['umbral_decision']} elegido por validación cruzada (F2) en entrenamiento.",
             "motivo": "En tamizaje es más costoso omitir un enfermo que generar una falsa alarma."},
        ],
        "limites": [
            "Datos sintéticos: los resultados no son evidencia clínica.",
            f"Pocos casos positivos del centro B en prueba ({m_mej[config.GRUPO_MINORITARIO]['positivos']}): intervalos de confianza amplios.",
            "El modelo usa el centro como variable; debe revisarse que no introduzca otra forma de sesgo.",
            "Una sola partición de prueba; no se evaluó deriva temporal.",
        ],
        "umbrales_seguimiento": {
            "recall_minimo_por_grupo": config.UMBRAL_RECALL_MINIMO_GRUPO,
            "brecha_maxima_recall": config.UMBRAL_BRECHA_RECALL,
            "precision_minima_por_grupo": config.UMBRAL_PRECISION_MINIMA_GRUPO,
            "faltantes_maximos": config.UMBRAL_FALTANTES,
            "accion": "Si alguna regla no se cumple, se convoca una nueva revisión antes de usar el modelo.",
        },
        "estado_seguimiento": seguimiento,
        "requiere_nueva_revision": requiere_revision,
    }
    mejora.guardar_json(decisiones, R / "3_registro_decisiones.json")

    huella = hashlib.sha256(config.RUTA_DATOS.read_bytes()).hexdigest()[:16]
    mejora.guardar_json({
        "version_prototipo": VERSION,
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "semilla": config.SEMILLA,
        "python": platform.python_version(), "scikit_learn": sklearn.__version__, "numpy": np.__version__,
        "sha256_dataset": huella,
        "filas_entrenamiento": len(entrenamiento), "filas_prueba": len(prueba),
        "huella_ids_entrenamiento": mejora.hash_ids(entrenamiento), "huella_ids_prueba": mejora.hash_ids(prueba),
        "ids_compartidos_entre_particiones": len(set(entrenamiento[config.COL_ID]) & set(prueba[config.COL_ID])),
        "metricas_resumen": {"antes": m_base["global"], "despues": m_mej["global"]},
    }, R / "4_registro_ejecucion.json")
    print("\nEvidencia escrita en", R)


if __name__ == "__main__":
    main()

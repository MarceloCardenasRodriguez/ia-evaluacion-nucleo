"""Genera los registros de coordinación SIMULADOS (acta, comunicación y seguimiento).

Responsables y comunicación son simulados; las pruebas y métricas informadas son REALES:
el script ejecuta pytest y lee los resultados guardados en resultados/.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from medpredict import VERSION, config  # noqa: E402

R, RAIZ = config.RUTA_RESULTADOS, config.RAIZ
D = RAIZ / "docs"
FECHA_ACTA, F_ENTREGA, F_PRUEBAS, F_INFORME, F_CIERRE = "21-10-2026", "21-10-2026", "21-10-2026", "21-10-2026", "30-10-2026"


def main() -> int:
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider"],
                          cwd=RAIZ, capture_output=True, text=True)
    resumen = (proc.stdout.strip().splitlines() or ["sin salida"])[-1]
    (R / "6_resultado_pruebas.txt").write_text(proc.stdout, encoding="utf-8")
    pruebas_ok = proc.returncode == 0

    comp = json.loads((R / "2_comparacion_metricas.json").read_text(encoding="utf-8"))
    dec = json.loads((R / "3_registro_decisiones.json").read_text(encoding="utf-8"))
    ant, des = comp["antes"], comp["despues"]
    a, b = config.GRUPOS
    pend = {k: v for k, v in dec["estado_seguimiento"].items() if not v["cumple"]}
    huella = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(Path(config.__file__).parent.glob("*.py")))).hexdigest()[:12]

    acta = f"""# Acta de compromisos (SIMULADA) - {config.EMPRESA}

Fecha: {FECHA_ACTA} | Versión del prototipo: {VERSION}
Participantes: {config.RESPONSABLE}; {config.REVISOR_SIMULADO}; {config.DOCENTE_SIMULADO}.

| N.º | Compromiso | Responsable | Plazo | Evidencia esperada |
|---|---|---|---|---|
| C1 | Entregar el prototipo | {config.RESPONSABLE} | {F_ENTREGA} | Repositorio con código, datos sintéticos y README |
| C2 | Ejecutar las pruebas del prototipo | {config.RESPONSABLE} | {F_PRUEBAS} | resultados/6_resultado_pruebas.txt |
| C3 | Informar los resultados | {config.RESPONSABLE} | {F_INFORME} | docs/comunicacion_resultados.md |
| C4 | Cerrar las correcciones acordadas en la revisión | {config.RESPONSABLE} con {config.REVISOR_SIMULADO} | {F_CIERRE} | docs/seguimiento_cierre.md |

Firmas (simuladas): {config.RESPONSABLE} | {config.REVISOR_SIMULADO} | {config.DOCENTE_SIMULADO}
"""
    (D / "acta_compromisos.md").write_text(acta, encoding="utf-8")

    comunicacion = f"""# Comunicación de resultados (SIMULADA) - {F_INFORME}

De: {config.RESPONSABLE}
Para: {config.REVISOR_SIMULADO}; {config.DOCENTE_SIMULADO}
Asunto: Resultados del prototipo v{VERSION} ({config.EMPRESA})

Estimados:

Informo los resultados reales de la ejecución del prototipo con datos sintéticos.

**Pruebas automáticas:** {resumen}.

**Modelo (conjunto de prueba, recall antes -> después):** global {ant['global']['recall']} -> {des['global']['recall']}; \
grupo {a} {ant[a]['recall']} -> {des[a]['recall']}; grupo {b} {ant[b]['recall']} -> {des[b]['recall']}. \
Brecha de recall entre grupos: {ant['brecha_recall']} -> {des['brecha_recall']}.

**Costo de la mejora:** la precisión global baja de {ant['global']['precision']} a {des['global']['precision']} \
(más falsas alarmas), efecto esperado al priorizar la detección.

**Pendientes para la revisión:** {', '.join(f'{k} (valor {v["valor"]}, umbral {v["umbral"]})' for k, v in pend.items()) or 'ninguno'}.

Saludos,
{config.RESPONSABLE}
"""
    (D / "comunicacion_resultados.md").write_text(comunicacion, encoding="utf-8")

    cierre = [f"# Seguimiento del cierre (SIMULADO) - corte {F_INFORME}", "",
              "| Compromiso | Estado | Evidencia real |", "|---|---|---|",
              f"| C1 Entregar prototipo | {'CUMPLIDO' if True else ''} | Huella del código fuente: {huella}; versión {VERSION} |",
              f"| C2 Ejecutar pruebas | {'CUMPLIDO' if pruebas_ok else 'CON FALLAS'} | {resumen} |",
              "| C3 Informar resultados | CUMPLIDO | docs/comunicacion_resultados.md |",
              f"| C4 Cerrar correcciones | {'PENDIENTE' if pend else 'CUMPLIDO'} | docs/registro_revision.md |", ""]
    if pend:
        cierre += ["## Pendiente con acuerdo de recuperación", ""]
        for k, v in pend.items():
            cierre.append(f"- `{k}`: valor actual {v['valor']}, umbral {v['umbral']}.")
        cierre += ["", f"Acuerdo: el responsable presentará un plan de mitigación (más datos del grupo {b}, revisión de "
                       f"recolección y ajuste del umbral) y repetirá la ejecución y la revisión a más tardar el {F_CIERRE}. "
                       f"Mientras tanto, el modelo no se libera para uso productivo."]
    (D / "seguimiento_cierre.md").write_text("\n".join(cierre) + "\n", encoding="utf-8")
    print(f"Registros generados en {D}\nPruebas: {resumen}")
    return 0 if pruebas_ok else 1


if __name__ == "__main__":
    sys.exit(main())

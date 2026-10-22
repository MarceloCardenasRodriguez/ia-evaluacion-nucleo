# Caso 1 - MedPredict Solutions: diagnóstico asistido en salud

Prototipo en Python (evaluación núcleo 800TA06 - Teoría y Aplicaciones de la Inteligencia Artificial).
**Todos los datos son sintéticos**: no existen personas, clientes, medidores ni redes reales detrás de ellos.

## Estructura

```
caso1_medpredict/
├── medpredict/              # código fuente (config, seguridad, datos, mejora)
├── scripts/                 # generar_datos, demo_seguridad, ejecutar_mejora, verificar_lineamientos, generar_registros_coordinacion
├── tests/                   # 22 pruebas automáticas (pytest)
├── data/                    # dataset sintético incluido (CSV)
├── resultados/              # evidencia generada por la ejecución (JSON, TXT)
├── docs/                    # registros de revisión y coordinación (simulados, con resultados reales)
├── CHANGELOG.md, requirements.txt, run_all.sh
```

## Requisitos y reproducción

Python 3.10 o superior.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
bash run_all.sh          # reproduce TODA la evidencia (genera clave temporal si no existe)
python3 -m pytest -q     # solo las pruebas
```

Ejecución por partes:

```bash
export MEDPREDICT_CLAVE="$(python3 -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
python3 scripts/generar_datos.py            # regenera data/pacientes_sinteticos.csv (semilla 42, determinista)
python3 scripts/demo_seguridad.py           # entradas y salidas de los controles
python3 scripts/ejecutar_mejora.py          # diagnóstico, intervención, comparación, seguimiento
python3 scripts/verificar_lineamientos.py   # lista de verificación y registro de revisión
python3 scripts/generar_registros_coordinacion.py   # acta, comunicación y seguimiento
```

La clave de cifrado se entrega **solo por la variable de entorno `MEDPREDICT_CLAVE`**; nunca se escribe en el código ni en el repositorio.

## Componente de seguridad y privacidad

| Control | Implementación | Etapa del proyecto donde se integra | Cómo protege |
|---|---|---|---|
| Control de acceso | `ControlAcceso`: scrypt con sal, bloqueo tras 3 fallos, roles `medico`, `analista_datos`, `auditor` con mínimo privilegio | Diseño de la API y despliegue | Solo usuarios autorizados acceden a datos identificables |
| Protección de campos sensibles | `ProtectorCampos`: cifrado Fernet de `nombre`, `rut`, `direccion`, `telefono`; pseudónimos HMAC | Ingesta y almacenamiento | Una filtración de la base no expone identidades |
| Registro de eventos | `RegistroAuditoria`: JSON-lines con usuario y objeto pseudonimizados y redacción de RUT, correo y teléfono | Operación y monitoreo | Permite auditar sin crear una segunda fuente de datos personales |
| Pruebas de controles | `tests/test_seguridad.py` + `scripts/demo_seguridad.py` | Verificación continua (CI) | Evidencia aceptación y rechazo |

## Flujo de mejora del modelo

- Grupos de evaluación declarados: centro **A** (clínica de alto volumen, mayoritario) y centro **B** (centro regional, minoritario).
- Variable objetivo: `enfermedad_respiratoria` (1 = enfermedad respiratoria presente).
- Problema sintetizado: El centro B tiene menos registros, más datos faltantes y un equipo de imagen con otra calibración.
- Modelo base: imputación por media, sin ponderación, umbral 0,5.
- Intervención: imputación por mediana con indicadores de dato faltante, ponderación inversa por celda grupo x clase, interacción grupo x variable y umbral elegido por validación cruzada **dentro del entrenamiento**.
- El conjunto de prueba (25 %, estratificado por grupo y clase) se aísla antes de cualquier ajuste; la prueba `test_la_prueba_no_influye_en_el_ajuste` lo verifica.
- Umbrales de seguimiento (en `config.py`): recall mínimo por grupo, brecha máxima de recall, precisión mínima por grupo y faltantes máximos. Si alguno no se cumple se requiere una nueva revisión.

## Límites

Los resultados provienen de datos simulados y no constituyen evidencia clínica ni operacional. Una sola partición de prueba y pocos casos positivos del grupo minoritario implican intervalos de confianza amplios (se informan en `resultados/1_diagnostico_inicial.json` y `2_comparacion_metricas.json`).

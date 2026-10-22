#!/usr/bin/env bash
# Reproduce toda la evidencia: datos -> seguridad -> mejora -> lineamientos -> registros -> pruebas
set -euo pipefail
cd "$(dirname "$0")"
export ENERGYSMART_CLAVE="${ENERGYSMART_CLAVE:-$(python3 -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')}"
python3 scripts/generar_datos.py
python3 scripts/demo_seguridad.py | tee resultados/0_demo_seguridad.txt
python3 scripts/ejecutar_mejora.py | tee resultados/0_salida_mejora.txt
python3 scripts/verificar_lineamientos.py | tee resultados/0_verificacion_lineamientos.txt
python3 scripts/generar_registros_coordinacion.py

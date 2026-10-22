"""Configuración central del prototipo del Caso 1 (diagnóstico asistido en salud).

Todos los datos del proyecto son SINTÉTICOS. Ningún valor corresponde a una persona real.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data" / "pacientes_sinteticos.csv"
RUTA_RESULTADOS = RAIZ / "resultados"
SEMILLA = 42

# ---------------------------------------------------------------- Seguridad
VARIABLE_ENTORNO_CLAVE = "MEDPREDICT_CLAVE"          # la clave NUNCA se escribe en el código
CAMPOS_SENSIBLES = ["nombre", "rut", "direccion", "telefono"]
COL_ID = "paciente_id"

# Mínimo privilegio: cada rol recibe solo los permisos que necesita.
ROLES_PERMISOS = {
    "medico": {"leer_identidad", "leer_clinico", "predecir"},
    "analista_datos": {"leer_clinico", "predecir"},
    "auditor": {"leer_auditoria"},
}

# ------------------------------------------------------------------ Modelo
COL_GRUPO = "centro"                 # grupos de evaluación declarados
GRUPOS = ("A", "B")                  # A: clínica de alto volumen (mayoritario); B: centro regional (minoritario)
GRUPO_MINORITARIO = "B"
COL_OBJETIVO = "enfermedad_respiratoria"
CARACTERISTICAS = [
    "edad", "fumador", "saturacion_o2", "frecuencia_respiratoria",
    "temperatura_c", "pcr_mg_l", "puntaje_tos", "indice_opacidad_imagen",
]
PROPORCION_PRUEBA = 0.25

# Umbrales de seguimiento (se activa una nueva revisión cuando se incumplen)
UMBRAL_RECALL_MINIMO_GRUPO = 0.70
UMBRAL_BRECHA_RECALL = 0.10
UMBRAL_PRECISION_MINIMA_GRUPO = 0.30   # limita la carga de falsas alarmas
UMBRAL_FALTANTES = 0.25

# ------------------------------------------------------ Registros del ejercicio
EMPRESA = "MedPredict Solutions"
RESPONSABLE = "Estudiante (autor del prototipo)"
REVISOR_SIMULADO = "Revisor técnico (simulado)"
DOCENTE_SIMULADO = "Docente de la asignatura (simulado)"

"""Configuración central del prototipo del Caso 2 (predicción de demanda energética).

Todos los datos del proyecto son SINTÉTICOS. Ningún valor corresponde a clientes, medidores o redes reales.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
RUTA_DATOS = RAIZ / "data" / "consumo_sensores_sinteticos.csv"
RUTA_RESULTADOS = RAIZ / "resultados"
SEMILLA = 42

# ---------------------------------------------------------------- Seguridad
VARIABLE_ENTORNO_CLAVE = "ENERGYSMART_CLAVE"         # la clave NUNCA se escribe en el código
CAMPOS_SENSIBLES = ["cliente", "rut_cliente", "id_medidor", "direccion"]
COL_ID = "registro_id"

# Mínimo privilegio: cada rol recibe solo los permisos que necesita.
ROLES_PERMISOS = {
    "operador_red": {"leer_identidad", "leer_telemetria", "predecir"},
    "analista_datos": {"leer_telemetria", "predecir"},
    "auditor": {"leer_auditoria"},
}

# ------------------------------------------------------------------ Modelo
COL_GRUPO = "zona"                   # grupos de evaluación declarados
GRUPOS = ("urbana", "rural")         # urbana: red densa (mayoritaria); rural: red con conectividad limitada
GRUPO_MINORITARIO = "rural"
COL_OBJETIVO = "demanda_critica"     # 1 = demanda horaria sobre el 90 % de la capacidad de la subestación
CARACTERISTICAS = [
    "hora", "fin_de_semana", "temperatura_c", "humedad_pct",
    "consumo_hace_1h_kwh", "consumo_hace_24h_kwh", "voltaje_v", "desviacion_frecuencia_mhz",
]
PROPORCION_PRUEBA = 0.25

# Umbrales de seguimiento (se activa una nueva revisión cuando se incumplen)
UMBRAL_RECALL_MINIMO_GRUPO = 0.70
UMBRAL_BRECHA_RECALL = 0.10
UMBRAL_PRECISION_MINIMA_GRUPO = 0.30   # limita la carga de falsas alarmas
UMBRAL_FALTANTES = 0.25

# ------------------------------------------------------ Registros del ejercicio
EMPRESA = "EnergySmart Analytics"
RESPONSABLE = "Estudiante (autor del prototipo)"
REVISOR_SIMULADO = "Revisor técnico (simulado)"
DOCENTE_SIMULADO = "Docente de la asignatura (simulado)"

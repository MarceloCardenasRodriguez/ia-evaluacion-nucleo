"""Generador de datos clínicos SINTÉTICOS (reproducible por semilla).

El escenario replica los problemas del caso: datos limitados para el centro B (minoritario),
valores faltantes más frecuentes en B, clase positiva poco frecuente y una señal de imagen
con calibración distinta entre centros.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

_NOMBRES = ["Ana", "Luis", "Marta", "Pedro", "Sofía", "Diego", "Camila", "Jorge", "Valeria", "Tomás"]
_APELLIDOS = ["Sintético", "Ficticio", "Simulado", "Ejemplo", "Prueba", "Demo"]


def _rut_sintetico(rng: np.random.Generator) -> str:
    cuerpo = int(rng.integers(30_000_000, 39_999_999))
    suma, factor = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    dv = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return f"{cuerpo:,}".replace(",", ".") + f"-{dv}"


def generar(n: int = 10000, semilla: int = config.SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    centro = rng.choice(["A", "B"], size=n, p=[0.80, 0.20])
    b = centro == "B"

    edad = np.clip(rng.normal(52, 16, n), 18, 95).round()
    fumador = rng.binomial(1, 0.25, n)
    prob = 1 / (1 + np.exp(-(-2.3 + 0.025 * (edad - 50) + 0.7 * fumador - 0.35 * b)))
    y = rng.binomial(1, prob)

    spo2 = np.clip(rng.normal(97.0 - 1.1 * y, 1.8), 80, 100)
    fr = np.clip(rng.normal(15.5 + 1.5 * y, 3.0), 8, 40)
    temp = rng.normal(36.7 + 0.2 * y, 0.5)
    pcr = rng.lognormal(0.8 + 0.55 * y, 0.9)
    tos = np.clip(rng.normal(2.5 + 1.3 * y, 2.1), 0, 10)
    # Equipo de imagen del centro B: desplazamiento de calibración y señal más débil.
    opacidad = np.where(b, rng.normal(0.9 + 0.45 * y, 1.3), rng.normal(0.0 + 1.2 * y, 1.0))

    df = pd.DataFrame({
        config.COL_ID: [f"SYN-{i:06d}" for i in range(n)],
        "nombre": [f"{rng.choice(_NOMBRES)} {rng.choice(_APELLIDOS)}" for _ in range(n)],
        "rut": [_rut_sintetico(rng) for _ in range(n)],
        "direccion": [f"Calle Ficticia {int(rng.integers(1, 999))}" for _ in range(n)],
        "telefono": [f"+56 9 {int(rng.integers(1000, 9999))} {int(rng.integers(1000, 9999))}" for _ in range(n)],
        config.COL_GRUPO: centro,
        "edad": edad, "fumador": fumador,
        "saturacion_o2": spo2.round(1), "frecuencia_respiratoria": fr.round(1),
        "temperatura_c": temp.round(2), "pcr_mg_l": pcr.round(2),
        "puntaje_tos": tos.round(1), "indice_opacidad_imagen": opacidad.round(3),
        config.COL_OBJETIVO: y,
    })

    # Datos incompletos: más frecuentes en el centro B y más aún en pacientes sin enfermedad.
    def faltante(p_a, p_b_sano, p_b_enfermo):
        p = np.where(b, np.where(y == 1, p_b_enfermo, p_b_sano), p_a)
        return rng.random(n) < p

    df.loc[faltante(0.05, 0.38, 0.18), "pcr_mg_l"] = np.nan
    df.loc[faltante(0.02, 0.10, 0.06), "saturacion_o2"] = np.nan
    df.loc[faltante(0.03, 0.12, 0.08), "indice_opacidad_imagen"] = np.nan
    df.loc[faltante(0.02, 0.06, 0.04), "temperatura_c"] = np.nan
    return df

"""Generador de datos SINTÉTICOS de sensores IoT y consumo energético (reproducible por semilla).

El escenario replica los problemas del caso: pocos registros de la zona rural (minoritaria), sensores
con pérdidas de telemetría más frecuentes en esa zona (sobre todo en horas de alta carga), eventos de
demanda crítica poco frecuentes y un sensor de voltaje con calibración distinta.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

_NOMBRES = ["Empresa Ejemplo", "Comercial Prueba", "Industria Simulada", "Hogar Ficticio", "Taller Demo"]


def _rut_sintetico(rng: np.random.Generator) -> str:
    cuerpo = int(rng.integers(70_000_000, 79_999_999))
    suma, factor = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    dv = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return f"{cuerpo:,}".replace(",", ".") + f"-{dv}"


def generar(n: int = 10000, semilla: int = config.SEMILLA) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    zona = rng.choice(["urbana", "rural"], size=n, p=[0.80, 0.20])
    r = zona == "rural"

    hora = rng.integers(0, 24, n)
    fin_semana = rng.binomial(1, 2 / 7, n)
    punta = ((hora >= 18) & (hora <= 22)).astype(float)
    temp = np.clip(rng.normal(np.where(r, 17, 21), 7), -2, 40)
    humedad = np.clip(rng.normal(60, 15, n), 15, 100)
    base = 48 + 10 * punta - 5 * fin_semana + np.where(r, -8, 0)
    c24 = np.clip(rng.normal(base, 7), 5, None)
    c1h = np.clip(c24 * rng.normal(1.0, 0.10, n) + 2.0 * punta, 5, None)
    volt = np.where(r, rng.normal(224, 7, n), rng.normal(230, 3, n))
    dfrec = rng.normal(0, 25, n)

    # La relación con la demanda crítica difiere por zona (calefacción y uso residencial en la zona rural).
    efecto_temp = np.where(r, -0.07, 0.10) * (temp - 20)          # frío en zona rural, calor en urbana
    efecto_volt = np.where(r, 0.0, -0.05) * (volt - 230)
    z = (-3.5 + 0.06 * (c1h - 48) + 0.02 * (c24 - 48) + 1.3 * punta - 0.3 * fin_semana
         + efecto_temp + efecto_volt + 0.008 * np.abs(dfrec) + rng.normal(0, 0.4, n))
    y = rng.binomial(1, 1 / (1 + np.exp(-z)))

    df = pd.DataFrame({
        config.COL_ID: [f"SYN-{i:06d}" for i in range(n)],
        "cliente": [f"{rng.choice(_NOMBRES)} {int(rng.integers(1, 999))}" for _ in range(n)],
        "rut_cliente": [_rut_sintetico(rng) for _ in range(n)],
        "id_medidor": [f"MED-SIM-{int(rng.integers(0, 10**7)):07d}" for _ in range(n)],
        "direccion": [f"Camino Ficticio {int(rng.integers(1, 999))}" for _ in range(n)],
        config.COL_GRUPO: zona,
        "hora": hora, "fin_de_semana": fin_semana,
        "temperatura_c": temp.round(1), "humedad_pct": humedad.round(1),
        "consumo_hace_1h_kwh": c1h.round(2), "consumo_hace_24h_kwh": c24.round(2),
        "voltaje_v": volt.round(1), "desviacion_frecuencia_mhz": dfrec.round(1),
        config.COL_OBJETIVO: y,
    })

    # Telemetría incompleta: más frecuente en zona rural y más aún cuando la carga es crítica.
    def faltante(p_urbana, p_rural_normal, p_rural_critica):
        p = np.where(r, np.where(y == 1, p_rural_critica, p_rural_normal), p_urbana)
        return rng.random(n) < p

    df.loc[faltante(0.04, 0.22, 0.40), "consumo_hace_1h_kwh"] = np.nan
    df.loc[faltante(0.03, 0.12, 0.20), "voltaje_v"] = np.nan
    df.loc[faltante(0.03, 0.10, 0.18), "desviacion_frecuencia_mhz"] = np.nan
    df.loc[faltante(0.02, 0.08, 0.12), "temperatura_c"] = np.nan
    return df

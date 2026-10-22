"""Flujo de mejora del modelo: diagnóstico, tratamiento de datos, comparación y seguimiento.

Regla de oro: el conjunto de prueba se separa primero y NO participa en ninguna decisión
(imputación, ponderación, hiperparámetros ni umbral). Solo se usa para medir, una vez por modelo.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (balanced_accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from . import config

GRID_UMBRALES = np.round(np.arange(0.05, 0.96, 0.01), 2)


# ------------------------------------------------------------------ datos
def cargar_datos() -> pd.DataFrame:
    return pd.read_csv(config.RUTA_DATOS)


def separar(df: pd.DataFrame, semilla: int = config.SEMILLA):
    """Partición estratificada por grupo y clase. La prueba queda aislada desde aquí."""
    estrato = df[config.COL_GRUPO].astype(str) + "_" + df[config.COL_OBJETIVO].astype(str)
    entrenamiento, prueba = train_test_split(
        df, test_size=config.PROPORCION_PRUEBA, random_state=semilla, stratify=estrato)
    return entrenamiento.reset_index(drop=True), prueba.reset_index(drop=True)


def hash_ids(df: pd.DataFrame) -> str:
    return hashlib.sha256("|".join(sorted(df[config.COL_ID])).encode()).hexdigest()[:16]


def diagnostico_datos(entrenamiento: pd.DataFrame) -> dict:
    """Diagnóstico inicial calculado SOLO con entrenamiento."""
    salida = {}
    for g in config.GRUPOS:
        sub = entrenamiento[entrenamiento[config.COL_GRUPO] == g]
        salida[g] = {
            "n": int(len(sub)),
            "positivos": int(sub[config.COL_OBJETIVO].sum()),
            "prevalencia": round(float(sub[config.COL_OBJETIVO].mean()), 4),
            "faltantes_por_variable": {c: round(float(sub[c].isna().mean()), 4) for c in config.CARACTERISTICAS},
        }
    return salida


# ------------------------------------------------------------------ modelos
def _con_interacciones(matriz: np.ndarray) -> np.ndarray:
    """Agrega interacciones grupo x variable (la última columna es el indicador del grupo)."""
    base, grupo = matriz[:, :-1], matriz[:, -1:]
    return np.hstack([base, grupo, base * grupo])


def _indicador_grupo(x: pd.DataFrame) -> np.ndarray:
    return (x[config.COL_GRUPO] == config.GRUPO_MINORITARIO).to_numpy(dtype=float).reshape(-1, 1)


def construir_base() -> Pipeline:
    """Modelo inicial: imputación por media, sin ponderación, umbral 0,5."""
    pre = ColumnTransformer([("num", Pipeline([("imp", SimpleImputer(strategy="mean")),
                                               ("esc", StandardScaler())]), config.CARACTERISTICAS)])
    return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=1000))])


def construir_mejorado() -> Pipeline:
    """Modelo mejorado: mediana + indicadores de faltante, ponderación e interacción por grupo."""
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                          ("esc", StandardScaler())]), config.CARACTERISTICAS),
        ("grupo", FunctionTransformer(_indicador_grupo, validate=False), [config.COL_GRUPO]),
    ])
    return Pipeline([("pre", pre),
                     ("inter", FunctionTransformer(_con_interacciones, validate=False)),
                     ("clf", LogisticRegression(max_iter=2000, C=0.5))])


def pesos_por_celda(x: pd.DataFrame, y: pd.Series) -> np.ndarray:
    """Peso inverso a la frecuencia de cada celda (grupo x clase), calculado en entrenamiento."""
    celda = x[config.COL_GRUPO].astype(str).to_numpy() + "_" + y.astype(str).to_numpy()
    serie = pd.Series(celda)
    frecuencia = serie.map(serie.value_counts())
    return (len(serie) / (serie.nunique() * frecuencia)).to_numpy()


def _fbeta(y, pred, beta=2.0):
    p = precision_score(y, pred, zero_division=0)
    r = recall_score(y, pred, zero_division=0)
    return 0.0 if p + r == 0 else (1 + beta**2) * p * r / (beta**2 * p + r)


def elegir_umbral(modelo_fabrica, x: pd.DataFrame, y: pd.Series, semilla: int = config.SEMILLA) -> tuple[float, float]:
    """Umbral que maximiza F2 sobre predicciones fuera de muestra (validación cruzada en entrenamiento)."""
    estrato = x[config.COL_GRUPO].astype(str).to_numpy() + "_" + y.astype(str).to_numpy()
    oof = np.zeros(len(x))
    for idx_tr, idx_va in StratifiedKFold(5, shuffle=True, random_state=semilla).split(x, estrato):
        modelo = modelo_fabrica()
        modelo.fit(x.iloc[idx_tr], y.iloc[idx_tr], clf__sample_weight=pesos_por_celda(x.iloc[idx_tr], y.iloc[idx_tr]))
        oof[idx_va] = modelo.predict_proba(x.iloc[idx_va])[:, 1]
    puntajes = [_fbeta(y, (oof >= u).astype(int)) for u in GRID_UMBRALES]
    mejor = int(np.argmax(puntajes))
    return float(GRID_UMBRALES[mejor]), float(puntajes[mejor])


@dataclass
class ModeloEntrenado:
    nombre: str
    pipeline: Pipeline
    umbral: float


def entrenar_base(entrenamiento: pd.DataFrame) -> ModeloEntrenado:
    x, y = entrenamiento[config.CARACTERISTICAS], entrenamiento[config.COL_OBJETIVO]
    modelo = construir_base().fit(x, y)
    return ModeloEntrenado("base", modelo, 0.5)


def entrenar_mejorado(entrenamiento: pd.DataFrame) -> ModeloEntrenado:
    cols = config.CARACTERISTICAS + [config.COL_GRUPO]
    x, y = entrenamiento[cols], entrenamiento[config.COL_OBJETIVO]
    umbral, _ = elegir_umbral(construir_mejorado, x, y)
    modelo = construir_mejorado().fit(x, y, clf__sample_weight=pesos_por_celda(x, y))
    return ModeloEntrenado("mejorado", modelo, umbral)


def probabilidades(modelo: ModeloEntrenado, df: pd.DataFrame) -> np.ndarray:
    cols = config.CARACTERISTICAS + ([config.COL_GRUPO] if modelo.nombre == "mejorado" else [])
    return modelo.pipeline.predict_proba(df[cols])[:, 1]


# ------------------------------------------------------------------ métricas
def _metricas(y, proba, umbral) -> dict:
    pred = (proba >= umbral).astype(int)
    return {
        "n": int(len(y)), "positivos": int(np.sum(y)),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "exactitud_balanceada": round(float(balanced_accuracy_score(y, pred)), 4),
        "auc": round(float(roc_auc_score(y, proba)), 4),
    }


def _ic_recall(y, proba, umbral, semilla=config.SEMILLA, repeticiones=1000) -> list[float]:
    rng = np.random.default_rng(semilla)
    y = np.asarray(y)
    pos = np.where(y == 1)[0]
    pred = (proba >= umbral).astype(int)
    valores = [pred[rng.choice(pos, len(pos))].mean() for _ in range(repeticiones)]
    return [round(float(np.percentile(valores, 2.5)), 3), round(float(np.percentile(valores, 97.5)), 3)]


def evaluar_por_grupo(modelo: ModeloEntrenado, prueba: pd.DataFrame) -> dict:
    proba = probabilidades(modelo, prueba)
    y = prueba[config.COL_OBJETIVO].to_numpy()
    resultado = {"global": _metricas(y, proba, modelo.umbral)}
    for g in config.GRUPOS:
        mascara = (prueba[config.COL_GRUPO] == g).to_numpy()
        m = _metricas(y[mascara], proba[mascara], modelo.umbral)
        m["recall_ic95"] = _ic_recall(y[mascara], proba[mascara], modelo.umbral)
        resultado[g] = m
    a, b = config.GRUPOS
    resultado["brecha_recall"] = round(abs(resultado[a]["recall"] - resultado[b]["recall"]), 4)
    resultado["umbral_decision"] = round(modelo.umbral, 2)
    return resultado


# ------------------------------------------------------------------ seguimiento
def evaluar_seguimiento(metricas: dict, diagnostico: dict) -> dict:
    """Aplica los umbrales de seguimiento y devuelve el estado de cada regla."""
    a, b = config.GRUPOS
    reglas = {
        f"recall_grupo_{a}>=umbral": (metricas[a]["recall"] >= config.UMBRAL_RECALL_MINIMO_GRUPO,
                                      metricas[a]["recall"], config.UMBRAL_RECALL_MINIMO_GRUPO),
        f"recall_grupo_{b}>=umbral": (metricas[b]["recall"] >= config.UMBRAL_RECALL_MINIMO_GRUPO,
                                      metricas[b]["recall"], config.UMBRAL_RECALL_MINIMO_GRUPO),
        "brecha_recall<=umbral": (metricas["brecha_recall"] <= config.UMBRAL_BRECHA_RECALL,
                                  metricas["brecha_recall"], config.UMBRAL_BRECHA_RECALL),
    }
    for g in config.GRUPOS:
        reglas[f"precision_grupo_{g}>=umbral"] = (metricas[g]["precision"] >= config.UMBRAL_PRECISION_MINIMA_GRUPO,
                                                  metricas[g]["precision"], config.UMBRAL_PRECISION_MINIMA_GRUPO)
    max_faltante = max(v for g in config.GRUPOS for v in diagnostico[g]["faltantes_por_variable"].values())
    reglas["faltantes_maximos<=umbral"] = (max_faltante <= config.UMBRAL_FALTANTES, round(max_faltante, 4),
                                           config.UMBRAL_FALTANTES)
    return {k: {"cumple": bool(v[0]), "valor": v[1], "umbral": v[2]} for k, v in reglas.items()}


def guardar_json(objeto, ruta) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(objeto, indent=2, ensure_ascii=False), encoding="utf-8")

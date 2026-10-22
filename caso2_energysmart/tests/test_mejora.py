import numpy as np
import pytest

from energysmart import config, mejora


@pytest.fixture(scope="module")
def particiones():
    return mejora.separar(mejora.cargar_datos())


def test_datos_son_sinteticos():
    df = mejora.cargar_datos()
    assert df[config.COL_ID].str.startswith("SYN-").all()
    assert df["direccion"].str.contains("Ficticio").all() and df["id_medidor"].str.startswith("MED-SIM").all()


def test_entrenamiento_y_prueba_no_comparten_registros(particiones):
    entrenamiento, prueba = particiones
    assert set(entrenamiento[config.COL_ID]).isdisjoint(prueba[config.COL_ID])


def test_particion_conserva_ambos_grupos_y_clases(particiones):
    _, prueba = particiones
    for g in config.GRUPOS:
        sub = prueba[prueba[config.COL_GRUPO] == g]
        assert sub[config.COL_OBJETIVO].nunique() == 2


def test_la_prueba_no_influye_en_el_ajuste(particiones):
    """Si se alteran las etiquetas de prueba, el modelo y el umbral no cambian."""
    entrenamiento, prueba = particiones
    m1 = mejora.entrenar_mejorado(entrenamiento)
    prueba_alterada = prueba.copy()
    prueba_alterada[config.COL_OBJETIVO] = 1 - prueba_alterada[config.COL_OBJETIVO]
    m2 = mejora.entrenar_mejorado(entrenamiento)          # prueba_alterada no se entrega al ajuste
    assert m1.umbral == m2.umbral
    assert np.allclose(m1.pipeline.named_steps["clf"].coef_, m2.pipeline.named_steps["clf"].coef_)
    assert mejora.evaluar_por_grupo(m1, prueba)["global"]["recall"] != \
        mejora.evaluar_por_grupo(m1, prueba_alterada)["global"]["recall"]


def test_imputacion_se_ajusta_solo_con_entrenamiento(particiones):
    entrenamiento, prueba = particiones
    modelo = mejora.entrenar_mejorado(entrenamiento)
    imputador = modelo.pipeline.named_steps["pre"].named_transformers_["num"].named_steps["imp"]
    esperado = entrenamiento[config.CARACTERISTICAS].median().to_numpy()
    assert np.allclose(imputador.statistics_, esperado, equal_nan=True)


def test_mejora_aumenta_recall_en_ambos_grupos(particiones):
    entrenamiento, prueba = particiones
    antes = mejora.evaluar_por_grupo(mejora.entrenar_base(entrenamiento), prueba)
    despues = mejora.evaluar_por_grupo(mejora.entrenar_mejorado(entrenamiento), prueba)
    for g in config.GRUPOS:
        assert despues[g]["recall"] > antes[g]["recall"]


def test_pesos_equilibran_las_celdas(particiones):
    entrenamiento, _ = particiones
    x, y = entrenamiento, entrenamiento[config.COL_OBJETIVO]
    w = mejora.pesos_por_celda(x, y)
    celda = x[config.COL_GRUPO].astype(str) + "_" + y.astype(str)
    totales = np.array([w[(celda == c).to_numpy()].sum() for c in celda.unique()])
    assert np.allclose(totales, totales[0])

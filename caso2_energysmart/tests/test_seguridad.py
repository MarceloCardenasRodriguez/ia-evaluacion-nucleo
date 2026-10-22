import json

import pytest

from energysmart import config, seguridad


# ---- 1. Control de acceso ------------------------------------------------
def test_usuario_autorizado_inicia_sesion(entorno):
    servicio, _, _ = entorno
    sesion = servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    assert sesion.rol == "operador_red"


def test_contrasena_incorrecta_es_rechazada(entorno):
    servicio, _, _ = entorno
    with pytest.raises(seguridad.AccesoDenegado):
        servicio.iniciar_sesion("op.test", "incorrecta-000")


def test_usuario_inexistente_es_rechazado(entorno):
    servicio, _, _ = entorno
    with pytest.raises(seguridad.AccesoDenegado):
        servicio.iniciar_sesion("intruso", "ClaveSegura-123")


def test_cuenta_se_bloquea_tras_tres_fallos(entorno):
    servicio, _, _ = entorno
    for _ in range(3):
        with pytest.raises(seguridad.AccesoDenegado):
            servicio.iniciar_sesion("op.test", "mala-contrasena")
    with pytest.raises(seguridad.AccesoDenegado, match="bloqueada"):
        servicio.iniciar_sesion("op.test", "ClaveSegura-123")


def test_operador_puede_leer_identidad(entorno):
    servicio, registro, _ = entorno
    sesion = servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    protegido = servicio.protector.proteger(registro)
    assert servicio.leer_identidad(sesion, protegido)["rut_cliente"] == registro["rut_cliente"]


def test_analista_no_puede_leer_identidad(entorno):
    servicio, registro, _ = entorno
    sesion = servicio.iniciar_sesion("analista.test", "ClaveSegura-456")
    with pytest.raises(seguridad.AccesoDenegado):
        servicio.leer_identidad(sesion, servicio.protector.proteger(registro))


def test_contrasena_debil_no_se_registra():
    with pytest.raises(ValueError):
        seguridad.ControlAcceso().registrar_usuario("x", "corta", "operador_red")


# ---- 2. Protección de campos sensibles ------------------------------------
def test_campos_sensibles_quedan_cifrados(entorno):
    servicio, registro, _ = entorno
    protegido = servicio.protector.proteger(registro)
    for campo in config.CAMPOS_SENSIBLES:
        assert protegido[campo] != registro[campo]
        assert registro[campo] not in protegido[campo]
    assert protegido["hora"] == 19            # campos no sensibles no cambian


def test_clave_incorrecta_no_descifra(entorno, clave):
    servicio, registro, _ = entorno
    protegido = servicio.protector.proteger(registro)
    otro = seguridad.ProtectorCampos(seguridad.generar_clave_nueva().encode())
    sesion = servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    with pytest.raises(ValueError):
        otro.revelar(protegido, sesion)


def test_sin_clave_en_entorno_falla_de_forma_explicita(monkeypatch):
    monkeypatch.delenv(config.VARIABLE_ENTORNO_CLAVE, raising=False)
    with pytest.raises(seguridad.ClaveNoConfigurada):
        seguridad.cargar_clave()


def test_clave_no_esta_escrita_en_el_codigo():
    for archivo in (config.RAIZ / "energysmart").glob("*.py"):
        texto = archivo.read_text(encoding="utf-8")
        assert "gAAAA" not in texto and "Fernet.generate_key()" not in texto.replace("return Fernet.generate_key()", "")


# ---- 3. Registro de eventos sin datos identificables -----------------------
def test_bitacora_no_contiene_datos_identificables(entorno):
    servicio, registro, ruta = entorno
    sesion = servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    servicio.leer_identidad(sesion, servicio.protector.proteger(registro))
    servicio.auditoria.registrar("nota", "op.test", registro[config.COL_ID],
                                 detalle=f"cliente {registro['rut_cliente']} correo ana@ejemplo.cl")
    contenido = ruta.read_text(encoding="utf-8")
    for valor in (registro["cliente"], registro["rut_cliente"], registro["id_medidor"], registro[config.COL_ID],
                  "op.test", "ana@ejemplo.cl"):
        assert valor not in contenido


def test_bitacora_registra_aceptacion_y_rechazo(entorno):
    servicio, registro, ruta = entorno
    servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    with pytest.raises(seguridad.AccesoDenegado):
        servicio.iniciar_sesion("op.test", "mala-contrasena")
    resultados = [json.loads(l)["resultado"] for l in ruta.read_text(encoding="utf-8").splitlines()]
    assert resultados == ["ok", "rechazado"]


def test_solo_auditor_consulta_la_bitacora(entorno):
    servicio, _, _ = entorno
    operador = servicio.iniciar_sesion("op.test", "ClaveSegura-123")
    with pytest.raises(seguridad.AccesoDenegado):
        servicio.consultar_auditoria(operador)
    auditor = servicio.iniciar_sesion("auditor.test", "ClaveSegura-789")
    assert len(servicio.consultar_auditoria(auditor)) >= 2


def test_pseudonimo_es_estable_y_no_revela_el_id(entorno):
    servicio, _, _ = entorno
    p1 = servicio.protector.pseudonimo("SYN-000001")
    assert p1 == servicio.protector.pseudonimo("SYN-000001")
    assert "SYN-000001" not in p1 and p1 != servicio.protector.pseudonimo("SYN-000002")

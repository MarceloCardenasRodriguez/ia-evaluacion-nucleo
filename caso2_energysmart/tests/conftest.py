import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from energysmart import config, seguridad  # noqa: E402


@pytest.fixture(scope="session")
def clave():
    return seguridad.generar_clave_nueva().encode()


@pytest.fixture()
def entorno(tmp_path, clave):
    control = seguridad.ControlAcceso()
    control.registrar_usuario("op.test", "ClaveSegura-123", "operador_red")
    control.registrar_usuario("analista.test", "ClaveSegura-456", "analista_datos")
    control.registrar_usuario("auditor.test", "ClaveSegura-789", "auditor")
    protector = seguridad.ProtectorCampos(clave)
    auditoria = seguridad.RegistroAuditoria(tmp_path / "auditoria.jsonl", protector)
    servicio = seguridad.ServicioClinico(control, protector, auditoria)
    registro = {config.COL_ID: "SYN-000001", "cliente": "Empresa Ejemplo 12", "rut_cliente": "76.123.456-0",
                "id_medidor": "MED-SIM-0001234", "direccion": "Camino Ficticio 361", "hora": 19}
    return servicio, registro, tmp_path / "auditoria.jsonl"

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from medpredict import config, seguridad  # noqa: E402


@pytest.fixture(scope="session")
def clave():
    return seguridad.generar_clave_nueva().encode()


@pytest.fixture()
def entorno(tmp_path, clave):
    control = seguridad.ControlAcceso()
    control.registrar_usuario("dra.test", "ClaveSegura-123", "medico")
    control.registrar_usuario("analista.test", "ClaveSegura-456", "analista_datos")
    control.registrar_usuario("auditor.test", "ClaveSegura-789", "auditor")
    protector = seguridad.ProtectorCampos(clave)
    auditoria = seguridad.RegistroAuditoria(tmp_path / "auditoria.jsonl", protector)
    servicio = seguridad.ServicioClinico(control, protector, auditoria)
    registro = {config.COL_ID: "SYN-000001", "nombre": "Ana Sintético", "rut": "31.412.327-1",
                "direccion": "Calle Ficticia 361", "telefono": "+56 9 4696 8337", "edad": 45}
    return servicio, registro, tmp_path / "auditoria.jsonl"

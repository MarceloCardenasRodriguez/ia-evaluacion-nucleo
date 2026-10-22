"""Controles de seguridad y privacidad: acceso, protección de campos y auditoría.

Etapas del ciclo de vida donde se integra cada control (ver README):
  - ControlAcceso      -> diseño de la API y despliegue (autenticación y autorización).
  - ProtectorCampos    -> ingesta y almacenamiento de datos clínicos (cifrado en reposo).
  - RegistroAuditoria  -> operación y monitoreo (trazabilidad sin datos identificables).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from . import config


class AccesoDenegado(Exception):
    """El usuario no está autenticado o no tiene el permiso requerido."""


class ClaveNoConfigurada(RuntimeError):
    """La clave de cifrado no está definida en el entorno."""


@dataclass(frozen=True)
class Sesion:
    usuario: str
    rol: str


# --------------------------------------------------------------------------
# 1. Control de acceso
# --------------------------------------------------------------------------
class ControlAcceso:
    """Autenticación con contraseñas derivadas (scrypt + sal) y autorización por rol."""

    MAX_INTENTOS = 3

    def __init__(self) -> None:
        self._usuarios: dict[str, tuple[bytes, bytes, str]] = {}
        self._fallos: dict[str, int] = {}

    @staticmethod
    def _derivar(contrasena: str, sal: bytes) -> bytes:
        return hashlib.scrypt(contrasena.encode(), salt=sal, n=2**14, r=8, p=1, dklen=32)

    def registrar_usuario(self, usuario: str, contrasena: str, rol: str) -> None:
        if rol not in config.ROLES_PERMISOS:
            raise ValueError(f"Rol desconocido: {rol}")
        if len(contrasena) < 10:
            raise ValueError("La contraseña debe tener al menos 10 caracteres")
        sal = secrets.token_bytes(16)
        self._usuarios[usuario] = (sal, self._derivar(contrasena, sal), rol)

    def autenticar(self, usuario: str, contrasena: str) -> Sesion:
        if self._fallos.get(usuario, 0) >= self.MAX_INTENTOS:
            raise AccesoDenegado("Cuenta bloqueada por intentos fallidos")
        registro = self._usuarios.get(usuario)
        if registro is None:
            self._derivar(contrasena, b"\x00" * 16)          # costo similar: evita enumerar usuarios
            self._fallos[usuario] = self._fallos.get(usuario, 0) + 1
            raise AccesoDenegado("Credenciales inválidas")
        sal, esperado, rol = registro
        if not hmac.compare_digest(esperado, self._derivar(contrasena, sal)):
            self._fallos[usuario] = self._fallos.get(usuario, 0) + 1
            raise AccesoDenegado("Credenciales inválidas")
        self._fallos[usuario] = 0
        return Sesion(usuario=usuario, rol=rol)

    @staticmethod
    def autorizar(sesion: Sesion, permiso: str) -> None:
        if permiso not in config.ROLES_PERMISOS.get(sesion.rol, set()):
            raise AccesoDenegado(f"El rol '{sesion.rol}' no tiene el permiso '{permiso}'")


# --------------------------------------------------------------------------
# 2. Protección de campos sensibles (sin exponer claves)
# --------------------------------------------------------------------------
def cargar_clave() -> bytes:
    """Lee la clave desde una variable de entorno. Nunca se imprime ni se guarda en el repositorio."""
    valor = os.environ.get(config.VARIABLE_ENTORNO_CLAVE)
    if not valor:
        raise ClaveNoConfigurada(
            f"Defina la variable de entorno {config.VARIABLE_ENTORNO_CLAVE} (clave Fernet)."
        )
    return valor.encode()


def generar_clave_nueva() -> str:
    """Genera una clave Fernet aleatoria para exportarla como variable de entorno."""
    return Fernet.generate_key().decode()


class ProtectorCampos:
    """Cifra campos sensibles (Fernet: AES-128-CBC + HMAC) y pseudonimiza identificadores."""

    def __init__(self, clave: bytes) -> None:
        self._fernet = Fernet(clave)
        self._clave_pseudonimo = hmac.new(clave, b"pseudonimizacion-v1", hashlib.sha256).digest()

    def pseudonimo(self, identificador: object) -> str:
        """Identificador estable pero no reversible (HMAC-SHA256 truncado)."""
        return hmac.new(self._clave_pseudonimo, str(identificador).encode(), hashlib.sha256).hexdigest()[:16]

    def proteger(self, registro: dict) -> dict:
        salida = dict(registro)
        for campo in config.CAMPOS_SENSIBLES:
            if salida.get(campo) is not None:
                salida[campo] = self._fernet.encrypt(str(salida[campo]).encode()).decode()
        return salida

    def revelar(self, registro: dict, sesion: Sesion) -> dict:
        ControlAcceso.autorizar(sesion, "leer_identidad")
        salida = dict(registro)
        try:
            for campo in config.CAMPOS_SENSIBLES:
                if salida.get(campo) is not None:
                    salida[campo] = self._fernet.decrypt(salida[campo].encode()).decode()
        except InvalidToken as error:
            raise ValueError("No fue posible descifrar: clave incorrecta o dato alterado") from error
        return salida


# --------------------------------------------------------------------------
# 3. Registro de eventos sin datos identificables
# --------------------------------------------------------------------------
_PATRONES = [
    (re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b"), "[RUT-REDACTADO]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[CORREO-REDACTADO]"),
    (re.compile(r"\+?56\s?9\s?\d{4}\s?\d{4}"), "[TELEFONO-REDACTADO]"),
]


def sanitizar(texto: str) -> str:
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


class RegistroAuditoria:
    """Bitácora JSON-lines: usuario y objeto se registran como pseudónimos, nunca en claro."""

    def __init__(self, ruta: Path, protector: ProtectorCampos) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._protector = protector

    def registrar(self, evento: str, usuario: str, objeto_id: object = None,
                  resultado: str = "ok", detalle: str = "") -> dict:
        entrada = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evento": evento,
            "usuario": self._protector.pseudonimo(usuario),
            "objeto": self._protector.pseudonimo(objeto_id) if objeto_id is not None else None,
            "resultado": resultado,
            "detalle": sanitizar(detalle),
        }
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return entrada


# --------------------------------------------------------------------------
# Servicio que integra los tres controles
# --------------------------------------------------------------------------
class ServicioClinico:
    def __init__(self, control: ControlAcceso, protector: ProtectorCampos, auditoria: RegistroAuditoria) -> None:
        self.control, self.protector, self.auditoria = control, protector, auditoria

    def iniciar_sesion(self, usuario: str, contrasena: str) -> Sesion:
        try:
            sesion = self.control.autenticar(usuario, contrasena)
        except AccesoDenegado as error:
            self.auditoria.registrar("inicio_sesion", usuario, resultado="rechazado", detalle=str(error))
            raise
        self.auditoria.registrar("inicio_sesion", usuario, resultado="ok", detalle=f"rol={sesion.rol}")
        return sesion

    def leer_identidad(self, sesion: Sesion, registro_protegido: dict) -> dict:
        paciente = registro_protegido.get(config.COL_ID)
        try:
            datos = self.protector.revelar(registro_protegido, sesion)
        except AccesoDenegado as error:
            self.auditoria.registrar("leer_identidad", sesion.usuario, paciente, "rechazado", str(error))
            raise
        self.auditoria.registrar("leer_identidad", sesion.usuario, paciente, "ok")
        return datos

    def consultar_auditoria(self, sesion: Sesion) -> list[dict]:
        try:
            self.control.autorizar(sesion, "leer_auditoria")
        except AccesoDenegado as error:
            self.auditoria.registrar("consultar_auditoria", sesion.usuario, resultado="rechazado", detalle=str(error))
            raise
        self.auditoria.registrar("consultar_auditoria", sesion.usuario)
        with self.auditoria.ruta.open(encoding="utf-8") as archivo:
            return [json.loads(linea) for linea in archivo]

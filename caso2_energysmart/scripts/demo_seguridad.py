"""Demostración reproducible de los controles de seguridad (entradas y salidas).

Uso:  python scripts/demo_seguridad.py
La clave de cifrado se genera en memoria y se entrega por variable de entorno; nunca se imprime.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from energysmart import config, datos, seguridad  # noqa: E402

os.environ.setdefault(config.VARIABLE_ENTORNO_CLAVE, seguridad.generar_clave_nueva())

RUTA_LOG = config.RUTA_RESULTADOS / "auditoria_demo.jsonl"
RUTA_LOG.unlink(missing_ok=True)


def intento(descripcion, funcion):
    try:
        salida = funcion()
        print(f"  ENTRADA : {descripcion}\n  SALIDA  : ACEPTADO -> {salida}\n")
        return True
    except (seguridad.AccesoDenegado, ValueError) as error:
        print(f"  ENTRADA : {descripcion}\n  SALIDA  : RECHAZADO -> {type(error).__name__}: {error}\n")
        return False


control = seguridad.ControlAcceso()
control.registrar_usuario("op.rojas", "ClaveSegura-123", "operador_red")
control.registrar_usuario("analista.vera", "ClaveSegura-456", "analista_datos")
control.registrar_usuario("auditor.lagos", "ClaveSegura-789", "auditor")
protector = seguridad.ProtectorCampos(seguridad.cargar_clave())
servicio = seguridad.ServicioClinico(control, protector, seguridad.RegistroAuditoria(RUTA_LOG, protector))

registro = datos.generar(n=5).iloc[0].to_dict()
registro = {k: (v if not hasattr(v, "item") else v.item()) for k, v in registro.items()}
protegido = protector.proteger(registro)

print("=== 1. CONTROL DE ACCESO ===")
operador = servicio.iniciar_sesion("op.rojas", "ClaveSegura-123")
intento("inicio de sesión op.rojas con contraseña correcta", lambda: servicio.iniciar_sesion("op.rojas", "ClaveSegura-123"))
intento("inicio de sesión op.rojas con contraseña incorrecta", lambda: servicio.iniciar_sesion("op.rojas", "contraseña-mala"))
intento("inicio de sesión de usuario inexistente 'intruso'", lambda: servicio.iniciar_sesion("intruso", "ClaveSegura-123"))
analista = servicio.iniciar_sesion("analista.vera", "ClaveSegura-456")
intento("rol operador_red lee identidad del cliente", lambda: {k: servicio.leer_identidad(operador, protegido)[k] for k in ("cliente", "rut_cliente")})
intento("rol analista_datos intenta leer identidad", lambda: servicio.leer_identidad(analista, protegido))

print("=== 2. PROTECCIÓN DE CAMPOS SENSIBLES ===")
print("  Registro original (sintético):")
for campo in config.CAMPOS_SENSIBLES:
    print(f"    {campo:<11}: {registro[campo]}")
print("  Registro protegido en almacenamiento:")
for campo in config.CAMPOS_SENSIBLES:
    print(f"    {campo:<10}: {protegido[campo][:44]}...")
print(f"  Campo no sensible (hora) sin cambios: {protegido['hora']}")
print(f"  Clave en el entorno ({config.VARIABLE_ENTORNO_CLAVE}): definida, valor no mostrado\n")

print("=== 3. REGISTRO DE EVENTOS SIN DATOS IDENTIFICABLES ===")
servicio.auditoria.registrar("nota_operacion", "op.rojas", registro[config.COL_ID],
                             detalle=f"revisión del cliente {registro['rut_cliente']} contacto ana@ejemplo.cl")
auditor = servicio.iniciar_sesion("auditor.lagos", "ClaveSegura-789")
for entrada in servicio.consultar_auditoria(auditor):
    print("  ", entrada)
contenido = RUTA_LOG.read_text(encoding="utf-8")
filtrados = [v for v in (registro["cliente"], registro["rut_cliente"], registro["id_medidor"], registro[config.COL_ID],
                         "op.rojas", "ana@ejemplo.cl") if v in contenido]
print(f"\n  Verificación: valores identificables encontrados en la bitácora = {len(filtrados)} (esperado 0)")

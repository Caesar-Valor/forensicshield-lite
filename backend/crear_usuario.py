# =============================================
# ForensicShield Lite — crear_usuario.py
# Crea (o actualiza la contraseña de) un usuario desde la terminal.
#
# Uso (desde backend/):
#   python crear_usuario.py
#   python crear_usuario.py --email admin@ejemplo.com --nombre Ana --apellido Pérez --rol admin
# =============================================

import argparse
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError

from database import SessionLocal
from models   import Usuario
from auth     import hashear_password

ROLES = ("admin", "analista", "viewer")


def pedir(valor, mensaje):
    return valor if valor else input(mensaje).strip()


def main():
    parser = argparse.ArgumentParser(description="Crear un usuario de ForensicShield Lite")
    parser.add_argument("--email")
    parser.add_argument("--nombre")
    parser.add_argument("--apellido")
    parser.add_argument("--rol", choices=ROLES)
    args = parser.parse_args()

    email = pedir(args.email, "Email: ").lower()
    try:
        TypeAdapter(EmailStr).validate_python(email)
    except ValidationError:
        sys.exit("❌ Email inválido.")

    db = SessionLocal()
    try:
        existente = db.query(Usuario).filter(Usuario.email == email).first()

        if existente:
            print(f"El usuario {email} ya existe. Se actualizará su contraseña.")
        else:
            nombre   = pedir(args.nombre,   "Nombre: ")
            apellido = pedir(args.apellido, "Apellido: ")
            rol      = args.rol or input(f"Rol {ROLES} [analista]: ").strip() or "analista"
            if not nombre or not apellido:
                sys.exit("❌ Nombre y apellido son obligatorios.")
            if rol not in ROLES:
                sys.exit(f"❌ Rol inválido. Usa uno de: {', '.join(ROLES)}")

        password = getpass.getpass("Contraseña (mín. 8 caracteres): ")
        if len(password) < 8 or len(password) > 128:
            sys.exit("❌ La contraseña debe tener entre 8 y 128 caracteres.")
        if password != getpass.getpass("Repite la contraseña: "):
            sys.exit("❌ Las contraseñas no coinciden.")

        if existente:
            existente.password_hash = hashear_password(password)
            existente.activo        = True
        else:
            db.add(Usuario(
                nombre        = nombre,
                apellido      = apellido,
                email         = email,
                password_hash = hashear_password(password),
                rol           = rol,
                activo        = True,
            ))
        db.commit()
        print(f"✅ Usuario {email} listo para iniciar sesión.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

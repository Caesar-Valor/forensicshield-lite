# =============================================
# ForensicShield Lite — Conexión a PostgreSQL
# =============================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Carga las variables del archivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Motor de conexión a PostgreSQL
engine = create_engine(DATABASE_URL)

# Cada petición a la API tendrá su propia sesión de BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base para los modelos
Base = declarative_base()

# =============================================
# Dependencia para los endpoints de FastAPI
# Abre la sesión, la usa, y la cierra sola
# =============================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
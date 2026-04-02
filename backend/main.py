from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import os

from routers import auth    as auth_router
from routers import scanner as scanner_router
from routers import network as network_router   # ← AGREGAR AQUÍ

load_dotenv()

# =============================================
# Rate Limiter global
# =============================================
limiter = Limiter(key_func=get_remote_address)

# =============================================
# Instancia principal de FastAPI
# =============================================
app = FastAPI(
    title       = "ForensicShield Lite API",
    description = "Plataforma de Auditoría de Seguridad y Análisis Forense Digital",
    version     = "1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# =============================================
# CORS — orígenes permitidos
# =============================================
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5501",
    "http://localhost:5501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["GET", "POST"],
    allow_headers     = ["Content-Type", "Authorization"],
)

# =============================================
# Headers de seguridad en todas las respuestas
# =============================================
@app.middleware("http")
async def agregar_headers_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-XSS-Protection"]       = "1; mode=block"
    response.headers["Referrer-Policy"]        = "strict-origin-when-cross-origin"
    return response

# =============================================
# Registrar routers
# =============================================
app.include_router(auth_router.router)
app.include_router(scanner_router.router)
app.include_router(network_router.router)   # ← AGREGAR AQUÍ

# =============================================
# Ruta raíz
# =============================================
@app.get("/", tags=["Estado"])
def raiz():
    return {
        "sistema": "ForensicShield Lite",
        "version": "1.0.0",
        "estado":  "activo",
        "docs":    "/docs"
    }
"""Point d'entrée de l'API : `create_app()`.

- Toutes les routes sous /api ; les modules de api/routes/ sont découverts automatiquement.
- Si web/dist/index.html existe, l'interface construite est servie à / avec repli SPA.
- Erreurs en JSON : {"erreur": "...", "detail": ...}.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from api import VERSION, chemins, db
from api import routes as paquet_routes

ORIGINES = ["http://127.0.0.1:5173", "http://localhost:5173"]
log = logging.getLogger("api")


def decouvrir_routeurs() -> list:
    routeurs = []
    for info in sorted(pkgutil.iter_modules(paquet_routes.__path__), key=lambda i: i.name):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{paquet_routes.__name__}.{info.name}")
        routeur = getattr(mod, "router", None)
        if routeur is not None:
            routeurs.append(routeur)
    return routeurs


@asynccontextmanager
async def _cycle_de_vie(app: FastAPI):
    db.initialiser()
    chemins.dossier_lots().mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Atelier 3D", version=VERSION, lifespan=_cycle_de_vie,
                  docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINES, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    for routeur in decouvrir_routeurs():
        app.include_router(routeur, prefix="/api")
    # Le plan demande « une route /sante qui répond ok » : la même route, aussi hors de /api.
    from api.routes import sante as route_sante
    app.include_router(route_sante.router)

    # Enregistré sur la classe de Starlette : c'est elle qui est levée pour une route inconnue (404)
    # ou une méthode refusée (405) ; fastapi.HTTPException en hérite, donc tout passe ici.
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        return JSONResponse({"erreur": str(exc.detail), "detail": None}, status_code=exc.status_code,
                            headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        return JSONResponse({"erreur": "Valeurs invalides", "detail": exc.errors()}, status_code=422)

    @app.exception_handler(Exception)
    async def _interne(request: Request, exc: Exception):
        log.exception("erreur interne sur %s", request.url.path)
        return JSONResponse({"erreur": f"{type(exc).__name__}: {exc}", "detail": None}, status_code=500)

    dist = chemins.dossier_web_dist()
    index = dist / "index.html"
    if index.exists():
        if (dist / "statique").is_dir():
            app.mount("/statique", StaticFiles(directory=dist / "statique"), name="statique")

        @app.get("/{chemin:path}", include_in_schema=False)
        async def spa(chemin: str):
            if chemin.startswith("api/"):
                raise HTTPException(404, "route inconnue")
            fichier = (dist / chemin).resolve() if chemin else index
            if chemin and fichier.is_file() and dist.resolve() in fichier.parents:
                return FileResponse(fichier)
            return FileResponse(index)
    else:
        @app.get("/", include_in_schema=False)
        async def racine():
            return {"application": "Atelier 3D", "version": VERSION,
                    "message": "Interface non construite : lance `python dev.py` (Vite sur http://127.0.0.1:5173) "
                               "ou `npm --prefix web run build`.", "api": "/api/sante"}
    return app

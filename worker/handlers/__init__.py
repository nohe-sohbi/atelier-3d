"""Registre des handlers : chaque module worker/handlers/<nom>.py expose TYPE et run(tache, ctx)."""
from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

HANDLERS: dict[str, Callable] = {}


def decouvrir() -> dict[str, Callable]:
    """Importe tous les modules du paquet et remplit HANDLERS = {TYPE: run}."""
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        type_ = getattr(mod, "TYPE", None)
        run = getattr(mod, "run", None)
        if type_ and callable(run):
            HANDLERS[type_] = run
    return HANDLERS


decouvrir()

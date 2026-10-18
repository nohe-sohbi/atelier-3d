"""`python -m api` : lance uvicorn sur 127.0.0.1:8000."""
from __future__ import annotations

import argparse

import uvicorn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="API d'Atelier 3D")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="rechargement automatique (développement)")
    args = parser.parse_args(argv)
    uvicorn.run("api.main:create_app", factory=True, host=args.host, port=args.port, reload=args.reload,
                reload_dirs=["api"] if args.reload else None, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

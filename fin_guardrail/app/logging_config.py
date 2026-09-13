"""Configuração central de logging da aplicação."""

import logging

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configura o logging raiz. Idempotente (força a reconfiguração)."""
    logging.basicConfig(level=level, format=_FORMAT, force=True)

"""Fixtures dos testes.

O log vive num deque em memória (singleton do módulo). Cada teste começa com
o log limpo e sem persistência.
"""

import pytest

from app import trace_store


@pytest.fixture(autouse=True)
def clean_store():
    trace_store.configure_persistence(None)
    trace_store.clear_traces()
    yield
    trace_store.configure_persistence(None)
    trace_store.clear_traces()

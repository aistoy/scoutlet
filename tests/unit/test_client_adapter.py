"""Unit tests for client adapter system — offline tests only.

Live network tests are in tests/live/test_client_adapter_live.py.
"""

import pytest

from scoutlet.client_adapter import (
    ClientAdapter,
    HttpxAdapter,
    PrimpAdapter,
    create_adapter,
    register_adapter,
)


class TestCreateAdapter:
    def test_default_creates_httpx(self):
        adapter = create_adapter("default")
        assert isinstance(adapter, HttpxAdapter)

    def test_httpx_creates_httpx(self):
        adapter = create_adapter("httpx")
        assert isinstance(adapter, HttpxAdapter)

    def test_fingerprint_creates_primp(self):
        adapter = create_adapter("fingerprint")
        assert isinstance(adapter, PrimpAdapter)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown adapter backend"):
            create_adapter("nonexistent")


class TestRegisterAdapter:
    def test_register_custom_adapter(self):
        class DummyAdapter(ClientAdapter):
            def get(self, url, **kwargs):
                pass
            def post(self, url, **kwargs):
                pass
            def close(self):
                pass

        register_adapter("dummy", DummyAdapter)
        adapter = create_adapter("dummy")
        assert isinstance(adapter, DummyAdapter)


class TestPrimpAdapterInit:
    def test_creates_without_error(self):
        adapter = PrimpAdapter()
        assert adapter is not None

    def test_close_is_noop(self):
        adapter = PrimpAdapter()
        adapter.close()  # should not raise


class TestNetworkBackendSwitch:
    def test_set_adapter_backend_default(self):
        from scoutlet import network
        original = network._adapter_backend
        try:
            network.set_adapter_backend("default")
            assert network._adapter_backend == "default"
        finally:
            network._adapter_backend = original
            network.close()

    def test_set_adapter_backend_fingerprint(self):
        from scoutlet import network
        original = network._adapter_backend
        try:
            network.set_adapter_backend("fingerprint")
            assert network._adapter_backend == "fingerprint"
        finally:
            network._adapter_backend = original
            network.close()

    def test_set_adapter_clears_cache(self):
        from scoutlet import network
        network.set_adapter_backend("default")
        # After switch, adapters cache should be empty
        assert len(network._adapters) == 0
        network.close()

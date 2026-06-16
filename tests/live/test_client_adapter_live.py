"""Live tests for client adapter — verifies real HTTP requests work with both backends.

Set SCOUTLET_LIVE=1 to run.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SCOUTLET_LIVE") != "1",
    reason="Live tests disabled. Set SCOUTLET_LIVE=1 to enable.",
)


@pytest.mark.live
@pytest.mark.timeout(30)
class TestHttpxAdapterLive:
    def test_get(self):
        from scoutlet.client_adapter import HttpxAdapter
        adapter = HttpxAdapter()
        resp = adapter.get("https://httpbin.org/get")
        assert resp.status_code == 200
        assert "httpbin.org" in resp.text
        adapter.close()

    def test_post(self):
        from scoutlet.client_adapter import HttpxAdapter
        adapter = HttpxAdapter()
        resp = adapter.post("https://httpbin.org/post", json={"key": "value"})
        assert resp.status_code == 200
        adapter.close()


@pytest.mark.live
@pytest.mark.timeout(30)
class TestPrimpAdapterLive:
    def test_get(self):
        from scoutlet.client_adapter import PrimpAdapter
        adapter = PrimpAdapter()
        resp = adapter.get("https://httpbin.org/get")
        assert resp.status_code == 200
        assert "httpbin.org" in resp.text

    def test_post(self):
        from scoutlet.client_adapter import PrimpAdapter
        adapter = PrimpAdapter()
        resp = adapter.post("https://httpbin.org/post", json={"key": "value"})
        assert resp.status_code == 200

    def test_headers(self):
        from scoutlet.client_adapter import PrimpAdapter
        adapter = PrimpAdapter()
        resp = adapter.get("https://httpbin.org/headers", headers={"X-Test": "scoutlet"})
        assert resp.status_code == 200
        assert "scoutlet" in resp.text


@pytest.mark.live
@pytest.mark.timeout(30)
class TestNetworkBackendLive:
    def test_default_backend_search(self):
        from scoutlet import network
        network.set_adapter_backend("default")
        resp = network.get("https://httpbin.org/get")
        assert resp.status_code == 200
        network.close()

    def test_fingerprint_backend_search(self):
        from scoutlet import network
        network.set_adapter_backend("fingerprint")
        resp = network.get("https://httpbin.org/get")
        assert resp.status_code == 200
        network.close()

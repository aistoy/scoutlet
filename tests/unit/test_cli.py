"""Unit tests for CLI."""

import json
import subprocess
import sys

import pytest


class TestCLI:
    def test_list_engines(self):
        result = subprocess.run(
            ["scoutlet", "--list-engines"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        engines = result.stdout.strip().split("\n")
        assert "google" in engines
        assert "bing" in engines

    def test_no_query_shows_error(self):
        result = subprocess.run(
            ["scoutlet"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0

    def test_json_output_format(self):
        result = subprocess.run(
            ["scoutlet", "python tutorial", "-e", "bing", "-f", "json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            # Response shape: {results, engines, skipped}
            assert isinstance(data, dict)
            assert "results" in data
            assert "engines" in data
            assert "skipped" in data
            if data["results"]:
                assert "url" in data["results"][0]
                assert "title" in data["results"][0]

    def test_adapter_backend_flag_passed(self, monkeypatch, capsys):
        from scoutlet import cli
        from scoutlet.response import SearchResponse

        captured = {}

        def fake_search_sync(**kwargs):
            captured.update(kwargs)
            return SearchResponse()

        monkeypatch.setattr(cli, "search_sync", fake_search_sync)
        monkeypatch.setattr(
            sys,
            "argv",
            ["scoutlet", "python asyncio", "-e", "bing", "--adapter-backend", "fingerprint"],
        )

        cli.main()

        assert captured["search_adapter_backend"] == "fingerprint"

    def test_adapter_backend_invalid_choice_rejected(self, monkeypatch, capsys):
        from scoutlet import cli

        monkeypatch.setattr(
            sys,
            "argv",
            ["scoutlet", "python asyncio", "-e", "bing", "--adapter-backend", "curl"],
        )

        with pytest.raises(SystemExit):
            cli.main()

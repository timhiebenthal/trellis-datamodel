"""Behaviour tests for the `trellis run` / `serve` / `generate-company-data` CLI.

Only the blocking server launch (uvicorn.run) and the browser are replaced;
config loading, flag handling and output are the real thing.
"""

import importlib.util
import os

import pytest
from typer.testing import CliRunner

from trellis_datamodel.cli import app

runner = CliRunner()

PROJECT_CONFIG = "framework: dbt-core\ndbt_project_path: .\ndata_model_file: dm.yml\n"


class _Launch:
    """Records the uvicorn launch and browser opens."""

    def __init__(self):
        self.uvicorn_args = None
        self.uvicorn_kwargs = None
        self.browser_urls = []


@pytest.fixture
def launch(monkeypatch):
    rec = _Launch()

    def _uvicorn_run(*args, **kwargs):
        rec.uvicorn_args = args
        rec.uvicorn_kwargs = kwargs

    monkeypatch.setattr("trellis_datamodel.cli.uvicorn.run", _uvicorn_run)
    monkeypatch.setattr(
        "trellis_datamodel.cli.webbrowser.open", lambda url: rec.browser_urls.append(url)
    )
    # run() exports these for the server; restore them after each test.
    monkeypatch.setenv("TRELLIS_BIND_HOST", "")
    monkeypatch.delenv("TRELLIS_CONFIG_PATH", raising=False)
    return rec


@pytest.fixture
def project_config(tmp_path):
    path = tmp_path / "trellis.yml"
    path.write_text(PROJECT_CONFIG)
    return path


def _run(project_config, *extra, command="run"):
    return runner.invoke(app, [command, "--config", str(project_config), *extra])


def test_run_starts_the_app_on_port_8089_without_reload_by_default(
    launch, project_config
):
    result = _run(project_config, "--no-browser")

    assert result.exit_code == 0
    assert launch.uvicorn_args == ("trellis_datamodel.server:app",)
    assert launch.uvicorn_kwargs == {
        "host": "127.0.0.1",
        "port": 8089,
        "reload": False,
        "log_level": "info",
    }


def test_run_port_option_changes_the_bound_port_and_announced_url(
    launch, project_config
):
    result = _run(project_config, "--no-browser", "--port", "9123")

    assert launch.uvicorn_kwargs["port"] == 9123
    assert "Server running at http://localhost:9123" in result.output


def test_run_short_port_flag_is_accepted(launch, project_config):
    _run(project_config, "--no-browser", "-p", "9124")

    assert launch.uvicorn_kwargs["port"] == 9124


def test_run_opens_the_browser_at_the_announced_url(launch, project_config):
    _run(project_config, "--port", "9125")

    assert launch.browser_urls == ["http://localhost:9125"]


def test_run_no_browser_flag_does_not_open_the_browser(launch, project_config):
    _run(project_config, "--no-browser")

    assert launch.browser_urls == []


def test_run_still_starts_the_server_when_the_browser_cannot_be_opened(
    launch, project_config, monkeypatch
):
    def _broken(_url):
        raise RuntimeError("no display")

    monkeypatch.setattr("trellis_datamodel.cli.webbrowser.open", _broken)

    result = _run(project_config)

    assert result.exit_code == 0
    assert launch.uvicorn_kwargs["port"] == 8089


def test_run_prints_version_banner_and_config_source(launch, project_config):
    from trellis_datamodel import __version__

    result = _run(project_config, "--no-browser")

    assert f"Trellis Data v{__version__}" in result.output
    assert f"Loading config from {project_config}" in result.output
    assert "Press Ctrl+C to stop" in result.output


def test_run_discovers_trellis_yml_in_the_working_directory(
    launch, project_config, monkeypatch
):
    monkeypatch.chdir(project_config.parent)

    result = runner.invoke(app, ["run", "--no-browser"])

    assert result.exit_code == 0
    assert f"Loading config from {project_config}" in result.output
    assert launch.uvicorn_kwargs["host"] == "127.0.0.1"


def test_run_discovers_config_yml_when_there_is_no_trellis_yml(
    launch, tmp_path, monkeypatch
):
    config_yml = tmp_path / "config.yml"
    config_yml.write_text(PROJECT_CONFIG)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["run", "--no-browser"])

    assert result.exit_code == 0
    assert f"Loading config from {config_yml}" in result.output


def test_run_without_any_config_exits_with_guidance_and_does_not_start_server(
    launch, tmp_path, monkeypatch
):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    monkeypatch.delenv("DATAMODEL_TEST_DIR", raising=False)
    monkeypatch.delenv("DATAMODEL_DATA_MODEL_PATH", raising=False)

    result = runner.invoke(app, ["run", "--no-browser"])

    assert result.exit_code == 1
    assert "No config file found" in result.output
    assert f"Expected location: {empty / 'trellis.yml'}" in result.output
    assert "trellis init" in result.output
    assert launch.uvicorn_kwargs is None


def test_run_without_config_starts_in_test_mode_when_test_env_is_set(
    launch, tmp_path, monkeypatch
):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    monkeypatch.setenv("DATAMODEL_TEST_DIR", str(tmp_path))

    result = runner.invoke(app, ["run", "--no-browser"])

    assert result.exit_code == 0
    assert launch.uvicorn_kwargs["port"] == 8089


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_run_loopback_hosts_bind_without_a_network_warning(
    launch, project_config, host
):
    result = _run(project_config, "--no-browser", "--host", host)

    assert launch.uvicorn_kwargs["host"] == host
    assert "Warning: bound to" not in result.output
    assert os.environ["TRELLIS_BIND_HOST"] == host


def test_run_non_loopback_host_warns_about_missing_authentication(
    launch, project_config
):
    result = _run(project_config, "--no-browser", "--host", "192.168.1.20")

    assert launch.uvicorn_kwargs["host"] == "192.168.1.20"
    assert "Warning: bound to 192.168.1.20" in result.output
    assert "no authentication" in result.output


def test_serve_is_an_alias_for_run_with_the_same_defaults(launch, project_config):
    result = _run(project_config, "--no-browser", command="serve")

    assert result.exit_code == 0
    assert launch.uvicorn_args == ("trellis_datamodel.server:app",)
    assert launch.uvicorn_kwargs["host"] == "127.0.0.1"
    assert launch.uvicorn_kwargs["port"] == 8089


def test_serve_forwards_host_port_and_browser_options(launch, project_config):
    result = _run(
        project_config, "--host", "0.0.0.0", "--port", "9200", command="serve"
    )

    assert launch.uvicorn_kwargs["host"] == "0.0.0.0"
    assert launch.uvicorn_kwargs["port"] == 9200
    assert launch.browser_urls == ["http://localhost:9200"]
    assert "Warning: bound to 0.0.0.0" in result.output


def test_trellis_without_a_subcommand_shows_help():
    result = runner.invoke(app, [])

    assert "Usage" in result.output
    assert "run" in result.output
    assert "generate-company-data" in result.output


# --- generate-company-data -------------------------------------------------

_GENERATOR_DEPS_INSTALLED = importlib.util.find_spec("pandas") is not None
_needs_missing_deps = pytest.mark.skipif(
    _GENERATOR_DEPS_INSTALLED,
    reason="generator dependencies installed; the run would generate real data",
)


@_needs_missing_deps
def test_generate_company_data_tells_user_how_to_install_missing_dependencies(
    tmp_path,
):
    result = runner.invoke(
        app, ["generate-company-data"], input=f"{tmp_path / 'out'}\n"
    )

    assert result.exit_code != 0
    assert "Missing generator dependencies" in result.output
    assert "pip install trellis-datamodel[dbt-example]" in result.output


@_needs_missing_deps
def test_generate_company_data_offers_the_configured_output_directory(tmp_path):
    out = tmp_path / "dummy_out"
    config = tmp_path / "trellis.yml"
    config.write_text(PROJECT_CONFIG + f"dbt_company_dummy_path: {out}\n")

    result = runner.invoke(
        app, ["generate-company-data", "--config", str(config)], input="y\n"
    )

    assert f"Output directory: {out}" in result.output
    assert "Generate CSV files to this directory?" in result.output


@_needs_missing_deps
def test_generate_company_data_declining_the_configured_directory_asks_for_another(
    tmp_path,
):
    config = tmp_path / "trellis.yml"
    config.write_text(
        PROJECT_CONFIG + f"dbt_company_dummy_path: {tmp_path / 'configured'}\n"
    )

    result = runner.invoke(
        app,
        ["generate-company-data", "--config", str(config)],
        input=f"n\n{tmp_path / 'chosen'}\n",
    )

    assert "Enter output directory" in result.output

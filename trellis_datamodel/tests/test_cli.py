"""Tests for CLI commands.

These tests verify CLI commands work correctly when the package is installed
(not just when running from source). This catches issues like path resolution
bugs that only manifest in installed packages.
"""

import os
import sys
import subprocess
import tempfile
import re
import pytest
from typer.testing import CliRunner
from pathlib import Path

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences (Typer/Rich help output in CI)."""
    return _ANSI_RE.sub("", text)


class TestCLIVersion:
    """Test version command."""

    def test_version_flag(self):
        """Test --version flag shows version."""
        from trellis_datamodel.cli import app

        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        # Should output a version string like "0.3.3"
        assert result.output.strip()
        # Version should be a valid semver-ish string
        parts = result.output.strip().split(".")
        assert len(parts) >= 2


class TestCLIInit:
    """Test init command."""

    def test_init_creates_config(self):
        """Test trellis init creates trellis.yml."""
        from trellis_datamodel.cli import app

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for the test
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["init"])
                assert result.exit_code == 0
                assert "Created trellis.yml" in result.output

                # Verify file was created
                config_path = Path(tmpdir) / "trellis.yml"
                assert config_path.exists()

                # Verify content
                content = config_path.read_text()
                assert "framework: dbt-core" in content
                assert "dbt_project_path" in content
            finally:
                os.chdir(original_cwd)

    def test_init_fails_if_exists(self):
        """Test trellis init fails if trellis.yml already exists."""
        from trellis_datamodel.cli import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                # Create existing config
                Path(tmpdir, "trellis.yml").write_text("existing: true")

                result = runner.invoke(app, ["init"])
                assert result.exit_code == 1
                assert "already exists" in result.output
            finally:
                os.chdir(original_cwd)


class TestCLIGenerateCompanyData:
    """Test generate-company-data command.

    These tests specifically verify the path resolution logic works correctly
    in various scenarios that have caused bugs in the past.

    IMPORTANT: These tests must clear DATAMODEL_TEST_DIR and reload the config
    module to simulate production behavior (not test mode).
    """

    def _create_mock_generator(self, path: Path):
        """Create a minimal mock generate_data.py script."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '''"""Mock generator for testing."""
def main():
    print("Mock data generation complete")
'''
        )

    def _get_fresh_app(self):
        """Get fresh CLI app without test mode enabled."""
        # Clear test environment to simulate production
        old_test_dir = os.environ.pop("DATAMODEL_TEST_DIR", None)

        # Force reload of config and cli modules
        modules_to_remove = [
            k for k in list(sys.modules.keys()) if "trellis_datamodel" in k
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Import fresh
        from trellis_datamodel.cli import app

        return app, old_test_dir

    def _restore_test_env(self, old_test_dir):
        """Restore test environment after test."""
        if old_test_dir:
            os.environ["DATAMODEL_TEST_DIR"] = old_test_dir
        # Reload modules to restore test mode
        modules_to_remove = [
            k for k in list(sys.modules.keys()) if "trellis_datamodel" in k
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

    def test_generate_without_config_finds_cwd_script(self):
        """Test generate-company-data finds script in cwd when no config exists.

        Scenario: User clones repo and runs command without any config file.
        Expected: Should find ./dbt_company_dummy/generate_data.py
        """
        app, old_test_dir = self._get_fresh_app()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create mock generator in cwd
                generator_path = Path(tmpdir) / "dbt_company_dummy" / "generate_data.py"
                self._create_mock_generator(generator_path)

                result = runner.invoke(app, ["generate-company-data"])
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Mock data generation complete" in result.output
        finally:
            os.chdir(original_cwd)
            self._restore_test_env(old_test_dir)

    def test_generate_with_config_but_no_dummy_path_configured(self):
        """Test generate-company-data works when config exists but dbt_company_dummy_path is not set.

        Scenario: User runs 'trellis init' then 'trellis generate-company-data'.
        The config file exists but doesn't have dbt_company_dummy_path configured.
        Expected: Should fall back to ./dbt_company_dummy/generate_data.py in cwd.

        This is the exact bug that was fixed in v0.3.3 - the config loader was
        setting a default path that didn't exist instead of letting CLI use fallback logic.
        """
        app, old_test_dir = self._get_fresh_app()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create config file WITHOUT dbt_company_dummy_path
                config_path = Path(tmpdir) / "trellis.yml"
                config_path.write_text(
                    """\
framework: dbt-core
dbt_project_path: "."
dbt_manifest_path: "target/manifest.json"
data_model_file: "data_model.yml"
"""
                )

                # Create mock generator in cwd
                generator_path = Path(tmpdir) / "dbt_company_dummy" / "generate_data.py"
                self._create_mock_generator(generator_path)

                result = runner.invoke(app, ["generate-company-data"])
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Mock data generation complete" in result.output
        finally:
            os.chdir(original_cwd)
            self._restore_test_env(old_test_dir)

    def test_generate_with_explicit_dummy_path_configured(self):
        """Test generate-company-data uses explicit dbt_company_dummy_path from config."""
        app, old_test_dir = self._get_fresh_app()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create custom directory for dummy data
                custom_dummy_dir = Path(tmpdir) / "my_custom_dummy"
                generator_path = custom_dummy_dir / "generate_data.py"
                self._create_mock_generator(generator_path)

                # Create config with explicit dbt_company_dummy_path
                config_path = Path(tmpdir) / "trellis.yml"
                config_path.write_text(
                    f"""\
framework: dbt-core
dbt_project_path: "."
dbt_company_dummy_path: "{custom_dummy_dir}"
"""
                )

                result = runner.invoke(app, ["generate-company-data"])
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Mock data generation complete" in result.output
        finally:
            os.chdir(original_cwd)
            self._restore_test_env(old_test_dir)

    def test_generate_with_relative_dummy_path_configured(self):
        """Test generate-company-data resolves relative dbt_company_dummy_path."""
        app, old_test_dir = self._get_fresh_app()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create custom directory for dummy data
                custom_dummy_dir = Path(tmpdir) / "subdir" / "dummy_data"
                generator_path = custom_dummy_dir / "generate_data.py"
                self._create_mock_generator(generator_path)

                # Create config with relative dbt_company_dummy_path
                config_path = Path(tmpdir) / "trellis.yml"
                config_path.write_text(
                    """\
framework: dbt-core
dbt_project_path: "."
dbt_company_dummy_path: "subdir/dummy_data"
"""
                )

                result = runner.invoke(app, ["generate-company-data"])
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Mock data generation complete" in result.output
        finally:
            os.chdir(original_cwd)
            self._restore_test_env(old_test_dir)

    def test_generate_fails_gracefully_when_script_missing(self):
        """Test generate-company-data shows helpful error when script not found."""
        app, old_test_dir = self._get_fresh_app()
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)

                # Create a config file to prevent fallback to repo root
                config_path = Path(tmpdir) / "trellis.yml"
                config_path.write_text(
                    """\
framework: dbt-core
dbt_project_path: "."
dbt_company_dummy_path: "nonexistent_dummy"
"""
                )

                # No generator script exists at configured path
                result = runner.invoke(app, ["generate-company-data"])
                assert result.exit_code == 1
                assert "Generator script not found" in result.output
                assert "nonexistent_dummy" in result.output
        finally:
            os.chdir(original_cwd)
            self._restore_test_env(old_test_dir)


class TestCLIRun:
    """Test run/serve commands."""

    def test_run_fails_without_config(self):
        """Test trellis run fails gracefully without config file."""
        original_cwd = os.getcwd()
        # Clear test environment variable to simulate production
        old_test_dir = os.environ.pop("DATAMODEL_TEST_DIR", None)

        # Force reload of config and cli modules
        modules_to_remove = [
            k for k in list(sys.modules.keys()) if "trellis_datamodel" in k
        ]
        for mod in modules_to_remove:
            del sys.modules[mod]

        from trellis_datamodel.cli import app

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                os.chdir(tmpdir)
                result = runner.invoke(app, ["run"])
                assert result.exit_code == 1
                assert "No config file found" in result.output
                assert "trellis init" in result.output
        finally:
            os.chdir(original_cwd)
            if old_test_dir:
                os.environ["DATAMODEL_TEST_DIR"] = old_test_dir
            # Reload modules to restore test mode
            modules_to_remove = [
                k for k in list(sys.modules.keys()) if "trellis_datamodel" in k
            ]
            for mod in modules_to_remove:
                del sys.modules[mod]


class TestCLIHelp:
    """Test help output."""

    def test_help_shows_commands(self):
        """Test --help shows available commands."""
        from trellis_datamodel.cli import app

        # Disable rich/ANSI output so assertions work in CI ("dumb" terminals).
        result = runner.invoke(app, ["--help"], color=False)
        assert result.exit_code == 0
        out = _strip_ansi(result.output)
        assert "run" in out
        assert "init" in out
        assert "generate-company-data" in out

    def test_subcommand_help(self):
        """Test subcommand --help works."""
        from trellis_datamodel.cli import app

        # Disable rich/ANSI output so "--port" isn't split by escape codes.
        result = runner.invoke(app, ["run", "--help"], color=False)
        assert result.exit_code == 0
        out = _strip_ansi(result.output)
        assert "--port" in out
        assert "--config" in out


class TestCLIInstalledPackage:
    """Test CLI commands when package is installed (not from source).

    These tests simulate real-world usage by:
    1. Building the package as a wheel
    2. Creating an isolated virtual environment
    3. Installing the wheel in that venv
    4. Running CLI commands from a completely different directory
    5. Verifying path resolution works correctly

    This catches bugs that only manifest when:
    - __file__ points to site-packages, not source repo
    - No access to source repo's dbt_company_dummy directory
    - Package is installed via pip/uv, not editable mode
    """

    def _build_package(self, repo_root: Path) -> Path:
        """Build the package and return path to wheel."""
        # Try different build methods
        build_commands = [
            ["uv", "build"],  # Preferred: uv build
            ["python", "-m", "build", "--wheel"],  # Fallback: python -m build
        ]

        dist_dir = repo_root / "dist"
        dist_dir.mkdir(exist_ok=True)

        # Check if wheel already exists (from previous test run or manual build)
        wheels = list(dist_dir.glob("*.whl"))
        if wheels:
            return wheels[0]

        # Try to build
        for cmd in build_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    wheels = list(dist_dir.glob("*.whl"))
                    if wheels:
                        return wheels[0]
            except FileNotFoundError:
                continue

        pytest.skip(
            "Could not build package - no build tool available (uv or python -m build)"
        )

    def _create_isolated_venv(self, venv_dir: Path):
        """Create an isolated virtual environment."""
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

    def _install_package_in_venv(self, venv_dir: Path, wheel_path: Path):
        """Install the wheel in the virtual environment."""
        pip = venv_dir / "bin" / "pip"
        if not pip.exists():
            pip = venv_dir / "Scripts" / "pip.exe"  # Windows

        subprocess.run(
            [str(pip), "install", str(wheel_path)],
            check=True,
            capture_output=True,
        )

    def _get_venv_trellis_command(self, venv_dir: Path) -> Path:
        """Get path to trellis command in venv."""
        trellis = venv_dir / "bin" / "trellis"
        if not trellis.exists():
            trellis = venv_dir / "Scripts" / "trellis.exe"  # Windows
        return trellis

    def test_generate_company_data_with_installed_package(self):
        """Test generate-company-data works when package is installed (not editable).

        This simulates the exact scenario from the bug report:
        - Package installed via pip (not editable)
        - User runs 'trellis init' in their project
        - User runs 'trellis generate-company-data'
        - No dbt_company_dummy_path configured in trellis.yml
        - dbt_company_dummy exists in user's project directory

        This test ensures the fix works in real-world installations.
        """
        repo_root = Path(__file__).parent.parent.parent
        original_cwd = os.getcwd()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # 1. Build the package (skip if build tools unavailable)
            try:
                wheel_path = self._build_package(repo_root)
            except Exception as e:
                pytest.skip(f"Could not build package: {e}")

            # 2. Create isolated venv
            venv_dir = tmp_path / "venv"
            try:
                self._create_isolated_venv(venv_dir)
            except Exception as e:
                pytest.skip(f"Could not create venv: {e}")

            # 3. Install package in venv
            try:
                self._install_package_in_venv(venv_dir, wheel_path)
            except Exception as e:
                pytest.skip(f"Could not install package: {e}")

            # 4. Create a completely separate "user project" directory
            #    (simulating a different repo/system where user installed the package)
            user_project_dir = tmp_path / "my_project"
            user_project_dir.mkdir()

            # 5. Create mock generator in user's project (simulating cloned dbt_company_dummy)
            generator_path = user_project_dir / "dbt_company_dummy" / "generate_data.py"
            generator_path.parent.mkdir(parents=True, exist_ok=True)
            generator_path.write_text(
                '''"""Mock generator for testing."""
def main():
    print("Mock data generation complete")
'''
            )

            # 6. Create trellis.yml WITHOUT dbt_company_dummy_path (the bug scenario)
            config_path = user_project_dir / "trellis.yml"
            config_path.write_text(
                """\
framework: dbt-core
dbt_project_path: "."
dbt_manifest_path: "target/manifest.json"
data_model_file: "data_model.yml"
"""
            )

            # 7. Run trellis command from user's project directory
            #    This simulates real-world usage where __file__ points to site-packages
            trellis_cmd = self._get_venv_trellis_command(venv_dir)
            if not trellis_cmd.exists():
                pytest.skip(f"trellis command not found at {trellis_cmd}")

            os.chdir(user_project_dir)

            # Clear any test environment variables that might interfere
            test_env = {
                k: v for k, v in os.environ.items() if not k.startswith("DATAMODEL_")
            }
            test_env["PYTHONUNBUFFERED"] = "1"

            try:
                result = subprocess.run(
                    [str(trellis_cmd), "generate-company-data"],
                    capture_output=True,
                    text=True,
                    cwd=str(user_project_dir),
                    env=test_env,  # Use clean environment without test vars
                )

                assert result.returncode == 0, (
                    f"Command failed with exit code {result.returncode}\n"
                    f"STDOUT: {result.stdout}\n"
                    f"STDERR: {result.stderr}"
                )
                assert "Mock data generation complete" in result.stdout, (
                    f"Expected 'Mock data generation complete' in output\n"
                    f"STDOUT: {result.stdout}\n"
                    f"STDERR: {result.stderr}"
                )
            finally:
                os.chdir(original_cwd)

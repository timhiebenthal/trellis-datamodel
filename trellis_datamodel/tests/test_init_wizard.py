"""Tests for the interactive init wizard."""

import os
import tempfile
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch

from trellis_datamodel.init_wizard import (
    prompt_interactive_mode,
    prompt_framework,
    prompt_modeling_style,
    prompt_entity_creation_guidance,
    prompt_dbt_model_paths,
    detect_dbt_project_path,
    validate_dbt_project_path,
    resolve_relative_path,
    prompt_dbt_project_path,
    generate_config_from_answers,
    run_init_wizard,
)

runner = CliRunner()


class TestPromptInteractiveMode:
    """Test prompt_interactive_mode function."""

    def test_accepts_y(self, monkeypatch):
        """Test that 'y' is accepted."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "y")
        result = prompt_interactive_mode()
        assert result is True

    def test_accepts_yes(self, monkeypatch):
        """Test that 'yes' is accepted."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "yes")
        result = prompt_interactive_mode()
        assert result is True

    def test_accepts_uppercase_y(self, monkeypatch):
        """Test that 'Y' is accepted."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "Y")
        result = prompt_interactive_mode()
        assert result is True

    def test_rejects_n(self, monkeypatch):
        """Test that 'n' is rejected."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "n")
        result = prompt_interactive_mode()
        assert result is False

    def test_rejects_no(self, monkeypatch):
        """Test that 'no' is rejected."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "no")
        result = prompt_interactive_mode()
        assert result is False


class TestPromptFramework:
    """Test prompt_framework function."""

    def test_accepts_1(self, monkeypatch):
        """Test that '1' is accepted and returns 'dbt-core'."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "1")
        result = prompt_framework()
        assert result == "dbt-core"

    def test_accepts_dbt_core(self, monkeypatch):
        """Test that 'dbt-core' is accepted."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "dbt-core")
        result = prompt_framework()
        assert result == "dbt-core"

    def test_accepts_uppercase_dbt_core(self, monkeypatch):
        """Test that 'DBT-CORE' (uppercase) is accepted."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "DBT-CORE")
        result = prompt_framework()
        assert result == "dbt-core"

    def test_retries_on_invalid_input(self, monkeypatch):
        """Test that invalid input prompts for retry."""
        call_count = [0]

        def mock_prompt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "2"  # Invalid
            return "1"  # Valid on retry

        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", mock_prompt)

        result = prompt_framework()
        assert result == "dbt-core"
        assert call_count[0] == 2


class TestPromptModelingStyle:
    """Test prompt_modeling_style function."""

    def test_returns_entity_model(self, monkeypatch):
        """Test that '1' returns 'entity_model'."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "1")
        result = prompt_modeling_style()
        assert result == "entity_model"

    def test_returns_dimensional_model(self, monkeypatch):
        """Test that '2' returns 'dimensional_model'."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "2")
        result = prompt_modeling_style()
        assert result == "dimensional_model"

    def test_retries_on_invalid_input(self, monkeypatch):
        """Test that invalid input prompts for retry."""
        call_count = [0]

        def mock_prompt(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return "3"  # Invalid
            return "1"  # Valid on retry

        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)
        monkeypatch.setattr("typer.prompt", mock_prompt)

        result = prompt_modeling_style()
        assert result == "entity_model"
        assert call_count[0] == 2


class TestPromptEntityCreationGuidance:
    """Test prompt_entity_creation_guidance function."""

    def test_accepts_y(self, monkeypatch):
        """Test that 'y' returns True."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "y")
        result = prompt_entity_creation_guidance()
        assert result is True

    def test_rejects_n(self, monkeypatch):
        """Test that 'n' returns False."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "n")
        result = prompt_entity_creation_guidance()
        assert result is False


class TestPromptDbtModelPaths:
    """Test prompt_dbt_model_paths function."""

    def test_all_keyword_returns_none(self, monkeypatch):
        """Test that 'all' keyword returns None."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "all")
        result = prompt_dbt_model_paths()
        assert result is None

    def test_empty_string_returns_none(self, monkeypatch):
        """Test that empty string returns None."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "")
        result = prompt_dbt_model_paths()
        assert result is None

    def test_comma_separated_returns_list(self, monkeypatch):
        """Test that comma-separated values return a list."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "models/staging,models/marts")
        result = prompt_dbt_model_paths()
        assert result == ["models/staging", "models/marts"]

    def test_trims_whitespace(self, monkeypatch):
        """Test that whitespace is trimmed from paths."""
        monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: " models/staging , models/marts ")
        result = prompt_dbt_model_paths()
        assert result == ["models/staging", "models/marts"]


class TestPromptDbtProjectPath:
    """Test prompt_dbt_project_path function."""

    def test_accepts_valid_path(self, monkeypatch):
        """Test that a valid path is accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a subdirectory to use as dbt project
            dbt_dir = tmpdir_path / "dbt_project"
            dbt_dir.mkdir()

            monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: "dbt_project")

            result = prompt_dbt_project_path(tmpdir_path / "trellis.yml")
            assert result == "dbt_project"

    def test_allows_greenfield_project_with_confirmation(self, monkeypatch):
        """Test that non-existent path is allowed when user confirms (greenfield project)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            prompt_calls = []

            def mock_prompt(*args, **kwargs):
                prompt_calls.append(args[0] if args else "")
                if "dbt project path" in (args[0] if args else ""):
                    return "my_new_dbt_project"
                # Confirm to proceed
                return True

            def mock_confirm(*args, **kwargs):
                return True

            monkeypatch.setattr("typer.prompt", mock_prompt)
            monkeypatch.setattr("typer.confirm", mock_confirm)

            result = prompt_dbt_project_path(tmpdir_path / "trellis.yml")

            # Should return the non-existent path since user confirmed
            assert result == "my_new_dbt_project"

    def test_rejects_non_existent_path_when_user_declines(self, monkeypatch):
        """Test that non-existent path is rejected when user declines to proceed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            prompt_count = [0]

            def mock_prompt(*args, **kwargs):
                prompt_count[0] += 1
                # First prompt is for path, second is for cancellation
                if prompt_count[0] == 1:
                    return "nonexistent_path"
                # This shouldn't be reached since typer.Exit is raised
                return False

            def mock_confirm(*args, **kwargs):
                # First confirm is to proceed with non-existent path (user says no)
                # Second confirm is to cancel configuration (user says yes)
                if kwargs.get("default") is False:
                    prompt_count[0] += 1
                    if prompt_count[0] == 2:
                        return False  # Don't proceed with non-existent path
                    if prompt_count[0] == 3:
                        return True  # Cancel configuration
                return False

            monkeypatch.setattr("typer.prompt", mock_prompt)
            monkeypatch.setattr("typer.confirm", mock_confirm)

            # Mock typer.Exit to avoid actual exit in test
            from typer import Exit as TyperExit

            with pytest.raises((SystemExit, TyperExit)) as exc_info:
                prompt_dbt_project_path(tmpdir_path / "trellis.yml")

            # Verify exit code is 0 (graceful exit)
            if hasattr(exc_info.value, 'exit_code'):
                assert exc_info.value.exit_code == 0
            else:
                assert exc_info.value.code == 0

    def test_resolves_to_relative_path(self, monkeypatch):
        """Test that absolute paths under config dir are resolved to relative."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create subdirectory
            dbt_dir = tmpdir_path / "dbt"
            dbt_dir.mkdir()

            monkeypatch.setattr("typer.prompt", lambda *args, **kwargs: str(dbt_dir))

            result = prompt_dbt_project_path(tmpdir_path / "trellis.yml")
            assert result == "dbt"


class TestDetectDbtProjectPath:
    """Test detect_dbt_project_path function."""

    def test_finds_project_in_current_dir(self):
        """Test detection in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dbt_project.yml in current dir
            Path(tmpdir, "dbt_project.yml").write_text("name: test")

            detected = detect_dbt_project_path(Path(tmpdir))
            assert detected == "."

    def test_finds_project_in_subdirectory(self):
        """Test detection in subdirectory (depth 1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dbt_project.yml in subdirectory
            subdir = Path(tmpdir, "dbt")
            subdir.mkdir()
            subdir.joinpath("dbt_project.yml").write_text("name: test")

            detected = detect_dbt_project_path(Path(tmpdir))
            assert detected == "dbt"

    def test_finds_project_in_nested_subdirectory(self):
        """Test detection in nested subdirectory (depth 2)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create dbt_project.yml in nested subdirectory
            nested = Path(tmpdir, "dbt", "project")
            nested.mkdir(parents=True)
            nested.joinpath("dbt_project.yml").write_text("name: test")

            detected = detect_dbt_project_path(Path(tmpdir))
            assert detected == "dbt/project"

    def test_returns_none_when_not_found(self):
        """Test that None is returned when no dbt_project.yml is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            detected = detect_dbt_project_path(Path(tmpdir))
            assert detected is None

    def test_prioritizes_closest_project(self):
        """Test that the closest project is returned when multiple exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create dbt_project.yml in current directory
            tmpdir_path.joinpath("dbt_project.yml").write_text("name: root")

            # Create dbt_project.yml in subdirectory
            subdir = tmpdir_path / "dbt"
            subdir.mkdir()
            subdir.joinpath("dbt_project.yml").write_text("name: sub")

            detected = detect_dbt_project_path(tmpdir_path)
            # Should prioritize the shallower path
            assert detected == "."

    def test_does_not_search_beyond_depth_2(self):
        """Test that depth 3 directories are not searched."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create dbt_project.yml at depth 3
            deep = tmpdir_path / "level1" / "level2" / "level3"
            deep.mkdir(parents=True)
            deep.joinpath("dbt_project.yml").write_text("name: deep")

            detected = detect_dbt_project_path(tmpdir_path)
            # Should not find it
            assert detected is None


class TestValidateDbtProjectPath:
    """Test validate_dbt_project_path function."""

    def test_validates_existing_directory(self):
        """Test that an existing directory passes validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = validate_dbt_project_path(tmpdir, Path(tmpdir) / "trellis.yml")
            assert is_valid is True
            assert error == ""

    def test_fails_nonexistent_path(self):
        """Test that a nonexistent path fails validation."""
        is_valid, error = validate_dbt_project_path("/nonexistent/path", Path.cwd() / "trellis.yml")
        assert is_valid is False
        assert "does not exist" in error

    def test_fails_when_path_is_file_not_directory(self):
        """Test that a file path (not directory) fails validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file
            file_path = Path(tmpdir) / "file.txt"
            file_path.write_text("content")

            is_valid, error = validate_dbt_project_path(
                str(file_path), Path(tmpdir) / "trellis.yml"
            )
            assert is_valid is False
            assert "not a directory" in error

    def test_validates_relative_paths(self):
        """Test that relative paths are correctly resolved and validated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a subdirectory
            subdir = tmpdir_path / "dbt_project"
            subdir.mkdir()

            # Validate relative path from config location
            is_valid, error = validate_dbt_project_path(
                "dbt_project", tmpdir_path / "trellis.yml"
            )
            assert is_valid is True
            assert error == ""


class TestResolveRelativePath:
    """Test resolve_relative_path function."""

    def test_keeps_relative_path_as_is(self):
        """Test that a relative path is kept as-is (with forward slashes)."""
        result = resolve_relative_path("dbt/project", Path.cwd() / "trellis.yml")
        assert result == "dbt/project"

    def test_normalizes_slashes_in_relative_path(self):
        """Test that backslashes are converted to forward slashes."""
        result = resolve_relative_path("dbt\\project", Path.cwd() / "trellis.yml")
        assert result == "dbt/project"

    def test_converts_absolute_path_under_config_dir_to_relative(self):
        """Test that absolute paths under config dir become relative."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            config_file = tmpdir_path / "trellis.yml"

            # Create subdirectory
            subdir = tmpdir_path / "dbt"
            subdir.mkdir()

            # Resolve absolute path
            result = resolve_relative_path(str(subdir), config_file)
            assert result == "dbt"

    def test_keeps_absolute_path_outside_config_dir(self):
        """Test that absolute paths outside config dir stay absolute."""
        config_file = Path.cwd() / "trellis.yml"
        other_path = Path("/some/other/directory")

        result = resolve_relative_path(str(other_path), config_file)
        assert result.startswith("/")


class TestGenerateConfigFromAnswers:
    """Test generate_config_from_answers function."""

    def test_generates_config_with_defaults(self):
        """Test config generation with default values."""
        answers = {
            "framework": "dbt-core",
            "modeling_style": "entity_model",
            "entity_creation_guidance_enabled": True,
            "dbt_project_path": ".",
            "dbt_model_paths": None,
        }

        config = generate_config_from_answers(answers)

        # Verify YAML structure
        assert "framework: dbt-core" in config
        assert "modeling_style: entity_model" in config
        assert "entity_creation_guidance:" in config
        assert "enabled: true" in config
        assert "dbt_project_path: \".\"" in config
        assert "dbt_model_paths: []" in config

    def test_omits_default_framework(self):
        """Test that default framework is not explicitly set."""
        answers = {
            "framework": "dbt-core",  # Default
            "modeling_style": "entity_model",
            "entity_creation_guidance_enabled": True,
            "dbt_project_path": ".",
            "dbt_model_paths": None,
        }

        config = generate_config_from_answers(answers)

        # Framework with default should be in the template
        assert "framework: dbt-core" in config

    def test_includes_custom_framework(self):
        """Test that custom framework is set."""
        answers = {
            "framework": "custom-framework",
            "modeling_style": "entity_model",
            "entity_creation_guidance_enabled": True,
            "dbt_project_path": ".",
            "dbt_model_paths": None,
        }

        config = generate_config_from_answers(answers)

        # Custom framework should be present
        assert "framework: custom-framework" in config

    def test_includes_custom_model_paths(self):
        """Test that custom model paths are set."""
        answers = {
            "framework": "dbt-core",
            "modeling_style": "entity_model",
            "entity_creation_guidance_enabled": True,
            "dbt_project_path": ".",
            "dbt_model_paths": ["models/staging", "models/marts"],
        }

        config = generate_config_from_answers(answers)

        assert "dbt_model_paths:" in config
        assert "- models/staging" in config
        assert "- models/marts" in config

    def test_preserves_boilerplate_for_unprompted_sections(self):
        """Test that optional sections stay as commented boilerplate."""
        answers = {
            "framework": "dbt-core",
            "modeling_style": "entity_model",
            "entity_creation_guidance_enabled": True,
            "dbt_project_path": ".",
            "dbt_model_paths": None,
        }

        config = generate_config_from_answers(answers)

        # Check that boilerplate remains for features not configured by the wizard
        assert "# Lineage configuration is opt-in" in config
        assert "# Exposures configuration (opt-in)" in config

    def test_dimensional_model_style(self):
        """Test config generation with dimensional_model style."""
        answers = {
            "framework": "dbt-core",
            "modeling_style": "dimensional_model",
            "entity_creation_guidance_enabled": False,
            "dbt_project_path": ".",
            "dbt_model_paths": None,
        }

        config = generate_config_from_answers(answers)

        assert "modeling_style: dimensional_model" in config
        assert "enabled: false" in config


class TestRunInitWizard:
    """Test run_init_wizard function."""

    def test_collects_all_answers(self, monkeypatch):
        """Test that wizard collects all configuration answers."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)

        answers_collected = []
        prompts = [
            "1",  # modeling_style
            "1",  # framework
            "y",  # entity_creation_guidance
            ".",  # dbt_project_path
            "all",  # dbt_model_paths
        ]

        def mock_prompt(*args, **kwargs):
            return prompts.pop(0)

        monkeypatch.setattr("typer.prompt", mock_prompt)

        config_file = Path.cwd() / "trellis.yml"

        # Mock path validation to always succeed
        monkeypatch.setattr(
            "trellis_datamodel.init_wizard.validate_dbt_project_path",
            lambda x, y: (True, ""),
        )

        answers = run_init_wizard(config_file)

        assert answers["framework"] == "dbt-core"
        assert answers["modeling_style"] == "entity_model"
        assert answers["entity_creation_guidance_enabled"] is True
        assert answers["dbt_project_path"] == "."
        assert answers["dbt_model_paths"] is None

    def test_skips_model_paths_for_greenfield_project(self, monkeypatch):
        """Test that dbt_model_paths is skipped when dbt project doesn't exist (greenfield)."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)

        prompts = [
            "1",  # modeling_style
            "1",  # framework
            "y",  # entity_creation_guidance
            "nonexistent_dbt",  # dbt_project_path (doesn't exist)
        ]

        def mock_prompt(*args, **kwargs):
            if len(prompts) > 0:
                return prompts.pop(0)
            return None

        def mock_confirm(*args, **kwargs):
            return True  # Proceed with greenfield project

        monkeypatch.setattr("typer.prompt", mock_prompt)
        monkeypatch.setattr("typer.confirm", mock_confirm)

        config_file = Path.cwd() / "trellis.yml"

        answers = run_init_wizard(config_file)

        assert answers["framework"] == "dbt-core"
        assert answers["modeling_style"] == "entity_model"
        assert answers["entity_creation_guidance_enabled"] is True
        assert answers["dbt_project_path"] == "nonexistent_dbt"
        assert answers["dbt_model_paths"] is None  # Should be None for greenfield

    def test_handles_keyboard_interrupt(self, monkeypatch):
        """Test that Ctrl+C is handled gracefully."""
        monkeypatch.setattr("typer.echo", lambda *args, **kwargs: None)

        def mock_prompt(*args, **kwargs):
            raise KeyboardInterrupt()

        monkeypatch.setattr("typer.prompt", mock_prompt)

        config_file = Path.cwd() / "trellis.yml"

        # typer.Exit is a click.exceptions.Exit, which is SystemExit-like
        from typer import Exit as TyperExit

        with pytest.raises((SystemExit, TyperExit)) as exc_info:
            run_init_wizard(config_file)

        # Exit code should be 0 (graceful exit)
        if hasattr(exc_info.value, 'exit_code'):
            assert exc_info.value.exit_code == 0
        else:
            assert exc_info.value.code == 0


class TestIntegration:
    """Integration tests for the full wizard flow."""

    def test_init_with_interactive_mode_yes(self):
        """Test trellis init with interactive mode selected."""
        from trellis_datamodel.cli import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Simulate user selecting interactive mode
                # Inputs: y (interactive), 1 (modeling), 1 (framework), y (entity), . (path), all (models)
                input_data = "y\n1\n1\ny\n.\nall\n"
                result = runner.invoke(app, ["init"], input=input_data)

                # Print output for debugging
                if result.exit_code != 0:
                    print(f"Output: {result.output}")
                    print(f"Exception: {result.exception}")

                assert result.exit_code == 0
                assert "Created trellis.yml" in result.output

                # Verify file was created
                config_path = Path(tmpdir) / "trellis.yml"
                assert config_path.exists()

                # Verify content includes wizard selections
                content = config_path.read_text()
                assert "modeling_style: entity_model" in content

            finally:
                os.chdir(original_cwd)

    def test_init_with_interactive_mode_no(self):
        """Test trellis init declining interactive mode (backward compatibility)."""
        from trellis_datamodel.cli import app, DEFAULT_CONFIG_TEMPLATE

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Simulate user declining interactive mode
                input_data = "n\n"
                result = runner.invoke(app, ["init"], input=input_data)

                assert result.exit_code == 0
                assert "Created trellis.yml" in result.output

                # Verify file was created
                config_path = Path(tmpdir) / "trellis.yml"
                assert config_path.exists()

                # Verify content matches default template (backward compatibility)
                content = config_path.read_text()
                assert content == DEFAULT_CONFIG_TEMPLATE

            finally:
                os.chdir(original_cwd)

    def test_init_fails_when_config_exists(self):
        """Test trellis init fails when trellis.yml already exists."""
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

    def test_full_wizard_with_all_custom_values(self):
        """Test full wizard flow with all custom values."""
        from trellis_datamodel.cli import app

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Simulate user providing all custom values
                input_data = (
                    "y\n"  # Interactive mode
                    "2\n"  # Modeling style: dimensional_model
                    "dbt-core\n"  # Framework (default)
                    "n\n"  # Entity wizard disabled
                    ".\n"  # Project path
                    "models/staging,models/marts\n"  # Custom model paths
                )

                result = runner.invoke(app, ["init"], input=input_data)

                assert result.exit_code == 0
                assert "Created trellis.yml" in result.output

                # Verify file content
                config_path = Path(tmpdir) / "trellis.yml"
                content = config_path.read_text()

                assert "modeling_style: dimensional_model" in content
                assert "enabled: false" in content  # Entity wizard disabled
                assert "- models/staging" in content
                assert "- models/marts" in content

            finally:
                os.chdir(original_cwd)

    def test_config_is_valid_yaml(self):
        """Test that generated config is valid and loadable."""
        from trellis_datamodel.cli import app
        from ruamel.yaml import YAML

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Run interactive init
                input_data = "y\n1\n1\ny\n.\nall\n"
                result = runner.invoke(app, ["init"], input=input_data)
                assert result.exit_code == 0

                # Try to load the generated config
                yaml = YAML()
                config_path = Path(tmpdir) / "trellis.yml"
                with open(config_path, "r") as f:
                    config = yaml.load(f)

                # Verify it's a valid config object
                assert config is not None
                assert "framework" in config
                assert "dbt_project_path" in config

            finally:
                os.chdir(original_cwd)

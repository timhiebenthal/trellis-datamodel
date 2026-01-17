"""
Interactive CLI Wizard for trellis init command.

Guides users through configuring their trellis.yml file with sensible defaults
and auto-detection capabilities.
"""

import glob
import os
from pathlib import Path
from typing import Optional, Dict, Any

import typer
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

# Original template with comments (copied here to avoid circular import)
DEFAULT_CONFIG_TEMPLATE = """\
# trellis configuration for data model UI

# Transformation framework currently supported.
framework: dbt-core

# Path to the dbt project directory (relative to this file or absolute)
dbt_project_path: "."
# Path to dbt manifest.json (relative to dbt_project_path or absolute)
dbt_manifest_path: "target/manifest.json"
# Path to dbt catalog.json (relative to dbt_project_path or absolute)
dbt_catalog_path: "target/catalog.json"

# Where the generated data_model.yml is written (relative to dbt_project_path)
data_model_file: "data_model.yml"

# List of path patterns to include (empty list includes all models)
dbt_model_paths: []  # Empty = include all models

# Helper project used by `trellis generate-company-data`.
# Run the command to populate ./dbt_company_dummy or replace with your own project.
dbt_company_dummy_path: "./dbt_company_dummy"

# Lineage configuration is opt-in. Uncomment to customize defaults.
#lineage:
#  enabled: false  # Set to true to enable lineage UI/endpoints
#  layers: []  # Ordered folder names that become lineage layers

# Entity creation guidance (preferred block). Defaults match new schema.
#entity_creation_guidance:
#  enabled: true  # Set false to disable the step-by-step wizard
#  push_warning_enabled: true  # Show push warnings when interacting with dbt
#  min_description_length: 10  # Minimum characters required for descriptions
#  disabled_guidance: []  # Helper flows to disable

# Exposures configuration (opt-in). Uncomment to enable Exposures view mode.
# Use this feature if you want to track and visualize how your dbt models are used in
# downstream BI dashboards, notebooks, and applications via dbt exposures.
#exposures:
#  enabled: false  # Set to true to enable Exposures view mode (opt-in)
#  default_layout: dashboards-as-rows  # Default table orientation: dashboards-as-rows (exposures as rows, entities as columns) or entities-as-rows (exposures as columns, entities as rows). Use toggle button in UI to switch layouts.

# Dimensional modeling configuration (opt-in).
# Use this feature if you want to enable Kimball dimensional modeling features such as:
# - Entity classification (fact vs dimension)
# - Smart default positioning for star/snowflake schemas
# - Kimball Bus Matrix view mode
# Default is entity_model for backward compatibility.
#modeling_style: entity_model  # Options: dimensional_model or entity_model

# Dimensional modeling inference patterns (used when modeling_style is dimensional_model).
# Customize these patterns to match your dbt model naming conventions.
#
# When your dbt project loads, entities are automatically classified based on model names:
# - Models matching dimension_prefix → classified as "dimension" (green icon)
# - Models matching fact_prefix → classified as "fact" (blue icon)
# - Unmatched models → classified as "unclassified" (gray icon)
#
# You can override any classification by clicking the entity type badge on entity nodes.
# This inference only runs on initial load; manual changes are always preserved.
#
# Common naming conventions:
# - Dimensions: dim_, d_, dim, dimension (e.g., dim_customer, d_employee)
# - Facts: fct_, fact_, f (e.g., fct_orders, fact_sales, f_transactions)
#
# You can specify prefixes as either a string (single prefix) or a list (multiple prefixes, first is used):
#   dimension_prefix: "d_"           # Single prefix as string
#   dimension_prefix: ["dim_", "d_"]  # Multiple prefixes as list (first is used)
#   fact_prefix: "f_"                # Single prefix as string
#   fact_prefix: ["fct_", "fact_"]   # Multiple prefixes as list (first is used)
#dimensional_modeling:
#  inference_patterns:
#    dimension_prefix: ["dim_", "d_"]  # Prefixes for dimension tables (string or list)
#    fact_prefix: ["fct_", "fact_"]  # Prefixes for fact tables (string or list)

"""

# Optional sections we keep as boilerplate when the wizard hasn't configured them
BOILERPLATE_OPTIONAL_SECTIONS = """\

# Lineage configuration is opt-in. Uncomment to customize defaults.
#lineage:
#  enabled: false  # Set to true to enable lineage UI/endpoints
#  layers: []  # Ordered folder names that become lineage layers

# Exposures configuration (opt-in). Uncomment to enable Exposures view mode.
# Use this feature if you want to track and visualize how your dbt models are used in
# downstream BI dashboards, notebooks, and applications via dbt exposures.
#exposures:
#  enabled: false  # Set to true to enable Exposures view mode (opt-in)
#  default_layout: dashboards-as-rows  # dashboards-as-rows (exposures as rows, entities as columns) or entities-as-rows (exposures as columns, entities as rows). Use toggle button in UI to switch layouts.
"""


def prompt_interactive_mode() -> bool:
    """
    Ask user if they want to configure trellis.yml interactively.

    Returns:
        bool: True if user selects interactive mode, False otherwise
    """
    typer.echo()
    typer.echo(
        typer.style(
            "Would you like to configure trellis.yml interactively?",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )
    response = typer.prompt(
        "[y/n]",
        default="y",
        show_default=True,
    )
    return response.lower() in ("y", "yes")


def prompt_framework() -> str:
    """
    Prompt user for framework configuration.

    Shows numbered list of options and validates input.

    Returns:
        str: The framework value (default: "dbt-core")

    Note:
        Currently only dbt-core is supported. This option is shown for
        transparency about what framework trellis uses.
    """
    typer.echo()
    typer.echo(
        typer.style(
            "Which transformation tool trellis will interact with?",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )
    typer.echo("  1. dbt-core (dbt-fusion not verified yet)")

    while True:
        choice = typer.prompt(
            "Select framework",
            default="1",
            show_default=True,
        )

        if choice == "1" or choice.lower() == "dbt-core":
            return "dbt-core"
        else:
            typer.echo(
                typer.style(
                    "Invalid choice. Please enter 1 or dbt-core.", fg=typer.colors.RED
                )
            )


def prompt_modeling_style() -> str:
    """
    Prompt user for modeling style configuration.

    Shows numbered list of options and validates input.

    Returns:
        str: The modeling style ("entity_model" or "dimensional_model")
    """
    typer.echo()
    typer.echo(
        typer.style(
            "Which Data Modeling style do you want to use?",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )
    typer.echo("  1. entity_model - Traditional ERD-style modeling")
    typer.echo("  2. dimensional_model - Kimball dimensional modeling (fact/dimension)")

    while True:
        choice = typer.prompt(
            "Select modeling style",
            default="1",
            show_default=True,
        )

        if choice == "1":
            return "entity_model"
        elif choice == "2":
            return "dimensional_model"
        else:
            typer.echo(
                typer.style("Invalid choice. Please enter 1 or 2.", fg=typer.colors.RED)
            )


def prompt_entity_creation_guidance() -> bool:
    """
    Prompt user for entity creation guidance configuration.

    Returns:
        bool: True if entity wizard should be enabled, False otherwise

    Note:
        The entity creation wizard is a step-by-step guide that helps users
        create new entities with proper descriptions. Disabling this removes
        the helper wizard from the UI.
    """
    typer.echo()
    typer.echo(
        typer.style(
            "Enable entity creation wizard?",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )
    typer.echo("  Step-by-step UI guidance when creating new entities")
    typer.echo("  Recommended: Keep enabled for better documentation")

    response = typer.prompt(
        "[y/n]",
        default="y",
        show_default=True,
    )
    return response.lower() in ("y", "yes")


def prompt_dbt_model_paths() -> Optional[list]:
    """
    Prompt user for dbt_model_paths configuration.

    Accepts comma-separated paths or "all" keyword for empty list.

    Returns:
        Optional[list]: List of paths or None (empty list) for "all"

    Note:
        Specifying paths filters which models trellis includes in the data
        model. Leave empty (type 'all') to include all models in your dbt
        project.
    """
    typer.echo()
    typer.echo(
        typer.style(
            "dbt model paths to include in data model:",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )
    typer.echo("  Leave empty or type 'all' to include all models")
    typer.echo(
        "  Specify comma-separated subdirectory-paths to filter specific models (e.g. `core`)"
    )
    typer.echo()

    response = typer.prompt(
        'Path(s) or "all"',
        default="all",
        show_default=True,
    )

    if response.lower() == "all" or not response.strip():
        return None  # Empty list

    # Parse comma-separated paths
    paths = [p.strip() for p in response.split(",") if p.strip()]
    return paths


def detect_dbt_project_path(current_dir: Optional[Path] = None) -> Optional[str]:
    """
    Auto-detect dbt project directory by searching for dbt_project.yml files.

    Searches in current directory and subdirectories up to depth 2.
    If multiple files found, returns the closest one (shallowest depth).

    Args:
        current_dir: Directory to search from (defaults to current working directory)

    Returns:
        Optional[str]: Detected dbt project directory path relative to current_dir, or None
    """
    if current_dir is None:
        current_dir = Path.cwd()

    # Search patterns for depth 0, 1, and 2
    patterns = [
        "dbt_project.yml",
        "*/dbt_project.yml",
        "*/*/dbt_project.yml",
    ]

    found_files = []

    for pattern in patterns:
        # Use glob to find matching files
        matches = glob.glob(str(current_dir / pattern), recursive=True)
        for match in matches:
            found_files.append(match)

    if not found_files:
        return None

    # Sort by depth (number of directories) - prefer shallower paths
    def get_depth(path_str: str) -> int:
        rel_path = Path(path_str).relative_to(current_dir)
        return len(rel_path.parts)

    found_files.sort(key=get_depth)

    # Return the closest (shallowest) match
    closest = found_files[0]
    rel_path = Path(closest).relative_to(current_dir)

    # Return parent directory (dbt project folder), not the file itself
    dbt_project_dir = rel_path.parent
    # Use "." if the file is in the current directory
    if str(dbt_project_dir) == ".":
        return "."

    # Return as string with forward slashes
    return str(dbt_project_dir).replace("\\", "/")


def validate_dbt_project_path(
    path: str, config_file_location: Path
) -> tuple[bool, str]:
    """
    Validate that the dbt project path exists and is accessible.

    Note: Non-existent paths return False, but callers may allow proceeding
    for greenfield projects (e.g., prompt_dbt_project_path).

    Args:
        path: The path to validate (relative or absolute)
        config_file_location: Location of config file (for resolving relative paths)

    Returns:
        tuple[bool, str]: (is_valid, error_message_or_empty_string)
    """
    # Resolve the path relative to config file location
    if Path(path).is_absolute():
        resolved_path = Path(path)
    else:
        resolved_path = (config_file_location.parent / path).resolve()

    if not resolved_path.exists():
        error_msg = (
            f"Path does not exist: '{path}'\n"
            f"  Resolved to: '{resolved_path}'\n"
            f"  Please verify the path is correct."
        )
        return False, error_msg

    if not resolved_path.is_dir():
        error_msg = (
            f"Path is not a directory: {path}\n"
            f"  Please provide a path to a directory."
        )
        return False, error_msg

    return True, ""


def resolve_relative_path(
    path: str,
    config_file_location: Path,
) -> str:
    """
    Compute relative path from config file location, if possible.

    Returns relative path if the path is under the config file directory,
    otherwise returns absolute path.

    Args:
        path: The path to resolve (relative or absolute)
        config_file_location: Location of config file

    Returns:
        str: Relative path (with forward slashes) or absolute path
    """
    path_obj = Path(path)

    # If path is already relative, keep it as is (normalize slashes)
    if not path_obj.is_absolute():
        # Normalize to use forward slashes
        return str(path).replace("\\", "/")

    # Path is absolute - try to make it relative
    config_dir = config_file_location.parent

    try:
        rel_path = path_obj.relative_to(config_dir)
        # Convert to forward slashes
        return str(rel_path).replace("\\", "/")
    except ValueError:
        # Path is outside config directory, keep absolute
        return str(path).replace("\\", "/")


def prompt_dbt_project_path(config_file_location: Path) -> str:
    """
    Prompt user for dbt project path with auto-detection and validation.

    Integrates auto-detection, validation, and retry logic.
    Allows greenfield projects where the dbt project folder doesn't exist yet.

    Args:
        config_file_location: Path where config file will be written

    Returns:
        str: Validated dbt project path (relative to config file when possible)
    """
    # Auto-detect dbt_project.yml
    detected = detect_dbt_project_path(config_file_location.parent)

    # Determine default value and prompt text
    if detected:
        default_value = detected
        prompt_suffix = f" (auto-detected: {detected})"
    else:
        default_value = "."
        prompt_suffix = ""

    typer.echo()
    typer.echo(
        typer.style(
            "In which folder is your dbt-project located?",
            fg=typer.colors.CYAN,
            bold=True,
        )
    )

    while True:
        path_input = typer.prompt(
            f"dbt project path{prompt_suffix}",
            default=default_value,
            show_default=bool(detected),
        )

        # Validate the path
        is_valid, error_msg = validate_dbt_project_path(
            path_input, config_file_location
        )

        if is_valid:
            # Resolve to relative path when possible
            resolved = resolve_relative_path(path_input, config_file_location)
            return resolved
        else:
            # Path doesn't exist - check if user wants to proceed (greenfield project)
            if "does not exist" in error_msg:
                typer.echo()
                typer.echo(
                    typer.style(
                        "Warning: The specified folder does not exist.",
                        fg=typer.colors.YELLOW,
                    )
                )
                # Resolve the path to show the absolute path in parentheses
                if Path(path_input).is_absolute():
                    resolved_path = Path(path_input)
                else:
                    resolved_path = (config_file_location.parent / path_input).resolve()
                typer.echo(f"Path does not exist: {path_input} ({resolved_path})")
                typer.echo()
                typer.echo(
                    typer.style(
                        "If you don't have a dbt-project set up yet, it's OK to use trellis without.",
                        fg=typer.colors.CYAN,
                    )
                )
                typer.echo("You can create the dbt-project structure later.")
                typer.echo()

                # Ask if user wants to proceed
                proceed = typer.confirm("Proceed anyway?", default=False)
                if proceed:
                    # Resolve to relative path when possible
                    resolved = resolve_relative_path(path_input, config_file_location)
                    return resolved

            # Show the error for non-existence issues or when user doesn't want to proceed
            typer.echo(typer.style(error_msg, fg=typer.colors.RED))
            typer.echo()

            # Offer to cancel
            cancel = typer.confirm("Cancel configuration?", default=False)
            if cancel:
                typer.echo("Configuration cancelled.")
                raise typer.Exit(0)


def generate_config_from_answers(answers: Dict[str, Any]) -> str:
    """
    Generate trellis.yml configuration from wizard answers.

    Creates a config with only non-default fields explicitly set,
    while preserving all template comments and structure.

    Args:
        answers: Dictionary of configuration answers from wizard

    Returns:
        str: Generated YAML configuration as string
    """
    # Parse template using ruamel.yaml to preserve comments
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=2)

    config = CommentedMap()
    config.yaml_set_start_comment("Trellis configuration for data model UI")

    # Modeling style and optional dimensional modeling section
    modeling_style = answers.get("modeling_style", "entity_model")
    config["modeling_style"] = modeling_style
    config.yaml_set_comment_before_after_key(
        "modeling_style",
        before="Select data modeling style (entity_model or dimensional_model)",
    )
    # Enforce mutual exclusion - only write the appropriate config based on modeling_style
    if modeling_style == "dimensional_model":
        config["dimensional_modeling"] = CommentedMap(
            {
                "inference_patterns": CommentedMap(
                    {
                        "dimension_prefix": ["dim_", "d_"],
                        "fact_prefix": ["fct_", "fact_"],
                    }
                )
            }
        )
        config["dimensional_modeling"].yaml_set_comment_before_after_key(
            "inference_patterns",
            before="Customize these patterns to match your dbt model naming conventions",
        )
    # Note: entity_model is the default and doesn't require explicit config

    # Core settings the wizard always knows
    framework = answers.get("framework", "dbt-core")
    config["framework"] = framework
    config.yaml_set_comment_before_after_key(
        "framework", before="Transformation framework currently supported."
    )

    dbt_project_path = answers.get("dbt_project_path", ".")
    config["dbt_project_path"] = DoubleQuotedScalarString(dbt_project_path)
    config.yaml_set_comment_before_after_key(
        "dbt_project_path",
        before="Path to the dbt project directory (relative to this file or absolute)",
    )

    config["dbt_manifest_path"] = DoubleQuotedScalarString("target/manifest.json")
    config["dbt_catalog_path"] = DoubleQuotedScalarString("target/catalog.json")
    config["data_model_file"] = DoubleQuotedScalarString("data_model.yml")

    # dbt model paths: empty list means include all models
    dbt_model_paths = answers.get("dbt_model_paths")
    config["dbt_model_paths"] = dbt_model_paths if dbt_model_paths is not None else []
    config.yaml_set_comment_before_after_key(
        "dbt_model_paths",
        before="List of path patterns to include (empty list includes all models)",
    )

    config["dbt_company_dummy_path"] = DoubleQuotedScalarString("./dbt_company_dummy")
    config.yaml_set_comment_before_after_key(
        "dbt_company_dummy_path",
        before="Helper project used by `trellis generate-company-data`.",
    )

    # Entity creation guidance mirrors the wizard choice with sensible defaults
    if "entity_creation_guidance_enabled" in answers:
        config["entity_creation_guidance"] = CommentedMap(
            {
                "enabled": answers["entity_creation_guidance_enabled"],
                "push_warning_enabled": True,
                "min_description_length": 10,
                "disabled_guidance": [],
            }
        )
        config["entity_creation_guidance"].yaml_set_comment_before_after_key(
            "push_warning_enabled",
            before="Show push warnings when interacting with dbt",
        )
        config["entity_creation_guidance"].yaml_set_comment_before_after_key(
            "min_description_length",
            before="Minimum characters required for descriptions",
        )
        config["entity_creation_guidance"].yaml_set_comment_before_after_key(
            "disabled_guidance", before="Helper flows to disable"
        )

    # Generate YAML output
    from io import StringIO

    output = StringIO()
    yaml.dump(config, output)

    def insert_blank_after_block(lines: list[str], startswith: str) -> list[str]:
        """Insert a blank line after a mapping block beginning with `startswith`."""
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.lstrip().startswith(startswith):
                base_indent = len(line) - len(line.lstrip(" "))
                j = i + 1
                while j < len(lines):
                    next_line = lines[j]
                    next_indent = len(next_line) - len(next_line.lstrip(" "))
                    if next_line.strip() == "":
                        j += 1
                        continue
                    if next_indent <= base_indent:
                        lines.insert(j, "")
                        i = j  # continue after insertion
                        break
                    j += 1
                else:
                    lines.append("")
                    i = len(lines)
            i += 1
        return lines

    lines = output.getvalue().splitlines()
    for marker in [
        "modeling_style:",
        "dimensional_modeling:",
        "framework:",
        "data_model_file:",
        "dbt_model_paths:",
        "dbt_company_dummy_path:",
        "entity_creation_guidance:",
    ]:
        lines = insert_blank_after_block(lines, marker)

    formatted = "\n".join(lines).rstrip()

    # Append boilerplate for settings the wizard did not ask about
    return f"{formatted}\n{BOILERPLATE_OPTIONAL_SECTIONS}"


def run_init_wizard(config_file_location: Path) -> Dict[str, Any]:
    """
    Run the interactive init wizard, collecting configuration from user.

    Orchestrates all prompts and returns collected answers.

    Args:
        config_file_location: Path where config file will be written

    Returns:
        Dict[str, Any]: Dictionary of configuration answers

    Raises:
        typer.Exit: If user cancels with Ctrl+C
    """
    try:
        answers: Dict[str, Any] = {}

        typer.echo()
        typer.echo(typer.style("Welcome to trellis!", bold=True, fg=typer.colors.GREEN))
        typer.echo("Let's configure your trellis.yml file.\n")

        # Prompt for all configuration options
        answers["modeling_style"] = prompt_modeling_style()
        answers["framework"] = prompt_framework()
        answers["entity_creation_guidance_enabled"] = prompt_entity_creation_guidance()
        answers["dbt_project_path"] = prompt_dbt_project_path(config_file_location)

        # Only prompt for dbt_model_paths if dbt project exists
        # (skip for greenfield projects)
        dbt_path = answers["dbt_project_path"]
        if Path(dbt_path).is_absolute():
            resolved_path = Path(dbt_path)
        else:
            resolved_path = (config_file_location.parent / dbt_path).resolve()

        if resolved_path.exists():
            answers["dbt_model_paths"] = prompt_dbt_model_paths()
        else:
            # Greenfield project - skip model paths prompt
            answers["dbt_model_paths"] = None

        return answers

    except KeyboardInterrupt:
        typer.echo("\n")
        typer.echo(
            typer.style("Configuration cancelled by user.", fg=typer.colors.YELLOW)
        )
        raise typer.Exit(0)

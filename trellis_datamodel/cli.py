"""
Trellis CLI

Command-line interface for Trellis - visual data model editor for dbt projects.
"""

import typer
import uvicorn
import webbrowser
from pathlib import Path
from typing import Optional

from trellis_datamodel import __version__
from trellis_datamodel import config as cfg
from trellis_datamodel.config import (
    load_config,
    find_config_file,
    print_config,
)

app = typer.Typer(
    name="trellis",
    help="Trellis - Visual data model editor for dbt projects",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    """Trellis - Visual data model editor for dbt projects."""
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def run(
    port: int = typer.Option(8089, "--port", "-p", help="Port to run the server on"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (trellis.yml or config.yml)"
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't open browser automatically"
    ),
):
    """
    Start the Trellis server.

    Looks for trellis.yml or config.yml in the current directory.
    """
    # Load configuration
    import os

    # Allow running without config file if test environment variables are set
    is_test_mode = bool(
        os.environ.get("DATAMODEL_DATA_MODEL_PATH")
        or os.environ.get("DATAMODEL_TEST_DIR")
    )

    config_path = config
    if not config_path:
        found_config = find_config_file()
        if not found_config:
            if is_test_mode:
                # Test mode: allow running without config file
                config_path = None
            else:
                cwd = os.getcwd()
                expected_path = os.path.join(cwd, "trellis.yml")
                typer.echo(
                    typer.style(
                        "Error: No config file found.",
                        fg=typer.colors.RED,
                    )
                )
                typer.echo(f"   Expected location: {expected_path}")
                typer.echo()
                typer.echo("   Run 'trellis init' to create a starter config file.")
                raise typer.Exit(1)
        else:
            config_path = found_config

    if config_path:
        load_config(config_path)
    elif is_test_mode:
        # Test mode: config will be loaded from environment variables
        load_config(None)

    # Print startup info
    typer.echo(
        typer.style(f"🌿 Trellis Data v{__version__}", fg=typer.colors.GREEN, bold=True)
    )
    typer.echo(f"   Loading config from {config_path}")
    print_config()
    typer.echo()

    # Start server
    url = f"http://localhost:{port}"
    typer.echo(typer.style(f"   Server running at {url}", fg=typer.colors.CYAN))
    typer.echo("   Press Ctrl+C to stop")
    typer.echo()

    # Open browser
    if not no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # Ignore browser errors

    # Run server
    uvicorn.run(
        "trellis_datamodel.server:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Disable reload in production
        log_level="info",
    )


@app.command(name="serve")
def serve(
    port: int = typer.Option(8089, "--port", "-p", help="Port to run the server on"),
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (trellis.yml or config.yml)"
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't open browser automatically"
    ),
):
    """
    Start the Trellis server (alias for 'run').

    Looks for trellis.yml or config.yml in the current directory.
    """
    # Delegate to run function
    run(port=port, config=config, no_browser=no_browser)


@app.command()
def init():
    """
    Initialize a new trellis.yml config file in the current directory.
    """
    config_file = Path("trellis.yml")
    if config_file.exists():
        typer.echo(
            typer.style(
                "trellis.yml already exists in this directory.", fg=typer.colors.YELLOW
            )
        )
        raise typer.Exit(1)

    default_config = """\
# Trellis configuration
framework: dbt-core
dbt_project_path: "."
dbt_manifest_path: "target/manifest.json"
dbt_catalog_path: "target/catalog.json"
data_model_file: "data_model.yml"
dbt_model_paths: []  # Empty = include all models
"""
    config_file.write_text(default_config)
    typer.echo(typer.style("✓ Created trellis.yml", fg=typer.colors.GREEN))
    typer.echo("  Edit the file to configure your dbt project paths, then run:")
    typer.echo(typer.style("  trellis run", fg=typer.colors.CYAN))


@app.command(name="generate-company-data")
def generate_company_data(
    config: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file (trellis.yml or config.yml)"
    ),
):
    """
    Generate mock commercial company data for modeling exercises.

    Creates CSV files in dbt_company_dummy/data/ directory with realistic
    commercial company data including departments, employees, leads, customers,
    products, orders, and order items.

    The path to the dbt company dummy project can be configured in trellis.yml
    via the 'dbt_company_dummy_path' option (defaults to './dbt_company_dummy').
    """
    import sys
    import importlib.util

    # Load config to get dbt_company_dummy_path
    config_path = config
    if not config_path:
        found_config = find_config_file()
        if found_config:
            config_path = found_config

    if config_path:
        load_config(config_path)

    # Use configured path or fallback to default relative to current working directory
    import os

    if cfg.DBT_COMPANY_DUMMY_PATH:
        generator_path = Path(cfg.DBT_COMPANY_DUMMY_PATH) / "generate_data.py"
    else:
        # Fallback: check current working directory first (for installed packages)
        # This is the most common case when running from repo root
        cwd_dummy_path = Path(os.getcwd()) / "dbt_company_dummy" / "generate_data.py"
        if cwd_dummy_path.exists():
            generator_path = cwd_dummy_path
        else:
            # Try repo root (for development when running from source)
            project_root = Path(__file__).parent.parent
            repo_dummy_path = project_root / "dbt_company_dummy" / "generate_data.py"
            if repo_dummy_path.exists():
                generator_path = repo_dummy_path
            else:
                # Last resort: use current working directory even if it doesn't exist yet
                # (will show helpful error message)
                generator_path = cwd_dummy_path

    if not generator_path.exists():
        import os

        typer.echo(
            typer.style(
                f"Error: Generator script not found at {generator_path}",
                fg=typer.colors.RED,
            )
        )
        typer.echo()
        typer.echo("The generator script should be located at:")
        if cfg.DBT_COMPANY_DUMMY_PATH:
            typer.echo(f"  {cfg.DBT_COMPANY_DUMMY_PATH}/generate_data.py")
            typer.echo()
            typer.echo("This path is configured in your trellis.yml file.")
        else:
            typer.echo(f"  {os.getcwd()}/dbt_company_dummy/generate_data.py")
            typer.echo()
            typer.echo(
                "Make sure you're running this command from the repository root,"
            )
            typer.echo(
                "or configure 'dbt_company_dummy_path' in your trellis.yml file."
            )
        raise typer.Exit(1)

    # Load and run the generator module
    try:
        spec = importlib.util.spec_from_file_location("generate_data", generator_path)
        generator_module = importlib.util.module_from_spec(spec)
        sys.modules["generate_data"] = generator_module
        spec.loader.exec_module(generator_module)

        # Call the main function
        generator_module.main()

        typer.echo()
        typer.echo(
            typer.style(
                "✓ Company dummy data generation completed successfully!",
                fg=typer.colors.GREEN,
            )
        )
    except ImportError as e:
        typer.echo(
            typer.style(
                f"Error: Missing dependency - {e}",
                fg=typer.colors.RED,
            )
        )
        typer.echo(
            "  Install required dependencies with: pip install trellis-datamodel[dbt-example]"
        )
        typer.echo("  Or install directly: pip install pandas faker")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(
            typer.style(
                f"Error generating data: {e}",
                fg=typer.colors.RED,
            )
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

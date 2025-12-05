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
from trellis_datamodel.config import load_config, find_config_file, print_config

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
    is_test_mode = bool(os.environ.get("DATAMODEL_DATA_MODEL_PATH") or os.environ.get("DATAMODEL_TEST_DIR"))
    
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


if __name__ == "__main__":
    app()

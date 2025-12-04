"""
Trellis Data CLI

Command-line interface for running the Trellis Data server.
"""

import typer
import uvicorn
import webbrowser
from pathlib import Path
from typing import Optional

from trellis_datamodel import __version__
from trellis_datamodel.config import load_config, find_config_file, print_config

app = typer.Typer(
    name="trellis-datamodel",
    help="Trellis Datamodel - Visual data model editor for dbt projects",
    add_completion=False,
)


@app.command()
def serve(
    port: int = typer.Option(8089, "--port", "-p", help="Port to run the server on"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file (trellis.yml or config.yml)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
):
    """
    Start the Trellis Data server.
    
    Looks for trellis.yml or config.yml in the current directory.
    """
    # Load configuration
    config_path = config
    if not config_path:
        found_config = find_config_file()
        if not found_config:
            typer.echo(
                typer.style(
                    "Error: No config file found. Looking for trellis.yml or config.yml in current directory.",
                    fg=typer.colors.RED,
                )
            )
            raise typer.Exit(1)
        config_path = found_config
    
    load_config(config_path)
    
    # Print startup info
    typer.echo(typer.style(f"🌿 Trellis Data v{__version__}", fg=typer.colors.GREEN, bold=True))
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


if __name__ == "__main__":
    app()


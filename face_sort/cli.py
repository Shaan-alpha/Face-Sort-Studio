import click
from .app.main import create_app

@click.command()
@click.option('--port', default=8000, help='Port to run the server on.')
@click.option('--host', default='127.0.0.1', help='Host to bind to.')
def main(port, host):
    """Face Sort Studio — Desktop AI Photo Sorter"""
    app = create_app()
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    main()

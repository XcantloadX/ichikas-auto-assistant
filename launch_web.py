"""
IAA Web UI launcher.

Starts the aiohttp WebSocket + HTTP server and (optionally) opens the browser
at http://127.0.0.1:<port>/.

Usage:
    python launch_web.py [--port 18765] [--no-browser]
"""

import argparse
import os
import sys
import threading
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(description='Run IAA Web UI')
    parser.add_argument('--port', type=int, default=18765, help='HTTP/WS server port (default: 18765)')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Server host (default: 127.0.0.1)')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser automatically')
    parser.add_argument('--config', '-c', type=str, default='default', help='Configuration name to use')
    args = parser.parse_args()

    # Override config name before constructing the service
    import iaa.application.service.config_service as config_service_module
    config_service_module.DEFAULT_CONFIG_NAME = args.config

    from iaa.application.service.iaa_service import IaaService
    service = IaaService()

    # Determine static directory (built React app)
    _here = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(_here, 'ui', 'dist')
    if not os.path.isdir(static_dir):
        static_dir = None
        print(
            '[warn] React UI dist not found. Run `cd ui && npm run build` first.\n'
            '       WebSocket endpoint will still be available at '
            f'ws://{args.host}:{args.port}/ws'
        )

    url = f'http://{args.host}:{args.port}/'
    if not args.no_browser and static_dir:
        # Open browser slightly after the server starts
        def _open() -> None:
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()

    print(f'Starting IAA Web UI on {url}')
    from iaa.application.web.server import run_server
    run_server(service, host=args.host, port=args.port, static_dir=static_dir)


if __name__ == '__main__':
    main()

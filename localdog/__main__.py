from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from localdog import __version__
from localdog.proxy import parse_dc_ip_list, proxy_config, run_proxy
from localdog.proxy.config import analyze_zapret_list, load_config


def _setup_logging(verbose: bool, debug: bool = False, log_file: str | None = None) -> None:
    fmt = logging.Formatter("%(asctime)s  %(levelname)-5s  %(message)s",
                            datefmt="%H:%M:%S")
    root = logging.getLogger()
    if debug:
        root.setLevel(logging.DEBUG)
    elif verbose:
        root.setLevel(logging.INFO)
    else:
        root.setLevel(logging.WARNING)
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    root.addHandler(handler)
    if log_file:
        try:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except OSError:
            pass
    logging.getLogger("asyncio").setLevel(logging.WARNING if not debug else logging.DEBUG)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="localdog",
                                     description="LocalDog — MTProto↔WS bridge for Telegram")
    parser.add_argument("--version", action="store_true",
                        help="Show version and exit")
    parser.add_argument("--config", default=None,
                        help="Path to config file")
    parser.add_argument("--no-ui", action="store_true",
                        help="Run as a headless console proxy")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--secret", default=None,
                        help="32-hex secret (auto-generated if absent)")
    parser.add_argument("--dc-ip", action="append", metavar="DC:IP",
                        help="DC routing override; can be repeated")
    parser.add_argument("--api-path", default=None,
                        help="WebSocket API path (default /apiws)")
    parser.add_argument("--ws-timeout", type=float, default=None,
                        help="WebSocket connect timeout in seconds")
    parser.add_argument("--log-file", default=None,
                        help="Write log output to a file")
    parser.add_argument("--zapret-list", default=None,
                        help="Load a Zapret list file for blocked-host analysis")
    parser.add_argument("--zapret-enable", action="store_true",
                        help="Enable Zapret integration")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    load_config(args.config)

    if args.api_path is not None:
        proxy_config.ws_path = args.api_path
    if args.ws_timeout is not None:
        proxy_config.ws_timeout = args.ws_timeout
    if args.zapret_list is not None:
        if not Path(args.zapret_list).exists():
            parser.error(f"--zapret-list path does not exist: {args.zapret_list}")
        proxy_config.zapret_list_path = args.zapret_list
        proxy_config.zapret_enabled = True
        try:
            total, matched, recommended = analyze_zapret_list(args.zapret_list)
            if recommended:
                print(f"Zapret list loaded: {total} entries, {matched} Telegram-related entries.")
            else:
                print(f"Zapret list loaded: {total} entries, no obvious Telegram entries found.")
        except Exception as exc:
            parser.error(str(exc))
    if args.zapret_enable:
        proxy_config.zapret_enabled = True

    if args.host is not None:
        proxy_config.host = args.host
    if args.port is not None:
        proxy_config.port = args.port
    if args.secret is not None:
        if len(args.secret) != 32:
            parser.error("--secret must be 32 hex chars")
        bytes.fromhex(args.secret)
        proxy_config.secret = args.secret
    if args.dc_ip:
        proxy_config.dc_redirects = parse_dc_ip_list(args.dc_ip)
    if args.verbose:
        proxy_config.verbose = True

    logging_configured = False
    if args.no_ui:
        _setup_logging(proxy_config.verbose, args.debug, args.log_file)
        logging_configured = True
        run_proxy()
        return 0

    if args.log_file or args.verbose or args.debug:
        _setup_logging(proxy_config.verbose, args.debug, args.log_file)
        logging_configured = True

    try:
        from localdog.ui.window import run_app
    except ImportError as exc:
        print(f"Qt UI unavailable ({exc}); falling back to --no-ui",
              file=sys.stderr)
        if not logging_configured:
            _setup_logging(proxy_config.verbose, args.debug, args.log_file)
        run_proxy()
        return 0

    if not proxy_config.secret:
        proxy_config.secret = os.urandom(16).hex()
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
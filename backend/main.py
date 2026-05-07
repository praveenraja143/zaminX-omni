"""
main.py — Zamin X CLI Entry Point
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def cmd_server(args):
    import uvicorn
    logger.info("Starting Zamin X API on 0.0.0.0:%d", args.port)
    uvicorn.run("api.app:app", host="0.0.0.0", port=args.port, reload=args.reload)


def main():
    parser = argparse.ArgumentParser(description="Zamin X — Land Litigation Intelligence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp = subparsers.add_parser("server", help="Start FastAPI server")
    sp.add_argument("--port", type=int, default=8000)
    sp.add_argument("--reload", action="store_true")
    sp.set_defaults(func=cmd_server)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

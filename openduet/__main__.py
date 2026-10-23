import argparse
import asyncio
import sys
from pathlib import Path

import uvicorn

from .config import Config
from .server import create_app


def main():
    try:
        return _main()
    except (ValueError, OSError) as error:
        print("OpenDuet: " + str(error), file=sys.stderr)
        raise SystemExit(1) from None


def _main():
    parser = argparse.ArgumentParser(description="OpenDuet self-hosted assistant")
    from importlib.metadata import version

    parser.add_argument("--version", action="version", version="OpenDuet " + version("openduet"))
    parser.add_argument("--config", type=Path, help="Path to openduet.toml")
    commands = parser.add_subparsers(dest="command")
    setup = commands.add_parser("setup", help="Create a private local installation")
    setup.add_argument("--directory", type=Path)
    setup.add_argument("--background", action="store_true", help="Install macOS login services")
    setup.add_argument("--open", action="store_true", help="Open one-use local sign-in")
    for name in ("open", "doctor", "service"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=argparse.SUPPRESS)
        if name == "doctor":
            command.add_argument("--check-model", action="store_true")
        if name == "service":
            command.add_argument("action", choices=["install", "start", "stop", "status", "uninstall"])
    args = parser.parse_args()
    if args.command:
        import json

        from . import installation

        path = args.config or installation.default_directory() / "openduet.toml"
        if args.command == "setup":
            path, config = installation.setup(args.directory)
            if args.background:
                installation.service(path, "install")
            print("Configuration: " + str(path))
            if args.open:
                installation.open_console(config)
            return
        config = Config.load(path)
        if args.command == "open":
            installation.open_console(config)
        elif args.command == "service":
            print(json.dumps(installation.service(path, args.action), indent=2))
        else:
            from .diagnostics import model_probe, readiness
            from .runtime import Runtime
            from .store import Store

            async def check():
                runtime = Runtime(config, Store(config.data_dir))
                try:
                    if args.check_model:
                        await model_probe(runtime, config.default_provider)
                    return readiness(runtime)
                finally:
                    await runtime.close()

            result = asyncio.run(check())
            print(json.dumps(result, indent=2))
            if not result["ready"]:
                raise SystemExit(1)
        return
    config = Config.load(args.config)
    # One worker owns the browser and task queue; multiple workers are intentionally unsupported.
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(config),
            host=config.host,
            port=config.port,
            access_log=False,
            ws_max_size=1_048_576,
            timeout_graceful_shutdown=5,
        )
    )

    asyncio.run(server.serve())


if __name__ == "__main__":
    main()

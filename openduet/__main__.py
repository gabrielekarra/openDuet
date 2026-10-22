import argparse
import asyncio
import os
from pathlib import Path

import uvicorn

from .config import Config
from .server import create_app


def main():
    parser = argparse.ArgumentParser(description="OpenDuet self-hosted assistant")
    parser.add_argument("--config", type=Path, help="Path to openduet.toml")
    parser.add_argument("--parent-pid", type=int, help="Exit when the owning native app exits")
    args = parser.parse_args()
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

    async def serve():
        async def watch_parent():
            while True:
                if os.getppid() != args.parent_pid:
                    server.should_exit = True
                    return
                await asyncio.sleep(0.5)

        monitor = asyncio.create_task(watch_parent()) if args.parent_pid else None
        try:
            await server.serve()
        finally:
            if monitor:
                monitor.cancel()
                await asyncio.gather(monitor, return_exceptions=True)

    asyncio.run(serve())


if __name__ == "__main__":
    main()

import argparse
import asyncio
from pathlib import Path

import uvicorn

from .config import Config
from .server import create_app


def main():
    parser = argparse.ArgumentParser(description="OpenDuet self-hosted assistant")
    parser.add_argument("--config", type=Path, help="Path to openduet.toml")
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

    asyncio.run(server.serve())


if __name__ == "__main__":
    main()

import argparse
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
    uvicorn.run(create_app(config), host=config.host, port=config.port, access_log=False)


if __name__ == "__main__":
    main()

import asyncio
import logging
from trap.app_root.app_root import AppRoot

async def main() :
    logging.basicConfig(level=logging.DEBUG)

    app = AppRoot()
    await app.run_trap()

if __name__ == "__main__":
    asyncio.run(main())
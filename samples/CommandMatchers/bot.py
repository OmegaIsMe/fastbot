from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastbot.bot import FastBot
import logging
import colorlog

fmt = '%(asctime)s [%(levelname)s] %(message)s'
colors = {'*': 'light_blue', '+': 'green', '!': 'yellow', '-': 'red', '!!': 'purple,bg_white'}
fmt_colored = colorlog.ColoredFormatter(f'%(log_color)s{fmt}', datefmt=None, reset=True, log_colors=colors)
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt_colored)
logging.basicConfig(level=logging.INFO, handlers=[console_handler])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Register a websocket adapter to `FastAPI`
    app.add_api_websocket_route('/onebot/v11/ws', FastBot.ws_adapter)

    yield


if __name__ == '__main__':
    (
        FastBot
        # `plugins` parameter will pass to `fastbot.plugin.PluginManager.import_from(...)`
        # the rest arameter will pass to `FastAPI(...)`
        .build(plugins=['plugins'], lifespan=lifespan)
        # Parameter will pass to `uvicorn.run(...)`
        .run(host='0.0.0.0', port=80)
    )

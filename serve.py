# serve.py
import os
import sys
import asyncio
import signal
import contextlib
from aiohttp import web

PORT = int(os.environ.get("PORT", "10000"))
BOT_ENTRY = os.environ.get("BOT_ENTRY", "bot.py")  # можно переопределить, но по умолчанию bot.py

async def health(_):
    return web.Response(text="ok")

async def start_http():
    app = web.Application()
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    # держим HTTP-сервер живым
    while True:
        await asyncio.sleep(3600)

async def run_bot_forever():
    backoff = 1
    while True:
        try:
            proc = await asyncio.create_subprocess_exec(sys.executable, BOT_ENTRY)
            rc = await proc.wait()
            # если бот завершился — подождём чуть-чуть и перезапустим
            await asyncio.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)
        except Exception:
            # на случай редких ошибок при запуске — тоже подождать и снова попробовать
            await asyncio.sleep(min(backoff, 30))
            backoff = min(backoff * 2, 30)

async def main():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    t_http = asyncio.create_task(start_http())
    t_bot = asyncio.create_task(run_bot_forever())

    await stop.wait()

    # аккуратно останавливаемся
    for t in (t_http, t_bot):
        t.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await asyncio.gather(t_http, t_bot)

if __name__ == "__main__":
    asyncio.run(main())

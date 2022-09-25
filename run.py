from app import app
from prisma.utils import async_run

import asyncio

# async def setup():
#     await app.api.create_server(host="0.0.0.0", port=3000)


def run():
    async_run(app.prisma.connect())

    app.api.add_task(app.task_cleaner())
    app.api.add_task(app.daily_message_sender())
    app.api.run(host="0.0.0.0", port=3000)


if __name__ == "__main__":
    run()

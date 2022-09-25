from app import app
from prisma.utils import async_run

import asyncio

import os
from dotenv import load_dotenv

def run():
    load_dotenv()

    async_run(app.prisma.connect())

    app.api.add_task(app.task_cleaner())
    app.api.add_task(app.daily_message_sender())
    app.api.run(host=os.environ.get("APP_HOST"), port=os.environ.get("APP_PORT"))


if __name__ == "__main__":
    run()

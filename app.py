import os
from slack_bolt.async_app import AsyncApp
from prisma import Prisma

from prisma.models import Post
import asyncio

app = AsyncApp( token="xoxb-3924779483874-4020715904659-1ABd2ayLMGlIBxC4HPJefqlD",
                signing_secret="6d5cbac7a0f8958c5e834d67356e8631")

@app.event("app_home_opened")
async def update_home_tab(client, event, logger):
    await Post.prisma().create({
        "data": {
            "title": "My first post",
            "published": True,
    }})

async def main():
    db = Prisma(auto_register=True)
    await db.connect()

if __name__ == "__main__":
    asyncio.run(main())
    app.start(3000)
import os
from slack_bolt.async_app import AsyncApp
from prisma import Prisma

import asyncio

class App(AsyncApp):
    def __init__(self):
        super().__init__(token="xoxb-3924779483874-4020715904659-1ABd2ayLMGlIBxC4HPJefqlD",
                    signing_secret="6d5cbac7a0f8958c5e834d67356e8631")
        self.prisma = Prisma()

app = App()
from app import app
from prisma.utils import async_run

def run():
    async_run(app.prisma.connect())
    app.start(3000)

if __name__ == "__main__":
    run()
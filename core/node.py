import aiohttp
import random
from asyncio import sleep, create_task, CancelledError
import websockets

from core.error import InvaidFile, NoHostAvailable
from logging import getLogger
import re
logger = getLogger(__name__)

class Node:
    def __init__(self):
        self.available_problems: set[str] = set()
        self.backoff = 1
        self.max_backoff = 60
        self.resolve_host = []
        self.node_in_queue = []
        self.websocket_tasks = []

    @staticmethod
    async def ping(hostname, port):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"{hostname}:{port}/version")
            return resp.ok

    async def get_best_node(self):
        if not self.resolve_host:
            return None
        for node in self.resolve_host:
            if node not in self.node_in_queue:
                self.node_in_queue.append(node)
                return node
            if len(self.node_in_queue) == len(self.resolve_host):
                return random.choice(self.resolve_host)

    async def fetch_problems(self, hostname, port):
        if not hostname.startswith("http"):
            hostname = "http://" + hostname
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"{hostname}:{port}/problems")
            if resp.ok:
                problems = await resp.json()
                if not isinstance(problems, list):
                    return None
                for problem in problems:
                    self.available_problems.add(problem)
                return self.available_problems
            return None

    async def connect(self, hostname, port):
        if not hostname.startswith("http"):
            hostname = "http://" + hostname
        if f"{hostname}:{port}" in self.resolve_host:
            return
        async with aiohttp.ClientSession() as session:
            try:
                resp = await session.get(f"{hostname}:{port}/version")
            except aiohttp.ClientConnectorError:
                return False
            if resp.ok:
                h = re.sub(r"https?://", "", hostname)
                self.websocket_tasks.append(create_task(self.__keep_alive__(h, port)))
                self.resolve_host.append(f"{hostname}:{port}")
                return {"version": await resp.text()}
            return False

    async def __keep_alive__(self, hostname, port):
        backoff = self.backoff
        while True:
            try:
                async with websockets.connect(f"ws://{hostname}:{port}/ws") as ws:
                    logger.info(f"Connected to websocket server: {hostname}")
                    while True:
                        try:
                            await ws.send("ping")
                            resp = await ws.recv()
                            logger.debug(f"Servers response: {resp}")
                            await sleep(10)
                        except websockets.exceptions.ConnectionClosed:
                            logger.error(f"Connection closed to {hostname}:{port}")
                            break

            except CancelledError:
                await ws.close()
                break
            except Exception as e:
                logger.error(f"Failed to connect to {hostname}:{port} - {repr(e)}")

            backoff = min(backoff * 2, self.max_backoff)
            if backoff == self.max_backoff:
                await ws.close()
                self.resolve_host.remove(f"{hostname}:{port}")
                break
            jitter = random.uniform(0, 1)
            sleep_time = backoff + jitter

            logger.debug("Reconnecting in %s seconds", sleep_time)
            await sleep(sleep_time)

    async def __close_ws__(self):
        for task in self.websocket_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except CancelledError:
                    pass
        self.websocket_tasks = []

    async def close_connection(self):
        logger.info("Closing all connections")
        await self.__close_ws__()
        self.resolve_host.clear()

    async def submit(self, id: str, problem_id: str = None, module: str = None, file = None):
        if file is None:
            raise InvaidFile()
        if not self.resolve_host:
            raise NoHostAvailable()
        async with aiohttp.ClientSession() as session:

            async with session.get(file) as resp:
                resolve_file = await resp.read()

            form = aiohttp.FormData()
            form.add_field('id', id)
            form.add_field('problem_id', problem_id)
            form.add_field('target_module', module)
            form.add_field('file', resolve_file)

            node = await self.get_best_node()
            if node is None:
                raise NoHostAvailable()

            async with session.post(f"{node}/submit", data=form) as _response:
                response = await _response.json()

                _response = {
                    "id": response['id'],
                    "status": response['status'],
                    "message": response['message'],
                    "code_running_time": response.get('running_time', None)
                }
                self.node_in_queue.remove(node)
                return _response


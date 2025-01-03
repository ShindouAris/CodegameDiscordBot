import aiohttp
import random
from core.error import InvaidFile, NoHostAvailable

class Node:
    def __init__(self):
        self.resolve_host = []

    @staticmethod
    async def ping(hostname, port):
        async with aiohttp.ClientSession() as session:
            resp = await session.get(f"{hostname}:{port}/version")
            return resp.ok

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
                self.resolve_host.append(f"{hostname}:{port}")
                return {"version": await resp.text()}
            return False

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


            async with session.post(f"{random.choice(self.resolve_host)}/submit", data=form) as _response:
                response = await _response.json()

                _response = {
                    "id": response['id'],
                    "status": response['status'],
                    "message": response['message'],
                    "code_running_time": response.get('running_time', None)
                }
                return _response


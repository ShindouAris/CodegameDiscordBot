from __future__ import annotations

import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv
import logging

from core.loader import ProblemHandler
from core.node import Node
import json
from database.database import DataBase

load_dotenv()

logger = logging.getLogger(__name__)       

class ClientUser(commands.AutoShardedBot):
    
    def __init__(self, *args, intents, command_sync_flag, command_prefix: str, **kwargs) -> None:
        super().__init__(*args, **kwargs, intents=intents, command_sync_flags=command_sync_flag, command_prefix=command_prefix)
        self.uptime = disnake.utils.utcnow()
        self.log = logger
        self.codegame_node = Node()
        self.codegame_problem = ProblemHandler()
        self.codegame_database = DataBase(os.environ.get("MONGO_URI"))

    async def connect_node(self):
        hostname = "./hostname.json"
        with open(hostname, "r") as f:
            data = json.load(f)
        for node in data:
            r = await self.codegame_node.connect(node["host"], node["port"])
            if r:
                self.log.info(f"Connected to {node['name']} - Version {r['version']}")
            else:
                self.log.error(f"Failed to connect to {node['name']}")

    async def on_ready(self):
        await self.connect_node()
        logger.info(f"Logged in as {self.user.name} - {self.user.id}")

    async def close(self) -> None:
        await self.codegame_database.close()
        await super().close()

    def load_modules(self):
        modules_dir = "Module"
        for item in os.walk(modules_dir):
            files = filter(lambda f: f.endswith('.py'), item[-1])
            for file in files:
                filename, _ = os.path.splitext(file)
                module_filename = os.path.join(modules_dir, filename).replace('\\', '.').replace('/', '.')
                try:
                    self.reload_extension(module_filename)
                    logger.info(f'Module {file} Đã tải lên thành công')
                except (commands.ExtensionAlreadyLoaded, commands.ExtensionNotLoaded):
                    try:
                        self.load_extension(module_filename)
                        logger.info(f'Module {file} Đã tải lên thành công')
                    except Exception as e:
                        logger.error(f"Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                        continue
                except Exception as e:
                    logger.error(f"Đã có lỗi xảy ra với Module {file}: Lỗi: {repr(e)}")
                    continue

def load():
        logger.info("Booting Client....")
        
        DISCORD_TOKEN = os.environ.get("TOKEN")
        
        intents = disnake.Intents()
        intents.guilds = True # noqa
        intents.message_content = True # noqa
        intents.messages = True # noqa
        intents.members = True # noqa
           
        sync_cfg = True
        command_sync_config = commands.CommandSyncFlags(
                            allow_command_deletion=sync_cfg,
                            sync_commands=sync_cfg,
                            sync_commands_debug=sync_cfg,
                            sync_global_commands=sync_cfg,
                            sync_guild_commands=sync_cfg
                        )

        memberCacheflags = disnake.MemberCacheFlags()
        memberCacheflags.joined = True # noqa
        memberCacheflags.voice = False # noqa
        
        bot  = ClientUser(intents=intents, command_prefix=os.environ.get("PREFIX") or "?", command_sync_flag=command_sync_config, member_cache_flags=memberCacheflags)

        bot.load_modules()
        print("-"*40)
        
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            if  "LoginFailure" in str(e):
                logger.error("An Error occured:", repr(e))

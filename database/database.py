from datetime import datetime

from motor import motor_asyncio
from utils.cache import LRUCache
from bisect import bisect_right
from asyncio import sleep, create_task

def get_current_time() -> int:
    return int(datetime.now().timestamp())

class LRUCacheDatabase(LRUCache):
    def __init__(self):
        super().__init__(capacity=1000, expire_seconds=-1)

    def get_user(self, user_id: int):
        try:
            user = self.get(user_id)
            return user
        except KeyError:
            return None

    def put_user(self, user_id: int, value: dict):
        self.put(user_id, value)

    def get_leaderboard(self):
        try:
            leaderboard = self.get("leaderboard")
            return leaderboard
        except KeyError:
            return None

    def put_leaderboard(self, value: list):
        self.put("leaderboard", value)

    def delete_user(self, user_id: int):
        self.delete(user_id)

LEVEL_LIMIT = 1000
LEVEL_XP_LIMIT = [150]
for i in range(2, LEVEL_LIMIT + 1): LEVEL_XP_LIMIT.append(100 * i + LEVEL_XP_LIMIT[-1])

def get_current_level(exp: int) -> int:
    return bisect_right(LEVEL_XP_LIMIT, exp)

class DataBase(motor_asyncio.AsyncIOMotorClient):
    def __init__(self, host: str):
        super().__init__(host)
        self.db = self.codegame_db["codegame"]
        self.cache: LRUCacheDatabase = LRUCacheDatabase()
        self.last_update_leaderboard = get_current_time()


    async def run_sync_task(self):
        await create_task(self.__sync_user__())
        await create_task(self.__sync_leaderboard__())

    async def __save__(self):
        count = 0
        for userID in self.cache.cache.keys():
            userdata = self.cache.get_user(userID)
            if isinstance(userdata, list):
                continue
            if userdata["synced"]:
                continue
            await self.__update_user__(userID, userdata) # noqa
            userdata["synced"] = True
            count += 1
        if count > 0:
            print(f"Đã cập nhật dữ liệu của {count} người dùng")

    async def __sync_user__(self):
        while True:
            await self.__save__()
            await sleep(600)

    async def __sync_leaderboard__(self):
        while True:
            self.cache.delete("leaderboard")
            await self.get_top_leaderboard()
            await sleep(3600)

    async def close(self):
        await self.__save__()

    async def create_user(self, user_id: int):
        await self.db.insert_one({"user_id": user_id, "pp": 0, "level": 0, "exp": 0})
        self.cache.put_user(user_id, {"user_id": user_id, "pp": 0, "level": 0, "exp": 0})

    async def get_user(self, user_id: int) -> dict | None:
        db = await self.db.find_one({"user_id": user_id})
        if db is None:
            return None
        fetched = {
            "user_id": db["user_id"],
            "pp": db["pp"],
            "level": db["level"],
            "exp": db["exp"],
            "synced": True
        }
        self.cache.put_user(user_id, fetched)
        return fetched

    async def update_user(self, user_id: int, pp: int, exp: int):
        user = self.cache.get_user(user_id)
        if user:
            user.update({"pp": user["pp"] + pp, "exp": user["exp"] + exp, "level": get_current_level(user["exp"] + exp), "synced": False})
        else:
            user = await self.get_user(user_id)
            user.update({"pp": user["pp"] + pp, "exp": user["exp"] + exp, "level": get_current_level(user["exp"] + exp), "synced": False})
            self.cache.put_user(user_id, user)

    async def __update_user__(self, user_id: int, data: dict):
        await self.db.update_one({"user_id": user_id}, {"$set": {"pp": data["pp"], "level": data["level"], "exp": data["exp"]}})

    async def delete_user(self, user_id: int):
        self.cache.delete_user(user_id)
        await self.db.delete_one({"user_id": user_id})

    async def get_top_leaderboard(self, limit: int = 10) -> list:
        leaderboard = self.cache.get_leaderboard()
        if leaderboard is None:
            cursor = self.db.find().sort("pp", -1).limit(limit)
            leaderboard = []
            async for document in cursor:
                leaderboard.append({
                    "user_id": document["user_id"],
                    "pp": document["pp"],
                    "level": document["level"],
                    "exp": document["exp"]
                })
            self.cache.put_leaderboard(leaderboard)
        return leaderboard
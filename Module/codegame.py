from asyncio import sleep

import disnake
from disnake.ext import commands

from database.database import get_current_level
from utils.ClientUser import ClientUser
from utils.cache import LRUCache
import re
from core.ppcalculation import calculate_pp

class TaskStatus(enumerate):
    waiting = "wait"
    running = "run"
    done = "done"

task_status = {
    "wait": "⌛",
    "run": "🏃‍♀️",
    "done":  "✅"
}

level_rating = {
    "Easy": "<:Easy:1322790227357728831>",
    "Medium": "<:Med:1322790241932808202>",
    "Hard": "<:Hard:1322790261956284426>"
}

def embed_builder(problem_name, problem_desc, difficulty, tag, star, testcase):
    embed = disnake.Embed()
    embed.set_author(name=f"{problem_name}")
    txt =   f"""
            > Difficulty: **{level_rating.get(difficulty)}**
            > Tag: **{tag}**
            > Star: **⭐ {star}**
            > Testcase: **{testcase}**
            """
    txt += problem_desc
    embed.set_footer(text="Bài làm của bạn sẽ hết hạn sau 10 phút")
    embed.description = txt
    return embed

def get_execption(msg):
    msg = msg.replace('\n', ' ')
    match = re.search(r"Expected: (.*?) , Got: (.*?) ", msg)
    if match:
        return f"\n```{match.group(0).rstrip(')')}```"
    else: return None

def render_score(id, status, message, qName):
    embed = disnake.Embed()
    embed.description = f"""
                        ### Kết quả chấm cho bài làm có id {id}:
                        > Tên bài: {qName}
                        - {"✅ Đã được chấp thuận" if status == "ACCEPTED" else f"❌ Thất bại ({status})"}
                        - {"✅ Tất cả các testcase đã thông qua" if 'All test cases passed' in message else "❌ Thất bại trên testcase " + message[-1] + get_execption(message) if status == "WRONG_ANSWER" else message}
                        """
    return embed

def render_task(task1, task2, problem_name, codelang):
    embed = disnake.Embed()
    embed.description = f"""
                        ### Đang chấm bài {problem_name}:
                        > Được viết bởi {codelang}
                        - {task_status.get(task1)}: Gửi Bài
                        - {task_status.get(task2)}: Chấm bài
                        """
    return embed

def getch_config(problem_config):
    return problem_config["problem_name"], problem_config['title'], problem_config['difficulty'], problem_config['tag'], problem_config['star'], problem_config["testcase"]

class UserScore:
    def __init__(self, user_id, pp, level, exp, client):
        self.user_id = user_id
        self.pp = pp
        self.level = level
        self.exp = exp
        self.client: ClientUser = client

    def calculation(self, data, level_rating, testcase, wrong_submission):
        pp = calculate_pp(level_rating, testcase, int(data['code_running_time']), wrong_submission)
        self.pp = pp
        self.exp += 10
        self.level = get_current_level(self.exp)
        return pp

    async def sync_db(self):
        await self.client.codegame_database.update_user(self.user_id, self.pp, self.exp)

class UserSession:
    def __init__(self, qid: int, rating: int, testcases: int, title: str, problem_name: str, msgID: int, score: UserScore):
        self.qid = qid
        self.rating = rating
        self.testcases = testcases
        self.problem_title = title
        self.problem_name = problem_name
        self.message_id = msgID
        self.score: UserScore = score
        self.wrong = 0

class SessionCache(LRUCache):
    def __init__(self):
        super().__init__(1000, 600)

    def add_session(self, id, session_data: UserSession):
        self.put(id, session_data)

    def get_session(self, id) -> UserSession | None:
        try:
            return self.get(id)
        except KeyError:
            return None

    def remove_session(self, id):
        self.delete(id)

class CodeGame(commands.Cog):

    def __init__(self, bot):
        self.bot: ClientUser = bot
        self.session: SessionCache = SessionCache()

    @commands.slash_command(name="submit", description="Submit your code", options=[disnake.Option(name="file",
                                                                                                    description="Your source code file",
                                                                                                    type=disnake.OptionType.attachment, required=True),
                                                                                    disnake.Option(name="language", description="Your coding language",
                                                                                                    choices=[disnake.OptionChoice(name="C++ 17", value="c++17"),
                                                                                                            disnake.OptionChoice(name="C++ 98", value="c++98"),
                                                                                                            disnake.OptionChoice(name="C++ 11", value="c++11"),
                                                                                                            disnake.OptionChoice(name="C++", value="c++"),
                                                                                                            disnake.OptionChoice(name="C 17", value="c17"),
                                                                                                            disnake.OptionChoice(name="C 11", value="c11"),
                                                                                                            disnake.OptionChoice(name="C 98", value="c98"),
                                                                                                            disnake.OptionChoice(name="C", value="c"),
                                                                                                            disnake.OptionChoice(name="Python", value="python3")],
                                                                                                    required=True)])
    async def submit_code(self, inter: disnake.AppCmdInter, file: disnake.Attachment, language: str):
        await inter.response.defer(ephemeral=False)
        if file.size > 10000:
            return await inter.edit_original_response("File không đc vượt quá 1MB")
        session = self.session.get(inter.author.id)
        if session is None:
            return await inter.edit_original_response("Bạn chưa tạo session làm bài, hoặc session của bạn đã quá hạn")
        embed = render_task(TaskStatus.running, TaskStatus.waiting, session.problem_title, language)
        await inter.edit_original_response(embed=embed)
        await sleep(3)
        embed = render_task(TaskStatus.done, TaskStatus.running, session.problem_title, language)
        await inter.edit_original_response(embed=embed)
        resp = await self.bot.codegame_node.submit(str(inter.author.id), session.problem_name, language, file.url)
        await inter.edit_original_response(embed=render_score(resp['id'], resp['status'], resp['message'], session.problem_title))

        if resp['status'] != "ACCEPTED":
            session.wrong += 1
            return
        qMsg = inter.bot.get_message(session.message_id)
        try: await qMsg.delete()
        except Exception: pass
        pp = session.score.calculation(resp, session.rating, session.testcases, session.wrong)
        embed = disnake.Embed(title="Chúc mừng, bài làm đã được chấp thuận", color=0x2F3136)
        embed.add_field(name="PP", value=pp)
        embed.add_field(name="exp", value=session.score.exp)
        await inter.send(embed=embed)
        await session.score.sync_db()
        self.session.remove_session(inter.author.id)

    @commands.cooldown(1, 20, commands.BucketType.user)
    @commands.slash_command(name="get_random_problem", description="Get a random problem")
    async def get_random_problem(self, inter: disnake.AppCmdInter):
        await inter.response.defer()
        if self.session.get_session(inter.author.id) is not None:
            return await inter.edit_original_response("Bạn đã có một session khác đang chờ chấm bài, hãy hoàn thành hoặc chờ hết hạn session trước")
        problem = self.bot.codegame_problem.get_random_problem()
        problem_config = self.bot.codegame_problem.get_problem_config(problem)
        problem_desc = self.bot.codegame_problem.get_problem_description(problem)
        name, title, difficulty, tag, star, testcase = getch_config(problem_config)
        embed = embed_builder(title, problem_desc, difficulty, tag, star, testcase)
        db = self.bot.codegame_database.cache.get_user(inter.author.id)
        if db is None:
            db = await self.bot.codegame_database.get_user(inter.author.id)
            if db is None: return await inter.edit_original_response("Bạn chưa đăng ký tài khoản")
        msg = await inter.edit_original_response(embed=embed)
        self.session.put(inter.author.id, UserSession(inter.author.id, star, testcase, title, name, msg.id, UserScore(inter.author.id, db['pp'], db['level'], db['exp'], self.bot)))

    @commands.cooldown(1, 50, commands.BucketType.user)
    @commands.slash_command(name="get_problem", description="Get a problem", options=[disnake.Option(name="difficulty",
                                                                                                        choices=[disnake.OptionChoice(name="Easy", value="easy"),
                                                                                                                disnake.OptionChoice(name="Medium", value="medium"),
                                                                                                                disnake.OptionChoice(name="Hard", value="hard")],
                                                                                                        required=True)])
    async def get_problems(self, inter: disnake.AppCmdInter, difficulty: str):
        await inter.response.defer()
        if self.session.get_session(inter.author.id) is not None:
            return await inter.edit_original_response("Bạn đã có một session khác đang chờ chấm bài, hãy hoàn thành hoặc chờ hết hạn session trước")
        problem = self.bot.codegame_problem.get_problem_by_difficulty(difficulty)
        problem_config = self.bot.codegame_problem.get_problem_config(problem)
        problem_desc = self.bot.codegame_problem.get_problem_description(problem)
        name, title, difficulty, tag, star, testcase = getch_config(problem_config)
        embed = embed_builder(title, problem_desc, difficulty, tag, star, testcase)
        db = self.bot.codegame_database.cache.get_user(inter.author.id)
        if db is None:
            db = await self.bot.codegame_database.get_user(inter.author.id)
            if db is None: return await inter.edit_original_response("Bạn chưa đăng ký tài khoản")
        msg = await inter.edit_original_response(embed=embed)
        self.session.put(inter.author.id, UserSession(inter.author.id, star, testcase, title,name, msg.id, UserScore(inter.author.id, db['pp'], db['level'], db['exp'], self.bot)))

    @commands.cooldown(1, 70, commands.BucketType.user)
    @commands.slash_command(name="set_challenge", description="Create a codegame challenge", options=[disnake.Option(name="difficulty",
                                                                                                                        description="Difficulty of the problem",
                                                                                                                        choices=[disnake.OptionChoice(name="Easy", value="easy"),
                                                                                                                                disnake.OptionChoice(name="Medium", value="medium"),
                                                                                                                                disnake.OptionChoice(name="Hard", value="hard")],
                                                                                                                        required=True),
                                                                                                        disnake.Option(name="number", description="Number of problems",
                                                                                                                        max_value=16, min_value=1,
                                                                                                                        type=disnake.OptionType.integer, required=True)])
    async def set_challenge(self, inter: disnake.ApplicationCommandInteraction, difficulty, number):
        await inter.response.defer()
        await inter.edit_original_response("Chức năng này đang được phát triển")
        pass

    @commands.cooldown(1, 50, commands.BucketType.user)
    @commands.slash_command(name="play_problem", description="Play a problem", options=[disnake.Option(name="problem_name", description="Search problem by name", type=disnake.OptionType.string, required=True)])
    async def play_problem(self, inter: disnake.ApplicationCommandInteraction, problem_name):
        await inter.response.send_message("Chức năng này đang được phát triển")
        pass

    @commands.cooldown(1, 50, commands.BucketType.user)
    @commands.slash_command(name="end_session", description="End your current session")
    async def end_session(self, inter: disnake.AppCmdInter):
        await inter.response.defer()
        if not self.session.get_session(inter.author.id):
            return await inter.edit_original_response("Bạn không có session làm bài nào")
        self.session.remove_session(inter.author.id)
        await inter.edit_original_response("Đã kết thúc session của bạn")

def setup(bot):
    bot.add_cog(CodeGame(bot))

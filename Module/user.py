import disnake
from disnake.ext import commands
from utils.ClientUser import ClientUser

class User(commands.Cog):
    def __init__(self, bot):
        self.bot: ClientUser = bot

    @commands.cooldown(1, 80, commands.BucketType.user)
    @commands.slash_command(name="register", description="Đăng ký tài khoản")
    async def register(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        user = await self.bot.codegame_database.get_user(ctx.author.id)
        if user is not None:
            return await ctx.edit_original_response("Bạn đã đăng ký rồi", delete_after=5)
        await self.bot.codegame_database.create_user(ctx.author.id)
        embed = disnake.Embed(title="Đăng ký thành công", description="Bạn đã đăng ký tài khoản thành công", color=0x2F3136)
        await ctx.edit_original_response(embed=embed)

    @commands.cooldown(1, 80, commands.BucketType.user)
    @commands.slash_command(name="profile", description="Xem thông tin cá nhân")
    async def profile(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        user = self.bot.codegame_database.cache.get_user(ctx.author.id)
        if user is None:
            user = await self.bot.codegame_database.get_user(ctx.author.id)
            if user is None:
                return await ctx.edit_original_response("Bạn chưa đăng ký tài khoản", delete_after=5)
        embed = disnake.Embed(title=f"Thông tin cá nhân của {ctx.author.display_name}", color=0x2F3136)
        embed.add_field(name="Level", value=user['level'])
        embed.add_field(name="PP", value=user['pp'])
        embed.add_field(name="Exp", value=user['exp'])
        await ctx.edit_original_response(embed=embed)

    @commands.cooldown(1, 80, commands.BucketType.user)
    @commands.slash_command(name="leaderboard", description="Xem bảng xếp hạng")
    async def leaderboard(self, ctx: disnake.ApplicationCommandInteraction):
        await ctx.response.defer()
        leaderboard = await self.bot.codegame_database.get_top_leaderboard()
        embed = disnake.Embed(title="Bảng xếp hạng", color=0x2F3136)
        for index, user in enumerate(leaderboard):
            embed.add_field(name=f"{index + 1}. {ctx.bot.get_user(user['user_id']).display_name}", value=f"Level: {user['level']} - PP: {user['pp']}", inline=False)
        await ctx.edit_original_response(embed=embed)

def setup(bot):
    bot.add_cog(User(bot))
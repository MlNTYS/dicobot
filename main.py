import discord
import sqlite3
from discord.ext import commands
from mytoken import Mytoken

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS warnings (
        user_id TEXT PRIMARY KEY,
        warning_1 BOOLEAN DEFAULT FALSE,
        warning_2 BOOLEAN DEFAULT FALSE,
        reason_1 TEXT,
        reason_2 TEXT,
        time_1 DATETIME,
        time_2 DATETIME
    )
''')

# Intents 설정
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # 메시지 콘텐츠 접근 권한 활성화
intents.members = True  # 서버 멤버 정보 접근 권한 활성화

# Bot 초기화
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')


@bot.command()
async def 경고(ctx, uid: int = None):
    # UID를 입력하지 않은 경우
    if uid is None:
        await ctx.send("사용법: `!경고 <UID>`\nUID를 입력하지 않으셨습니다.")
        return

    # 서버에서 UID로 멤버 찾기
    member = ctx.guild.get_member(uid)

    if member:  # 멤버가 존재하면
        embed = discord.Embed(title="유저 정보", color=discord.Color.blue())
        embed.add_field(name="닉네임", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="역할", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]),
                        inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

        await ctx.send(embed=embed)
    else:  # 멤버가 없을 경우
        await ctx.send(f"ID {uid}에 해당하는 유저를 찾을 수 없습니다.")

bot.run(Mytoken)
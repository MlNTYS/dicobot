import discord
import sqlite3
from discord.ext import commands
from mytoken import Mytoken
from datetime import datetime, timezone

conn = sqlite3.connect('users.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS warnings (
        user_id INTEGER PRIMARY KEY,
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
        await ctx.send("사용법: `!경고 <UID>`\nUID를 입력해주세요.")
        return

    # 서버에서 UID로 멤버 찾기
    member = ctx.guild.get_member(uid)

    if member:  # 멤버가 존재하면
        cursor.execute("SELECT warning_1, warning_2, reason_1, reason_2, time_1, time_2 FROM warnings WHERE user_id = ?", (uid,)) #DB에서 유저 결과 가져오기
        result = cursor.fetchone() #결과를 result에 저장

        embed = discord.Embed(title="유저 정보", color=discord.Color.blue())
        embed.add_field(name="닉네임", value=member.display_name, inline=True)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="역할", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]), inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 줄 추가

        #DB 결과로 출력
        if result:
            if result[0]:#bool 데이터
                embed.add_field(name="경고 1:", value=result[2], inline=False)
                embed.add_field(name="일시", value=(datetime.fromtimestamp(result[4] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')), inline=False) #utc 기준으로 시간 변환
            else:#경고 삭감으로 없을 경우
                embed.add_field(name="경고 없음", value=" ", inline=False)

            if result[1]:
                embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 줄 추가
                embed.add_field(name="경고 2:", value=result[3], inline=False)
                embed.add_field(name="일시", value=(datetime.fromtimestamp(result[5] / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')), inline=False)

        else:
            embed.add_field(name="경고 기록 없음", value=" ", inline=False)

        await ctx.send(embed=embed)
    else:  # 멤버가 없을 경우
        await ctx.send(f"ID {uid}에 해당하는 유저를 찾을 수 없습니다.")

bot.run(Mytoken)
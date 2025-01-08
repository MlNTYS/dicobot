import discord
import sqlite3
from discord.ext import commands
from torch.autograd import set_detect_anomaly

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
intents.reactions = True  # 반응 처리 관련 접근 권한 활성화

# Bot 초기화
bot = commands.Bot(command_prefix='!', intents=intents)

# 관리자 권한 확인을 위한 데코레이터
def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

#utc 기준으로 시간 변환
def formattime(dbtime):
    return datetime.fromtimestamp(dbtime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')


@bot.command()
@is_admin() #관리자 권한 확인
async def 경고(ctx, uid: int = None):
    # UID를 입력하지 않은 경우
    if uid is None:
        await ctx.send("사용법: `!경고 <UID>`\nUID를 입력해주세요.")
        return

    # 서버에서 UID로 멤버 찾기
    member = ctx.guild.get_member(uid)

    if member:  # 멤버가 존재하면
        warnflag = 0 #유저 정보에 반응 추가를 위한 flag

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
                embed.add_field(name="일시", value=formattime(result[4]), inline=False)
                warnflag = 1
            else:#경고 삭감으로 없을 경우
                embed.add_field(name="경고 없음", value=" ", inline=False)
                warnflag = 0

            if result[1]:
                embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 줄 추가
                embed.add_field(name="경고 2:", value=result[3], inline=False)
                embed.add_field(name="일시", value=formattime(result[5]), inline=False)
                warnflag = 2

        else:
            embed.add_field(name="경고 기록 없음", value=" ", inline=False)
            warnflag = 0

        await ctx.send(embed=embed)

        msg = await ctx.send("원하는 행동을 선택해 주세요 (경고 추가/각감, 유저 추방)") # 메시지 보내기
        match warnflag: #warnflaf에 맞게 반응 추가
            case 0:
                await msg.add_reaction("\U00002B06")  #경고 추가
            case 1:
                await msg.add_reaction("\U00002B07")  #경고 삭감
                await msg.add_reaction("\U00002B06")  #경고 추가
            case 2:
                await msg.add_reaction("\U00002B07")  #경고 삭감
                await msg.add_reaction("\U0001F6AB") #유저 추방

    else:  # 멤버가 없을 경우
        await ctx.send(f"ID {uid}에 해당하는 유저를 찾을 수 없습니다.")

bot.run(Mytoken)
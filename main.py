import discord
import sqlite3
import asyncio
from discord.ext import commands
from mytoken import Mytoken
from datetime import datetime, timezone, timedelta

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
intents.guilds = True # 권한 처리 관련 접근 권한 활성화

# Bot 초기화
bot = commands.Bot(command_prefix='!', intents=intents)

warn_role1 = None
warn_role2 = None

# 관리자 권한 확인을 위한 데코레이터
def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

#utc 기준으로 시간 변환
def formattime(dbtime):
    return datetime.fromtimestamp(dbtime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

# 유저 정보 표시
async def display_user_info(ctx, member, uid):
    cursor.execute("SELECT warning_1, warning_2, reason_1, reason_2, time_1, time_2 FROM warnings WHERE user_id = ?", (uid,)) # DB에서 유저 결과 가져오기
    result = cursor.fetchone() # 결과를 result에 저장

    embed = discord.Embed(title="유저 정보", color=discord.Color.blue())
    embed.add_field(name="닉네임", value=member.display_name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="역할", value=", ".join([role.name for role in member.roles if role.name != "@everyone"]), inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 줄 추가

    # DB 결과로 출력
    if result:
        if result[0]:  # bool 데이터
            embed.add_field(name="경고 1:", value=result[2], inline=False)
            embed.add_field(name="일시", value=formattime(result[4]), inline=False)
        else: # 경고 삭감으로 없을 경우
            embed.add_field(name="경고 1:", value="없음", inline=False)

        if result[1]:
            embed.add_field(name="\u200b", value="\u200b", inline=False)  # 빈 줄 추가
            embed.add_field(name="경고 2:", value=result[3], inline=False)
            embed.add_field(name="일시", value=formattime(result[5]), inline=False)
    else:
        embed.add_field(name="경고 기록", value="없음", inline=False)

    await ctx.send(embed=embed)

# 최종 확인
async def confirm_action(ctx, action_desc):
    confirm_msg = await ctx.send(f"{action_desc} 하시겠습니까?.")
    await confirm_msg.add_reaction("\U00002705")
    await confirm_msg.add_reaction("\U0000274C")

    def check(con_reaction, user):
        return user == ctx.author and str(con_reaction.emoji) in ["\U00002705", "\U0000274C"] and con_reaction.message.id == confirm_msg.id

    try:
        reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        await confirm_msg.delete()
        if str(reaction.emoji) == "\U00002705":
            return True
        else:
            await ctx.send("작업이 취소되었습니다.")
            return False
    except asyncio.TimeoutError:
        await confirm_msg.delete()
        await ctx.send("시간 초과로 인해 작업이 취소되었습니다.")
        return False

async def add_warning(ctx, uid, warnflag, member):
    # 경고 사유 요청
    ask_message = await ctx.send("경고 부여 사유를 입력해주세요. (3분)")

    # 사용자 입력 대기 (3분)
    try:
        reason_msg = await bot.wait_for(
            'message',
            timeout=180,
            check=lambda message: message.author == ctx.author and message.channel == ctx.channel
        )
        reason = reason_msg.content

        # 입력 메시지 및 요청 메시지 삭제
        await ask_message.delete()
        await reason_msg.delete()

    except asyncio.TimeoutError:
        await ctx.send("시간 초과로 인해 경고 부여가 취소되었습니다.")
        return

    current_time = int((datetime.now(timezone.utc) + timedelta(hours=9)).timestamp() * 1000) # 경고 부여 시간(밀리초, 한국시 기준)

    if warnflag == 0:  # 경고가 0개 일때 추가
        action_desc = f"ID {uid}에 해당하는 유저에 경고(1)을 추가.\n사유: {reason}"
        if not await confirm_action(ctx, action_desc):
            return

        await member.add_roles(warn_role1)  # 경고(1) 추가

        # DB 업데이트
        cursor.execute("INSERT OR REPLACE INTO warnings (user_id, warning_1, reason_1, time_1) VALUES (?, ?, ?, ?)",
                       (uid, True, reason, current_time))
        conn.commit()

        await ctx.send(f"ID {uid}에 해당하는 유저에 경고(1) 추가 완료.")
    else:  # 경고가 1개 일때 추가
        action_desc = f"ID {uid}에 해당하는 유저에 경고(2)을 추가.\n사유: {reason}"
        if not await confirm_action(ctx, action_desc):
            return

        await member.add_roles(warn_role2)  # 경고(2) 추가

        cursor.execute("UPDATE warnings SET warning_2 = TRUE, reason_2 = ?, time_2 = ? WHERE user_id = ?",(reason, current_time, uid,))
        conn.commit()

        await ctx.send(f"ID {uid}에 해당하는 유저에 경고(2) 추가 완료.")

        # 작업 완료 후 사용자 정보 다시 표시
    await display_user_info(ctx, member, uid)

async def reduce_warning(ctx, uid, warnflag, member):
    if warnflag == 2:  # 경고가 2개 일때 삭감
        action_desc = f"ID {uid}에 해당하는 유저의 경고(2)를 삭감."
    else:  # 경고가 1개 일때 삭감
        action_desc = f"ID {uid}에 해당하는 유저의 경고(1)를 삭감."

    if not await confirm_action(ctx, action_desc):
        return

    if warnflag == 2:  # 경고가 2개 일때 삭감
        await member.remove_roles(warn_role2)  # 경고(2) 빼기

        # DB 업데이트
        cursor.execute("UPDATE warnings SET warning_2 = FALSE WHERE user_id = ?", (uid,))
        conn.commit()

        await ctx.send(f"ID {uid}에 해당하는 유저의 경고(2) 삭감 완료.")
    else:  # 경고가 1개 일때 삭감
        await member.remove_roles(warn_role1)  # 경고(1) 빼기

        cursor.execute("UPDATE warnings SET warning_1 = FALSE WHERE user_id = ?", (uid,))
        conn.commit()

        await ctx.send(f"ID {uid}에 해당하는 유저의 경고(1) 삭감 완료.")

        # 작업 완료 후 사용자 정보 다시 표시
    await display_user_info(ctx, member, uid)

async def ban_user(ctx, uid):
    await ctx.send(f"추방은 리스크 문제로 봇에서 지원하지 않습니다. 수동으로 {uid}에 해당하는 유저를 추방해 주세요.")

@bot.event
async def on_ready():
    global warn_role1, warn_role2  # 전역 변수로 접근

    # 봇 실행 시 경고 1,2 role를 찾아 저장하기
    for guild in bot.guilds:
        warn_role1 = discord.utils.get(guild.roles, name="경고(1)")
        warn_role2 = discord.utils.get(guild.roles, name="경고(2)")
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
        warnflag = 0 # 유저 정보에 반응 추가를 위한 flag

        def check(reaction, user): # 확인에서의 딜레이 최소화를 위해 유저가 기다릴 수 있는 확인 단계에서 def
            # 반응이 지정된 이모지 중 하나이며 메시지를 보낸 유저만 체크
            return (
                    user == ctx.author
                    and str(reaction.emoji) in ["\U00002B06", "\U00002B07", "\U0001F6AB"]
                    and reaction.message.id == msg.id
            )

        cursor.execute(
            "SELECT warning_1, warning_2, reason_1, reason_2, time_1, time_2 FROM warnings WHERE user_id = ?",
            (uid,))  # DB에서 유저 결과 가져오기
        result = cursor.fetchone()  # 결과를 result에 저장

        if result:
            if result[0]:  # 경고 1
                warnflag = 1
            if result[1]:  # 경고 2
                warnflag = 2

        # 유저 정보 표시
        await display_user_info(ctx, member, uid)

        msg = await ctx.send("원하는 행동을 선택해 주세요 60초...(경고 추가/삭감, 유저 추방)") # 메시지 보내기
        match warnflag: # warnflaf에 맞게 반응 추가
            case 0:
                await msg.add_reaction("\U00002B06")  # 경고 추가
            case 1:
                await msg.add_reaction("\U00002B06")  # 경고 추가
                await msg.add_reaction("\U00002B07")  # 경고 삭감
            case 2:
                await msg.add_reaction("\U00002B07")  # 경고 삭감
                await msg.add_reaction("\U0001F6AB") # 유저 추방

        try:
            # 반응 대기 (timeout: 60초)
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)

            # 반응 이후 메시지 삭제
            await msg.delete()

            # 선택된 반응에 따른 기능 실행
            match str(reaction.emoji):
                case "\U00002B06":  # 경고 추가
                    await add_warning(ctx, uid, warnflag, member)
                case "\U00002B07":  # 경고 삭감
                    await reduce_warning(ctx, uid, warnflag, member)
                case "\U0001F6AB":  # 유저 추방
                    await ban_user(ctx, uid)
        except asyncio.TimeoutError:
            # 시간 초과 시 메시지 삭제
            await msg.delete()
            await ctx.send("시간 초과되었습니다. 다시 시도해 주세요.")

    else:  # 멤버가 없을 경우
        await ctx.send(f"ID {uid}에 해당하는 유저를 찾을 수 없습니다.")

bot.run(Mytoken)
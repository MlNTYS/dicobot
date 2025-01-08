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

# Bot 초기화
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Login bot: {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send('Hi!')

bot.run(Mytoken)
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from core.channel_store import load_channels

load_dotenv() # 載入 .env 檔案中的變數


class IsNcuDownBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="$", intents=intents)

    async def setup_hook(self):
        # 自動載入 cogs 資料夾下的所有 .py 檔
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'已載入模組: {filename}')

        await self.tree.sync()
        print('已同步斜線指令')

    async def broadcast(self, embed: discord.Embed):
        """發送到所有已註冊的通知頻道"""
        for channel_id in load_channels():
            channel = self.get_channel(channel_id)
            try:
                if channel is None:
                    channel = await self.fetch_channel(channel_id)
                await channel.send(embed=embed)
            except discord.DiscordException as e:
                print(f"通知頻道 {channel_id} 發送失敗: {e}")

    async def on_ready(self):
        print(f'機器人 {self.user} 已上線！')


bot = IsNcuDownBot()
bot.run(os.getenv("DISCORD_TOKEN"))

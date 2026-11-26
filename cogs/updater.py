import asyncio
import discord
from discord.ext import commands
from core.version import VERSION, load_saved_version, save_version, changes_since


class Updater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self.announce_update())

    async def announce_update(self):
        """啟動時比對 data 裡的版本，不一致就公告更新內容"""
        await self.bot.wait_until_ready()
        old = load_saved_version()
        if old == VERSION:
            return

        embed = discord.Embed(
            title=f":arrows_counterclockwise: 我更新了！ v{VERSION}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        for version, changes in changes_since(old):
            embed.add_field(
                name=f"v{version}",
                value="\n".join(f"• {c}" for c in changes),
                inline=False,
            )
        await self.bot.broadcast(embed)
        save_version()
        print(f"版本更新 {old} -> {VERSION}，已公告")


async def setup(bot):
    await bot.add_cog(Updater(bot))

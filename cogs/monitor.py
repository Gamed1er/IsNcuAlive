import json
import asyncio
import discord
from datetime import datetime
from discord.ext import commands, tasks
from discord import app_commands
from core.site_checker import SiteState, ping, ping_once, new_session, format_duration
from core.channel_store import load_channels, toggle_channel

WEB_LIST_PATH = "web_list.json"
GOOGLE_URL = "https://www.google.com"


class Monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sites: list[SiteState] = []
        self.session = None

    async def cog_load(self):
        with open(WEB_LIST_PATH, "r", encoding="utf-8") as f:
            self.sites = [SiteState(s["name"], s["url"]) for s in json.load(f)]
        self.session = new_session()
        self.passive_check.start()

    async def cog_unload(self):
        self.passive_check.cancel()
        if self.session:
            await self.session.close()

    async def broadcast(self, embed: discord.Embed):
        """發送到所有已註冊的通知頻道"""
        for channel_id in load_channels():
            channel = self.bot.get_channel(channel_id)
            try:
                if channel is None:
                    channel = await self.bot.fetch_channel(channel_id)
                await channel.send(embed=embed)
            except discord.DiscordException as e:
                print(f"通知頻道 {channel_id} 發送失敗: {e}")

    # ---------- 被動偵測 ----------
    @tasks.loop(minutes=1)
    async def passive_check(self):
        # 先確認自己的網路沒問題，連 google 都連不上就不檢查
        if not (await ping(self.session, GOOGLE_URL)).ok:
            print(f"[{datetime.now():%F %T}] Google 無回應，略過本次檢查")
            return

        results = await asyncio.gather(*(ping(self.session, s.url) for s in self.sites))
        now = datetime.now()

        for site, result in zip(self.sites, results):
            was_up = site.is_up
            site.is_up = result.ok

            if not result.ok and was_up is not False:
                # 剛炸 (或機器人剛啟動就是炸的)
                site.down_since = now
                await self.notify_down(site, result.error)
            elif result.ok and was_up is False:
                downtime = (now - site.down_since).total_seconds() if site.down_since else 0
                site.down_since = None
                await self.notify_up(site, downtime)

    @passive_check.before_loop
    async def before_passive_check(self):
        await self.bot.wait_until_ready()

    async def notify_down(self, site: SiteState, reason):
        embed = discord.Embed(
            title=f":boom: {site.name} 炸了",
            description=f"又來了，[{site.name}]({site.url}) 連不上 :upside_down:",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        if reason:
            embed.add_field(name="原因", value=reason)
        await self.broadcast(embed)

    async def notify_up(self, site: SiteState, downtime: float):
        embed = discord.Embed(
            title=f":sparkles: {site.name} 復活了",
            description=f"[{site.name}]({site.url}) 這次炸了 **{format_duration(downtime)}**",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        await self.broadcast(embed)

    # ---------- 主動偵測 ----------
    @app_commands.command(name="is_ncu_alive", description="立刻檢查所有中央大學網站是否還活著")
    @app_commands.checks.cooldown(1, 10, key=lambda i: 0)  # 整個機器人共用 10 秒冷卻
    async def is_ncu_alive(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        results = await asyncio.gather(*(ping_once(self.session, s.url) for s in self.sites))

        all_up = all(r.ok for r in results)
        embed = discord.Embed(
            title="NCU 還活著嗎？",
            description="今天居然都活著 :tada:" if all_up else "果然有東西炸了 :fire:",
            color=discord.Color.green() if all_up else discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        for site, r in zip(self.sites, results):
            if r.ok:
                value = f":green_circle: 正常｜{r.latency_ms:.0f} ms"
            else:
                value = f":red_circle: 連接失敗｜{r.error}"
            embed.add_field(name=site.name, value=f"{value}\n{site.url}", inline=False)

        await interaction.followup.send(embed=embed)

    # ---------- 頻道註冊 ----------
    @app_commands.command(name="notify_channel_register", description="讓這個頻道接收 / 不再接收網站炸裂通知")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def notify_channel_register(self, interaction: discord.Interaction):
        if toggle_channel(interaction.channel_id):
            await interaction.response.send_message(":loud_sound: 這個頻道現在會收到 NCU 炸裂通知")
        else:
            await interaction.response.send_message(":mute: 這個頻道不再收到 NCU 炸裂通知")

    async def cog_app_command_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f":hourglass: 冷卻中，請 {error.retry_after:.1f} 秒後再試", ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                ":negative_squared_cross_mark: 權限不足：只有管理員可以執行此指令", ephemeral=True
            )
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Monitor(bot))

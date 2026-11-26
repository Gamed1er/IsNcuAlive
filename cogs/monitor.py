import json
import asyncio
import discord
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import app_commands
from core.site_checker import SiteState, ping, ping_once, new_session, format_duration
from core.channel_store import toggle_channel
from core.outage_log import open_records, start_outage, mark_notified, end_outage

WEB_LIST_PATH = "web_list.json"
GOOGLE_URL = "https://www.google.com"
NOTIFY_THRESHOLD = timedelta(minutes=5)  # 炸超過這麼久才發通知


class Monitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sites: list[SiteState] = []
        self.session = None

    async def cog_load(self):
        with open(WEB_LIST_PATH, "r", encoding="utf-8") as f:
            self.sites = [SiteState(s["name"], s["url"]) for s in json.load(f)]

        # 從當機紀錄還原重啟前還沒結束的當機
        unfinished = open_records()
        for site in self.sites:
            record = unfinished.get(site.url)
            if record:
                site.is_up = False
                site.down_since = datetime.fromisoformat(record["start"])
                site.notified = record["notified"]

        self.session = new_session()
        self.passive_check.start()

    async def cog_unload(self):
        self.passive_check.cancel()
        if self.session:
            await self.session.close()

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
            if not result.ok:
                if site.is_up is not False:
                    # 剛炸，先記錄，等超過門檻再通知
                    site.is_up = False
                    site.down_since = now
                    site.notified = False
                    start_outage(site.name, site.url, now, result.error)

                if not site.notified and now - site.down_since >= NOTIFY_THRESHOLD:
                    site.notified = True
                    mark_notified(site.url)
                    await self.notify_down(site, result.error, (now - site.down_since).total_seconds())

            elif site.is_up is False:
                # 復活了，只有發過「炸了」通知的才發「復活了」
                end_outage(site.url, now)
                if site.notified:
                    await self.notify_up(site, (now - site.down_since).total_seconds())
                site.is_up = True
                site.down_since = None
                site.notified = False

            else:
                site.is_up = True

    @passive_check.before_loop
    async def before_passive_check(self):
        await self.bot.wait_until_ready()

    async def notify_down(self, site: SiteState, reason, downtime: float):
        embed = discord.Embed(
            title=f":boom: {site.name} 炸了",
            description=f"又來了，[{site.name}]({site.url}) 已經連不上 **{format_duration(downtime)}** :upside_down:",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        if reason:
            embed.add_field(name="原因", value=reason)
        await self.bot.broadcast(embed)

    async def notify_up(self, site: SiteState, downtime: float):
        embed = discord.Embed(
            title=f":sparkles: {site.name} 復活了",
            description=f"[{site.name}]({site.url}) 這次炸了 **{format_duration(downtime)}**",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )
        await self.bot.broadcast(embed)

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

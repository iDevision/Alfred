# IMPORTS
import discord
import json
import datetime
import aiohttp
import asyncpg

from discord.ext import commands
from utils.views import AccessRoles, CharlesNews, ApiNews, GamesNews

print('[CONNECT] Logging in...')

class CTX(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

class Alfred(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", 
            reconnect=True, 
            case_insensitive=True, 
            intents=discord.Intents.all(),
            member_cache_flags=discord.MemberCacheFlags.all(),
            owner_ids=[171539705043615744, 547861735391100931],
            slash_command_guilds=[514232441498763279])

        # Bot vars
        self.requests = {}

        with open("config.json") as f:
            self.config = json.load(f)
        
        for ext in ['cogs.help', 'cogs.owner', 'jishaku', 'cogs.devision', 'cogs.tags', 'cogs.reports']:
            self.load_extension(ext)

    async def on_message(self, msg):
        if not self.is_ready() or msg.author.bot:
            return

        await self.process_commands(msg)

    async def on_ready(self):
        print(f'[CONNECT] Logged in as:\n{self.user} (ID: {self.user.id})\n')

        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

    async def setup(self):
        self.add_view(AccessRoles())
        self.add_view(CharlesNews())
        self.add_view(GamesNews())
        self.add_view(ApiNews())

        await super().setup()

    def run(self):
        loop = self.loop
        try:
            loop.run_until_complete(self.bot_start())
        except KeyboardInterrupt:
            loop.run_until_complete(self.bot_logout())


    async def bot_logout(self):
        await self.session.close()
        await self.db.close()
        await super().close()

    async def bot_start(self):
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.db = await asyncpg.create_pool(dsn=self.config['db'])
        await self.login(self.config['token'])
        await self.setup()
        await self.connect()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=CTX)

Alfred().run()

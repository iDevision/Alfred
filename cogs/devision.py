import discord
import time
import re
import os
from io import BytesIO
import zlib
from discord.ext import commands
from utils.views import Paginator
from discord import ui

class SphinxObjectFileReader:
    # Inspired by Sphinx's InventoryFileReader
    BUFSIZE = 16 * 1024

    def __init__(self, buffer):
        self.stream = BytesIO(buffer)

    def readline(self):
        return self.stream.readline().decode('utf-8')

    def skipline(self):
        self.stream.readline()

    def read_compressed_chunks(self):
        decompressor = zlib.decompressobj()
        while True:
            chunk = self.stream.read(self.BUFSIZE)
            if len(chunk) == 0:
                break
            yield decompressor.decompress(chunk)
        yield decompressor.flush()

    def read_compressed_lines(self):
        buf = b''
        for chunk in self.read_compressed_chunks():
            buf += chunk
            pos = buf.find(b'\n')
            while pos != -1:
                yield buf[:pos].decode('utf-8')
                buf = buf[pos + 1:]
                pos = buf.find(b'\n')


def finder(text, collection, *, key=None, lazy=True):
    suggestions = []
    text = str(text)
    pat = '.*?'.join(map(re.escape, text))
    regex = re.compile(pat, flags=re.IGNORECASE)
    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            suggestions.append((len(r.group()), r.start(), item))

    def sort_key(tup):
        if key:
            return tup[0], tup[1], key(tup[2])
        return tup

    if lazy:
        return (z for _, _, z in sorted(suggestions, key=sort_key))
    else:
        return [z for _, _, z in sorted(suggestions, key=sort_key)]

class Devision(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slashurl = "https://discord.com/api/v9/applications/638493797575163953/guilds/514232441498763279/commands"
        self.headers = {
            "Authorization": f"Bot {self.bot.http.token}",
            "Content-Type": "application/json"
        }

    def parse_object_inv(self, stream, url):
        # key: URL
        # n.b.: key doesn't have `discord` or `discord.ext.commands` namespaces
        result = {}

        # first line is version info
        inv_version = stream.readline().rstrip()

        if inv_version != '# Sphinx inventory version 2':
            raise RuntimeError('Invalid objects.inv file version.')

        # next line is "# Project: <name>"
        # then after that is "# Version: <version>"
        projname = stream.readline().rstrip()[11:]
        version = stream.readline().rstrip()[11:]  # noqa: F841

        # next line says if it's a zlib header
        line = stream.readline()
        if 'zlib' not in line:
            raise RuntimeError('Invalid objects.inv file, not z-lib compatible.')

        # This code mostly comes from the Sphinx repository.
        entry_regex = re.compile(r'(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)')
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(':')
            if directive == 'py:module' and name in result:
                # From the Sphinx Repository:
                # due to a bug in 1.1 and below,
                # two inventory entries are created
                # for Python modules, and the first
                # one is correct
                continue

            # Most documentation pages have a label
            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if dispname == '-' else dispname
            prefix = f'{subdirective}:' if domain == 'std' else ''

            if projname == 'discord.py':
                key = key.replace('discord.ext.commands.', '').replace('discord.', '').replace('ext.menus.', '')

            result[f'{prefix}{key}'] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self, page_types):
        cache = {}
        for key, page in page_types.items():
            cache[key] = {}
            async with self.bot.session.get(page + '/objects.inv') as resp:
                if resp.status != 200:
                    raise RuntimeError('Cannot build rtfm lookup table, try again later.')

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx, key, obj):
        page_types = {
            'python': 'https://docs.python.org/3',
            'enhanced-dpy': 'https://enhanced-dpy.readthedocs.io/en/latest',
        }

        if obj is None:
            await ctx.send(page_types[key])
            return

        if not hasattr(self, '_rtfm_cache'):
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(page_types)

        obj = re.sub(r'^(?:discord\.(?:ext\.)?)?(?:commands\.)?(.+)', r'\1', obj)

        if key.startswith('latest'):
            # point the abc.Messageable types properly:
            q = obj.lower()
            for name in dir(discord.abc.Messageable):
                if name[0] == '_':
                    continue
                if q == name:
                    obj = f'abc.Messageable.{name}'
                    break

        cache = list(self._rtfm_cache[key].items())

        matches = finder(obj, cache, key=lambda t: t[0], lazy=False)[:8]

        if len(matches) == 0:
            return await ctx.send('Could not find anything. Sorry.')

        e = discord.Embed(colour=0x2F3136, title=f"RTFM Search: `{obj}`")
        e.set_author(icon_url=ctx.guild.icon.url, name=f"Docs: {key}", url=page_types[key])
        e.set_thumbnail(url="https://readthedocs-static-prod.s3.amazonaws.com/images/home-logo.eaeeed28189e.png")
        e.description = '\n'.join(f'[`{key}`]({url})' for key, url in matches)
        await ctx.send(embed=e)
        
    @commands.Cog.listener('on_message')
    async def publish_datamine(self, message):
        if message.channel.id != 841654142250254336:
            return
        try:
            await message.publish()
        except Exception:
            return

    async def get_tag_data(self, ctx, name_or_id):
        if name_or_id.isdigit():
            data = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_id = $1 AND aliases IS NULL", int(name_or_id))
            if not data:
                await ctx.send("No tag was found with that ID!")
        else:
            data = await self.bot.db.fetchrow("SELECT * FROM tags WHERE LOWER(name) = $1", discord.utils.escape_mentions(name_or_id).lower())
            if not data:
                await ctx.send("No tag was found with that name!")
        
        if data:
            if alias := data.get('aliases'):
                data = await self.bot.db.fetchrow("SELECT * FROM tags WHERE name = $1", alias)
        
        return data

    @commands.command()
    async def tags(self, ctx, member: discord.Member = None):
        await ctx.invoke(self.tag_list, member=member)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name_or_id: str.lower):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return

        await ctx.send(data['content'], reference=ctx.replied_reference)

    # @commands.is_owner()
    @tag.command(name="add", aliases=['create', 'make'])
    async def tag_add(self, ctx, name: str, *, content: str):
        name = discord.utils.escape_mentions(name)
        check = await self.bot.db.fetchval("SELECT tag_id FROM tags WHERE LOWER(name) = $1", name.lower())
        if check:
            return await ctx.send("A tag with that name already exists!")
        if name.split(' ')[0] in ('add', 'delete', 'del', 'info', 'owner', 
            'stats', 'leaderboard', 'lb', 'claim', 'raw', 'transfer',
            'list', 'search', 'edit', 'alias', 'make', 'create'):
                return await ctx.send("Tag name starts with a reserved word!")
        if name.isdigit():
            return await ctx.send("Tag names may not be numerical only!")
        clean_content = discord.utils.escape_mentions(content)
        if len(clean_content) == 0 or len(clean_content) > 2000:
            return await ctx.send("Tag content must be between 0-2000 characters!")
        await self.bot.db.execute("INSERT INTO tags VALUES($1, $2, $3, (NOW() AT TIME ZONE 'utc'))", name, clean_content, ctx.author.id, int(time.time()))
        await ctx.send("Tag is successfully created!")

    @tag.command(name="delete", aliases=['del'])
    async def tag_delete(self, ctx, name_or_id: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        if data['owner_id'] != ctx.author.id:
            return await ctx.send("You do not own this tag!")
        await self.bot.db.execute("DELETE FROM tags WHERE name = $1", data['name'])
        await ctx.send(f"Tag `[#{data['tag_id']}]` **{data['name']}** has been deleted!")

    @tag.command(name="info", aliases=['owner'])
    async def tag_info(self, ctx, name_or_id: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        await ctx.send("COMING SOON")

    @tag.command(name="stats", aliases=['leaderboard', 'lb'])
    async def tag_stats(self, ctx):
        await ctx.send("COMING SOON")
    
    @tag.command(name="claim")
    async def tag_claim(self, ctx, name_or_id: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        await ctx.send("COMING SOON")

    @tag.command(name="raw")
    async def tag_raw(self, ctx, *, name_or_id: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        await ctx.send(discord.utils.escape_markdown(data['content']).replace("<", "\\<"), reference=ctx.replied_reference)

    @tag.command(name="transfer")
    async def tag_transfer(self, ctx, member: discord.Member, *, name_or_id: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        await ctx.send("COMING SOON")

    @tag.command(name="list")
    async def tag_list(self, ctx, member: discord.Member = None):
        if member:
            tags = await self.bot.db.fetch("SELECT tag_id, name FROM tags WHERE owner_id = $1", member.id)
        else:
            tags = await self.bot.db.fetch("SELECT tag_id, name FROM tags")
        pages = Paginator(ctx,
                          title=f"Tags by: {member}" if member else "All tags",
                          entries=[f"[**#{x['tag_id']}**] {x['name']}" for x in tags],
                          per_page=15)
        await pages.start()

    @tag.command(name="search")
    async def tag_search(self, ctx, query: str):
        if len(query) < 4:
            return await ctx.send("Search query must be at least 4 characters!")

        tags = await self.bot.db.fetch("SELECT tag_id, name FROM tags WHERE SIMILARITY(name, $1) > 0.75 ORDER BY similarity(name, $1) DESC LIMIT 150", query)
        pages = Paginator(ctx,
                          entries=[f"[**#{x['tag_id']}**] {x['name']}" for x in tags],
                          show_entry_num=True,
                          per_page=15)
        await pages.start()


    @tag.command(name="edit")
    async def tag_edit(self, ctx, name_or_id: str, *, new_content: str):
        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        if data.get('alias'):
            data = await self.get_tag_data(ctx, data['alias'])
        if data['owner_id'] != ctx.author.id:
            return await ctx.send("You do not own this tag!")

        clean_content = discord.utils.escape_mentions(new_content)
        if len(clean_content) == 0 or len(clean_content) > 2000:
            return await ctx.send("Tag content must be between 0-2000 characters!")
        await self.bot.db.execute("UPDATE tags SET content = $2 WHERE name = $1", data['name'], clean_content)
        await ctx.send("Tag was successfully edited!")

    @tag.command(name="alias")
    async def tag_alias(self, ctx, name_or_id: str, alias: str):
        return await ctx.send("Temporarily disabled, sorry")

        data = await self.get_tag_data(ctx, name_or_id)
        if not data:
            return
        original = None
        if data.get('alias'):
            original = data['alias']
            data = await self.get_tag_data(ctx, original)

        name = discord.utils.escape_mentions(alias)
        check = await self.bot.db.fetchval("SELECT tag_id FROM tags WHERE LOWER(name) = $1", name.lower())
        if check:
            return await ctx.send("A tag with that name already exists!")

        check2 = await self.bot.db.fetchval("SELECT tag_id FROM tags WHERE LOWER(name) = $1", data['name'].lower())
        if not check2:
            return await ctx.send("A tag with that name doesn't exist!")

        if name.split(' ')[0] in ('add', 'delete', 'del', 'info', 'owner', 
            'stats', 'leaderboard', 'lb', 'claim', 'raw', 'transfer',
            'list', 'search', 'edit', 'alias', 'make', 'create'):
                return await ctx.send("Tag name starts with a reserved word!")
        if name.isdigit():
            return await ctx.send("Tag names may not be numerical only!")

        await self.bot.db.execute("INSERT INTO tags VALUES($1, $2, $3, $4, $5)", name, None, ctx.author.id, int(time.time()), data['name'])
        if original:
            await ctx.send(f"Alias **{name}** is now pointing to **{data['name']}**! ***{original}** is an alias of that tag, so its being pointed to the original*")
        else:
            await ctx.send(f"Alias **{name}** is now pointing to **{data['name']}**!")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        rc = self.bot.get_channel(881226123478974484)

        if member.bot:
            data = await self.bot.db.fetchrow("DELETE FROM bots WHERE bot_id = $1 RETURNING *", member.id)
            if not data:
                return

            if data['message_id']:
                msg = await rc.fetch_message(data['message_id'])
                e = msg.embeds[0]
                e.color = 0xff0000
                await msg.edit(content="Bot left", embed=e)

            await rc.send(f"bot {member.mention} ({member}) has left.")

        else:
            async with self.bot.db.acquire() as conn:
                async with conn.transaction(): # if something fucks up, roll back the deletion
                    bots = await conn.fetch("DELETE FROM bots WHERE owner_id = $1 RETURNING *", member.id)
                    if not bots:
                        return

                    messages = []
                    for data in bots:
                        if data['message_id']:
                            msg = await rc.fetch_message(data['message_id'])
                            e = msg.embeds[0]
                            e.color = 0xff0000
                            await msg.edit(content="Bot removed (owner left)", embed=e)
                            usr = member.guild.get_member(data['bot_id'])
                            await usr.kick(reason="owner left server")

                            messages.append((msg, usr))

                    view = ui.View()
                    for info in messages:
                        msg = info[0]
                        usr = info[1]
                        view.add_item(ui.Button(url=msg.jump_url, style=discord.ButtonStyle.link, label=str(usr)))

                    await rc.send(f"Removed the following {len(bots)} bots belonging to {member} ({member.id})", view=view)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            return

        rc = self.bot.get_channel(881226123478974484)

        try:
            data = await self.bot.db.fetchrow("UPDATE bots SET date_add = $1 WHERE bot_id = $2 RETURNING *", int(time.time()), member.id)
        except:
            data = None

        if data is None:
            await rc.send(f"{member.mention} ({member}) has been added to the server. It is not registered in the invite system.")
            return

        user = self.bot.get_user(data['owner_id'])
        if not user: # user left
            await member.kick(reason="User left server")
            m = await rc.fetch_message(data['message_id'])
            v = ui.View()
            v.add_item(ui.Button(label="Bot Invited", disabled=True, style=discord.ButtonStyle.green))
            e = m.embeds[0]
            e.color = 0xff0000
            await m.edit(content="Bot removed due to owner leaving", embed=e, view=v)
            return

        try:
            await user.send(f"Your bot {member.mention} (`{member}`) has been added to Devision!")
        except:
            c = self.bot.get_channel(881194048101167215)
            await c.send(f"{user.mention}, your bot {member.mention} has been added to the server!")

        await member.add_roles(member.guild.get_role(881237986212208682))
        
        m: discord.Message = await rc.fetch_message(data['message_id'])
        v = ui.View()
        v.add_item(ui.Button(label="Bot Invited", disabled=True, style=discord.ButtonStyle.green))
        e = m.embeds[0]
        e.colour = 0x52d174
        await m.edit(embed=e, view=v)

    @commands.command(slash_command=True)
    async def whoadd(self, ctx, bot: discord.Member = commands.Option(description="the bot you want to see the info for")):
        """See who requested a bot to join this server"""
        if not bot.bot:
            return await ctx.send("That is a user, not a bot!", ephemeral=True)

        data = await self.bot.db.fetchrow("SELECT * FROM bots WHERE bot_id = $1", bot.id)
        if not data:
            return await ctx.send("It seems the bot you requested is not stored in my database yet. This bot was probably added before this system was created...", ephemeral=True)

        if not data['date_add']:
            await ctx.send("This bot is pending...", ephemeral=True)

        e = discord.Embed(color=0x2F3136, title=f"Who added {bot}?")
        e.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{bot.id}/{bot.avatar}.png")
        d = [f'**Bot:** {bot.mention} (`{bot.id}`)']
        d.append(f"**Submitted by:** <@{data['owner_id']}> (`{data['owner_id']}`)")
        d.append(f"**Date Submitted:** <t:{data['date_submit']}>")
        d.append(f"**Date Added:** <t:{data['date_add']}>")
        d.append(f"**Reason:** {data['reason']}")
        if ctx.author.guild_permissions.manage_guild:
            d.append(f"[Tooling link](https://canary.discord.com/channels/514232441498763279/881226123478974484/{data['message_id']})")

        e.description = "\n".join(d)

        await ctx.send(embed=e)

    @commands.command(slash_command=True)
    async def addbot(self, ctx, bot_id: str = commands.Option(description="The ID of your bot"), *, reason: str = commands.Option(description="Why you want your bot added here")):
        """Get your bot added to this server"""
        try:
            user = await self.bot.fetch_user(int(bot_id))
        except:
            return await ctx.send("That is not a valid bot ID.", ephemeral=True)

        if not user.bot:
            return await ctx.send("That is a user ID, not a bot ID.", ephemeral=True)

        if ctx.guild.get_member(int(bot_id)):
            return await ctx.send("This bot is already in the server.", ephemeral=True)

        if await self.bot.db.fetchrow("SELECT 1 FROM bots WHERE bot_id = $1", user.id):
            return await ctx.send("This bot is already pending.", ephemeral=True)

        channel = self.bot.get_channel(881226123478974484)
        e = discord.Embed(title=f"Bot request by {ctx.author}", color=0x2f3136)
        e.description = f"**Bot:** {user} `({bot_id})`\n**Reason:** {reason}"
        e.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{bot_id}/{user.avatar}.png")
        v = ui.View()
        v.add_item(ui.Button(label="Invite", url=discord.utils.oauth_url(bot_id, permissions=discord.Permissions.none(), guild=ctx.guild), style=discord.ButtonStyle.link))
        msg = await channel.send(embed=e, view=v)
        await self.bot.db.execute("INSERT INTO bots VALUES($1, $2, $3, $4, $5, $6)", int(bot_id), ctx.author.id, reason, None, int(time.time()), msg.id)

        await ctx.send("You bot has been submitted, you'll be notified when it's added to the server. Be sure to allow DMs from me!", ephemeral=True)


    @commands.group(slash_command=True)
    async def rtfm(self, ctx):
        """Search the docs for edpy or py"""
        pass

    @rtfm.command(slash_command=True)
    async def py(self, ctx, search: str = commands.Option(description="Item to search for")):
        """Search the Python docs"""
        await self.do_rtfm(ctx, 'python', search)

    @rtfm.command(slash_command=True)
    async def edpy(self, ctx, search: str = commands.Option(description="Item to search for")):
        """Search the Enhanced-dpy docs"""
        await self.do_rtfm(ctx, 'enhanced-dpy', search)
        
    @commands.command(slash_command=True, slash_command_guilds=[514232441498763279], name='test')
    async def testslash(self, ctx):
        md = ui.Modal(title="Add Your Bot")

        class Field(ui.InputText):
            async def callback(self, interaction):
                await interaction.response.send_message("Thanks", ephemeral=True)
        md.add_item(Field(label="Bot ID"))
        md.add_item(Field(label="Reason"))
        await ctx.interaction.response.send_modal(md)

def setup(bot):
    bot.add_cog(Devision(bot))
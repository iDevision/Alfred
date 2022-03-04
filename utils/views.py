import discord
import math
from datetime import datetime
from discord.ui import View, button, Button
from discord import Interaction

class AccessRoles(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Enhanced-Dpy", style=discord.ButtonStyle.blurple, custom_id="get_access:edpy", row=0)
    async def edpy(self, button, interaction):
        role = interaction.guild.get_role(881191755511369728)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Successfully left the Enhanced-Dpy section!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Successfully joined the Enhanced-Dpy section!", ephemeral=True)

    @button(label="Devision Support (no enhanced-dpy)", style=discord.ButtonStyle.blurple, custom_id="get_access:devision", row=1)
    async def devision(self, button, interaction):
        role = interaction.guild.get_role(881191827485622302)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Successfully left the Devision Support section!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Successfully joined the Devision Support section!", ephemeral=True)

    @button(label="Friends Hangout", style=discord.ButtonStyle.blurple, custom_id="get_access:hangout", row=1)
    async def hangout(self, button, interaction):
        role = interaction.guild.get_role(881191671444959253)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Successfully left the Hangout section!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Successfully joined the Hangout section!", ephemeral=True)

#!------------

class CharlesNews(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Add/Remove News Role", style=discord.ButtonStyle.blurple, custom_id="news:charles")
    async def charles(self, button, interaction):
        role = interaction.guild.get_role(654204973105807390)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Role removed, you'll no longer receive news about Charles.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Role added, you'll now receive news about Charles.", ephemeral=True)

#!-------------

class GamesNews(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Add/Remove News Role", style=discord.ButtonStyle.blurple, custom_id="news:games")
    async def games(self, button, interaction):
        role = interaction.guild.get_role(874843780824576041)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Role removed, you'll no longer receive news about My Games.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Role added, you'll now receive news about My Games.", ephemeral=True)

#!------------------

class ApiNews(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Add/Remove News Role", style=discord.ButtonStyle.blurple, custom_id="news:api")
    async def api(self, button, interaction):
        role = interaction.guild.get_role(696112264713076797)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("Role removed, you'll no longer receive news about the iDevision API.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Role added, you'll now receive news about the iDevision API.", ephemeral=True)

#!---------------

class Paginator(View):
    def __init__(self, ctx, *args, **kwargs):
        super().__init__()
        self.ctx = ctx
        self.embedded = kwargs.get('embedded', True)
        self.entries = kwargs.get('entries')
        self.per_page = kwargs.get('per_page', 15)
        self.page = 1
        self.pages = math.ceil(len(self.entries)/self.per_page)
        self.paginating = False

        self.title = kwargs.get("title")
        self.author = kwargs.get("author", ctx.author)
        self.thumbnail = kwargs.get("thumbnail")
        self.footericon = kwargs.get("footericon", discord.Embed.Empty)
        self.footertext = kwargs.get("footertext", discord.Embed.Empty)
        self.url = kwargs.get("url")
        self.image = kwargs.get("image")
        self.color = kwargs.get("color", 0x2F3136)
        self.timestamp = kwargs.get("timestamp", True)
        self.show_entry_count = kwargs.get("show_entry_count", False)
        self.per_page = kwargs.get("per_page", 1)
        self.show_entry_nums = kwargs.get("show_entry_nums", False)
        self.prefix = kwargs.get("prefix", "")
        self.suffix = kwargs.get("suffix", "")
        self.entries_name = kwargs.get("entries_name", "entries")

    async def interaction_check(self, _, interaction: Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id

    def generate_page(self):
        if not self.embedded:
            page = []
            num = (self.page - 1) * self.per_page
            if self.show_entry_nums:
                for i, n in enumerate(self.entries, start=1):
                    page.append(f"`[{i}]` {n}")
                text = self.prefix + "\n".join(page[num:num + self.per_page]) + self.suffix
            else:
                text = self.prefix + "\n".join(self.entries[num:num + self.per_page]) + self.suffix
            return text

        e = discord.Embed(color=self.color)
        if self.thumbnail:
            e.set_thumbnail(url=self.thumbnail)
        if self.image:
            e.set_image(url=self.image)
        e.set_footer(icon_url=self.footericon, text=self.footertext)

        if self.timestamp:
            e.timestamp = datetime.utcnow()

        if isinstance(self.url, list):
            if (ti:= len(self.url)) != (en:= self.pages):
                raise ValueError(f"Got a list of urls but it does not match the amount of entries: {ti}t/{en}e")
            e.url = self.url[self.page-1]
        else:
            e.url = self.url

        num = (self.page - 1) * self.per_page
        if self.show_entry_nums:
            x = []
            for i, n in enumerate(self.entries, start=1):
                x.append(f"`[{i}]` {n}")
            e.description = self.prefix + "\n".join(x[num:num + self.per_page]) + self.suffix
        else:
            e.description = self.prefix + "\n".join(self.entries[num:num + self.per_page]) + self.suffix

        title = ""
        if isinstance(self.title, list):
            if (ti:= len(self.title)) != (en:= self.pages):
                raise ValueError(f"Got a list of titles but it does not match the amount of entries: {ti}t/{en}e")
            title = str(self.title[self.page-1])
        elif isinstance(self.title, str):
            title = str(self.title)


        if self.show_entry_count:
            if self.footertext != discord.Embed.Empty:
                title += f" ({len(self.entries)} {self.entries_name})"
            else:
                e.set_footer(text=f"{len(self.entries)} {self.entries_name}")
        else:
            pass

        e.title = title

        if isinstance(self.author, (discord.User, discord.Member, discord.ClientUser)):
            e.set_author(icon_url=self.author.avatar.with_static_format("png").url, name=self.author)
        elif isinstance(self.author, discord.Guild):
            e.set_author(icon_url=self.author.icon.with_static_format("png").url, name=self.author)
        elif isinstance(self.author, str):
            e.set_author(icon_url=self.ctx.author.avatar.with_static_format("png").url, name=self.author)
        return e

    async def send_page(self, interaction):
        self.children[2].label = f"{self.page}/{self.pages}"
        page = self.generate_page()
        if isinstance(page, str):
            await interaction.response.edit_message(content=page, view=self)
        else:
            await interaction.response.edit_message(embed=page, view=self)

    @button(label="◄◄", style=discord.ButtonStyle.blurple)
    async def beginning(self, button: Button, interaction: Interaction):
        if self.page == 1:
            await interaction.response.defer()
        else:
            self.page = 1
            await self.send_page(interaction)

    @button(label="◄", style=discord.ButtonStyle.blurple)
    async def previous(self, button: Button, interaction: Interaction):
        if self.page == 1:
            await interaction.response.defer()
        else:
            self.page -= 1
            await self.send_page(interaction)

    @button(label="...", style=discord.ButtonStyle.grey, disabled=True)
    async def pagenum(self, button: Button, interaction: Interaction):
        return

    @button(label="►", style=discord.ButtonStyle.blurple)
    async def next(self, button: Button, interaction: Interaction):
        if self.page == self.pages:
            await interaction.response.defer()
        else:
            self.page += 1
            await self.send_page(interaction)

    @button(label="►►", style=discord.ButtonStyle.blurple)
    async def last(self, button: Button, interaction: Interaction):
        if self.page == self.pages:
            await interaction.response.defer()
        else:
            self.page = self.pages
            await self.send_page(interaction)

    @button(label="⬜", style=discord.ButtonStyle.red)
    async def cancel(self, button: Button, interaction: Interaction):
        await interaction.response.defer()
        self.stop()
        await interaction.message.delete()

    async def start(self):
        self.children[2].label = f"{self.page}/{self.pages}"
        page = self.generate_page()
        if isinstance(page, str):
            await self.ctx.send(page, view=self)
        else:
            await self.ctx.send(embed=page, view=self)
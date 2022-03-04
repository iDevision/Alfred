import discord
from discord.ext import commands

class Help(commands.HelpCommand):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.verify_checks = True

	async def send_bot_help(self, mapping):
		e = discord.Embed(
			title="Alfred | Devision Support Bot",
			color=0xA6B8D7)
		e.set_thumbnail(url=self.context.bot.user.avatar_url_as(format="png"))
		e.set_author(icon_url=self.context.author.avatar_url, name=self.context.author)
		cats = '\n- '.join([e.qualified_name for e in self.context.bot.cogs.values()])
		e.description = f"`Type !help <category/command> for more info`\n\n**Categories:**\n- {cats}"

		await self.context.send(embed=e)

	async def send_command_help(self, command):
		e = discord.Embed(
			title=f"!{command.qualified_name} {command.signature}",
			color=0xA6B8D7,
			description=command.help)
		e.set_thumbnail(url=self.context.bot.user.avatar_url_as(format="png"))
		e.set_author(icon_url=self.context.author.avatar_url, name=self.context.author)
		await self.context.send(embed=e)

	async def send_group_help(self, group):
		e = discord.Embed(
			title=f"!{group.qualified_name} {group.signature}",
			color=0xA6B8D7,
			description=group.help)
		e.set_thumbnail(url=self.context.bot.user.avatar_url_as(format="png"))
		e.set_author(icon_url=self.context.author.avatar_url, name=self.context.author)
		e.add_field(name="Subcommands", value="`"+"`, `".join([c.name for c in group.commands])+"`")
		await self.context.send(embed=e)

	async def send_cog_help(self, cog):
		e = discord.Embed(
			title=cog.qualified_name,
			color=0xA6B8D7,
			description="- " + "\n- ".join([f"{c.qualified_name} - `{c.short_doc}`" for c in cog.get_commands()]))
		e.set_thumbnail(url=self.context.bot.user.avatar_url_as(format="png"))
		e.set_author(icon_url=self.context.author.avatar_url, name=self.context.author)
		e.set_footer(text="Type !help <command> for more info")
		await self.context.send(embed=e)

def setup(bot):
	bot.help_command = Help(command_attrs=dict(aliases=['h', 'cmds', 'commands']))

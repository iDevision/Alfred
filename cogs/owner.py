import inspect

import discord

from discord.ext import commands

rules = [
    (
        "No NSFW topics/imagery etc.",
        "NSFW topics are not welcome here. This is a public place, be mindful of your avatars and usernames. Users found with NSFW content as part of their profile "
            "will be asked to remove such content. Failure to comply will result in removal from the community."
    ),
    (
        "Keep your usage of this server civil",
        "This is purposefully vague, but includes being hostile and slurs. We will not tolerate uncivil behaviour."
    ),
    (
        "Harassment will not be tolerated",
        "Harassment, including, but not limited to, impersonation and mockery, will result in a non-appealable ban."
    ),
    (
        "Do not abuse the platform",
        "Anyone found abusing the platform (including, but not limited to, spamming, selfbotting, etc) will immediatly be removed from the community, and will be reported to discord."
    ),
    (
        "Do not ping people for support",
        "People will help when they are able/willing to. Pinging will only annoy them."
    ),
    (
        "Stick to english",
        "This is an english speaking server. Avoid speaking other languages."
    ),
    (
        "This server is LGBTQ+ friendly",
        "Any homophobia of any sort will result in an immediate ban. We will not accept appeals for these sort of bans."
    ),
    (
        "Advertising is not permitted",
        """
        This includes, but is not limited to:
        - Offering goods or services
        - Discord invites
        - Any recruitment (paid or not)
        - Linking to online content (e.g. blog posts, videos) for personal gain (viewership, ads, etc.)
        """
    ),
    (
        "Rules around submitting bots",
        """
        Bots may be added to this server via the /addbot command. Submitted bots must be made using enhanced-discord.py, and may not use the prefixes `!` or `?`.
        Your bot may be kicked at any point, without warning.
        Bots that send unprompted (prefixless) messages will be removed.
        """
    )
]

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def rules(self, ctx):
        """Send the rules to #rules-and-info"""
        rulechan: discord.TextChannel = self.bot.get_channel(647540839672709123)
        await rulechan.purge()

        await ctx.message.delete()

        await rulechan.send("https://media.discordapp.net/attachments/460568954968997890/742213071631810631/devision_rules.png")

        for i, rule in enumerate(rules):
            await rulechan.send(f"**{i+1}. {rule[0]}**\n{inspect.cleandoc(rule[1])}")


def setup(bot):
    bot.add_cog(Owner(bot))
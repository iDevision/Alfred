from __future__ import annotations

import asyncpg
import discord
from typing import TYPE_CHECKING, Dict, Union

if TYPE_CHECKING:
    from bot import Alfred

def setup(bot: Alfred):
    bot.application_command(tag)
    bot.application_command(addTag)
    bot.application_command(aliasTag)
    bot.application_command(deleteTag)
    bot.application_command(infoTag)


class AutoCompletableCommand(discord.SlashCommand):
    client: Alfred

    async def autocomplete(
        self, options: Dict[str, Union[int, float, str]], focused: str
    ) -> discord.AutoCompleteResponse:
        tag_query = options[focused]
        query = """
        SELECT
            name
        FROM
            tag_lookup
        WHERE
            SIMILARITY(name, $1) > 0.25 
        ORDER BY
            similarity(name, $1) 
            DESC
            LIMIT 10
        """

        tags = await self.client.db.fetch(query, tag_query)
        return discord.AutoCompleteResponse({n["name"]: n["name"] for n in tags})

class tag(AutoCompletableCommand, guilds=[514232441498763279]):
    """
    Replies with the given tag
    """

    name: str = discord.Option(description="The tag to invoke", autocomplete=True)

    async def callback(self) -> None:

        data = await self.client.db.fetchrow("SELECT findTag($1)", self.name)
        if not data['findtag']:
            return await self.send("That tag does not exist", ephemeral=True)

        await self.send(data['findtag'][1])


class addTag(discord.SlashCommand, name="tag-add", guilds=[514232441498763279]):
    """
    Adds a tag
    """
    name: str = discord.Option(description="The name of the tag to create")
    content: str = discord.Option(description="The content of the tag")

    client: Alfred

    async def callback(self) -> None:
        self.name = self.name.strip().lower()
        if not self.name or len(self.name) > 32 or self.name.isdigit() or self.client.get_command("tag").get_command(self.name):
            return await self.send("Invalid tag name", ephemeral=True)

        content = discord.utils.escape_mentions(self.content.strip())
        if len(content) > 2000:
            return await self.send("Content must be 2000 characters or less")

        try:
            await self.client.db.execute(
                "SELECT createTag($1, $2, $3)",
                self.name, content, self.interaction.user.id
            )
        except asyncpg.UniqueViolationError:
            await self.send("Tag already exists", ephemeral=True)
        else:
            await self.send(f"Created tag {self.name}", ephemeral=True)


class aliasTag(AutoCompletableCommand, name="tag-alias", guilds=[514232441498763279]):
    """
    Creates an alias for a tag. The owner of the tag will own the alias as well
    """
    tag_name: str = discord.Option(description="The tag to add an alias to", autocomplete=True)
    alias_name: str = discord.Option(description="The name of the new alias")

    async def callback(self) -> None:
        alias = self.alias_name.strip().lower()
        if not alias or len(alias) > 32 or alias.isdigit() or self.client.get_command("tag").get_command(alias):
            return await self.send("Invalid alias name", ephemeral=True)

        try:
            resp = await self.client.db.fetchrow("SELECT createAlias($1, $2)", self.tag_name, alias)
            await self.send(resp['createalias'])
        except asyncpg.UniqueViolationError:
            await self.send("A tag/alias with that name already exists")


class deleteTag(discord.SlashCommand, name="tag-delete", guilds=[514232441498763279]):
    """
    Deletes a tag or tag alias
    """
    name: str = discord.Option(description="The tag/alias to delete", autocomplete=True)

    client: Alfred

    async def callback(self) -> None:
        name = self.name.strip().lower()

        resp = await self.client.db.fetchrow("SELECT deleteTag($1, $2)", name, self.interaction.user.id)
        await self.send(resp['deletetag'])


class infoTag(AutoCompletableCommand, name="tag-info", guilds=[514232441498763279]):
    """
    Shows information on a tag
    """
    name: str = discord.Option(description="The tag to fetch information on", autocomplete=True)

    async def callback(self) -> None:
        name = self.name.strip().lower()
        query = """
        SELECT
            tl.tagId, tl.isAlias, tn.name, tn.owner, tn.uses, tn.created
        FROM tag_lookup tl
        INNER JOIN tags_new tn ON tn.id = tl.tagId
        WHERE tl.name = $1
        """

        lookup = await self.client.db.fetchrow(query, name)
        if not lookup:
            return await self.send("Tag not found", ephemeral=True)

        tag_id, is_alias, tag_name, owner_id, uses, created_timestamp = lookup
        e = discord.Embed()

        if is_alias:
            e.title = f"Tag {name} -> {tag_name}"
        else:
            e.title = f"Tag {tag_name}"

        owner = self.client.get_user(owner_id)
        if owner:
            e.set_author(name=str(owner), icon_url=owner.avatar.url)

        e.description = \
            f"ID: {tag_id}\n" \
            f"Owned by <@{owner_id}> ({owner or 'Owner not found'} {(owner and owner.id) or ''})\n" \
            f"Used {uses} time{'s' if uses != 1 else ''}\n" \
            f"Created <t:{round(created_timestamp.timestamp())}:F>\n"

        await self.send(embed=e)

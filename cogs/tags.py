from __future__ import annotations

import asyncpg
import discord
from typing import TYPE_CHECKING, Dict, Union, Optional

if TYPE_CHECKING:
    from bot import Alfred

def setup(bot: Alfred):
    bot.application_command(tag)
    bot.application_command(addTag)
    bot.application_command(aliasTag)
    bot.application_command(deleteTag)
    bot.application_command(infoTag)
    bot.application_command(editTag)


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


class TagAddModal(discord.ui.Modal):
    def __init__(self, name: str, client: Alfred):
        self.client = client
        super().__init__("Add Tag")
        self.add_item(
            discord.ui.TextInput(
                "Name", value=name, placeholder="The name of your tag", style=discord.TextInputStyle.short, max_length=32, min_length=3
            )
        )
        self.add_item(discord.ui.TextInput(
            "Content", placeholder="The content of your tag", style=discord.TextInputStyle.long, max_length=2000, min_length=1
        ))

    async def callback(self, interaction: discord.Interaction):
        name = self.children[0].value.strip().lower() # type: ignore
        content = self.children[1].value.strip().lower() # type: ignore

        if name.isdigit() or self.client.get_command("tag").get_command(name): # type: ignore
            return await interaction.response.send_message("Invalid tag name", ephemeral=True)

        content = discord.utils.escape_mentions(content.strip())

        query = "SELECT createTag($1, $2, $3)"
        try:
            await self.client.db.execute(query, name, content, interaction.user.id) # type: ignore
        except asyncpg.UniqueViolationError:
            return await interaction.response.send_message("Tag already exists", ephemeral=True)

        return await interaction.response.send_message(f"Created tag {name}", ephemeral=True)


class addTag(discord.SlashCommand, name="tag-add", guilds=[514232441498763279]):
    """
    Adds a tag
    """
    name: str = discord.Option(description="The name of the tag to create")
    content: Optional[str] = discord.Option(description="The content of the tag")

    client: Alfred

    async def callback(self) -> None:
        self.name = self.name.strip().lower()
        if not self.name or 3 > len(self.name) > 32 or self.name.isdigit() or self.client.get_command("tag").get_command(self.name):
            return await self.send("Invalid tag name", ephemeral=True)

        if not self.content:
            return await self.interaction.response.send_modal(TagAddModal(self.name, self.client))

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


class TagEditModal(discord.ui.Modal):
    def __init__(self, tag_id: int, client: Alfred):
        self.tag = tag_id
        self.client = client
        super().__init__("Edit Tag")
        self.add_item(discord.ui.TextInput(
            "Content", placeholder="The new content for your tag", style=discord.TextInputStyle.long, max_length=2000, min_length=1
        ))

    async def callback(self, interaction: discord.Interaction):
        query = """
        UPDATE tags_new
        SET
            content = $1
        WHERE
            id = $2
        """
        await self.client.db.execute(query, self.children[0].value, self.tag) # type: ignore
        await interaction.response.send_message("Updated tag", ephemeral=True)

class editTag(AutoCompletableCommand, name="tag-edit", guilds=[514232441498763279]):
    name: str = discord.Option(description="The tag to update", autocomplete=True)
    content: Optional[str] = discord.Option(description="The new content of the tag. Not filling this in will bring up a modal")

    async def callback(self) -> None:
        name = self.name.strip().lower()
        query = """
                SELECT
                    tl.tagId, tn.owner
                FROM tag_lookup tl
                INNER JOIN tags_new tn ON tn.id = tl.tagId
                WHERE tl.name = $1
                """

        lookup = await self.client.db.fetchrow(query, name)
        if not lookup:
            return await self.send("Tag not found", ephemeral=True)

        if lookup['owner'] != self.interaction.user.id:
            return await self.send("You do not own this tag", ephemeral=True)

        if not self.content:
            return await self.interaction.response.send_modal(TagEditModal(lookup['tagid'], self.client))

        query = """
        UPDATE tags_new
        SET
            content = $1
        WHERE
            id = $2
        """
        await self.client.db.execute(query, self.content, lookup['tagid']) # type: ignore
        await self.send("Updated tag", ephemeral=True)
from __future__ import annotations

import asyncio
import datetime

import discord
from discord import ui
from typing import TYPE_CHECKING, Tuple, Optional, Union

if TYPE_CHECKING:
    from bot import Alfred

def setup(bot: Alfred) -> None:
    bot.application_command(reportUser)
    bot.application_command(reportMessage)

    @bot.listen()
    async def on_setup():
        data = await bot.db.fetch("SELECT * FROM modreports WHERE mod IS NULL;")
        for d in data:
            bot.add_view(
                IncidentView(d['id'], d['target'], bot.get_channel(947000488145076296).get_partial_message(d['reportMessage']), bot),
                message_id=d['reportMessage']
            )

REPORT_CHANNEL = 947000488145076296
NATLANG = {
    "warn": "You have been warned for the following reason:\n{reason}",
    "timeout": "You have received a timeout until {timeoutexp} for the following reason:\n{reason}",
    "kick": "You have been kicked for the following reason:\n{reason}",
    "ban": "You have been banned for the following reason:\n{reason}"
}

PAST = {
    "warn": "warned",
    "timeout": "timed out",
    "kick": "kicked",
    "ban": "banned"
}

class IncidentView(ui.View):
    def __init__(self, incident_id: int, user_id: int, msg: Union[discord.PartialMessage, discord.Message], bot: Alfred) -> None:
        super().__init__(timeout=None)
        self.incident_id = incident_id
        self.target_id = user_id
        self.msg = msg
        self.bot = bot

    async def upgrade_message(self):
        if isinstance(self.msg, discord.PartialMessage):
            self.msg = await self.msg.fetch()

    async def get_mod_input(self, inter: discord.Interaction) -> Optional[Tuple[str, str]]:
        waiter = asyncio.Future()
        modal = ModInput(waiter)
        await inter.response.send_modal(modal)

        timeout = asyncio.sleep(120)
        done, waiting = await asyncio.wait([timeout, waiter], return_when=asyncio.FIRST_COMPLETED)

        for wait in waiting:
            wait.cancel()

        if waiter.cancelled():
            return None

        return waiter.result()

    async def update_db(self, mod: int, action: str, remarks: Optional[str], response: Optional[str]) -> None:
        query = "UPDATE modreports SET mod = $1, modAction = $2, modRemarks = $3, modResponse = $4 WHERE id = $5"

        await self.bot.db.execute(query, mod, action, remarks, response, self.incident_id)

    async def invalidate_view(self, mod: discord.User, remarks: Optional[str], action: str) -> None:
        for item in self.children:
            item.disabled = True

        await self.upgrade_message()
        time = discord.utils.format_dt(discord.utils.utcnow(), style="f")
        text = f"update at {time} - {mod.mention} ({mod} {mod.id}) has responded to this incident with action {action}\n"
        if remarks:
            text += "".join([f"> {x}\n" for x in remarks.replace("\n\n", "\n").splitlines(False)]) + "\n"

        text += self.msg.content

        await self.msg.edit(content=text, view=self)
        self.stop()

    async def send_to_user(self, action: str, reason: str, timeoutexp: Optional[str]=None) -> bool:
        user = self.bot.get_user(self.target_id)
        if not user:
            return False

        msg = NATLANG[action].format(reason=reason, timeoutexp=timeoutexp)
        try:
            await user.send(msg)
            return True
        except:
            return False

    async def send_to_actions_channel(self, action: str, reason: str, mod: discord.User) -> None:
        actions_channel = self.bot.get_channel(892559499385270272)
        user = await self.bot.try_user(self.target_id)

        text = f"{mod.mention} ({mod} {mod.id}) {PAST[action]} {user.mention} ({user} {user.id}) {'for one day' if action == 'timeout' else ''} for {reason}. "
        await actions_channel.send(text)

    @ui.button(label="Ignore report", style=discord.ButtonStyle.blurple, custom_id="ignore")
    async def ignore(self, _, inter: discord.Interaction) -> None:
        await self.update_db(inter.user.id, "ignore", None, None)
        await self.invalidate_view(inter.user, None, "ignore")

    @ui.button(label="Warn user", style=discord.ButtonStyle.blurple, custom_id="warn")
    async def warn(self, _, inter: discord.Interaction) -> None:
        user = self.bot.get_guild(514232441498763279).get_member(self.target_id)
        if not user:
            await inter.response.send_message("User has left the server", ephemeral=True)
            return

        mod_input = await self.get_mod_input(inter)
        if not mod_input:
            return

        remarks, response = mod_input
        await self.update_db(inter.user.id, "warn", remarks, response)
        await self.invalidate_view(inter.user, remarks, "warn")
        await self.send_to_user("warn", response)
        await self.send_to_actions_channel("warn", response, inter.user)


    @ui.button(label="Timeout user", style=discord.ButtonStyle.blurple, custom_id="timeout")
    async def timeout_(self, _, inter: discord.Interaction) -> None:
        user = self.bot.get_guild(514232441498763279).get_member(self.target_id)
        if not user:
            await inter.response.send_message("User has left the server", ephemeral=True)
            return

        mod_input = await self.get_mod_input(inter)
        if not mod_input:
            return

        remarks, response = mod_input

        timeout_until = discord.utils.utcnow() + datetime.timedelta(days=1)
        time = discord.utils.format_dt(timeout_until, style="f")

        await self.update_db(inter.user.id, "timeout", remarks, response)
        await self.invalidate_view(inter.user, remarks, "timeout")
        await self.send_to_user("timeout", response, time)
        await self.send_to_actions_channel("timeout", response, inter.user)

        await user.edit(timeout_until=timeout_until)

    @ui.button(label="Kick user", style=discord.ButtonStyle.blurple, custom_id="kick")
    async def kick(self, _, inter: discord.Interaction) -> None:
        user = self.bot.get_guild(514232441498763279).get_member(self.target_id)
        if not user:
            await inter.response.send_message("User has left the server", ephemeral=True)
            return

        mod_input = await self.get_mod_input(inter)
        if not mod_input:
            return

        remarks, response = mod_input

        await self.update_db(inter.user.id, "kick", remarks, response)
        await self.invalidate_view(inter.user, remarks, "kick")
        await self.send_to_user("kick", response)
        await self.send_to_actions_channel("kick", response, inter.user)

        await user.kick()

    @ui.button(label="Ban user", style=discord.ButtonStyle.danger, custom_id="ban")
    async def ban(self, _, inter: discord.Interaction) -> None:
        mod_input = await self.get_mod_input(inter)
        if not mod_input:
            return

        remarks, response = mod_input

        await self.update_db(inter.user.id, "ban", remarks, response)
        await self.invalidate_view(inter.user, remarks, "ban")
        await self.send_to_user("ban", response)
        await self.send_to_actions_channel("ban", response, inter.user)

        await self.bot.get_guild(514232441498763279).ban(discord.Object(self.target_id))

class ModInput(ui.Modal):
    def __init__(self, waiter: asyncio.Future):
        self.waiter = waiter

        super().__init__("Mod input")

        self.add_item(ui.TextInput(
            label="Remarks on performing this action",
            placeholder="\"This user has consistently been rude towards staff\"",
            required=False,
            style=discord.TextInputStyle.long
        ))

        self.add_item(ui.TextInput(
            label="Message to send to offending user",
            placeholder="\"This will be your last warning before being banned\"",
            style=discord.TextInputStyle.long,
            required=True
        ))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Input received", ephemeral=True)
        self.waiter.set_result((self.children[0].value, self.children[1].value))


class ReportUserModal(ui.Modal):
    def __init__(self, client, target: discord.Member):
        self.client: Alfred = client
        self.target = target
        super().__init__("Report Information")
        self.add_item(
            ui.TextInput(
                label="Reason for your report",
                placeholder=f"Why are you reporting this user?",
                required=True
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        text = f"<@&881250948910055424> {interaction.user.mention} ({interaction.user} {interaction.user.id}) has reported " \
               f"{self.target.mention} ({self.target} {self.target.id}):\n\n>>> {self.children[0].value}"

        channel = self.client.get_channel(REPORT_CHANNEL)
        msg = await channel.send(text, allowed_mentions=discord.AllowedMentions(users=False, roles=True, everyone=False))

        incident_id = await self.client.db.fetchval(
            """
            INSERT INTO modreports
                (reporter, target, reportRemarks)
            VALUES
                ($1, $2, $3)
            RETURNING id
            """,
            interaction.user.id, self.target.id, self.children[0].value
        )
        time = discord.utils.format_dt(discord.utils.utcnow(), style="f")
        text = f"> incident {incident_id} at {time}\n" \
               f"<@&881250948910055424> {interaction.user.mention} ({interaction.user} {interaction.user.id}) has reported " \
               f"{self.target.mention} ({self.target} {self.target.id}):\n\n>>> {self.children[0].value}"

        msg = await msg.edit(content=text) # need to do this in two steps
        view = IncidentView(incident_id, self.target.id, msg, self.client)
        await msg.edit(content=text, view=view)

        await interaction.response.send_message("Thank you for your report.", ephemeral=True)


class ReportMessageModal(ui.Modal):
    def __init__(self, client, target: discord.Message):
        self.client: Alfred = client
        self.target = target
        super().__init__("Report Information")
        self.add_item(
            ui.TextInput(
                label="Reason for your report",
                placeholder=f"Why are you reporting this message?",
                required=True
            )
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        text = f"<@&881250948910055424> {interaction.user.mention} ({interaction.user} {interaction.user.id}) has reported " \
               f"{self.target.jump_url}:\n\n>>> {self.children[0].value}"

        channel = self.client.get_channel(REPORT_CHANNEL)
        msg = await channel.send(text,
                                 allowed_mentions=discord.AllowedMentions(users=False, roles=True, everyone=False))

        incident_id = await self.client.db.fetchval(
            """
            INSERT INTO modreports
                (reporter, target, reportRemarks, channel, message)
            VALUES
                ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            interaction.user.id, self.target.id, self.children[0].value, self.target.channel.id, self.target.id
        )

        time = discord.utils.format_dt(discord.utils.utcnow(), style="f")
        text = f"> incident {incident_id} at {time}\n" \
               f"<@&881250948910055424> {interaction.user.mention} ({interaction.user} {interaction.user.id}) has reported " \
               f"<{self.target.jump_url}>:\n\n>>> {self.children[0].value}"

        msg = await msg.edit(content=text)  # need to do this in two steps
        view = IncidentView(incident_id, self.target.author.id, msg, self.client)
        await msg.edit(content=text, view=view)

        await interaction.response.send_message("Thank you for your report.", ephemeral=True)


class reportUser(discord.UserCommand, name="report", guilds=[514232441498763279]):
    """
    Report this user to the mods. You will be asked to provide a reason for your report.
    """

    target: discord.Member

    async def callback(self) -> None:
        if self.target._roles.has(550825339077787708) or self.target._roles.has(519059592521449472):
            return await self.send("You may not report this user", ephemeral=True)

        modal = ReportUserModal(self.client, self.target)
        await self.interaction.response.send_modal(modal)


class reportMessage(discord.MessageCommand, name="report", guilds=[514232441498763279]):
    """
    Report this user to the mods. You will be asked to provide a reason for your report.
    """

    message: discord.Message

    async def callback(self) -> None:
        if self.message.author._roles.has(550825339077787708) or self.message.author._roles.has(519059592521449472):
            return await self.send("You may not report messages from this user", ephemeral=True)

        modal = ReportMessageModal(self.client, self.message)
        await self.interaction.response.send_modal(modal)
"""
Special gratitude to HyperGH, who shared that code
I had adapted it to tanjun and developed it as well
"""

import tanjun
import hikari
from functools import wraps
from typing import Optional, TypeVar, Tuple
from asyncio import sleep
from CommunityBot.utils.helper import DB, helper
import datetime

component = tanjun.Component(name="logs-mod")

ERROR_COLOR: int = 0xFF0000
WARN_COLOR: int = 0xFFCC4D
EMBED_BLUE: int = 0x009DFF
EMBED_GREEN: int = 0x77B255
UNKNOWN_COLOR: int = 0xBE1931
MISC_COLOR: int = 0xC2C2C2

EMOJI_CHANNEL = "<:channel:585783907841212418>"
EMOJI_MENTION = "<:mention:658538492019867683>"

perms_str = {
    hikari.Permissions.CREATE_INSTANT_INVITE: "Create Invites",
    hikari.Permissions.STREAM: "Go Live",
    hikari.Permissions.SEND_TTS_MESSAGES: "Send TTS Messages",
    hikari.Permissions.MANAGE_MESSAGES: "Manage Messages",
    hikari.Permissions.MENTION_ROLES: "Mention @everyone and all roles",
    hikari.Permissions.USE_EXTERNAL_EMOJIS: "Use external emojies",
    hikari.Permissions.VIEW_GUILD_INSIGHTS: "View Insights",
    hikari.Permissions.CONNECT: "Connect to Voice",
    hikari.Permissions.SPEAK: "Speak in Voice",
    hikari.Permissions.MUTE_MEMBERS: "Mute Others in Voice",
    hikari.Permissions.DEAFEN_MEMBERS: "Deafen Others in Voice",
    hikari.Permissions.MOVE_MEMBERS: "Move Others in Voice",
    hikari.Permissions.REQUEST_TO_SPEAK: "Request to Speak in Stage",
    hikari.Permissions.START_EMBEDDED_ACTIVITIES: "Start Activities",
    hikari.Permissions.MODERATE_MEMBERS: "Timeout Members",
}


def format_dt(time: datetime.datetime, style: Optional[str] = None) -> str:
    """
    Convert a datetime into a Discord timestamp.
    For styling see this link: https://discord.com/developers/docs/reference#message-formatting-timestamp-styles
    """
    valid_styles = ["t", "T", "d", "D", "f", "F", "R"]

    if style and style not in valid_styles:
        raise ValueError(
            f"Invalid style passed. Valid styles: {' '.join(valid_styles)}"
        )

    if style:
        return f"<t:{int(time.timestamp())}:{style}>"

    return f"<t:{int(time.timestamp())}>"


def get_perm_str(perm: hikari.Permissions) -> str:
    if perm_str := perms_str.get(perm):
        return perm_str

    assert perm.name is not None
    return perm.name.replace("_", " ").title()


async def find_auditlog_data(
    event: hikari.Event,
    *,
    event_type: hikari.AuditLogEventType,
    user_id: Optional[int] = None,
    bot: hikari.GatewayBot,
) -> Optional[hikari.AuditLogEntry]:
    """Find a recently sent audit log entry that matches criteria.
    Parameters
    ----------
    event : hikari.GuildEvent
        The event that triggered this search.
    type : hikari.AuditLogEventType
        The type of audit log entry to look for.
    user_id : Optional[int], optional
        The user affected by this audit log, if any. By default hikari.UNDEFINED
    Returns
    -------
    Optional[hikari.AuditLogEntry]
        The entry, if found.
    Raises
    ------
    ValueError
        The passed event has no guild attached to it, or was not found in cache.
    """

    # Stuff that is observed to just take too goddamn long to appear in AuditLogs
    takes_an_obscene_amount_of_time = [hikari.AuditLogEventType.MESSAGE_BULK_DELETE]

    guild = bot.cache.get_guild(event.guild_id)
    sleep_time = 5.0 if event_type not in takes_an_obscene_amount_of_time else 15.0
    await sleep(sleep_time)  # Wait for auditlog to hopefully fill in

    if not guild:
        raise ValueError("Cannot find guild to parse auditlogs for.")

    me = bot.cache.get_member(guild, 950682216512507934)
    assert me is not None
    perms = tanjun.utilities.calculate_permissions(me, guild, roles=guild.get_roles())
    if not (perms & hikari.Permissions.VIEW_AUDIT_LOG):
        # Do not attempt to fetch audit log if bot has no perms
        return

    try:
        return_next = False
        async for log in bot.rest.fetch_audit_log(guild, event_type=event_type):
            for entry in log.entries.values():
                # We do not want to return entries older than 15 seconds
                if (
                    datetime.datetime.now(datetime.timezone.utc) - entry.id.created_at
                ).total_seconds() > 30 or return_next:
                    return

                if user_id and user_id == entry.target_id:
                    return entry
                elif user_id:
                    return_next = True  # Only do two calls at max
                    continue
                else:
                    return entry

    except hikari.ForbiddenError:
        return


def send_webhook():
    time = datetime.datetime.now(datetime.timezone.utc)

    def send(func):
        @wraps(func)
        async def webhook(*args, **kwargs):
            data = None
            embed = await func(*args, **kwargs)
            if embed and type(embed) != hikari.Embed and len(embed) == 2:
                embed = tuple(embed)
                data = embed[1]
                embed = embed[0]
            elif embed:
                pass
            else:
                return
            embed.timestamp = time
            await helper.webhook_send(
                guild_id=args[0].guild_id, bot=kwargs["bot"], embed=embed, data=data
            )

        return webhook

    return send


def create_log_content(
    message: hikari.Message, max_length: Optional[int] = None
) -> str:

    contents = message.content
    if message.attachments:
        contents = (
            f"{contents}\n//Это сообщение имеет один или более прикреплённых объектов"
        )
    if message.embeds:
        contents = f"{contents}\n//Сообщение содержит один и более эмбедов (вставок)"
    if not contents:
        contents = "//В сообщении нет контента."
    if max_length and len(contents) > max_length:
        return contents[: max_length - 3] + "..."

    return contents


async def get_perms_diff(old_role: hikari.Role, role: hikari.Role, data: dict) -> str:

    old_perms = old_role.permissions
    new_perms = role.permissions
    perms_diff = ""
    is_colored = False
    is_colored = data["modules"].get("logs_color", False)

    gray = "[1;30m" if is_colored else ""
    white = "[0;37m" if is_colored else ""
    red = "[1;31m" if is_colored else ""
    green = "[1;32m" if is_colored else ""
    reset = "[0m" if is_colored else ""

    for perm in hikari.Permissions:
        if (old_perms & perm) == (new_perms & perm):
            continue

        old_state = f"{green}Allow" if (old_perms & perm) else f"{red}Deny"
        new_state = f"{green}Allow" if (new_perms & perm) else f"{red}Deny"

        perms_diff = f"{perms_diff}\n   {white}{get_perm_str(perm)}: {old_state} {gray}-> {new_state}"
    return perms_diff + reset


T = TypeVar("T")


async def get_diff(
    guild_id: int, old_object: T, object: T, attrs: dict[str, str]
) -> Tuple[str, dict, bool]:
    db = DB()
    data: dict = await db.findo({"_id": guild_id})
    diff = ""
    is_colored = False
    is_colored = data["modules"].get("logs_color", False)

    gray = "[1;30m" if is_colored else ""
    white = "[0;37m" if is_colored else ""
    red = "[1;31m" if is_colored else ""
    green = "[1;32m" if is_colored else ""
    reset = "[0m" if is_colored else ""

    for attribute in attrs.keys():
        old = getattr(old_object, attribute)
        new = getattr(object, attribute)

        if hasattr(old, "name"):
            diff = (
                f"{diff}\n{white}{attrs[attribute]}: {red}{old.name} {gray}-> {green}{new.name}"
                if old != new
                else diff
            )
        elif isinstance(old, datetime.timedelta):
            diff = (
                f"{diff}\n{white}{attrs[attribute]}: {red}{old.total_seconds()} {gray}-> {green}{new.total_seconds()}"
                if old != new
                else diff
            )
        else:
            diff = (
                f"{diff}\n{white}{attrs[attribute]}: {red}{old} {gray}-> {green}{new}"
                if old != new
                else diff
            )
    return diff + reset, data, is_colored


def strip_bot_reason(
    reason: Optional[str],
) -> Tuple[str, str | None] | Tuple[None, None]:
    """
    Strip action author for it to be parsed into the actual embed instead of the bot
    """
    if not reason:
        return None, None

    fmt_reason = (
        reason.split("): ", maxsplit=1)[1]
        if len(reason.split("): ", maxsplit=1)) > 1
        else reason
    )  # Remove author
    moderator = (
        reason.split(" (")[0] if fmt_reason != reason else None
    )  # Get actual moderator, not the bot
    return fmt_reason, moderator


@component.with_listener(hikari.GuildMessageDeleteEvent)
@send_webhook()
async def message_delete(
    event: hikari.GuildMessageDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:
    if not event.old_message or event.old_message.author.is_bot:
        return

    contents = create_log_content(event.old_message)

    entry = await find_auditlog_data(
        event,
        event_type=hikari.AuditLogEventType.MESSAGE_DELETE,
        user_id=event.old_message.author.id,
        bot=bot,
    )
    channel = event.get_channel()
    assert channel is not None

    if entry:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        assert moderator is not None

        embed = hikari.Embed(
            title=f"🗑️ Message deleted by Moderator",
            description=f"""**Message author:** {event.old_message.author.mention}
**Moderator:** {moderator.mention}
**Channel:** {channel.mention}
**Message content:** ```{contents}```""",
            color=ERROR_COLOR,
        )

    else:
        embed = hikari.Embed(
            title=f"🗑️ Message deleted",
            description=f"""**Message author:** `{event.old_message.author} ({event.old_message.author.id})`
**Channel:** {channel.mention}
**Message content:** ```{contents}```""",
            color=ERROR_COLOR,
        )
    return helper.embed_builder(embed, event.old_message.author)


@component.with_listener(hikari.GuildMessageUpdateEvent)
@send_webhook()
async def message_update(
    event: hikari.GuildMessageUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    if (
        not event.old_message
        or not event.old_message.author
        or event.old_message.author.is_bot
    ):
        return

    assert event.old_message and event.message

    old_content = create_log_content(event.old_message, max_length=1800)
    new_content = create_log_content(event.message, max_length=1800)
    channel = event.get_channel()
    assert channel is not None

    embed = hikari.Embed(
        title=f"🖊️ Message edited",
        description=f"""**Message author:** {event.author.mention}
**Channel:** {channel.mention}
**Before:** ```{old_content}``` \n**After:** ```{new_content}```
[Jump!]({event.message.make_link(event.guild_id)})""",
        color=EMBED_BLUE,
    )
    return helper.embed_builder(embed, event.old_message.author)


@component.with_listener(hikari.GuildBulkMessageDeleteEvent)
@send_webhook()
async def bulk_message_delete(
    event: hikari.GuildBulkMessageDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    moderator = "Discord"
    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.MESSAGE_BULK_DELETE, bot=bot
    )
    if entry:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)

    channel = event.get_channel()

    embed = hikari.Embed(
        title=f"🗑️ Bulk message deletion",
        description=f"""**Channel:** {channel.mention if channel else 'Unknown'}
**Moderator:** {moderator.mention if moderator != "Discord" else "Discord"}
```Multiple messages have been purged.```""",
        color=ERROR_COLOR,
    )
    return helper.embed_builder(embed, event.get_guild())


@component.with_listener(hikari.RoleDeleteEvent)
@send_webhook()
async def role_delete(
    event: hikari.RoleDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | hikari.Embed:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.ROLE_DELETE, bot=bot
    )
    if entry and event.old_role:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        embed = hikari.Embed(
            title=f"🗑️ Role deleted",
            description=f"**Role:** `{event.old_role}`\n**Moderator:** {moderator.mention}",
            color=ERROR_COLOR,
        )
        return helper.embed_builder(
            embed,
            bot.cache.get_available_guild(event.guild_id)
            or await bot.rest.fetch_guild(event.guild_id),
        )


@component.with_listener(hikari.RoleCreateEvent)
@send_webhook()
async def role_create(
    event: hikari.RoleCreateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | hikari.Embed:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.ROLE_CREATE, bot=bot
    )
    if entry and event.role:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        embed = hikari.Embed(
            title=f"❇️ Role created",
            description=f"**Role:** {event.role.mention}\n**Moderator:** {moderator.mention}",
            color=EMBED_GREEN,
        )
        return helper.embed_builder(
            embed,
            bot.cache.get_available_guild(event.guild_id)
            or await bot.rest.fetch_guild(event.guild_id),
        )


@component.with_listener(hikari.RoleUpdateEvent)
@send_webhook()
async def role_update(
    event: hikari.RoleUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | Tuple[hikari.Embed, dict]:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.ROLE_UPDATE, bot=bot
    )
    if entry and event.old_role:
        assert entry.user_id
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)

        attrs = {
            "name": "Name",
            "position": "Position",
            "is_hoisted": "Hoisted",
            "is_mentionable": "Mentionable",
            "color": "Color",
            "icon_hash": "Icon Hash",
            "unicode_emoji": "Unicode Emoji",
        }
        diff, data, iscolored = await get_diff(
            event.guild_id, event.old_role, event.role, attrs
        )
        diff = diff + "\n" if diff not in ["[0m", ""] else ""
        perms_diff = await get_perms_diff(event.old_role, event.role, data)
        if not diff and not perms_diff:
            diff = "Changes could not be resolved."
        color = "[0;37m" if iscolored else ""
        perms_str = (
            f"{color}Permissions:{perms_diff}" if perms_diff not in ["[0m", ""] else ""
        )
        embed = hikari.Embed(
            title=f"🖊️ Role updated",
            description=f"""**Role:** {event.role.mention}\n**Moderator:** {moderator.mention}\n**Changes:**```ansi\n{diff}{perms_str}```""",
            color=EMBED_BLUE,
        )
        return (
            helper.embed_builder(
                embed,
                bot.cache.get_available_guild(event.guild_id)
                or await bot.rest.fetch_guild(event.guild_id),
            ),
            data,
        )


@component.with_listener(hikari.GuildChannelDeleteEvent)
@send_webhook()
async def channel_delete(
    event: hikari.GuildChannelDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | hikari.Embed:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.CHANNEL_DELETE, bot=bot
    )
    if entry and event.channel:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        embed = hikari.Embed(
            title=f"#️⃣ Channel deleted",
            description=f"**Channel:** {event.channel.mention} `({event.channel.type.name})`\n**Moderator:** {moderator.mention}",  # type: ignore
            color=ERROR_COLOR,
        )
        return helper.embed_builder(
            embed,
            bot.cache.get_available_guild(event.guild_id)
            or await bot.rest.fetch_guild(event.guild_id),
        )


@component.with_listener(hikari.GuildChannelCreateEvent)
@send_webhook()
async def channel_create(
    event: hikari.GuildChannelCreateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | hikari.Embed:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.CHANNEL_CREATE, bot=bot
    )
    if entry and event.channel:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        embed = hikari.Embed(
            title=f"#️⃣ Channel created",
            description=f"**Channel:** {event.channel.mention} `({event.channel.type.name})`\n**Moderator:** {moderator.mention}",  # type: ignore
            color=EMBED_GREEN,
        )
        return helper.embed_builder(
            embed,
            bot.cache.get_available_guild(event.guild_id)
            or await bot.rest.fetch_guild(event.guild_id),
        )


@component.with_listener(hikari.GuildChannelUpdateEvent)
@send_webhook()
async def channel_update(
    event: hikari.GuildChannelUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | Tuple[hikari.Embed, dict]:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.CHANNEL_UPDATE, bot=bot
    )

    if entry and event.old_channel:
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)
        attrs = {
            "name": "Name",
            "position": "Position",
            "parent_id": "Category",
        }
        if isinstance(event.channel, hikari.TextableGuildChannel):
            attrs["topic"] = "Topic"
            attrs["is_nsfw"] = "Is NSFW"
        if isinstance(event.channel, hikari.GuildTextChannel):
            attrs["rate_limit_per_user"] = "Slowmode duration"

        if isinstance(
            event.channel, (hikari.GuildVoiceChannel, hikari.GuildStageChannel)
        ):
            attrs["bitrate"] = "Bitrate"
            attrs["region"] = "Region"
            attrs["user_limit"] = "User limit"
        if isinstance(event.channel, hikari.GuildVoiceChannel):
            attrs["video_quality_mode"] = "Video Quality"

        diff, data, iscolored = await get_diff(
            event.guild_id, event.old_channel, event.channel, attrs
        )
        diff = diff + "\n" if diff not in ["[0m", ""] else ""
        # Because displaying this nicely is practically impossible
        if (
            event.old_channel.permission_overwrites
            != event.channel.permission_overwrites
        ):
            diff = f"{diff}Channel overrides have been modified."

        diff = diff or "Changes could not be resolved."

        embed = hikari.Embed(
            title=f"#️⃣ Channel updated",
            description=f"**Channel:** {event.channel.mention}\n**Moderator:** {moderator.mention}\n**Changes:**\n```ansi\n{diff}```",
            color=EMBED_BLUE,
        )
        return (
            helper.embed_builder(
                embed,
                bot.cache.get_available_guild(event.guild_id)
                or await bot.rest.fetch_guild(event.guild_id),
            ),
            data,
        )


@component.with_listener(hikari.GuildUpdateEvent)
@send_webhook()
async def guild_update(
    event: hikari.GuildUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | Tuple[hikari.Embed, dict]:

    entry = await find_auditlog_data(
        event, event_type=hikari.AuditLogEventType.GUILD_UPDATE, bot=bot
    )

    if event.old_guild:
        if entry:
            assert entry.user_id is not None
            moderator = (
                bot.cache.get_member(event.guild_id, entry.user_id).mention
                if entry
                else "`Discord`"
            )
            moderator = moderator or "`Discord`"
        else:
            moderator = "`Discord`"

        if (
            event.old_guild.premium_subscription_count
            != event.guild.premium_subscription_count
            and event.old_guild.premium_tier == event.guild.premium_tier
        ):
            # If someone boosted but there was no tier change, ignore
            return

        attrs = {
            "name": "Name",
            "icon_url": "Icon URL",
            "features": "Features",
            "afk_channel_id": "AFK Channel",
            "afk_timeout": "AFK Timeout",
            "banner_url": "Banner URL",
            "default_message_notifications": "Default Notification Level",
            "description": "Description",
            "discovery_splash_hash": "Discovery Splash",
            "explicit_content_filter": "Explicit Content Filter",
            "is_widget_enabled": "Widget Enabled",
            "banner_hash": "Banner",
            "mfa_level": "MFA Level",
            "owner_id": "Owner ID",
            "preferred_locale": "Locale",
            "premium_tier": "Nitro Tier",
            "public_updates_channel_id": "Public Updates Channel",
            "rules_channel_id": "Rules Channel",
            "splash_hash": "Splash",
            "system_channel_id": "System Channel",
            "system_channel_flags": "System Channel Flags",
            "vanity_url_code": "Vanity URL",
            "verification_level": "Verification Level",
            "widget_channel_id": "Widget channel",
            "nsfw_level": "NSFW Level",
        }
        diff, data, iscolored = await get_diff(
            event.guild_id, event.old_guild, event.guild, attrs
        )
        diff = diff or "Changes could not be resolved."

        embed = hikari.Embed(
            title=f"🖊️ Guild updated",
            description=f"Guild settings have been updated by {moderator}.\n**Changes:**\n```ansi\n{diff}```",
            color=EMBED_BLUE,
        )
        return (
            helper.embed_builder(
                embed,
                bot.cache.get_available_guild(event.guild_id)
                or await bot.rest.fetch_guild(event.guild_id),
            ),
            data,
        )


@component.with_listener(hikari.BanDeleteEvent)
@send_webhook()
async def member_ban_remove(
    event: hikari.BanDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    entry = await find_auditlog_data(
        event,
        event_type=hikari.AuditLogEventType.MEMBER_BAN_REMOVE,
        user_id=event.user.id,
        bot=bot,
    )
    if entry:
        assert entry.user_id is not None
        moderator = (
            bot.cache.get_member(event.guild_id, entry.user_id).mention
            if entry
            else "`Unknown`"
        )
        reason: Optional[str] = entry.reason or "No reason provided"
    else:
        moderator = "Error"
        reason = "Unable to view audit logs! Please ensure the bot has the necessary permissions to view them!"

    if isinstance(moderator, hikari.Member) and moderator.id == bot.get_me().id:
        reason, moderator = strip_bot_reason(reason)
        moderator = moderator or bot.get_me()

    embed = hikari.Embed(
        title=f"🔨 User unbanned",
        description=f"**Offender:** {event.user.mention} ({event.user})\n**Moderator:** {moderator}\n**Reason:** ```{reason}```",
        color=EMBED_GREEN,
    )
    return helper.embed_builder(embed, event.user)


@component.with_listener(hikari.BanCreateEvent)
@send_webhook()
async def member_ban_add(
    event: hikari.BanCreateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    entry = await find_auditlog_data(
        event,
        event_type=hikari.AuditLogEventType.MEMBER_BAN_ADD,
        user_id=event.user.id,
        bot=bot,
    )
    if entry:
        assert entry.user_id is not None
        moderator = (
            bot.cache.get_member(event.guild_id, entry.user_id).mention
            if entry
            else "Unknown"
        )
        reason: Optional[str] = entry.reason or "No reason provided"
    else:
        moderator = "Unknown"
        reason = "Unable to view audit logs! Please ensure the bot has the necessary permissions to view them!"

    if isinstance(moderator, hikari.Member) and moderator.id == bot.get_me().id:
        reason, moderator = strip_bot_reason(reason)
        moderator = moderator or bot.get_me()
    member = bot.cache.get_member(event.guild_id, event.user_id).mention
    roles = (
        f"\n**Roles:** {(', '.join([i.mention for i in member.get_roles() if i.name != '@everyone']))}"
        if member
        else ""
    )
    embed = hikari.Embed(
        title=f"🔨 User banned",
        description=f"**Offender:** {event.user.mention} ({event.user}){roles}\n**Moderator:** {moderator.mention}\n**Reason:**```{reason}```",
        color=ERROR_COLOR,
    )
    return helper.embed_builder(embed, event.user)


@component.with_listener(hikari.MemberDeleteEvent)
@send_webhook()
async def member_delete(
    event: hikari.MemberDeleteEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    entry = await find_auditlog_data(
        event,
        event_type=hikari.AuditLogEventType.MEMBER_KICK,
        user_id=event.user.id,
        bot=bot,
    )
    roles = f"\n**Roles:** {(', '.join([i.mention for i in event.old_member.get_roles() if i.name != '@everyone']))}"
    if entry:  # This is a kick
        assert entry.user_id is not None
        moderator = (
            bot.cache.get_member(event.guild_id, entry.user_id).mention
            if entry
            else "Unknown"
        )
        reason: Optional[str] = entry.reason or "No reason provided"

        if isinstance(moderator, hikari.Member) and moderator.id == bot.get_me().id:
            reason, moderator = strip_bot_reason(reason)
            moderator = moderator or bot.get_me()

        embed = hikari.Embed(
            title=f"🚪👈 User was kicked",
            description=f"**Offender:** {event.user.mention} ({event.user}){roles}\n**Moderator:** {moderator}\n**Reason:**```{reason}```",
            color=ERROR_COLOR,
        )
        return helper.embed_builder(embed, event.user)

    embed = hikari.Embed(
        title=f"🚪 User left",
        description=f"**User:** `{event.user.mention} ({event.user})`{roles}\n**User count:** `{len(bot.cache.get_members_view_for_guild(event.guild_id))}`",
        color=ERROR_COLOR,
    )
    embed.set_thumbnail(event.user.display_avatar_url)
    return helper.embed_builder(embed, event.user)


@component.with_listener(hikari.MemberCreateEvent)
@send_webhook()
async def member_create(
    event: hikari.MemberCreateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:

    embed = hikari.Embed(
        title=f"🚪 User joined",
        description=f"**User:** {event.member} \n**User count:** `{len(bot.cache.get_members_view_for_guild(event.guild_id))}`",
        color=EMBED_GREEN,
    )
    embed.add_field(
        name="Account created",
        value=f"{format_dt(event.member.created_at)} ({format_dt(event.member.created_at, style='R')})",
        inline=False,
    )
    embed.set_thumbnail(event.member.display_avatar_url)
    return helper.embed_builder(embed, event.user)


@component.with_listener(hikari.MemberUpdateEvent)
@send_webhook()
async def member_update(
    event: hikari.MemberUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None | hikari.Embed:

    if not event.old_member:
        return

    old_member = event.old_member
    member = event.member

    if (
        old_member.communication_disabled_until()
        != member.communication_disabled_until()
    ):
        """Timeout logging"""
        entry = await find_auditlog_data(
            event,
            event_type=hikari.AuditLogEventType.MEMBER_UPDATE,
            user_id=event.user.id,
            bot=bot,
        )
        if not entry:
            return

        if (
            entry.reason == "Automatic timeout extension applied."
            and entry.user_id == bot.get_me().id
        ):
            return

        reason = entry.reason
        assert entry.user_id is not None
        moderator = bot.cache.get_member(event.guild_id, entry.user_id)

        if entry.user_id == bot.get_me().id:
            reason, moderator = strip_bot_reason(reason)
            moderator = moderator or bot.get_me()

        if member.communication_disabled_until() is None:
            embed = hikari.Embed(
                title=f"🔉 User timeout removed",
                description=f"**User:** {member.mention} \n**Moderator:** {moderator.mention} \n**Reason:** ```{reason}```",
                color=EMBED_GREEN,
            )
            """if mod:
                await mod.d.actions.add_note(
                    event.user, event.guild_id, f"🔉 **Timeout removed by {moderator}:** {reason}"
                )"""

        else:
            comms_disabled_until = member.communication_disabled_until()
            assert comms_disabled_until is not None

            embed = hikari.Embed(
                title=f"🔇 User timed out",
                description=f"""**User:** {member.mention}
**Moderator:** {moderator.mention} 
**Until:** {format_dt(comms_disabled_until)} ({format_dt(comms_disabled_until, style='R')})
**Reason:** ```{reason}```""",
                color=ERROR_COLOR,
            )

        return helper.embed_builder(embed, event.user)

    elif old_member.nickname != member.nickname:
        """Nickname change handling"""
        embed = hikari.Embed(
            title=f"🖊️ Nickname changed",
            description=f"**User:** {member.mention} \n**Nickname before:** `{old_member.nickname}`\n**Nickname after:** `{member.nickname}`",
            color=EMBED_BLUE,
        )
        return helper.embed_builder(embed, event.user)

    elif old_member.role_ids != member.role_ids:
        # Check difference in roles between the two
        add_diff = list(set(member.role_ids) - set(old_member.role_ids))
        rem_diff = list(set(old_member.role_ids) - set(member.role_ids))

        if len(add_diff) == 0 and len(rem_diff) == 0:
            # No idea why this is needed, but otherwise I get empty role updates
            return

        entry = await find_auditlog_data(
            event,
            event_type=hikari.AuditLogEventType.MEMBER_ROLE_UPDATE,
            user_id=event.user.id,
            bot=bot,
        )
        assert entry and entry.user_id
        moderator = (
            bot.cache.get_member(event.guild_id, entry.user_id) if entry else "Unknown"
        )
        reason: Optional[str] = entry.reason if entry else "No reason provided."

        if isinstance(moderator, (hikari.Member)) and moderator.is_bot:
            # Do not log role updates done by ourselves or other bots
            return

        if len(add_diff) != 0:
            role = bot.cache.get_role(add_diff[0])
            assert role is not None
            embed = hikari.Embed(
                title=f"🖊️ Member roles updated",
                description=f"**User:** {member.mention} \n**Moderator:** {moderator.mention}\n**Role added:** {role.mention}",
                color=EMBED_BLUE,
            )
            return helper.embed_builder(embed, event.user)

        elif len(rem_diff) != 0:
            role = bot.cache.get_role(rem_diff[0])
            assert role is not None

            embed = hikari.Embed(
                title=f"🖊️ Member roles updated",
                description=f"**User:** `{member.mention} \n**Moderator:** {moderator.mention}\n**Role removed:** {role.mention}",
                color=EMBED_BLUE,
            )
            return helper.embed_builder(embed, event.user)


@component.with_listener(hikari.VoiceStateUpdateEvent)
@send_webhook()
async def voice_update(
    event: hikari.VoiceStateUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:
    old_st = event.old_state
    st = event.state
    channel = (
        bot.cache.get_guild_channel(str(old_st.channel_id))
        if old_st
        else bot.cache.get_guild_channel(str(st.channel_id))
    )
    if old_st and st and old_st.channel_id and st.channel_id:
        channel1 = bot.cache.get_guild_channel(str(st.channel_id))
        checkdict = lambda x: {
            "deafened": x.is_guild_deafened,
            "muted": x.is_guild_muted,
            "self_deafened": x.is_self_deafened,
            "self_muted": x.is_self_muted,
            "streaming": x.is_streaming,
            "suppressed": x.is_suppressed,
            "sharing video": x.is_video_enabled,
        }
        st_diff = list(checkdict(old_st).items() - checkdict(st).items())
        entry = await find_auditlog_data(
            event,
            event_type=hikari.AuditLogEventType.MEMBER_UPDATE,
            user_id=old_st.member.id,
            bot=bot,
        )
        if st_diff != []:
            title = "User state update"
            text = f"Is "
            if st_diff[0][1] == True:
                text += f"not {st_diff[0][0]}"
            else:
                text += st_diff[0][0]
            if entry:
                text += f"\n**Moderator:** <@{entry.user_id}>"
        else:
            entry = await find_auditlog_data(
                event, event_type=hikari.AuditLogEventType.MEMBER_MOVE, bot=bot
            )
            if entry:  # it's forced
                title = "🔊🦵🔊 Force join"
                text = f"Was transfered from {channel.mention} to {channel1.mention}\n**Moderator:** <@{entry.user_id}>"
            else:
                title = "🔊👉🔊 Joined other VC"
                text = f"Left {channel.mention} and joined {channel1.mention}"
    elif not old_st and st:
        title = "🔊👈 Joined VC"
        text = f"Joined {channel.mention}"
    elif old_st and not st.channel_id:
        entry = await find_auditlog_data(
            event,
            event_type=hikari.AuditLogEventType.MEMBER_MOVE,
            user_id=old_st.member.id,
            bot=bot,
        )
        if entry:  # it's forced
            title = "🔊🦵🔊 Disconnect"
            text = (
                f"Was kicked from {channel.mention}\n**Moderator:** <@{entry.user_id}>"
            )
        else:
            title = "🔊👉 Left VC"
            text = f"Left {channel.mention}"
    text = (
        f"**User:** {event.old_state.member.mention if event.old_state else event.state.member.mention}\n**Action:** "
        + text
    )
    embed = hikari.Embed(title=title, description=text, color=EMBED_BLUE)

    return helper.embed_builder(
        embed, event.old_state.member if event.old_state else event.state.member
    )


@tanjun.as_loader
def load_component(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())


@tanjun.as_unloader
def unload_component(client: tanjun.abc.Client) -> None:
    client.remove_component(component.copy())

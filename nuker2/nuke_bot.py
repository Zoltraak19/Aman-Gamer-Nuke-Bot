import asyncio
from typing import Any, Awaitable, Callable, Optional, cast

import discord
from discord.ext import commands

import config
import nuke_functions
from nuke_functions import (
    ban_all_command,
    create_channels_command,
    create_roles_command,
    delete_channels_command,
    delete_roles_command,
    message_spam_command,
    nuke_command,
    prune_command,
    stop_command,
    webhook_spam_command,
)


def _is_valid_token(token: Optional[str]) -> bool:
    return bool(token and token.strip() and token not in {"YOUR_BOT_TOKEN_HERE", "YOUR_USER_TOKEN_HERE"})


BOT_TOKEN_VALID = _is_valid_token(config.BOT_TOKEN)

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
if hasattr(intents, "message_content"):
    setattr(intents, "message_content", True)
intents.bans = True
intents.members = True

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None, case_insensitive=True)
silent_mode = config.SILENT_MODE


async def handle_command(
    ctx: commands.Context,
    command_func: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Handle command execution with optional silent mode."""
    global silent_mode

    original_message = getattr(ctx, "message", ctx)

    stoppable_commands = (
        nuke_command,
        delete_channels_command,
        create_channels_command,
        delete_roles_command,
        create_roles_command,
        ban_all_command,
        prune_command,
        webhook_spam_command,
        message_spam_command,
    )

    try:
        if command_func in stoppable_commands:
            current_task = nuke_functions.active_nuke_task
            if current_task is not None and not current_task.done():
                current_task.cancel()
                try:
                    await current_task
                except asyncio.CancelledError:
                    pass

            nuke_functions.stop_requested = False
            coro = command_func(ctx, *args, **kwargs)
            nuke_functions.active_nuke_task = asyncio.create_task(cast(Any, coro))
            try:
                result = await nuke_functions.active_nuke_task
            finally:
                current_task = nuke_functions.active_nuke_task
                if current_task is not None and not current_task.done():
                    current_task.cancel()
                nuke_functions.active_nuke_task = None
        else:
            result = await command_func(ctx, *args, **kwargs)

        if silent_mode and hasattr(original_message, "delete"):
            try:
                delete_target = cast(Any, original_message)
                await delete_target.delete()
            except Exception:
                pass

        return result
    except asyncio.CancelledError:
        return None
    except Exception as e:
        print(f"Error executing command: {e}")
        if hasattr(ctx, "send"):
            await ctx.send(f"Error: {e}")
        return None


@bot.event
async def on_ready() -> None:
    user = bot.user
    if user is not None:
        print(f"Bot logged in as {user.name}")
    await bot.change_presence(activity=discord.Game(name=config.BOT_TAGLINE))


@bot.command(aliases=['n'])
async def nuke(ctx):
    """Complete server nuke"""
    await handle_command(ctx, nuke_command)


@bot.command(name='help')
async def help_command(ctx: commands.Context, command_name: Optional[str] = None) -> None:
    """Show help information"""
    if silent_mode:
        return

    if command_name:
        cmd: Any = bot.get_command(command_name)
        if cmd is None:
            await ctx.send(f"No command named '{command_name}' found.")
            return

        cmd_name = getattr(cmd, "name", command_name)
        signature = getattr(cmd, "signature", "")
        description = getattr(cmd, "help", "No description provided.") or "No description provided."
        usage = f"{config.COMMAND_PREFIX}{cmd_name} {signature}" if signature else f"{config.COMMAND_PREFIX}{cmd_name}"

        embed = discord.Embed(
            title=f"Help: {cmd_name}",
            description=config.BOT_TAGLINE,
            color=discord.Color.purple(),
        )
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.set_footer(text=config.BOT_TAGLINE)
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title="Captain Aizen Command Center",
        description=config.BOT_TAGLINE,
        color=discord.Color.purple(),
    )
    embed.set_footer(text=config.BOT_TAGLINE)
    for command in bot.commands:
        if getattr(command, "hidden", False):
            continue
        command_name_value = getattr(command, "name", None)
        if command_name_value is None:
            continue
        command_help = getattr(command, "help", "No description provided.") or "No description provided."
        embed.add_field(
            name=f"{config.COMMAND_PREFIX}{command_name_value}",
            value=command_help,
            inline=False,
        )
    await ctx.send(embed=embed)


@bot.command(aliases=['dc', 'delchan'])
async def deletechannels(ctx):
    """Delete all channels"""
    await handle_command(ctx, delete_channels_command)


@bot.command(aliases=['cc', 'makechan'])
async def createchannels(ctx: commands.Context, name: Optional[str] = None, count: Optional[int] = None) -> None:
    """Create channels"""
    await handle_command(ctx, create_channels_command, name, count)


@bot.command(aliases=['dr', 'delrole'])
async def deleteroles(ctx: commands.Context) -> None:
    """Delete all roles"""
    await handle_command(ctx, delete_roles_command)


@bot.command(aliases=['cr', 'makerole'])
async def createroles(ctx: commands.Context, name: Optional[str] = None, count: Optional[int] = None) -> None:
    """Create roles"""
    await handle_command(ctx, create_roles_command, name, count)


@bot.command(aliases=['ba'])
async def banall(ctx):
    """Ban all members"""
    await handle_command(ctx, ban_all_command)


@bot.command(aliases=['p'])
async def prune(ctx, days: int = 1):
    """Prune members"""
    await handle_command(ctx, prune_command, days)


@bot.command(aliases=['ws'])
async def webhookspam(ctx: commands.Context, count: Optional[int] = None, *, message: Optional[str] = None) -> None:
    """Spam webhooks across all text channels"""
    if isinstance(count, str) and message is None:
        message = count
        count = None
    await handle_command(ctx, webhook_spam_command, message, count)


@bot.command(aliases=['ms'])
async def messagespam(ctx: commands.Context, count: Optional[int] = None, *, message: Optional[str] = None) -> None:
    """Spam messages across all text channels"""
    if isinstance(count, str) and message is None:
        message = count
        count = None
    await handle_command(ctx, message_spam_command, message, count)


@bot.command(name='abort', aliases=['stop'])
async def stop(ctx):
    """Stop current nuke sequence"""
    await handle_command(ctx, stop_command)


@bot.command(name='silent', aliases=['s'])
async def silent(ctx):
    """Toggle silent mode"""
    global silent_mode
    silent_mode = not silent_mode
    config.SILENT_MODE = silent_mode
    status = "enabled" if silent_mode else "disabled"
    await ctx.send(f"Silent mode {status}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


if __name__ == "__main__":
    if BOT_TOKEN_VALID:
        try:
            bot.run(config.BOT_TOKEN)
        except discord.LoginFailure:
            print("BOT_TOKEN failed to authenticate. Verify the token in config.py and ensure it is a valid bot token.")
    else:
        print("BOT_TOKEN is invalid or not set in config.py")

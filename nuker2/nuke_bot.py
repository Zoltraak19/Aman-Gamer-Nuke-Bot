import discord
from discord.ext import commands
import asyncio
import config
import nuke_functions
import os
from nuke_functions import (
    delete_all_channels, create_channels, create_roles, delete_all_roles,
    ban_all_members, prune_members, webhook_spam, message_spam,
    nuke_command, delete_channels_command, create_channels_command,
    delete_roles_command, create_roles_command, ban_all_command,
    prune_command, webhook_spam_command, message_spam_command,
    stop_command
)

def _is_valid_token(token):
    return bool(token and token.strip() and token not in {"YOUR_BOT_TOKEN_HERE", "YOUR_USER_TOKEN_HERE"})

BOT_TOKEN_VALID = _is_valid_token(config.BOT_TOKEN)
SELF_BOT_TOKEN_VALID = _is_valid_token(config.SELF_BOT_TOKEN)
IS_SELF_BOT = SELF_BOT_TOKEN_VALID and not BOT_TOKEN_VALID

# Create intents for both self-bot and regular bot modes
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.bans = True
intents.members = True

if IS_SELF_BOT:
    # Self-bot configuration
    client = discord.Client(intents=intents)
    prefix = config.SELF_COMMAND_PREFIX
    print("Running as self-bot")
else:
    # Regular bot configuration
    bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents, help_command=None)
    prefix = config.COMMAND_PREFIX
    print("Running as regular bot")

# Global variable for silent mode
silent_mode = config.SILENT_MODE

async def handle_command(ctx, command_func, *args, **kwargs):
    """Handle command execution with optional silent mode"""
    global silent_mode

    # Store the original message for deletion if in silent mode
    original_message = ctx.message if hasattr(ctx, 'message') else ctx

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
            nuke_functions.stop_requested = False
            nuke_functions.active_nuke_task = asyncio.create_task(command_func(ctx, *args, **kwargs))
            try:
                result = await nuke_functions.active_nuke_task
            finally:
                current_task = nuke_functions.active_nuke_task
                if current_task is not None and not current_task.done():
                    current_task.cancel()
                nuke_functions.active_nuke_task = None
        else:
            result = await command_func(ctx, *args, **kwargs)
        
        # Delete original message if in silent mode
        if silent_mode and hasattr(original_message, 'delete'):
            try:
                await original_message.delete()
            except:
                pass  # Ignore if we can't delete the message
        
        return result
    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"Error executing command: {e}")
        if hasattr(ctx, 'send'):
            await ctx.send(f"Error: {e}")

if IS_SELF_BOT:
    @client.event
    async def on_ready():
        print(f'Self-bot logged in as {client.user.name}')
        config.SELF_BOT_USER_ID = client.user.id
    
    @client.event
    async def on_message(message):
        global silent_mode
        
        # Ignore messages from other users
        if message.author.id != client.user.id:
            return
        
        # Process commands
        content = message.content
        if not content.startswith(prefix):
            return
        
        command = content[len(prefix):].split()[0].lower()
        args = content[len(prefix)+len(command):].strip()
        
        # Create a context-like object for self-bot
        class SelfBotContext:
            def __init__(self, message):
                self.message = message
                self.guild = message.guild
                self.author = message.author
                self.channel = message.channel
            
            async def send(self, content=None, **kwargs):
                return await self.message.channel.send(content, **kwargs)
        
        ctx = SelfBotContext(message)
        
        # Handle commands
        if command in ["nuke", "n"]:
            await handle_command(ctx, nuke_command)
        elif command in ["deletechannels", "dc", "delchan"]:
            await handle_command(ctx, delete_channels_command)
        elif command in ["createchannels", "cc", "makechan"]:
            name = None
            count = None
            if args:
                parts = args.split()
                if len(parts) >= 1:
                    name = parts[0]
                if len(parts) >= 2:
                    try:
                        count = int(parts[1])
                    except:
                        pass
            await handle_command(ctx, create_channels_command, name, count)
        elif command in ["deleteroles", "dr", "delrole"]:
            await handle_command(ctx, delete_roles_command)
        elif command in ["createroles", "cr", "makerole"]:
            name = None
            count = None
            if args:
                parts = args.split()
                if len(parts) >= 1:
                    name = parts[0]
                if len(parts) >= 2:
                    try:
                        count = int(parts[1])
                    except:
                        pass
            await handle_command(ctx, create_roles_command, name, count)
        elif command in ["banall", "ba"]:
            await handle_command(ctx, ban_all_command)
        elif command in ["prune", "p"]:
            days = 1
            if args:
                try:
                    days = int(args.split()[0])
                except:
                    pass
            await handle_command(ctx, prune_command, days)
        elif command in ["webhookspam", "ws"]:
            message = None
            count = None
            if args:
                parts = args.split(maxsplit=1)
                if len(parts) >= 1:
                    try:
                        count = int(parts[0])
                    except:
                        message = args
                        count = None
                if len(parts) >= 2:
                    message = parts[1]
            await handle_command(ctx, webhook_spam_command, message, count)
        elif command in ["messagespam", "ms"]:
            message = None
            count = None
            if args:
                parts = args.split(maxsplit=1)
                if len(parts) >= 1:
                    try:
                        count = int(parts[0])
                    except:
                        message = args
                        count = None
                if len(parts) >= 2:
                    message = parts[1]
            await handle_command(ctx, message_spam_command, message, count)
        elif command in ["stop", "abort"]:
            await handle_command(ctx, stop_command)
        elif command in ["silent", "s"]:
            silent_mode = not silent_mode
            config.SILENT_MODE = silent_mode
            status = "enabled" if silent_mode else "disabled"
            await ctx.send(f"Silent mode {status}")
else:
    @bot.event
    async def on_ready():
        print(f'Bot logged in as {bot.user.name}')

    @bot.command(aliases=['n'])
    async def nuke(ctx):
        """Complete server nuke"""
        await handle_command(ctx, nuke_command)

    @bot.command(name='help')
    async def help_command(ctx, command_name: str = None):
        """Show help information"""
        if silent_mode:
            return

        if command_name:
            cmd = bot.get_command(command_name)
            if cmd is None:
                await ctx.send(f"No command named '{command_name}' found.")
                return
            usage = f"{config.COMMAND_PREFIX}{cmd.name} {cmd.signature}" if cmd.signature else f"{config.COMMAND_PREFIX}{cmd.name}"
            description = cmd.help or "No description provided."
            await ctx.send(f"Help for {cmd.name}:\nUsage: `{usage}`\nDescription: {description}")
            return

        lines = ["Available commands:"]
        for command in bot.commands:
            if command.hidden:
                continue
            lines.append(f"`{config.COMMAND_PREFIX}{command.name}` - {command.help or 'No description provided.'}")
        await ctx.send("\n".join(lines))

    @bot.command(aliases=['dc', 'delchan'])
    async def deletechannels(ctx):
        """Delete all channels"""
        await handle_command(ctx, delete_channels_command)

    @bot.command(aliases=['cc', 'makechan'])
    async def createchannels(ctx, name: str = None, count: int = None):
        """Create channels"""
        await handle_command(ctx, create_channels_command, name, count)

    @bot.command(aliases=['dr', 'delrole'])
    async def deleteroles(ctx):
        """Delete all roles"""
        await handle_command(ctx, delete_roles_command)

    @bot.command(aliases=['cr', 'makerole'])
    async def createroles(ctx, name: str = None, count: int = None):
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
    async def webhookspam(ctx, count: int = None, *, message: str = None):
        """Spam webhooks"""
        await handle_command(ctx, webhook_spam_command, message, count)

    @bot.command(aliases=['ms'])
    async def messagespam(ctx, count: int = None, *, message: str = None):
        """Spam messages"""
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
    if IS_SELF_BOT:
        if SELF_BOT_TOKEN_VALID:
            try:
                client.run(config.SELF_BOT_TOKEN)
            except discord.LoginFailure:
                print("SELF_BOT_TOKEN failed to authenticate. Verify the token in config.py and ensure it is a valid user token.")
        else:
            print("SELF_BOT_TOKEN is invalid or not set in config.py")
    else:
        if BOT_TOKEN_VALID:
            try:
                bot.run(config.BOT_TOKEN)
            except discord.LoginFailure:
                print("BOT_TOKEN failed to authenticate. Verify the token in config.py and ensure it is a valid bot token.")
        else:
            print("BOT_TOKEN is invalid or not set in config.py")
            if SELF_BOT_TOKEN_VALID:
                print("A valid self-bot token was found, but bot mode is currently preferred.")
            elif config.SELF_BOT_TOKEN:
                print("SELF_BOT_TOKEN appears to be a placeholder. Replace it with your user token or leave it blank to use BOT_TOKEN.")

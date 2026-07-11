import asyncio
import types
import unittest
from unittest.mock import AsyncMock

import nuke_bot
import nuke_functions


class StopCommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        nuke_functions.active_nuke_task = None
        nuke_functions.stop_requested = False

    async def asyncTearDown(self):
        nuke_functions.active_nuke_task = None
        nuke_functions.stop_requested = False

    async def test_stop_command_cancels_active_stoppable_command(self):
        async def fake_command(ctx, *args, **kwargs):
            await asyncio.sleep(10)

        original_command = nuke_bot.nuke_command
        nuke_bot.nuke_command = fake_command

        class FakeCtx:
            def __init__(self):
                self.message = types.SimpleNamespace(delete=AsyncMock())
                self.guild = None
                self.author = None
                self.channel = None

            async def send(self, content=None, **kwargs):
                return None

        ctx = FakeCtx()
        task = asyncio.create_task(nuke_bot.handle_command(ctx, nuke_bot.nuke_command))
        await asyncio.sleep(0.1)

        self.assertIsNotNone(nuke_functions.active_nuke_task)

        await nuke_bot.stop_command(ctx)
        await task

        self.assertIsNone(nuke_functions.active_nuke_task)
        nuke_bot.nuke_command = original_command


if __name__ == "__main__":
    unittest.main()

import logging
import hikari
import tanjun
import CommunityBot
from pathlib import Path
from os import environ

log = logging.getLogger(__name__)
TOKEN = environ["TOKEN"]

intents = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS
cache = hikari.CacheSettings(max_messages=10000, max_dm_channel_ids=100)
bot = hikari.GatewayBot(
    TOKEN,
    allow_color=True,
    force_color=True,
    intents=intents,
    cache_settings=cache,
)
client = tanjun.Client.from_gateway_bot(bot, declare_global_commands=905149838373560390)
client.add_prefix("-")
dct = "CommunityBot.modules."
mdls = [f"{dct}{m.stem}" for m in Path(__file__).parent.glob("modules/*.py")]
client.load_modules(*mdls)


def run() -> None:
    bot.run(
        activity=hikari.Activity(
            name=f"Version {CommunityBot.__version__}",
            type=hikari.ActivityType.WATCHING,
        )
    )

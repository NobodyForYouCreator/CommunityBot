import logging
import hikari
import tanjun
import StartBot
from pathlib import Path

log = logging.getLogger(__name__)

with open("token", mode="r", encoding="utf-8") as f:
    token = f.read().strip("\n")

intents = hikari.Intents.ALL_UNPRIVILEGED | hikari.Intents.GUILD_MEMBERS
cache = hikari.CacheSettings(max_messages=10000, max_dm_channel_ids=100)
bot = hikari.GatewayBot(
    token,
    allow_color=True,
    force_color=True,
    intents=intents,
    cache_settings=cache,
)
client = tanjun.Client.from_gateway_bot(bot, declare_global_commands=905149838373560390)
client.add_prefix("-")
dct = "StartBot.modules."
mdls = [f"{dct}{m.stem}" for m in Path(__file__).parent.glob("modules/*.py")]
client.load_modules(*mdls)


def run() -> None:
    bot.run(
        activity=hikari.Activity(
            name=f"Version {StartBot.__version__}",
            type=hikari.ActivityType.WATCHING,
        )
    )

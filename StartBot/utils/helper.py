import hikari
from motor.motor_asyncio import AsyncIOMotorClient

cluster = AsyncIOMotorClient(
    "..."
)
database = cluster.discordlocale


class helper:
    "Helper, simplifier for webhooks and embeds"

    async def webhook_send(guild_id: int, bot: hikari.GatewayBot, embed: hikari.Embed, data: dict = None):
        db = DB()
        if not data:
            data: dict = (await db.findo({"_id": guild_id}))
        data = data["modules"]
        try:
            channel_id = int(data.get("logs"))
        except KeyError:
            return
        guild = bot.cache.get_available_guild(guild_id)
        wh = None

        for wh in list(await bot.rest.fetch_channel_webhooks(channel_id)):
            if wh.name == guild.name:
                break
        if wh == None or wh.name != guild.name:
            wh = await bot.rest.create_webhook(
                channel_id, guild.name, reason="Log Creation"
            )
        await wh.execute(
            username=guild.name, avatar_url=guild.icon_url or None, embed=embed
        )


class DB:
    """Usual wrapper for MongoDB using motor"""

    def __init__(self, base: str = "CommunityBot") -> None:
        self.base = database[base]

    async def inserto(self, arg: dict) -> None:
        """
        Inserts ONE object

        await db.inserto({"_id": "smth"})
        """
        await self.base.insert_one(arg)

    async def findm(self, arg=None) -> list:
        """
        Returns MANY objects in a list

        data = await db.findm()
        """
        res = self.base.find(arg)
        res = await res.to_list(length=1000)
        return res

    def insertm(self, args: list) -> None:
        """
        Inserts MANY objects

        db.insertm([{"_id": "smth"}, {"_id": "smthagain}])
        """
        self.base.insert_many(args)

    async def deleteo(self, arg: dict) -> None:
        """
        Delete ONE object

        await db.deleteo({"_id": "smth"})
        """
        await self.base.delete_one(arg)

    async def deletem(self, args: list) -> None:
        """
        Delete MANY object

        await db.deletem([{"_id": "smth"}, {"_id": "smthagain"}])
        """
        for arg in args:
            await self.base.delete_one(arg)

    async def findo(self, arg=None) -> dict:
        """
        Returns ONE object in a dict

        await db.findo({"_id": "smth"})
        """
        return await self.base.find_one(arg)

    async def updateo(self, arg1: dict, arg2: dict, act="set"):
        """
        Update ONE object

        set - Sets the value of a field in a document.
        unset - Removes the specified field from a document.
        inc - Increments the value of the field by the specified amount.
        pop - Removes the first or last item of an array.
        pull - Removes all array elements that match a specified query.
        push - Adds an item to an array.

        await db.updateo({"_id": "smth"}, {"channel": CHANNEL_ID})
        """
        await self.base.update_one(arg1, {f"${act}": arg2})

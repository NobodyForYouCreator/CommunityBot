import tanjun
import hikari
from StartBot.utils.helper import DB

component = tanjun.Component(name="settings-mod")
MENUS = ["logs", "autochannel"]


async def waiting(
    bot: hikari.GatewayBot, ctx: tanjun.abc.SlashContext, message: hikari.Message
) -> hikari.InteractionCreateEvent:
    try:
        event = await bot.wait_for(
            hikari.InteractionCreateEvent,
            60,
            lambda x: x.interaction.message.id == message.id
            and x.interaction.user.id == ctx.author.id,
        )
        await event.interaction.create_initial_response(6)
        return event
    except TimeoutError:
        try:
            await ctx.edit_initial_response("Timed out", components=None)
        except hikari.NotFoundError:
            pass
        return


async def edit_logs(
    ctx: tanjun.abc.SlashContext, bot: hikari.GatewayBot, db: DB, mes: hikari.Message
) -> None:
    row = ctx.rest.build_action_row()
    try:
        data = await db.findo({"_id": ctx.guild_id})
        datachan = data["modules"]["logs"]
        textcolr = "simple"
        try:
            datacolr = data["modules"].get("logs_color")
        except KeyError:
            datacolr = False
        if datacolr == True:
            textcolr = "colored"

        text = f"I have found logs in <#{datachan}> and logs are set to be {textcolr}, would you like to change logs or color?"
        row.add_button(hikari.ButtonStyle.PRIMARY, "1").set_label(
            "Logs"
        ).add_to_container()
        row.add_button(hikari.ButtonStyle.SUCCESS, "01").set_label(
            "Color"
        ).add_to_container()
    except KeyError:
        text = f"I haven't found logs in server, would you like to set up them?"
        row.add_button(hikari.ButtonStyle.SUCCESS, "1").set_label(
            "Continue"
        ).add_to_container()
    row.add_button(hikari.ButtonStyle.SECONDARY, "0").set_label(
        "Cancel"
    ).add_to_container()
    await ctx.edit_initial_response(text, component=row)
    res = await waiting(bot, ctx, mes)
    if res.interaction.custom_id == "0":
        await ctx.edit_initial_response("Cancelled")
    elif res.interaction.custom_id == "01":
        row = ctx.rest.build_action_row()
        row.add_button(hikari.ButtonStyle.PRIMARY, "is").set_label(
            "Colored"
        ).add_to_container()
        row.add_button(hikari.ButtonStyle.SECONDARY, "not").set_label(
            "Uncolored"
        ).add_to_container()
        await ctx.edit_initial_response("So, choose color now!", component=row)
        res = await waiting(bot, ctx, mes)
        try:
            iscolored = True if res.interaction.custom_id == "is" else False
            data["modules"]["logs_color"] = iscolored
            await db.updateo({"_id": ctx.guild_id}, {"modules": data["modules"]}, "set")
            text = f"Now logs are {'simple' if iscolored == False else 'colored'}"
        except:
            text = "Something went wrong..."
    else:
        row = ctx.rest.build_action_row()
        menu = row.add_select_menu("channel")
        menu.set_placeholder("Choose channel")
        n = 0
        for channel in ctx.get_guild().get_channels():
            if n == 26:
                break
            channel = ctx.get_guild().get_channel(channel)
            if channel.type not in [0, 5] or channel.id == int(datachan):
                continue
            menu.add_option(channel.name, channel.id).add_to_menu()
            n += 1
        menu.add_to_container()
        await ctx.edit_initial_response("So, choose it now!", component=row)
        res = await waiting(bot, ctx, mes)
        try:
            data["modules"]["logs"] = res.interaction.values[0]
            await db.updateo({"_id": ctx.guild_id}, {"modules": data["modules"]}, "set")
            text = f"Now <#{res.interaction.values[0]}> is channel for logs"
        except:
            text = "Something went wrong..."
    await ctx.edit_initial_response(text, components=None)

async def edit_autochannel(ctx: tanjun.abc.SlashContext, bot: hikari.GatewayBot, db: DB, mes: hikari.Message):
    row = bot.rest.build_action_row()
    try:
        data = await db.findo({"_id": ctx.guild_id})
        datachan = data["modules"]["voice"][0]
        text = f"I have found autochannel in <#{datachan}>, would you like to change it?"
    except:
        datachan = None
        text = "I haven't found autochannel, would you like to setup it?"
    row.add_button(hikari.ButtonStyle.SUCCESS, "1").set_label(
        "Yes"
        ).add_to_container()
    row.add_button(hikari.ButtonStyle.SECONDARY, "01").set_label(
            "Cancel"
        ).add_to_container()
    await ctx.edit_initial_response(text, component=row)
    res = await waiting(bot, ctx, mes)
    if res.interaction.custom_id == "01":
        return await ctx.edit_initial_response("Cancelled", component=None)
    else:
        row = bot.rest.build_action_row()
        menu = row.add_select_menu("channels")
        n = 0
        for channel in ctx.get_guild().get_channels():
            if n == 26:
                break
            channel = ctx.get_guild().get_channel(channel)
            if channel.id == int(datachan):
                continue
            if channel.type == 2:
                menu.add_option(channel.name, channel.id).add_to_menu()
                n += 1
        menu.add_to_container()
        await ctx.edit_initial_response("So, choose it now!", component=row)
        res = await waiting(bot, ctx, mes)
        try:
            data["modules"]["voice"] = [res.interaction.values[0], []]
            await db.updateo({"_id": ctx.guild_id}, {"modules": data["modules"]}, "set")
            text = f"Now <#{res.interaction.values[0]}> is autochannel"
            await bot.rest.edit_channel(res.interaction.values[0], name="Create channel")
        except:
            text = "Something went wrong..."
    await ctx.edit_initial_response(text, components=None)
        

@component.with_slash_command
@tanjun.with_author_permission_check(
    8, error_message="You should have Administrator to do it"
)
@tanjun.as_slash_command(
    "settings", "manage setting on your server", default_to_ephemeral=True
)
async def settings(
    ctx: tanjun.abc.SlashContext,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> None:
    db = DB()
    row = ctx.rest.build_action_row()
    menu = row.add_select_menu("settingsmenu")
    menu.set_placeholder("Manage settings")
    for i in MENUS:
        menu.add_option(i.capitalize(), i).add_to_menu()
    menu.add_to_container()
    mes = await ctx.respond(
        "High time to change smth!", component=row, ensure_result=True
    )
    res = await waiting(bot, ctx, mes)
    if res.interaction.values[0] == "logs":
        await edit_logs(ctx, bot, db, mes)
    elif res.interaction.values[0] == "autochannel":
        await edit_autochannel(ctx, bot, db, mes)


@tanjun.as_loader
def load_component(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())


@tanjun.as_unloader
def unload_component(client: tanjun.abc.Client) -> None:
    client.remove_component(component.copy())

import tanjun
import hikari
from StartBot.utils.helper import DB

component = tanjun.Component(name="setups-mod")
db = DB()

@component.with_listener(hikari.VoiceStateUpdateEvent)
async def voice_update(
    event: hikari.VoiceStateUpdateEvent,
    bot: hikari.GatewayBot = tanjun.injected(type=hikari.GatewayBot),
) -> hikari.Embed:
    data = await db.findo({"_id": event.guild_id})
    if type(data["modules"].get("voice", False)) == list:
        if event.old_state:
            if dict(bot.cache.get_voice_states_view_for_channel(event.guild_id, event.old_state.channel_id)) == {} and event.old_state.channel_id in data["modules"]["voice"][1]:
                data["modules"]["voice"][1].remove(event.old_state.channel_id)
                await bot.rest.delete_channel(event.old_state.channel_id)
                await db.updateo({"_id": event.guild_id}, {"modules": data["modules"]}, "set")
        elif event.state and str(event.state.channel_id) == data["modules"]["voice"][0]:
            channel: hikari.GuildVoiceChannel = bot.cache.get_guild_channel(event.state.channel_id)
            new_chan = await bot.rest.create_guild_voice_channel(event.guild_id, f"Room for {event.state.member.display_name}", user_limit=channel.user_limit, bitrate=channel.bitrate, video_quality_mode=channel.video_quality_mode, permission_overwrites=channel.permission_overwrites, category=channel.parent_id, reason="autochannel")
            data["modules"]["voice"][1].append(new_chan.id)
            await event.state.member.edit(voice_channel=new_chan)
            await db.updateo({"_id": event.guild_id}, {"modules": data["modules"]}, "set")
        


@tanjun.as_loader
def load_component(client: tanjun.abc.Client) -> None:
    client.add_component(component.copy())


@tanjun.as_unloader
def unload_component(client: tanjun.abc.Client) -> None:
    client.remove_component(component.copy())
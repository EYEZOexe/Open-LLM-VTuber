from pydantic import Field
from typing import Dict, ClassVar, List
from .i18n import I18nMixin, Description


class BiliBiliLiveConfig(I18nMixin):
    """Configuration for BiliBili Live platform."""

    room_ids: List[int] = Field([], alias="room_ids")
    sessdata: str = Field("", alias="sessdata")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "room_ids": Description(
            en="List of BiliBili live room IDs to monitor", zh="要监控的B站直播间ID列表"
        ),
        "sessdata": Description(
            en="SESSDATA cookie value for authenticated requests (optional)",
            zh="用于认证请求的SESSDATA cookie值（可选）",
        ),
    }


class MyPlatformConfig(I18nMixin):
    """Configuration for My Platform Live integration."""

    channel_id: str = Field("", alias="channel_id")
    api_token: str = Field("", alias="api_token")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "channel_id": Description(
            en="Channel ID for My Platform", zh="My Platform 的频道 ID"
        ),
        "api_token": Description(
            en="API Token for My Platform", zh="My Platform 的 API Token"
        ),
    }


class TwitchLiveConfig(I18nMixin):
    """Configuration for Twitch Live integration."""

    channel: str = Field("", alias="channel")
    token: str = Field("", alias="token")
    bot_nick: str = Field("", alias="bot_nick")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "channel": Description(en="Twitch channel name", zh="Twitch频道名称"),
        "token": Description(en="Twitch OAuth token", zh="Twitch OAuth令牌"),
        "bot_nick": Description(en="Bot nickname", zh="Bot昵称"),
    }


class DiscordLiveConfig(I18nMixin):
    """Configuration for Discord Live integration."""

    token: str = Field("", alias="token")
    friend_ids: List[int] = Field([], alias="friend_ids")
    bot_nick: str = Field("DiscordBot", alias="bot_nick")
    character_name: str = Field("Mao", alias="character_name")

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "token": Description(en="Discord bot token", zh="Discord机器人令牌"),
        "friend_ids": Description(
            en="List of Discord friend user IDs", zh="Discord好友用户ID列表"
        ),
        "bot_nick": Description(en="Bot nickname", zh="Bot昵称"),
        "character_name": Description(en="Character name for AI", zh="AI角色名"),
    }


class LiveConfig(I18nMixin):
    """Configuration for live streaming platforms integration."""

    bilibili_live: BiliBiliLiveConfig = Field(
        BiliBiliLiveConfig(), alias="bilibili_live"
    )
    my_platform: MyPlatformConfig = Field(
        MyPlatformConfig(), alias="my_platform"
    )
    twitch_live: TwitchLiveConfig = Field(
        TwitchLiveConfig(), alias="twitch_live"
    )
    discord_live: DiscordLiveConfig = Field(
        DiscordLiveConfig(), alias="discord_live"
    )

    DESCRIPTIONS: ClassVar[Dict[str, Description]] = {
        "bilibili_live": Description(
            en="Configuration for BiliBili Live platform", zh="B站直播平台配置"
        ),
        "my_platform": Description(
            en="Configuration for My Platform", zh="My Platform 配置"
        ),
        "twitch_live": Description(
            en="Configuration for Twitch Live platform", zh="Twitch直播平台配置"
        ),
        "discord_live": Description(
            en="Configuration for Discord Live platform", zh="Discord直播平台配置"
        ),
    }

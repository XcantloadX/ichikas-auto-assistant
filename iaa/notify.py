import logging
import subprocess
from typing import Literal

import requests

from iaa.config.shared import NotifyConfig

logger = logging.getLogger(__name__)

NotificationType = Literal['info', 'success', 'error']

_DISCORD_COLORS: dict[NotificationType, int] = {
    'success': 0x57F287,  # green
    'error': 0xED4245,  # red
    'info': 0x5865F2,  # blurple
}


def _send_discord(webhook_url: str, title: str, message: str, type: NotificationType) -> None:
    if not webhook_url:
        logger.warning('Discord webhook URL is empty')
        return
    color = _DISCORD_COLORS[type]
    payload = {'embeds': [{'title': title, 'description': message, 'color': color}]}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    logger.debug('Discord webhook response: %s', resp.status_code)


def send_notification(title: str, message: str, config: NotifyConfig, *, type: NotificationType = 'info') -> None:
    if config.system:
        try:
            from plyer import notification
            notification.notify(title=title, message=message)  # type: ignore
            logger.debug('System notification sent: %s - %s', title, message)
        except Exception:
            logger.exception('Failed to send system notification')

    if config.push.enabled:
        from iaa.config.shared import CustomPushData, DiscordPushData
        data = config.push.data
        if isinstance(data, CustomPushData):
            command = data.command
            if not command:
                logger.warning('Push notification enabled but command is empty')
                return
            try:
                subprocess.Popen(command, shell=True)
                logger.debug('Push notification command executed: %s', command)
            except Exception:
                logger.exception('Failed to execute push notification command')
        elif isinstance(data, DiscordPushData):
            try:
                _send_discord(data.webhook_url, title, message, type)
                logger.debug('Discord notification sent: %s - %s', title, message)
            except Exception:
                logger.exception('Failed to send Discord webhook notification')
        else:
            raise ValueError(f'Unknown push notification data type: {data.type}')

import logging
import subprocess

from iaa.config.shared import NotifyConfig

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str, config: NotifyConfig) -> None:
    if config.system:
        try:
            from plyer import notification
            notification.notify(title=title, message=message) # type: ignore
            logger.debug('System notification sent: %s - %s', title, message)
        except Exception:
            logger.exception('Failed to send system notification')

    if config.push.enabled:
        if config.push.type == 'custom':
            command = config.push.data.command
            if not command:
                logger.warning('Push notification enabled but command is empty')
                return
            try:
                subprocess.Popen(command, shell=True)
                logger.debug('Push notification command executed: %s', command)
            except Exception:
                logger.exception('Failed to execute push notification command')

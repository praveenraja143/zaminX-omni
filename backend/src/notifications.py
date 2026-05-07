"""
src/notifications.py
====================
Notification service for Zamin X.
Supports SMS (Twilio) and WhatsApp (WhatsApp Business API).

Usage:
    notifier = NotificationService()
    await notifier.send("sms", "+919876543210", "Your land case was updated.")
    await notifier.send("whatsapp", "+919876543210", "Land case alert...")
"""

import logging
from typing import Literal, Optional

from src.config import settings

logger = logging.getLogger(__name__)

NotificationChannel = Literal["sms", "whatsapp", "push"]


class NotificationService:
    """
    Sends notifications via SMS, WhatsApp, or Firebase push.
    Falls back gracefully to logging when credentials are not configured.
    """

    async def send(
        self,
        channel: NotificationChannel,
        recipient: str,
        message: str,
    ) -> bool:
        """
        Send notification via specified channel.

        Returns True if successfully sent, False otherwise.
        """
        if channel == "sms":
            return await self._send_sms(recipient, message)
        elif channel == "whatsapp":
            return await self._send_whatsapp(recipient, message)
        elif channel == "push":
            return await self._send_push(recipient, message)
        else:
            logger.error("Unknown notification channel: %s", channel)
            return False

    async def _send_sms(self, to: str, body: str) -> bool:
        """Send SMS via Twilio Programmable SMS."""
        if not settings.twilio_account_sid:
            logger.info("[DEV] SMS to %s: %s", to, body[:100])
            return True  # Mock success in dev

        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body=body,
                from_=settings.twilio_phone,
                to=to,
            )
            logger.info("SMS sent to %s: SID=%s", to, message.sid)
            return True
        except Exception as e:
            logger.error("SMS delivery failed to %s: %s", to, e)
            return False

    async def _send_whatsapp(self, to: str, body: str) -> bool:
        """
        Send WhatsApp message via WhatsApp Business API (Meta Cloud API).
        Uses pre-approved template messages.
        """
        if not settings.twilio_account_sid:
            logger.info("[DEV] WhatsApp to %s: %s", to, body[:100])
            return True  # Mock success in dev

        try:
            # Using Twilio WhatsApp sandbox in development
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body=body,
                from_=f"whatsapp:{settings.twilio_phone}",
                to=f"whatsapp:{to}",
            )
            logger.info("WhatsApp sent to %s: SID=%s", to, message.sid)
            return True
        except Exception as e:
            logger.error("WhatsApp delivery failed to %s: %s", to, e)
            return False

    async def _send_push(self, firebase_token: str, body: str) -> bool:
        """Send Firebase Cloud Messaging push notification."""
        try:
            import firebase_admin
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title="Zamin X — Land Update",
                    body=body[:200],
                ),
                token=firebase_token,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(content_available=True)
                    )
                ),
            )
            response = messaging.send(message)
            logger.info("Push sent: %s", response)
            return True
        except Exception as e:
            logger.error("Push notification failed: %s", e)
            return False

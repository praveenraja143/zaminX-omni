"""
notification_service.py — SMS/WhatsApp Alerts via Twilio
Graceful: logs alerts if twilio is not installed.
"""
import logging
import os

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client as TwilioClient
    _HAS_TWILIO = True
except ImportError:
    _HAS_TWILIO = False
    logger.warning("twilio not installed. Alerts will be logged only.")


class NotificationService:
    def __init__(self):
        self.is_active = False
        if _HAS_TWILIO:
            sid = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            if sid and token:
                try:
                    self.client = TwilioClient(sid, token)
                    self.whatsapp_from = "whatsapp:+14155238886"
                    self.sms_from = os.getenv("TWILIO_SMS_NUMBER", "")
                    self.is_active = True
                    logger.info("Twilio: ACTIVE")
                except Exception as e:
                    logger.warning(f"Twilio init error: {e}")
            else:
                logger.warning("Twilio: credentials missing. Mock mode.")

    def send_alert(self, to_number: str, message: str, channel: str = "sms"):
        if not self.is_active:
            logger.info(f"[ALERT {channel.upper()}] To: {to_number} | {message}")
            return
        try:
            if channel == "whatsapp":
                self.client.messages.create(body=message, from_=self.whatsapp_from, to=f"whatsapp:{to_number}")
            else:
                self.client.messages.create(body=message, from_=self.sms_from, to=to_number)
            logger.info(f"{channel.upper()} sent to {to_number}")
        except Exception as e:
            logger.error(f"Send {channel} failed: {e}")


notification_service = NotificationService()

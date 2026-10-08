import os
import requests

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage


class ResendEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = os.environ.get("RESEND_API_KEY")

        if not api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not configured.")
            return 0

        sent_count = 0

        for message in email_messages:
            try:
                from_email = message.from_email or os.environ.get(
                    "EMAIL_FROM_ADDRESS",
                    "onboarding@resend.dev"
                )

                payload = {
                    "from": from_email,
                    "to": list(message.to),
                    "subject": message.subject,
                    "text": message.body,
                }

                response = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15,
                )

                if response.status_code >= 400:
                    raise RuntimeError(
                        f"Resend API error {response.status_code}: "
                        f"{response.text}"
                    )

                sent_count += 1

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count
"""Backend Django care trimite email prin API-ul HTTP al Resend.

Folosit ca alternativa la SMTP pentru ca portul 587 e blocat pe Render free tier.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendHTTPBackend(BaseEmailBackend):
    API_URL = "https://api.resend.com/emails"

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, "RESEND_API_KEY", "") or ""
        self.timeout = getattr(settings, "EMAIL_TIMEOUT", 15) or 15

    def send_messages(self, email_messages):
        if not email_messages or not self.api_key:
            return 0
        count = 0
        for msg in email_messages:
            try:
                self._send_one(msg)
                count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count

    def _send_one(self, message):
        html_body = None
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                html_body = content
                break

        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": list(message.to or []),
            "subject": message.subject or "",
        }
        if message.body:
            payload["text"] = message.body
        if html_body:
            payload["html"] = html_body
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.API_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "LeaveFlow/1.0",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise RuntimeError(f"Resend HTTP {exc.code}: {body}") from exc

"""Email delivery via Resend."""
import html
import os

import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Flesh Pulse <onboarding@resend.dev>")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

_WRAPPER = """
<div style="font-family:Georgia,serif;max-width:520px;margin:0 auto;padding:40px 20px;color:#111827;">
  <div style="font-size:22px;font-weight:700;margin-bottom:4px;">Flesh Pulse</div>
  <p style="color:#9ca3af;font-size:11px;margin-bottom:36px;text-transform:uppercase;letter-spacing:0.05em;">
    Independent reporting on surveillance, censorship, and authoritarian control
  </p>
  {body}
  <p style="margin-top:40px;font-size:11px;color:#9ca3af;border-top:1px solid #e5e7eb;padding-top:16px;">
    You received this email because an account was created or a request was made at fleshpulse.com.
  </p>
</div>
"""


def _send(to: str, subject: str, html: str) -> bool:
    if not resend.api_key:
        print(f"[email] RESEND_API_KEY not set — skipping send to {to} ({subject})")
        return False
    try:
        resend.Emails.send({"from": FROM_EMAIL, "to": to, "subject": subject, "html": html})
        return True
    except Exception as exc:
        print(f"[email] Failed to send to {to}: {exc}")
        return False


def send_verification_email(to: str, token: str) -> bool:
    link = f"{APP_URL}/auth/verify/{token}"
    body = f"""
      <h2 style="font-size:20px;margin-bottom:12px;">Verify your email address</h2>
      <p style="margin-bottom:24px;color:#374151;line-height:1.6;">
        Click the button below to verify your email and activate your account.
        This link expires in 24 hours.
      </p>
      <a href="{link}"
         style="display:inline-block;padding:12px 28px;background:#111827;color:#fff;
                text-decoration:none;font-weight:600;font-size:15px;letter-spacing:0.01em;">
        Verify my email
      </a>
    """
    return _send(to, "Verify your Flesh Pulse account", _WRAPPER.format(body=body))


def send_password_reset_email(to: str, token: str) -> bool:
    link = f"{APP_URL}/auth/reset-password/{token}"
    body = f"""
      <h2 style="font-size:20px;margin-bottom:12px;">Reset your password</h2>
      <p style="margin-bottom:24px;color:#374151;line-height:1.6;">
        Click the button below to set a new password.
        This link expires in 1 hour.
      </p>
      <a href="{link}"
         style="display:inline-block;padding:12px 28px;background:#111827;color:#fff;
                text-decoration:none;font-weight:600;font-size:15px;letter-spacing:0.01em;">
        Reset my password
      </a>
    """
    return _send(to, "Reset your Flesh Pulse password", _WRAPPER.format(body=body))


def send_contact_message(name: str, email: str, topic: str, message: str) -> bool:
    to = os.getenv("CONTACT_EMAIL", "contact@fleshpulse.com")
    safe_name = html.escape(name)
    safe_email = html.escape(email)
    safe_topic = html.escape(topic)
    safe_message = html.escape(message).replace("\n", "<br>")
    body = f"""
      <h2 style="font-size:20px;margin-bottom:12px;">New contact message</h2>
      <p style="margin-bottom:8px;color:#374151;"><strong>Name:</strong> {safe_name}</p>
      <p style="margin-bottom:8px;color:#374151;"><strong>Email:</strong> {safe_email}</p>
      <p style="margin-bottom:24px;color:#374151;"><strong>Topic:</strong> {safe_topic}</p>
      <div style="padding:16px;background:#f9fafb;border:1px solid #e5e7eb;color:#111827;line-height:1.6;">
        {safe_message}
      </div>
    """
    return _send(to, f"Flesh Pulse contact: {topic}", _WRAPPER.format(body=body))

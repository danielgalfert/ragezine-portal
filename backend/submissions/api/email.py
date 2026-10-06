from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape


def _introduction():
    return (
        settings.SUBMISSION_EMAIL_BODY.strip()
        or "Thank you for submitting to Rage Zine."
    )


def _receipt_body(submission):
    return (
        f"Hi {submission.artist_name},\n\n"
        f"{_introduction()}\n\n"
        f"We received \"{submission.title}\" and appreciate you sharing your work with us. "
        "Submissions are being reviewed, and we'll contact you at this email address "
        "to let you know the outcome.\n\n"
        f"Submission reference: #{submission.pk}\n\n"
        "With thanks,\nThe Rage Zine team\n\n"
        "Please keep this email as confirmation of your submission.\n"
    )


def _receipt_html(submission):
    artist_name = escape(submission.artist_name)
    title = escape(submission.title)
    reference = escape(str(submission.pk))
    introduction = escape(_introduction()).replace("\n", "<br>")

    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4eafa;color:#21172f;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f4eafa;">
    <tr><td align="center" style="padding:32px 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" width="600" style="width:100%;max-width:600px;background:#ffffff;border:1px solid #dfd0f2;border-radius:12px;">
        <tr><td style="padding:22px 36px;background:#6e39bd;border-radius:12px 12px 0 0;">
          <span style="color:#ffffff;font-size:16px;font-weight:800;letter-spacing:0.16em;">RAGE ZINE</span>
        </td></tr>
        <tr><td style="padding:36px;">
          <p style="margin:0 0 18px;font-size:16px;line-height:1.6;">Hi {artist_name},</p>
          <h1 style="margin:0 0 20px;color:#442275;font-size:30px;line-height:1.2;">Thank you for sharing your work.</h1>
          <p style="margin:0 0 16px;font-size:16px;line-height:1.7;">{introduction}</p>
          <p style="margin:0 0 26px;font-size:16px;line-height:1.7;">We received <strong>&ldquo;{title}&rdquo;</strong> and appreciate you sharing your work with us. Submissions are being reviewed, and we'll contact you at this email address to let you know the outcome.</p>
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f4eafa;border-left:4px solid #7e49d9;">
            <tr><td style="padding:16px 20px;">
              <span style="display:block;color:#644681;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">Submission reference</span>
              <span style="display:block;margin-top:5px;color:#21172f;font-size:19px;font-weight:700;">#{reference}</span>
            </td></tr>
          </table>
          <p style="margin:28px 0 0;font-size:16px;line-height:1.6;">With thanks,<br><strong>The Rage Zine team</strong></p>
        </td></tr>
        <tr><td style="padding:18px 36px;border-top:1px solid #eee4f8;color:#665a70;font-size:13px;line-height:1.5;">
          Please keep this email as confirmation of your submission.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_submission_receipt(submission):
    from_email = settings.SUBMISSION_EMAIL_FROM.strip()
    if not submission.email or not from_email:
        return 0

    message = EmailMultiAlternatives(
        subject=settings.SUBMISSION_EMAIL_SUBJECT.strip(),
        body=_receipt_body(submission),
        from_email=from_email,
        to=[submission.email],
    )
    message.attach_alternative(_receipt_html(submission), "text/html")
    return message.send(fail_silently=False)

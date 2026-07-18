import logging
from django.conf import settings

logger = logging.getLogger('accounts')


def _get_email_config():
    api_key = getattr(settings, 'RESEND_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'WMS·AI <onboarding@resend.dev>')
    return api_key, from_email


def _send_email(to_email, subject, html):
    api_key, from_email = _get_email_config()
    if not api_key:
        logger.error('RESEND_API_KEY not set — email NOT sent')
        return False
    try:
        import resend
        resend.api_key = api_key
        result = resend.Emails.send({"from": from_email, "to": [to_email], "subject": subject, "html": html})
        logger.warning(f'EMAIL OK to {to_email}: {result}')
        return True
    except Exception as e:
        logger.error(f'EMAIL FAILED to {to_email}: {type(e).__name__}: {e}')
        return False


def send_verification_email(to_email, first_name, verify_url):
    """Отправить письмо с ссылкой подтверждения."""
    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:500px;margin:0 auto;padding:40px;">
        <div style="text-align:center;margin-bottom:24px;">
            <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:24px;color:#111;">
                WMS<span style="color:#7C3AED;">·AI</span>
            </span>
        </div>
        <h2 style="color:#111;margin-bottom:12px;">Подтвердите email</h2>
        <p style="color:#6B7280;font-size:14px;line-height:1.6;">
            Здравствуйте, {first_name}!<br><br>
            Для завершения регистрации нажмите кнопку ниже:
        </p>
        <div style="text-align:center;margin:28px 0;">
            <a href="{verify_url}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#7C3AED,#C026D3);color:white;font-weight:600;font-size:15px;border-radius:10px;text-decoration:none;">
                Подтвердить email
            </a>
        </div>
        <p style="color:#6B7280;font-size:13px;">
            Или скопируйте ссылку:<br>
            <a href="{verify_url}" style="color:#7C3AED;word-break:break-all;">{verify_url}</a>
        </p>
        <p style="color:#9CA3AF;font-size:12px;margin-top:24px;">
            Если вы не регистрировались — просто проигнорируйте это письмо.
        </p>
    </div>
    """
    return _send_email(to_email, "Подтвердите email — WMS·AI", html)


def send_welcome_email(to_email, first_name, business_name, login_url):
    """Отправить приветственное письмо после подтверждения email."""
    html = f"""
    <div style="font-family:Inter,system-ui,sans-serif;max-width:500px;margin:0 auto;padding:40px;">
        <div style="text-align:center;margin-bottom:24px;">
            <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:24px;color:#111;">
                WMS<span style="color:#7C3AED;">·AI</span>
            </span>
        </div>
        <h2 style="color:#111;margin-bottom:12px;">Добро пожаловать!</h2>
        <p style="color:#6B7280;font-size:14px;line-height:1.6;">
            Здравствуйте, {first_name}!<br><br>
            Ваш бизнес <strong style="color:#111;">{business_name}</strong> успешно создан.
            Теперь вы можете войти в систему и начать работу.
        </p>
        <div style="text-align:center;margin:28px 0;">
            <a href="{login_url}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#7C3AED,#C026D3);color:white;font-weight:600;font-size:15px;border-radius:10px;text-decoration:none;">
                Войти в систему
            </a>
        </div>
        <p style="color:#6B7280;font-size:13px;">
            Ваш адрес для входа:<br>
            <a href="{login_url}" style="color:#7C3AED;word-break:break-all;">{login_url}</a>
        </p>
        <p style="color:#9CA3AF;font-size:12px;margin-top:24px;">
            Если вы не регистрировались — просто проигнорируйте это письмо.
        </p>
    </div>
    """
    return _send_email(to_email, f"Добро пожаловать в WMS·AI — {business_name}", html)

def build_welcome_email(user_name: str) -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f9f9f9; padding:20px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px; margin:0 auto; background:#fff; border:1px solid #ddd;">
          <tr>
            <td style="padding:20px; text-align:center; background:#4CAF50; color:#fff;">
              <h2 style="margin:0;">Welcome to React Market</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:20px; font-size:14px; color:#333;">
              <p>Hi {user_name},</p>
              <p>We’re excited to have you on board. Start exploring our products now!</p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

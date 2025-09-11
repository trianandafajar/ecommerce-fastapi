def build_otp_email(code: str, user_name: str = "User") -> str:
    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f4f4f7; margin:0; padding:20px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" 
               style="max-width:600px; margin:0 auto; background:#ffffff; border-radius:8px; 
                      box-shadow:0 2px 8px rgba(0,0,0,0.05); overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="padding:20px; text-align:center; background:#4CAF50; color:#fff;">
              <h2 style="margin:0; font-size:20px;">🔐 Security Verification</h2>
            </td>
          </tr>
          
          <!-- Body -->
          <tr>
            <td style="padding:30px; font-size:15px; color:#333; line-height:1.6;">
              <p style="margin:0 0 15px;">Hello <b>{user_name}</b>,</p>
              <p style="margin:0 0 20px;">
                We received a request to verify your account. Please use the following 
                one-time password (OTP) to continue:
              </p>
              
              <!-- OTP Code -->
              <div style="text-align:center; margin:30px 0;">
                <span style="display:inline-block; background:#222; color:#fff; 
                             font-size:28px; font-weight:bold; letter-spacing:6px; 
                             padding:15px 30px; border-radius:6px;">
                  {code}
                </span>
              </div>
              
              <p style="margin:0 0 10px;">⚠️ This code is valid for <b>10 minutes</b>.</p>
              <p style="margin:0 0 10px;">If you did not request this, please ignore this email.</p>
            </td>
          </tr>
          
          <!-- Footer -->
          <tr>
            <td style="padding:20px; font-size:12px; color:#888; text-align:center; background:#fafafa;">
              <p style="margin:0;">Stay secure,</p>
              <p style="margin:0;"><b>React Market Team</b></p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

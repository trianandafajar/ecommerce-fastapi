from app.models.order import Order


def build_checkout_email(order: Order) -> str:
    """Generate HTML email untuk checkout order"""

    items_html = ""
    for item in order.items:
        items_html += f"""
        <tr>
          <td style="padding:8px; border:1px solid #ddd; display:flex; align-items:center; gap:10px;">
            <img src="{item.product.image_url}" alt="{item.product.name}" 
                 style="width:50px; height:50px; object-fit:cover; border-radius:4px; border:1px solid #eee;" />
            <span>{item.product.name}</span>
          </td>
          <td style="padding:8px; border:1px solid #ddd; text-align:center;">{item.quantity}</td>
          <td style="padding:8px; border:1px solid #ddd; text-align:right;">${item.price:.2f}</td>
          <td style="padding:8px; border:1px solid #ddd; text-align:right;">
            ${float(item.price) * item.quantity:.2f}
          </td>
        </tr>
        """

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; background:#f9f9f9; padding:20px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" 
               style="max-width:700px; margin:0 auto; background:#fff; border:1px solid #ddd;">
          <tr>
            <td style="padding:20px; text-align:center; background:#4CAF50; color:#fff;">
              <h2 style="margin:0;">🛒 Order Confirmation</h2>
            </td>
          </tr>
          <tr>
            <td style="padding:20px; font-size:14px; color:#333;">
              <p>Hi {order.first_name or "Customer"},</p>
              <p>Thank you for shopping with <b>React Market</b>. Here are your order details:</p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 20px 20px 20px;">
              <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse; font-size:14px; width:100%;">
                <thead>
                  <tr style="background:#f1f1f1;">
                    <th style="padding:8px; border:1px solid #ddd; text-align:left;">Product</th>
                    <th style="padding:8px; border:1px solid #ddd; text-align:center;">Qty</th>
                    <th style="padding:8px; border:1px solid #ddd; text-align:right;">Price</th>
                    <th style="padding:8px; border:1px solid #ddd; text-align:right;">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {items_html}
                  <tr>
                    <td colspan="3" style="padding:8px; border:1px solid #ddd; text-align:right; font-weight:bold;">Grand Total</td>
                    <td style="padding:8px; border:1px solid #ddd; text-align:right; font-weight:bold;">
                      ${float(order.total_amount):.2f}
                    </td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:20px; font-size:14px; color:#333;">
              <h3 style="margin:0 0 10px 0;">📦 Shipping Information</h3>
              <p>
                {order.first_name} {order.last_name}<br/>
                {order.address}<br/>
                {order.city}, {order.postal_code}<br/>
                Phone: {order.phone}
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px; font-size:13px; color:#888; text-align:center;">
              <p>We’ll notify you once your order is shipped.</p>
              <p>Thanks for choosing <b>React Market</b>!</p>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

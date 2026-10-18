"""
=========================================================
Project : Sridevi Enterprises
File    : whatsapp_service.py
Purpose : WhatsApp click-to-chat (wa.me) link building.

          Builds the public https://wa.me/<number>?text=<message>
          links used by the floating WhatsApp button and the Product
          Details "Enquire on WhatsApp" button. The number comes only
          from Config.WHATSAPP_NUMBER (.env) - see config.py.

          Every function returns "" when no valid number is configured,
          and templates render a WhatsApp element only when one is - so
          an unconfigured deployment shows no button and no wa.me link
          at all.

          These wa.me URLs are never written into a page. The buttons
          link to this site's own /whatsapp and
          /products/<id>/whatsapp routes (routes/customer.py), which
          redirect here on click - so the number does not appear in
          the page HTML for anyone viewing source or scraping it.

          This is link building only: no WhatsApp Business API, no
          credentials, no network calls, no database access.

Author  : Srikar
=========================================================
"""

from urllib.parse import quote

from config import Config


def whatsapp_enabled() -> bool:
    """True when a valid WhatsApp number is configured."""

    return bool(Config.WHATSAPP_NUMBER)


def build_whatsapp_url(message: str = "") -> str:
    """Return a wa.me click-to-chat URL prefilled with `message`, or "" if unconfigured."""

    if not Config.WHATSAPP_NUMBER:
        return ""

    url = f"https://wa.me/{Config.WHATSAPP_NUMBER}"
    message = (message or "").strip()
    if not message:
        return url

    return f"{url}?text={quote(message, safe='')}"


def build_product_enquiry_url(product_name: str, product_url: str) -> str:
    """
    Return a wa.me URL prefilled with a product enquiry, or "" if unconfigured.

    Takes the product's public name and public page URL as plain strings -
    deliberately not a product dict - so the message can only ever contain
    those two values. Prices, stock counts, and GST details must never
    appear on a public surface, and this signature gives a caller no way
    to pass them in.
    """

    message = f"Hello, I would like to enquire about this product:\n{product_name}\n{product_url}"
    return build_whatsapp_url(message)

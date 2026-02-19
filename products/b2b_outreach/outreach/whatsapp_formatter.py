"""
WhatsApp Formatter
==================

Format messages for WhatsApp Business.
"""

import re


def format_for_whatsapp(message: str, max_length: int = 1000) -> str:
    """
    Format message for WhatsApp.

    WhatsApp style:
    - More casual and conversational
    - Emojis encouraged
    - Short paragraphs (add line breaks)
    """
    message = message.strip()

    # Break sentences into paragraphs for WhatsApp readability
    message = re.sub(r'\. (?=[A-Z])', '.\n\n', message)

    # Add WhatsApp bold formatting and emojis to section headers
    message = message.replace('Quick Win:', '✅ *Quick Win:*')
    message = message.replace('Opportunity:', '💡 *Opportunity:*')
    message = message.replace('Insight:', '📊 *Insight:*')

    if len(message) <= max_length:
        return message

    # Try to truncate at a paragraph boundary for clean reading
    truncate_at = message.rfind('\n\n', 0, max_length - 3)
    if truncate_at > max_length * 0.7:
        return message[:truncate_at]

    # Fall back to word boundary with ellipsis
    truncate_at = message.rfind(' ', 0, max_length - 3)
    if truncate_at > 0:
        return message[:truncate_at] + '...'

    return message[:max_length - 3] + '...'

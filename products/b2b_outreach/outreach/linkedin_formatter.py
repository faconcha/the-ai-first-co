"""
LinkedIn Formatter
==================

Format messages for LinkedIn InMail and connection requests.
"""


def _remove_emojis(text: str) -> str:
    """Remove emojis from text across all common emoji Unicode ranges."""
    emoji_ranges = [
        (0x1F600, 0x1F64F),
        (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF),
        (0x1F700, 0x1F77F),
        (0x2600, 0x26FF),
        (0x2700, 0x27BF),
        (0xFE00, 0xFE0F),
        (0x1F900, 0x1F9FF),
    ]

    def is_emoji(char):
        cp = ord(char)
        return any(start <= cp <= end for start, end in emoji_ranges)

    return ''.join(char for char in text if not is_emoji(char))


def format_for_linkedin(message: str, max_length: int = 300) -> str:
    """
    Format message for LinkedIn.

    LinkedIn constraints:
    - Connection request: 300 characters max
    - Professional tone required
    - No emojis
    """
    message = message.strip()

    message = _remove_emojis(message)

    if len(message) <= max_length:
        return message

    # Try to truncate at a sentence boundary (period) for clean reading
    truncate_at = message.rfind('.', 0, max_length - 3)
    if truncate_at > max_length * 0.7:
        return message[:truncate_at + 1]

    # Fall back to truncating at a word boundary with ellipsis
    truncate_at = message.rfind(' ', 0, max_length - 3)
    if truncate_at > 0:
        return message[:truncate_at] + '...'

    # Last resort: hard truncate
    return message[:max_length - 3] + '...'

"""
Campaign Tracking Utilities (Pure Functions)
=============================================

UTM URL building and engagement score computation.
Storage functions live in the consuming application (e.g. bison-aeo).
"""

from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from products.b2b_outreach.campaigns.models import EngagementEventType


def compute_engagement_score_delta(event_type: EngagementEventType) -> float:
    """Return the score increment for a given engagement event type.

    Higher-value actions (meeting booked = 50) score more than passive ones (opened = 10).
    """
    deltas = {
        EngagementEventType.MESSAGE_SENT: 0.0,
        EngagementEventType.MESSAGE_OPENED: 10.0,
        EngagementEventType.LINK_CLICKED: 20.0,
        EngagementEventType.REPLY_RECEIVED: 30.0,
        EngagementEventType.MEETING_BOOKED: 50.0,
    }
    return deltas.get(event_type, 0.0)


def build_utm_url(base_url: str, campaign_id: str, touch_channel: str) -> str:
    """Append UTM tracking parameters to a URL, preserving any existing query params."""
    parsed = urlparse(base_url)
    existing_params = parse_qs(parsed.query, keep_blank_values=True)

    utm_params = {
        'utm_source': ['bison'],
        'utm_medium': ['outreach'],
        'utm_campaign': [campaign_id],
        'utm_content': [touch_channel],
    }
    existing_params.update(utm_params)

    flat_params = {k: v[0] for k, v in existing_params.items()}
    new_query = urlencode(flat_params)

    updated = parsed._replace(query=new_query)
    return urlunparse(updated)

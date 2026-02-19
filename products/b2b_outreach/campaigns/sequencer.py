from typing import Optional, Callable
import datetime

from products.b2b_outreach.campaigns.models import (
    Campaign,
    CampaignStatus,
    Touch,
    TouchChannel,
    TouchType,
    TouchStatus,
)


def create_campaign(
    company_id: str,
    company_name: str,
    contact_id: Optional[str],
    lead_score: float = 0.0,
    report_url: str = "",
    on_campaign_created: Optional[Callable[[Campaign], None]] = None
) -> Campaign:
    """Create a new campaign with the standard 5-touch sequence.

    Touch sequence: LinkedIn connect (day 0) -> LinkedIn message (day 3) ->
    Email report (day 5) -> WhatsApp follow-up (day 7) -> Phone call (day 10).
    Each touch can have a condition that must be met before execution.
    """
    now = datetime.datetime.utcnow()
    campaign_id = f"camp_{company_id}_{int(now.timestamp())}"
    utm_campaign = campaign_id

    touches = [
        Touch(
            channel=TouchChannel.LINKEDIN,
            touch_type=TouchType.CONNECTION,
            delay_days=0,
            condition=None,
            scheduled_at=now + datetime.timedelta(days=0),
        ),
        Touch(
            channel=TouchChannel.LINKEDIN,
            touch_type=TouchType.MESSAGE,
            delay_days=3,
            condition="connected",
            scheduled_at=now + datetime.timedelta(days=3),
        ),
        Touch(
            channel=TouchChannel.EMAIL,
            touch_type=TouchType.REPORT_DELIVERY,
            delay_days=5,
            condition=None,
            scheduled_at=now + datetime.timedelta(days=5),
            content=report_url if report_url else None,
        ),
        Touch(
            channel=TouchChannel.WHATSAPP,
            touch_type=TouchType.FOLLOW_UP,
            delay_days=7,
            condition="email_opened",
            scheduled_at=now + datetime.timedelta(days=7),
        ),
        Touch(
            channel=TouchChannel.PHONE,
            touch_type=TouchType.DISCOVERY_CALL,
            delay_days=10,
            condition="lead_score>=70",
            scheduled_at=now + datetime.timedelta(days=10),
        ),
    ]

    campaign = Campaign(
        company_id=company_id,
        company_name=company_name,
        contact_id=contact_id,
        touches=touches,
        status=CampaignStatus.ACTIVE,
        current_touch_index=0,
        lead_score=lead_score,
        engagement_score=0.0,
        campaign_id=campaign_id,
        created_at=now,
        utm_campaign=utm_campaign,
    )
    if on_campaign_created is not None:
        on_campaign_created(campaign)
    return campaign


def get_next_pending_touch(campaign: Campaign) -> Optional[tuple[int, Touch]]:
    """Find the first pending touch whose scheduled time has passed.

    Iterates touches in order and returns the first one that is both
    PENDING and past its scheduled_at time. Returns None if all are
    either already executed or not yet due.
    """
    now = datetime.datetime.utcnow()

    for index, touch in enumerate(campaign.touches):
        if touch.status != TouchStatus.PENDING:
            continue
        if touch.scheduled_at is not None and touch.scheduled_at > now:
            continue
        return (index, touch)

    return None


def mark_touch_executed(campaign: Campaign, touch_index: int, content: str) -> Campaign:
    """Mark a touch as sent, record the content, and advance the campaign pointer.

    Automatically marks the campaign as COMPLETED when all touches are resolved.
    """
    touch = campaign.touches[touch_index]
    touch.status = TouchStatus.SENT
    touch.executed_at = datetime.datetime.utcnow()
    touch.content = content

    campaign.current_touch_index = touch_index + 1

    # Check if all touches have a terminal status (sent, skipped, or failed)
    all_done = all(t.status in (TouchStatus.SENT, TouchStatus.SKIPPED, TouchStatus.FAILED)
                   for t in campaign.touches)
    if all_done:
        campaign.status = CampaignStatus.COMPLETED

    return campaign


def should_skip_touch(touch: Touch, campaign: Campaign) -> bool:
    """Evaluate a touch's condition to decide if it should be skipped.

    Supported conditions:
    - None: never skip (unconditional)
    - "connected": never skip (assumes connection happened)
    - "email_opened": skip if no engagement yet (score <= 0)
    - "lead_score>=N": skip if lead score is below the threshold N
    """
    if touch.condition is None:
        return False

    if touch.condition == "connected":
        return False

    if touch.condition == "email_opened":
        return campaign.engagement_score <= 0

    if touch.condition.startswith("lead_score>="):
        threshold = float(touch.condition.split(">=")[1])
        return campaign.lead_score < threshold

    return False

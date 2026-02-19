import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field


class TouchChannel(str, Enum):
    """Communication channels available for outreach touches."""
    LINKEDIN = "linkedin"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PHONE = "phone"


class TouchType(str, Enum):
    """Type of outreach action within a campaign sequence."""
    CONNECTION = "connection"
    MESSAGE = "message"
    REPORT_DELIVERY = "report_delivery"
    FOLLOW_UP = "follow_up"
    DISCOVERY_CALL = "discovery_call"


class TouchStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"
    FAILED = "failed"


class CampaignStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EngagementEventType(str, Enum):
    MESSAGE_SENT = "message_sent"
    MESSAGE_OPENED = "message_opened"
    LINK_CLICKED = "link_clicked"
    REPLY_RECEIVED = "reply_received"
    MEETING_BOOKED = "meeting_booked"


class Touch(BaseModel):
    """A single outreach action within a campaign (e.g., LinkedIn connect, email send)."""
    channel: TouchChannel
    touch_type: TouchType
    delay_days: int
    condition: Optional[str] = None
    status: TouchStatus = TouchStatus.PENDING
    scheduled_at: Optional[datetime.datetime] = None
    executed_at: Optional[datetime.datetime] = None
    content: Optional[str] = None


class EngagementEvent(BaseModel):
    """Record of a prospect's interaction with a campaign touch (open, click, reply, etc.)."""
    event_type: EngagementEventType
    campaign_id: str
    company_id: str
    touch_index: int
    occurred_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Campaign(BaseModel):
    """Multi-touch outreach campaign targeting a single company/contact."""
    company_id: str
    company_name: str
    contact_id: Optional[str] = None
    touches: List[Touch] = Field(default_factory=list)
    status: CampaignStatus = CampaignStatus.ACTIVE
    current_touch_index: int = 0
    lead_score: float = 0.0
    engagement_score: float = 0.0
    campaign_id: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    utm_campaign: Optional[str] = None

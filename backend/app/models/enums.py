import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class UserStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    WITHDRAWN = "WITHDRAWN"


class StoreCreatedSource(str, enum.Enum):
    AUTO_COLLECTED = "AUTO_COLLECTED"
    USER_ADDED = "USER_ADDED"


class StoreStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    PENDING_REVIEW = "PENDING_REVIEW"


class FlagType(str, enum.Enum):
    GOLD = "GOLD"
    SILVER = "SILVER"


class EvidenceType(str, enum.Enum):
    NONE = "NONE"
    PHOTO = "PHOTO"
    RECEIPT = "RECEIPT"
    REALTIME_GPS = "REALTIME_GPS"
    QR = "QR"


class FlagStatus(str, enum.Enum):
    VALID = "VALID"
    UNDER_REVIEW = "UNDER_REVIEW"
    INVALIDATED = "INVALIDATED"


class ContentStatus(str, enum.Enum):
    PUBLISHED = "PUBLISHED"
    HIDDEN = "HIDDEN"
    DELETED = "DELETED"


class ReportTargetType(str, enum.Enum):
    FLAG = "FLAG"
    POST = "POST"
    COMMENT = "COMMENT"


class ReportStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWED = "REVIEWED"
    REJECTED = "REJECTED"


class ClaimStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationType(str, enum.Enum):
    FOLLOW = "FOLLOW"
    POST_COMMENT = "POST_COMMENT"
    POST_LIKE = "POST_LIKE"
    CLAIM_APPROVED = "CLAIM_APPROVED"
    CLAIM_REJECTED = "CLAIM_REJECTED"
    TIER_UP = "TIER_UP"
    FLAG_APPROVED = "FLAG_APPROVED"
    FLAG_INVALIDATED = "FLAG_INVALIDATED"
    QR_CONQUEST = "QR_CONQUEST"

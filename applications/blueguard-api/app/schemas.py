from datetime import datetime
from ipaddress import IPv4Address
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
TriageStatus = Literal["new", "investigating", "legitimate", "resolved"]


class Alert(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    detected_at: datetime
    severity: Severity
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=800)
    source_ip: IPv4Address
    destination_ip: IPv4Address
    bytes_out: int = Field(ge=0)
    detector: str = Field(min_length=1, max_length=80)
    rule_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=120)
    triage: TriageStatus
    provenance: Literal["synthetic"]


class AlertPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Alert]


class Summary(BaseModel):
    total: int
    by_severity: dict[str, int]
    new: int
    investigating: int
    data_mode: str


class Status(BaseModel):
    service: str
    version: str
    environment: str
    monitoring: str
    zeek_connected: bool
    wazuh_connected: bool
    source: str
    timestamp_utc: datetime

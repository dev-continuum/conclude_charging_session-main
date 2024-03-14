import datetime

from pydantic import BaseModel, validator
from decimal import Decimal
from typing import Optional, Dict
from decimal import Decimal


class DataToUpdateInSessionTable(BaseModel):
    update_table: bool
    table_name: str
    primary_key: dict
    sort_key: dict
    data_to_update: dict


class DataForLiveUpdate(BaseModel):
    current_charging_timer: Optional[str] = None
    current_energy_consumed: Optional[str] = None
    current_range: Optional[str] = None
    target_duration_timestamp: Optional[str] = None
    target_energy_kw: Optional[str] = None
    current_status: str
    emission_saved: Optional[str] = None
    battery_status: Optional[str] = None
    max_energy: Optional[str] = None
    wallet_details: Optional[Dict] = None


class DurationCalculatorData(BaseModel):
    duration_delta: datetime.timedelta
    duration_as_time_stamp_string: str


class CollectiveDataForCurrentState(BaseModel):
    booking_id: str
    station_id: str
    vendor_id: str
    charger_point_id: str
    connector_point_id: str
    target_duration_timestamp: Optional[str] = None
    target_energy_kw: Optional[int] = None
    start_time: Optional[str] = None
    session_data: Dict


class FinalDecisionData(BaseModel):
    start_charging_status: Optional[bool] = True
    stop_charging_status: bool
    user_stopped: bool
    final_duration_timestamp: str
    current_charging_timer: str
    final_energy_consumed: Optional[Decimal] = 0.0
    charging_target_reached: bool
    readable_summary: Dict
    end_time: str

    @validator('final_energy_consumed')
    def final_energy_validator(cls, v):
        if not v:
            return 0.0
        return v


class FinalOperationData(BaseModel):
    final_cost: Optional[str] = None
    emission_saved: Optional[str] = None
    battery_status: Optional[str] = None
    current_range: Optional[str] = None
    payment_mode: Optional[str] = "wallet"
    wallet_details: Optional[Dict] = None



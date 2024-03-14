from data_store.data_structure import ChargingStatus
from data_store.data_schemas import CollectiveDataForCurrentState, DataToUpdateInSessionTable, FinalOperationData, FinalDecisionData
from app.time_calculations import PrepareTimeDataForCurrentState
from abc import ABC, abstractmethod
from typing import Optional, Dict
from logger_init import get_logger

logger = get_logger(__name__)


class DataToReturn(ABC):
    """
    Represents an abstract class to implement a class to return final data to write in db
    """
    @abstractmethod
    def map_final_data(self, final_decision_data: FinalDecisionData, final_operation_data: FinalOperationData) -> Dict:
        """Returns a dictionary with required data"""


class FinalDataToReturnForDB(DataToReturn):
    def __init__(self, collective_data_for_current_state, time_related_data_for_current_state):
        self.collective_data_for_current_state: CollectiveDataForCurrentState = collective_data_for_current_state
        self.time_related_data_for_current_state: PrepareTimeDataForCurrentState = time_related_data_for_current_state

    def map_final_data(self, final_decision_data: FinalDecisionData, final_operation_data: FinalOperationData):
        merged_final_data = final_operation_data.dict()
        merged_final_data.update(final_decision_data.dict())
        logger.info(f"Final merged data is {merged_final_data}")
        return self._status_mapper(merged_final_data)

    def _status_mapper(self, final_response):
        return DataToUpdateInSessionTable.parse_obj({
            "update_table": True,
            "table_name": "ChargingSessionRecords",
            "primary_key": {"booking_id": self.collective_data_for_current_state.booking_id},
            "sort_key": {"vendor_id": self.collective_data_for_current_state.vendor_id},
            "data_to_update": final_response})


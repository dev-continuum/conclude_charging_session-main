from dataclasses import dataclass
from app.time_calculations import PrepareTimeDataForCurrentState
from app.final_data_maker import FinalDataToReturnForDB
from data_store.data_schemas import CollectiveDataForCurrentState, FinalOperationData, FinalDecisionData
from app.decision_making_functions import decider
from app.final_operations import OperateOnFinalData
from typing import Optional, Dict, Callable, List
from logger_init import get_logger
import datetime

logger = get_logger(__name__)


@dataclass
class ChargingSessionConclude:
    time_related_data: PrepareTimeDataForCurrentState
    collective_data_for_current_state: CollectiveDataForCurrentState
    activities: List
    final_operation: OperateOnFinalData
    final_data_decider: FinalDataToReturnForDB

    def conclude_current_charging_status(self):
        final_decision_data = {}
        for activity in self.activities:
            logger.info(f"Performing activity {activity}")
            final_decision_data.update(activity(self.collective_data_for_current_state, self.time_related_data))

        parsed_decision_data = FinalDecisionData.parse_obj(final_decision_data)
        logger.info(f"Final decision data after primary activities are {parsed_decision_data}")

        parsed_operation_data = self.final_operation.operate(parsed_decision_data)

        return self.final_data_decider.map_final_data(parsed_decision_data, parsed_operation_data)

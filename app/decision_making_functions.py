import data_store.data_structure
from logger_init import get_logger
from data_store.data_structure import ChargingStatus
from exceptions.exception import WrongStatusException
from simplejson import JSONDecodeError
from http import HTTPStatus
from app.time_calculations import PrepareTimeDataForCurrentState, CollectiveDataForCurrentState
from config import Settings
import requests

logger = get_logger(__name__)
settings = Settings()


def send_stop_request(collective_data_for_current_state: CollectiveDataForCurrentState,
                      time_related_data: PrepareTimeDataForCurrentState):
    if collective_data_for_current_state.session_data["user_stopped"]:
        logger.info("User stopped flag is set so not sending stop request again")
        return {"stop_charging_status": True, "user_stopped": True, "charging_target_reached": False}
    else:
        logger.info(f"Sending stop request for charging session {collective_data_for_current_state.booking_id}")

        try:
            response = requests.post(settings.STOP_URL,
                                     params={"vendor_id": collective_data_for_current_state.vendor_id,
                                             "booking_id": collective_data_for_current_state.booking_id},
                                     json=collective_data_for_current_state.session_data["data_to_stop"])
            parsed_response = response.json()

        except JSONDecodeError:
            logger.info(f"Charging stop failed or the booking id {collective_data_for_current_state.booking_id}")
            return {"stop_charging_status": False, "user_stopped": False, "charging_target_reached": True}
        else:
            logger.info(f"Charging stopped successfully for the booking id {collective_data_for_current_state.booking_id}. "
                        f"Response data is {parsed_response['data']}")
            return {"stop_charging_status": parsed_response["data"]["stop_charging_status"], "user_stopped": False,
                    "charging_target_reached": True}


def set_final_duration_timestamp(collective_data_for_current_state: CollectiveDataForCurrentState,
                                 time_related_data: PrepareTimeDataForCurrentState):
    return {"final_duration_timestamp": time_related_data.current_duration.duration_as_time_stamp_string,
            "end_time": time_related_data.current_end_time_object.strftime('%Y-%m-%d %H:%M:%S'),
            "readable_summary": time_related_data.readable_time_summary,
            "current_charging_timer": time_related_data.current_duration.duration_as_time_stamp_string}


def set_final_energy_consumed(collective_data_for_current_state: CollectiveDataForCurrentState,
                              time_related_data: PrepareTimeDataForCurrentState):
    print(collective_data_for_current_state.session_data["current_energy_consumed"])
    return {"final_energy_consumed": collective_data_for_current_state.session_data["current_energy_consumed"]}


def mark_start_failure(collective_data_for_current_state: CollectiveDataForCurrentState,
                       time_related_data: PrepareTimeDataForCurrentState):
    logger.info("Start itself failed so marking all start stop status as False")
    data_to_change_status = {"station_id": collective_data_for_current_state.station_id,
                            "vendor_id": collective_data_for_current_state.vendor_id,
                            "charger_point_id": collective_data_for_current_state.charger_point_id,
                            "charger_point_status": data_store.data_structure.ChargerStatus.CHARGER_AVAILABLE.value,
                            "connector_point_id": collective_data_for_current_state.connector_point_id,
                            "connector_point_status": data_store.data_structure.ChargerStatus.CHARGER_AVAILABLE.value}
    try:
        response = requests.post(settings.STATUS_URL,
                                 json=data_to_change_status)
        parsed_response = response.json()

    except JSONDecodeError:
        logger.info(f"Marking connector as free failed for {data_to_change_status}")
        return {"start_charging_status": False, "stop_charging_status": False, "user_stopped": False,
            "charging_target_reached": False}
    else:
        logger.info(f"Marking connector as free successful for {data_to_change_status}")
        return {"start_charging_status": False, "stop_charging_status": False, "user_stopped": False,
            "charging_target_reached": False}


def decider(current_status) -> []:
    action_mapper = {ChargingStatus.COMPLETED.value: [send_stop_request, set_final_duration_timestamp,
                                                      set_final_energy_consumed],
                     ChargingStatus.TERMINATED.value: [send_stop_request, set_final_duration_timestamp,
                                                       set_final_energy_consumed],
                     ChargingStatus.START_FAILED.value: [mark_start_failure, set_final_duration_timestamp,
                                                         set_final_energy_consumed],
                     ChargingStatus.STOP_FAILED.value: [send_stop_request, set_final_duration_timestamp,
                                                        set_final_energy_consumed],
                     ChargingStatus.PROGRESS_UPDATE_UNKNOWN.value: [send_stop_request, set_final_duration_timestamp,
                                                                    set_final_energy_consumed],
                     ChargingStatus.UNKNOWN_ERROR.value: [send_stop_request, set_final_duration_timestamp,
                                                          set_final_energy_consumed]}
    try:
        activities = action_mapper[current_status]
    except KeyError:
        raise WrongStatusException(code=404, message=f"The status: {current_status} is not mapped to any activity.")
    else:
        return activities

from logger_init import get_logger
from config import Settings
from app import get_lambda, get_s3
from app.conclude_it import ChargingSessionConclude
from lamda_services.s3_communicator import get_data_from_s3_bucket
from json.decoder import JSONDecodeError
from exceptions.exception import DbFetchException, SocketException
from app.time_calculations import PrepareTimeDataForCurrentState
from app.decision_making_functions import decider
from app.final_operations import OperateOnFinalData
from app.final_data_maker import FinalDataToReturnForDB
from data_store.data_schemas import DataToUpdateInSessionTable, DataForLiveUpdate, CollectiveDataForCurrentState
import requests
import simplejson

logger = get_logger(__name__)
settings = Settings()


class SocketCommunicator:
    def __init__(self, socket_client, latest_results: DataToUpdateInSessionTable,
                 collective_data_for_current_state: CollectiveDataForCurrentState):
        self.socket_client = socket_client
        self.collective_data_for_current_state = collective_data_for_current_state
        self.latest_results = latest_results
        try:
            self.connection_id = collective_data_for_current_state.session_data["socket_connection_id"]
        except KeyError:
            raise SocketException(code=400, message="There is no connection id in the incoming data")
        self.parsed_data_to_send_on_socket = self.parse_data_for_live_update()

    def parse_data_for_live_update(self):
        final_data_to_parse = {"current_charging_timer": self.latest_results.data_to_update["final_duration_timestamp"],
                               "current_energy_consumed": self.latest_results.data_to_update["final_energy_consumed"],
                               "emission_saved": self.latest_results.data_to_update["emission_saved"],
                               "battery_status": self.latest_results.data_to_update["battery_status"],
                               "current_range": self.latest_results.data_to_update["current_range"],
                               "target_duration_timestamp": self.collective_data_for_current_state.target_duration_timestamp,
                               "target_energy_kw": self.collective_data_for_current_state.session_data["target_energy_kw"],
                               "current_status": self.collective_data_for_current_state.session_data["current_status"],
                               "max_energy": self.collective_data_for_current_state.session_data["max_energy"],
                               "wallet_details": self.latest_results.data_to_update["wallet_details"]}

        return DataForLiveUpdate.parse_obj(final_data_to_parse)

    def send_message_to_socket(self):
        try:
            self.socket_client.post_to_connection(ConnectionId=self.connection_id,
                                                  Data=self.parsed_data_to_send_on_socket.json().encode("utf-8"))
        except Exception as e:
            raise SocketException(code=500, message="Unable to send data over socket")
        else:
            logger.info(f"Sent Live data on socket for id {self.connection_id}")
        finally:
            # save the parsed data to the state db
            logger.info("Finishing the state machine. Writing the final status in to charging states attribute")
            # self.latest_result data structure already have table update related data
            # Updating data_to_update attribute with charging_states data and calling the set operation
            self.latest_results.data_to_update = {"charging_states": self.parsed_data_to_send_on_socket.dict()}
            StatusManager.set_current_booking_session_data(self.latest_results, settings.DB_API)


class StatusManager:
    def __init__(self, event):
        self.event_data = event
        # call status data one last time
        self.session_data = self.get_current_booking_session_data(settings.DB_API, self.event_data["booking_id"],
                                                                  self.event_data["vendor_id"])
        # Taking start time data dynamically because initial data is passed at booking time
        # There will be no start time at that moment
        self.start_time = self.session_data["start_time"]
        self.lambda_client = get_lambda()
        self.collective_data_for_current_state = CollectiveDataForCurrentState(
            booking_id=self.event_data["booking_id"],
            station_id=self.event_data["station_id"],
            vendor_id=self.event_data["vendor_id"],
            charger_point_id=self.event_data["charger_point_id"],
            connector_point_id=self.event_data["connector_point_id"],
            target_duration_timestamp=self.event_data["target_duration_timestamp"],
            target_energy_kw=self.event_data["target_energy_kw"],
            start_time=self.start_time,
            session_data=self.session_data)

        self.tariff_data = get_data_from_s3_bucket(s3_client=get_s3(), bucket_name="electrolite-vendor-data",
                                                   file_name="tariff_rates.json")

        self.time_related_data = PrepareTimeDataForCurrentState.parse_obj({"collective_data_for_current_state":
                                                                               self.collective_data_for_current_state})
        self.time_related_data.calculate_time_related_data()

        logger.info(f"Initializing ChargingSessionMonitor")
        self.conclude_it = ChargingSessionConclude(
            collective_data_for_current_state=self.collective_data_for_current_state,
            time_related_data=self.time_related_data,
            activities=decider(self.collective_data_for_current_state.session_data["current_status"]),
            final_operation=OperateOnFinalData(self.collective_data_for_current_state, self.time_related_data,
                                               self.lambda_client, self.tariff_data),
            final_data_decider=FinalDataToReturnForDB(self.collective_data_for_current_state, self.time_related_data))

    def get_current_booking_session_data(self, db_api, booking_id, vendor_id):
        try:
            response = requests.post(db_api,
                                     json={"read_table": True,
                                           "table_name": "ChargingSessionRecords",
                                           "primary_key": "booking_id",
                                           "primary_key_value": booking_id,
                                           "sort_key": "vendor_id",
                                           "sort_key_value": vendor_id
                                           })
        except Exception:
            logger.exception("Error while reading data from session table")
            raise DbFetchException(code=500, message="Not able to fetch data from db")
        else:
            try:
                parsed_response = response.json()
            except JSONDecodeError:
                logger.exception(f"Unable to parse fetched data for the booking id: "
                                 f"{booking_id}")
                raise DbFetchException(code=500, message="No data available in response")
            else:
                logger.debug(f"Response from reading table {parsed_response} for booking id "
                             f"{booking_id}")
                return parsed_response

    def run_conclusion_workflow(self):
        data_to_update_db_and_return_status: DataToUpdateInSessionTable = self.conclude_it.conclude_current_charging_status()
        try:
            self.set_current_booking_session_data(data_to_update_db_and_return_status, settings.DB_API)
        except DbFetchException:
            logger.exception("Unable to write data in session table")
            return data_to_update_db_and_return_status
        else:
            return data_to_update_db_and_return_status

    @staticmethod
    def set_current_booking_session_data(result_to_update: DataToUpdateInSessionTable, db_api):
        # update to session db
        try:
            logger.info(f"Current result to update request is {result_to_update}")
            response = requests.post(db_api,
                                     json=result_to_update.dict())
        except Exception:
            raise DbFetchException(code=500, message="Not able to update data to db")
        else:
            return response

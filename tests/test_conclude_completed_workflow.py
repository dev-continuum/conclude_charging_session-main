from unittest import TestCase
import simplejson
import datetime
from app.status_manager import StatusManager
from lambda_handler import lambda_handler

# TODO: ChargingStatus.PROGRESS_UPDATE_UNKNOWN test case
# TODO: ChargingStatus.UNKNOWN_ERROR test case

class TestCompletedWorkFlow(TestCase):
    def setUp(self) -> None:
        with open("./test_data/session_data.json", "r") as fh:
            self.test_data = simplejson.load(fh)

    def mock_get_current_session_data(self, a, b, c):
        return self.test_data

    def mock_set_current_session_data(self, a, b):
        print(a)

    def mock_send_success_stop_request(self, a, b):
        # response = {
        #     "status_code": 400,
        #     "message": "Charging stopped",
        #     "data": {
        #         "booking_id": collective_data_for_current_state.booking_id,
        #         "vendor_id": collective_data_for_current_state.vendor_id,
        #         "reference_transaction_id": 83,
        #         "current_status": "COMPLETED",
        #         "end_time": "2022-11-17 08:01:25",
        #         "final_duration_hour": "00:02:19",
        #         "final_energy_consumed": "1.00",
        #         "stop_charging_status": True,
        #         "user_stopped": True
        #     }
        # }
        response = {"data": {
            "stop_charging_status": True,
            "user_stopped": True
        }}
        return {"stop_charging_status": response["data"]["stop_charging_status"], "user_stopped": False,
                "charging_target_reached": True}

    def mock_send_failure_stop_request(self, a, b):
        response = {"data": {
            "stop_charging_status": False,
            "user_stopped": True
        }}
        return {"stop_charging_status": response["data"]["stop_charging_status"], "user_stopped": False,
                "charging_target_reached": False}

    def test_completed_workflow_conclusion(self):
        current_time = datetime.datetime.utcnow()

        sample_start_time = (current_time - datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["booking_time"] = sample_start_time
        self.test_data["start_time"] = sample_start_time
        self.test_data["current_status"] = "COMPLETED"

        # Mocking the functions so that we don't actually read or write from db
        StatusManager.get_current_booking_session_data = self.mock_get_current_session_data
        StatusManager.set_current_booking_session_data = self.mock_set_current_session_data

        self.monitor = StatusManager(self.test_data)
        # Mocking the request sent to the user api here
        self.monitor.conclude_it.activities[0] = self.mock_send_success_stop_request
        result = self.monitor.run_conclusion_workflow()
        self.assertTrue(result.data_to_update['start_charging_status'])
        self.assertTrue(result.data_to_update['stop_charging_status'])
        self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:10:00')
        self.assertTrue(result.data_to_update['charging_target_reached'])

    def test_terminated_workflow_conclusion(self):
        current_time = datetime.datetime.utcnow()

        sample_start_time = (current_time - datetime.timedelta(minutes=8)).strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["booking_time"] = sample_start_time
        self.test_data["start_time"] = sample_start_time
        self.test_data["current_status"] = "TERMINATED"

        # Mocking the functions so that we don't actually read or write from db
        StatusManager.get_current_booking_session_data = self.mock_get_current_session_data
        StatusManager.set_current_booking_session_data = self.mock_set_current_session_data
        self.monitor = StatusManager(self.test_data)
        # Mocking the request sent to the user api here
        self.monitor.conclude_it.activities[0] = self.mock_send_success_stop_request
        result = self.monitor.run_conclusion_workflow()
        self.assertTrue(result.data_to_update['start_charging_status'])
        self.assertTrue(result.data_to_update['stop_charging_status'])
        self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:08:00')
        self.assertFalse(result.data_to_update['charging_target_reached'])

    def test_start_failed_workflow_conclusion(self):
        current_time = datetime.datetime.utcnow()

        sample_booking_time = (current_time - datetime.timedelta(minutes=8)).strftime('%Y-%m-%d %H:%M:%S')
        sample_start_time = (current_time - datetime.timedelta(minutes=0)).strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["booking_time"] = sample_booking_time
        self.test_data["start_time"] = sample_start_time
        self.test_data["current_status"] = "START_FAILED"

        # Mocking the functions so that we don't actually read or write from db
        StatusManager.get_current_booking_session_data = self.mock_get_current_session_data
        StatusManager.set_current_booking_session_data = self.mock_set_current_session_data
        self.monitor = StatusManager(self.test_data)
        result = self.monitor.run_conclusion_workflow()
        self.assertFalse(result.data_to_update['start_charging_status'])
        self.assertFalse(result.data_to_update['stop_charging_status'])
        self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:00:00')
        self.assertFalse(result.data_to_update['charging_target_reached'])

    def test_stop_failed_but_passed_in_second_try_workflow_conclusion(self):
        current_time = datetime.datetime.utcnow()

        sample_start_time = (current_time - datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["booking_time"] = sample_start_time
        self.test_data["start_time"] = sample_start_time
        self.test_data["current_status"] = "STOP_FAILED"

        # Mocking the functions so that we don't actually read or write from db
        StatusManager.get_current_booking_session_data = self.mock_get_current_session_data
        StatusManager.set_current_booking_session_data = self.mock_set_current_session_data
        self.monitor = StatusManager(self.test_data)
        # Mocking the request sent to the user api here
        self.monitor.conclude_it.activities[0] = self.mock_send_success_stop_request
        result = self.monitor.run_conclusion_workflow()
        self.assertTrue(result.data_to_update['start_charging_status'])
        self.assertTrue(result.data_to_update['stop_charging_status'])
        self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:10:00')
        self.assertTrue(result.data_to_update['charging_target_reached'])

    def test_stop_failed_in_second_try_workflow_conclusion(self):
        current_time = datetime.datetime.utcnow()

        sample_start_time = (current_time - datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["booking_time"] = sample_start_time
        self.test_data["start_time"] = sample_start_time
        self.test_data["current_status"] = "STOP_FAILED"

        # Mocking the functions so that we don't actually read or write from db
        StatusManager.get_current_booking_session_data = self.mock_get_current_session_data
        StatusManager.set_current_booking_session_data = self.mock_set_current_session_data
        self.monitor = StatusManager(self.test_data)
        # Mocking the request sent to the user api here
        self.monitor.conclude_it.activities[0] = self.mock_send_failure_stop_request
        result = self.monitor.run_conclusion_workflow()
        self.assertTrue(result.data_to_update['start_charging_status'])
        self.assertFalse(result.data_to_update['stop_charging_status'])
        self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:10:00')
        self.assertFalse(result.data_to_update['charging_target_reached'])


class TestCompletedWorkFlowWithoutMocks(TestCase):
    """
    ###############################################
    PROVIDE REAL TIME SESSION DATA IN JSON FILE BEFORE RUNNING THIS TEST
    """
    def setUp(self) -> None:
        with open("./test_data/real_session_data.json", "r") as fh:
            self.test_data = simplejson.load(fh)
    def test_completed_workflow_conclusion_without_mocking(self):
        result = lambda_handler(self.test_data, None)
        print(result)

        # self.assertTrue(result.data_to_update['start_charging_status'])
        # self.assertTrue(result.data_to_update['stop_charging_status'])
        # self.assertEqual(result.data_to_update['final_duration_timestamp'], '00:10:00')
        # self.assertTrue(result.data_to_update['charging_target_reached'])

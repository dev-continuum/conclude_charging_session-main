import datetime
from unittest import TestCase
import simplejson
from app.status_manager import StatusManager
from data_store.data_structure import ChargingStatus
from data_store.data_schemas import DataToUpdateInSessionTable
from config import Settings

settings = Settings()


class TestReadFromDB(TestCase):
    def setUp(self) -> None:
        with open("./test_data/session_data.json", "r") as fh:
            self.test_data = simplejson.load(fh)
        print(self.test_data)
        self.test_data["start_time"] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        self.test_data["current_status"] = "COMPLETED"
        self.status_manager = StatusManager(event=self.test_data)

    def test_read_data_from_session_db(self):
        response = self.status_manager.get_current_booking_session_data(settings.DB_API, self.test_data["booking_id"],
                                                                        self.test_data["vendor_id"])
        self.assertEqual(response["booking_id"], self.test_data["booking_id"])


class TestUpdateDB(TestCase):
    def setUp(self) -> None:
        with open("./test_data/session_data.json", "r") as fh:
            self.test_data = simplejson.load(fh)
            self.test_data["start_time"] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            self.test_data["current_status"] = "IN_PROGRESS"
        self.status_manager = StatusManager(self.test_data)
        self.result_to_update = DataToUpdateInSessionTable.parse_obj({
            "update_table": True,
            "table_name": "ChargingSessionRecords",
            "primary_key": {"booking_id": self.test_data["booking_id"]},
            "sort_key": {"vendor_id": self.test_data["vendor_id"]},
            "data_to_update": {"current_status": "TEST",
                               "current_energy_consumed": 10,
                               "current_charging_timer": "00:34:90"}
        })

    def test_write_data_to_session_db(self):
        response = self.status_manager.set_current_booking_session_data(self.result_to_update, settings.DB_API)
        self.assertEqual(response.status_code, 200)



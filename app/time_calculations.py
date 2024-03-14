from data_store.data_schemas import DurationCalculatorData, CollectiveDataForCurrentState
from pydantic import BaseModel
from typing import Optional
import pytz
from logger_init import get_logger
import datetime
import time

logger = get_logger(__name__)


class PrepareTimeDataForCurrentState(BaseModel):
    collective_data_for_current_state: CollectiveDataForCurrentState
    iso_formatted_booking_time: Optional[datetime.datetime] = None
    iso_formatted_start_time: Optional[datetime.datetime] = None
    target_duration_delta: Optional[datetime.timedelta] = None
    current_duration: Optional[DurationCalculatorData] = None
    current_end_time_object: Optional[datetime.datetime] = None
    readable_time_summary: Optional[str] = None
    current_booking_duration: Optional[DurationCalculatorData] = None

    def calculate_time_related_data(self):
        logger.info(f"Calculating time related data for the booking id "
                    f"{self.collective_data_for_current_state.booking_id}, "
                    f"start time: {self.collective_data_for_current_state.start_time}")
        if self.collective_data_for_current_state.start_time and self.collective_data_for_current_state.target_duration_timestamp:
            self.iso_formatted_start_time = self.define_time_in_iso_format(
                self.collective_data_for_current_state.start_time)
            self.current_end_time_object = self.calculate_end_time()
            self.readable_time_summary = self.get_readable_time_summary()
            self.target_duration_delta = self.convert_time_stamp_to_time_delta(
                self.collective_data_for_current_state.target_duration_timestamp)
            self.current_duration = self.calculate_duration(self.iso_formatted_start_time)

        elif self.collective_data_for_current_state.start_time and self.collective_data_for_current_state.target_energy_kw:
            self.iso_formatted_start_time = self.define_time_in_iso_format(
                self.collective_data_for_current_state.start_time)
            self.current_end_time_object = self.calculate_end_time()
            self.readable_time_summary = self.get_readable_time_summary()
            self.current_duration = self.calculate_duration(self.iso_formatted_start_time)

        elif self.collective_data_for_current_state.session_data["booking_time"]:
            self.iso_formatted_booking_time = self.define_time_in_iso_format(
                self.collective_data_for_current_state.session_data["booking_time"])
            self.current_booking_duration = self.calculate_duration(self.iso_formatted_booking_time)
            self.current_duration = self.calculate_duration(self.define_time_in_iso_format("1900-01-01 00:00:00"),
                                                            self.define_time_in_iso_format("1900-01-01 00:00:00"))

        else:
            logger.info("Neither start nor booking time is defined aborting")

        logger.info(f"All time related parameters are set. current duration: {self.current_duration}, "
                    f"summary: {self.readable_time_summary}")

    def generate_user_readable_summary(self):
        return {"date": self.iso_formatted_start_time.date(),
                "start_time": self.iso_formatted_start_time.time().strftime()}

    @staticmethod
    def calculate_end_time():
        return datetime.datetime.now(pytz.timezone('UTC'))

    @staticmethod
    def define_time_in_iso_format(start_time):
        logger.info(f"Defining time {start_time} in iso format")
        try:
            iso_formatted_start_time = datetime.datetime.fromisoformat(start_time)
        except ValueError:
            logger.exception("time format is not correct")
            raise
        else:
            return iso_formatted_start_time

    @staticmethod
    def convert_time_stamp_to_time_delta(time_stamp: str) -> datetime.timedelta:
        date_time_object = datetime.datetime.strptime(time_stamp, "%H:%M:%S")
        return datetime.timedelta(hours=date_time_object.hour, minutes=date_time_object.minute,
                                  seconds=date_time_object.second)

    @staticmethod
    def calculate_duration(iso_formatted_time, current_time=None):
        if not current_time:
            current_time = datetime.datetime.utcnow()
        current_duration_delta = (current_time - iso_formatted_time)
        current_duration_as_time_stamp_string = time.strftime("%H:%M:%S",
                                                              time.gmtime(current_duration_delta.total_seconds()))
        return DurationCalculatorData.parse_obj(
            {"duration_delta": current_duration_delta,
             "duration_as_time_stamp_string": current_duration_as_time_stamp_string}
        )

    def get_readable_time_summary(self):
        time_sumarry = {}
        time_sumarry.update({"date_string": self.iso_formatted_start_time.date().strftime("%d-%b-%Y"),
                             "start_time": self.iso_formatted_start_time.astimezone(pytz.timezone("Asia/Calcutta")).strftime('%I:%M %p'),
                             "end_time": self.current_end_time_object.astimezone(pytz.timezone("Asia/Calcutta")).strftime('%I:%M %p')})
        return time_sumarry


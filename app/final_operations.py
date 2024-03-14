from data_store.data_schemas import CollectiveDataForCurrentState, FinalOperationData, FinalDecisionData
from app.time_calculations import PrepareTimeDataForCurrentState
from lamda_services.lambda_communicator import invoke_third_party_url_lambda
from logger_init import get_logger

logger = get_logger(__name__)


class OperateOnFinalData:

    def __init__(self, collective_data_for_current_state, time_related_data, lambda_client, tariff_data):
        self.collective_data_for_current_state: CollectiveDataForCurrentState = collective_data_for_current_state
        self.time_related_data: PrepareTimeDataForCurrentState = time_related_data
        self.lambda_client = lambda_client
        self.tariff_data = tariff_data

    def calculate_final_charge(self, parsed_decision_data: FinalDecisionData):
        amount_in_rs = float((self.time_related_data.current_duration.duration_delta.total_seconds() / (60 * 60)) \
                             * float(parsed_decision_data.final_energy_consumed)\
                             * self.tariff_data[self.collective_data_for_current_state.vendor_id]["tariff"])
        logger.info(f"Calculated final cost current charging session {amount_in_rs}")
        return {"final_cost": amount_in_rs}

    def calculate_emission_saved(self):
        return {"emission_saved": self.collective_data_for_current_state.session_data["emission_saved"]}

    def calculate_battery_status(self):
        return {"battery_status": self.collective_data_for_current_state.session_data["battery_status"]}

    def calculate_current_range(self):
        return {"current_range": self.collective_data_for_current_state.session_data["current_range"]}

    def deduct_wallet(self, parsed_decision_data: FinalDecisionData, final_cost):
        payload_data = {"user_id": self.collective_data_for_current_state.session_data["user_id"],
                        "amount": int(final_cost["final_cost"]),
                        "add": False,
                        "deduct": True
                        }

        payload = {
            "action": "UPDATE",
            "data": payload_data
        }

        logger.info(f"Going to deduct wallet for user this payload {payload_data}")
        response = invoke_third_party_url_lambda(lambda_client=self.lambda_client, function_name="wallet_service",
                                                 payload=payload)
        logger.info(f"Here is the response from wallet service {response}")
        if response["status_code"] == 200:
            wallet_data = response["data"]
            return {"wallet_details": {"available_wallet_balance":
                                           wallet_data["final_wallet_balance"] + wallet_data["amount"],
                                       "final_charging_cost": wallet_data["amount"],
                                       "wallet_balance_left": wallet_data["final_wallet_balance"],
                                       "wallet_deduction_success": True}}
        else:
            return {"wallet_details": {"available_wallet_balance": None,
                                       "final_charging_cost": final_cost["final_cost"],
                                       "wallet_balance_left": None, "wallet_deduction_success": False}}

    def operate(self, parsed_decision_data: FinalDecisionData):
        operation_final_data = {}
        final_cost = self.calculate_final_charge(parsed_decision_data)
        operation_final_data.update(final_cost)
        operation_final_data.update(self.calculate_current_range())
        operation_final_data.update(self.calculate_emission_saved())
        operation_final_data.update(self.calculate_battery_status())
        operation_final_data.update(self.deduct_wallet(parsed_decision_data, final_cost))
        return FinalOperationData.parse_obj(operation_final_data)

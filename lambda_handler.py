import simplejson
from app.status_manager import StatusManager, SocketCommunicator
from app import get_socket_client
from exceptions.exception import SocketException
from logger_init import get_logger

logger = get_logger(__name__)


def lambda_handler(event, context):
    try:
        logger.info(f"Passing this event to status manager {event}")
        status_manager = StatusManager(event)
        latest_result = status_manager.run_conclusion_workflow()
    except Exception:
        logger.exception("Exception in performing final status")
    else:
        try:
            socket_comm = SocketCommunicator(get_socket_client(), latest_result, status_manager.collective_data_for_current_state)
            socket_comm.send_message_to_socket()
        except SocketException:
            logger.exception("Unable to send data on socket but we will continue the state machine")
            return {"socket_communication": False}
        else:
            return {"socket_communication": True}

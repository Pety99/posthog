from pydantic import BaseModel
from posthog.warehouse.external_data_source.client import send_request
from posthog.warehouse.models import ExternalDataSource
import structlog

AIRBYTE_CONNECTION_URL = "https://api.airbyte.com/v1/connections"
AIRBYTE_JOBS_URL = "https://api.airbyte.com/v1/jobs"
AIRBYTE_STREAMS_URL = "https://api.airbyte.com/v1/streams"

logger = structlog.get_logger(__name__)


class ExternalDataConnection(BaseModel):
    connection_id: str
    source_id: str
    destination_id: str
    name: str
    workspace_id: str


def create_connection(source_id: str, destination_id: str) -> ExternalDataConnection:
    payload = {
        "schedule": {"scheduleType": "cron", "cronExpression": "0 0 0 * * ?"},
        "namespaceFormat": None,
        "sourceId": source_id,
        "destinationId": destination_id,
    }

    response = send_request(AIRBYTE_CONNECTION_URL, method="POST", payload=payload)

    update_connection_stream(response["connectionId"])

    return ExternalDataConnection(
        source_id=response["sourceId"],
        name=response["name"],
        connection_id=response["connectionId"],
        workspace_id=response["workspaceId"],
        destination_id=response["destinationId"],
    )


def get_active_connection_streams_by_id(connection_id: str):
    connection_streams = get_connection_by_id(connection_id)["configurations"]["streams"]
    return connection_streams


def get_connection_by_id(connection_id: str):
    connection_id_url = f"{AIRBYTE_CONNECTION_URL}/{connection_id}"
    response = send_request(connection_id_url, method="GET")
    return response


def activate_connection_by_id(connection_id: str):
    update_connection_status_by_id(connection_id, "active")


def deactivate_connection_by_id(connection_id: str):
    update_connection_status_by_id(connection_id, "inactive")


def update_connection_status_by_id(connection_id: str, status: str):
    connection_id_url = f"{AIRBYTE_CONNECTION_URL}/{connection_id}"

    payload = {"status": status}

    send_request(connection_id_url, method="PATCH", payload=payload)


def update_connection_stream(connection_id: str):
    connection_id_url = f"{AIRBYTE_CONNECTION_URL}/{connection_id}"

    # TODO: hardcoded to stripe stream right now
    payload = {
        "configurations": {"streams": [{"name": "customers", "syncMode": "full_refresh_overwrite"}]},
        "schedule": {"scheduleType": "cron", "cronExpression": "0 0 0 * * ?"},
        "namespaceFormat": None,
        "prefix": "stripe_",
    }

    send_request(connection_id_url, method="PATCH", payload=payload)


def delete_connection(connection_id: str) -> None:
    send_request(AIRBYTE_CONNECTION_URL + "/" + connection_id, method="DELETE")


def get_connection_streams_by_external_data_source(external_data_source: ExternalDataSource):
    return get_connection_streams_by_ids(external_data_source.source_id, external_data_source.destination_id)


def get_connection_streams_by_ids(source_id: str, destination_id: str):
    streams_url = f"{AIRBYTE_STREAMS_URL}"

    params = {
        "destinationId": destination_id,
        "sourceId": source_id,
    }
    response = send_request(streams_url, method="GET", params=params)

    return response


# Fire and forget
def start_sync(connection_id: str):
    payload = {"jobType": "sync", "connectionId": connection_id}

    try:
        send_request(AIRBYTE_JOBS_URL, method="POST", payload=payload)
    except Exception as e:
        logger.exception(
            f"Data Warehouse: Sync Resource failed with an unexpected exception for connection id: {connection_id}",
            exc_info=e,
        )


def retrieve_sync(connection_id: str):
    params = {"connectionId": connection_id, "limit": 1}
    response = send_request(AIRBYTE_JOBS_URL, method="GET", params=params)

    data = response.get("data", [])
    if not data:
        return None

    latest_job = response["data"][0]

    return latest_job

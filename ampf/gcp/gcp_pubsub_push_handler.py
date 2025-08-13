import inspect
import logging

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse


def gcp_pubsub_push_handler():
    _log = logging.getLogger(__name__)

    def decorator(func):
        sig = inspect.signature(func)
        first_param = next(iter(sig.parameters.values()))
        first_param_type = first_param.annotation
        if issubclass(first_param_type, BaseModel):
            payload_class = first_param_type

        async def wrapper(request: GcpPubsubRequest) -> GcpPubsubResponse:
            try:
                payload = request.decoded_data(payload_class)
                result = await func(payload)
                if result:
                    request.publish_response(result)
                # Return acknowledgment
                return GcpPubsubResponse(status="acknowledged", messageId=request.message.messageId)
            except ValidationError as e:
                _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
                raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")
            except Exception as e:
                _log.error("Error processing message ID %s: %s", request.message.messageId, e)
                raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper.__qualname__ = func.__qualname__
        return wrapper

    return decorator

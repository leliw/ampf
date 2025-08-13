import inspect
import logging

from fastapi import HTTPException
from pydantic import ValidationError

from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse


def gcp_pubsub_push_handler():
    """
    Decorator factory for handling Google Cloud Pub/Sub push messages.
    Wraps an async function to:
    - Parse and validate the incoming Pub/Sub request.
    - Decode the payload using the provided Pydantic model.
    - Handle errors and return appropriate HTTP responses.
    - Optionally publish a response.
    """
    _log = logging.getLogger(__name__)

    def decorator(func):
        # Inspect the signature of the decorated function
        sig = inspect.signature(func)
        first_param = next(iter(sig.parameters.values()))
        first_param_name = first_param.name
        payload_class = first_param.annotation

        async def wrapper(*args, **kwargs) -> GcpPubsubResponse:
            """
            Wrapper function that:
            - Extracts and decodes the Pub/Sub request payload.
            - Calls the decorated function with the decoded payload.
            - Handles validation and processing errors.
            """
            try:
                # Get the GcpPubsubRequest object from args or kwargs
                request: GcpPubsubRequest = args[0] if len(args) > 0 else kwargs.get(first_param_name)  # type: ignore
                # Decode the payload using the expected Pydantic model
                payload = request.decoded_data(payload_class)
                # Inject the decoded payload into kwargs for the decorated function
                kwargs[first_param_name] = payload
                # Remove the original request from args if present
                new_args = args[1:] if len(args) > 0 else args
                # Call the decorated function with the decoded payload
                result = await func(*new_args, **kwargs)
                if result:
                    # Optionally publish a response if the decorated function returns one
                    request.publish_response(result)
                # Return acknowledgment response
                return GcpPubsubResponse(status="acknowledged", messageId=request.message.messageId)
            except ValidationError as e:
                # Handle payload validation errors
                _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
                raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")
            except Exception as e:
                # Handle all other processing errors
                _log.error("Error processing message ID %s: %s", request.message.messageId, e)
                raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

        # Adjust the wrapper's signature to expect a GcpPubsubRequest as the first argument
        params = list(sig.parameters.values())
        params[0] = params[0].replace(annotation=GcpPubsubRequest)
        wrapper.__signature__ = sig.replace(parameters=params, return_annotation=GcpPubsubResponse)
        return wrapper

    return decorator

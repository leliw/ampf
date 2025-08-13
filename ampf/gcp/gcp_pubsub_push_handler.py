try:
    import inspect
    import logging

    from fastapi import HTTPException
    from pydantic import BaseModel, ValidationError

    from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse


    def gcp_pubsub_push_handler():
        """
        Decorator for FastAPI endpoints to handle Google Cloud Pub/Sub push messages.
        It automatically decodes the incoming Pub/Sub message into a Pydantic model,
        validates it, and handles errors in a standardized way.
        """
        _log = logging.getLogger(__name__)

        def decorator(func):
            # Inspect the function signature to find the parameter annotated with a Pydantic BaseModel
            sig = inspect.signature(func)
            payload_name = None
            payload_class = None
            for name, param in sig.parameters.items():
                ann = param.annotation
                if inspect.isclass(ann) and issubclass(ann, BaseModel):
                    payload_name = name
                    payload_class = ann
                    break
            if payload_name is None:
                raise TypeError("No parameter annotated with a Pydantic BaseModel found in endpoint.")

            async def wrapper(*args, **kwargs) -> GcpPubsubResponse:
                """
                Wrapper function that:
                - Decodes and validates the Pub/Sub message payload
                - Calls the decorated endpoint function with the validated payload
                - Handles validation and processing errors
                - Publishes a response if returned by the endpoint
                - Returns a standardized acknowledgment response
                """
                try:
                    # Extract the GcpPubsubRequest from the arguments
                    request: GcpPubsubRequest = args[0] if len(args) > 0 else kwargs.get(payload_name)  # type: ignore
                    # Decode and validate the payload using the specified Pydantic model
                    payload = request.decoded_data(payload_class)  # type: ignore
                    kwargs[payload_name] = payload
                    # Remove the original request from args before passing to the endpoint
                    new_args = args[1:] if len(args) > 0 else args
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

            # Adjust the wrapper's signature to expect a GcpPubsubRequest instead of the original payload model
            params = []
            for name, param in sig.parameters.items():
                if name == payload_name:
                    params.append(param.replace(annotation=GcpPubsubRequest))
                else:
                    params.append(param)
            wrapper.__signature__ = sig.replace(parameters=params, return_annotation=GcpPubsubResponse)
            return wrapper

        return decorator

except ImportError:
    pass
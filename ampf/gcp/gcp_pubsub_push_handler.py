from inspect import Parameter
from typing import Annotated, Any, AsyncIterator, Coroutine, Iterator, List, Optional, Type, get_args, get_origin

from .gcp_base_factory import GcpBaseFactory

try:
    import inspect
    import logging

    from fastapi import HTTPException
    from pydantic import BaseModel, ValidationError

    from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse

    def gcp_pubsub_push_handler[T: GcpBaseFactory](factory_dep: Optional[Type[T] | Any] = None):
        """
        Decorator for FastAPI endpoints to handle Google Cloud Pub/Sub push messages.
        It automatically decodes the incoming Pub/Sub message into a Pydantic model,
        validates it, and handles errors in a standardized way.
        """
        _log = logging.getLogger(__name__)

        def decorator(func):
            sig = inspect.signature(func)
            payload_name = None
            payload_class = None
            gcp_request_name = None
            gcp_factory_name = None
            for name, param in sig.parameters.items():
                ann = param.annotation
                origin = get_origin(ann)
                if ann is GcpPubsubRequest:
                    gcp_request_name = name
                elif origin is Annotated:
                    # The first argument to Annotated is the actual type.
                    annotated_type = get_args(ann)[0]
                    if inspect.isclass(annotated_type) and issubclass(annotated_type, GcpBaseFactory):
                        gcp_factory_name = name
                elif inspect.isclass(ann) and issubclass(ann, BaseModel):
                    payload_name = name
                    payload_class = ann
            if not gcp_factory_name and factory_dep:
                gcp_factory_name = "gcp_factory"
            if payload_name is None:
                raise TypeError("No parameter annotated with a Pydantic BaseModel found in endpoint.")

            async def wrapper(*args, **kwargs) -> GcpPubsubResponse:
                try:
                    if gcp_factory_name and factory_dep:
                        gcp_factory = kwargs.pop(gcp_factory_name)
                    elif gcp_factory_name:
                        gcp_factory = kwargs.get(gcp_factory_name)
                    else:
                        gcp_factory = None
                    # If GcpPubsubRequest is already in the signature, use it directly
                    if gcp_request_name:
                        request: GcpPubsubRequest = kwargs.get(gcp_request_name)  # type: ignore
                        if request is None and len(args) > 0:
                            # Try to get by position
                            param_names = list(sig.parameters.keys())
                            idx = param_names.index(gcp_request_name)
                            request = args[idx] if idx < len(args) else None
                        if request is None:
                            raise TypeError("GcpPubsubRequest argument not found in call.")
                        payload = request.decoded_data(payload_class)  # type: ignore
                        kwargs[payload_name] = payload
                        ret = func(*args, **kwargs)
                    else:
                        # Extract the GcpPubsubRequest from the arguments (assume first positional)
                        request: GcpPubsubRequest = args[0] if len(args) > 0 else kwargs.get(payload_name)  # type: ignore
                        payload = request.decoded_data(payload_class)  # type: ignore
                        kwargs[payload_name] = payload
                        # Remove the original request from args before passing to the endpoint
                        new_args = args[1:] if len(args) > 0 else args
                        ret = func(*new_args, **kwargs)
                    if isinstance(ret, Coroutine):
                        ret = await ret
                    if isinstance(ret, AsyncIterator):
                        async for result in ret:
                            request.publish_response(result, gcp_factory=gcp_factory)
                    elif isinstance(ret, Iterator) or isinstance(ret, List):
                        for result in ret:
                            request.publish_response(result, gcp_factory=gcp_factory)
                    elif ret:
                        request.publish_response(ret, gcp_factory=gcp_factory)
                    return GcpPubsubResponse(status="acknowledged", messageId=request.message.messageId)
                except ValidationError as e:
                    _log.exception(
                        "Error processing message ID: %s",
                        request.message.messageId,
                        extra={"attributes": request.message.attributes},
                    )
                    raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")
                except ValueError as e:
                    _log.exception(
                        "Error processing message ID: %s",
                        request.message.messageId,
                        extra={"attributes": request.message.attributes},
                    )
                    raise HTTPException(status_code=400, detail=f"Value error: {e}")
                except Exception as e:
                    _log.exception(
                        "Error processing message ID %s",
                        request.message.messageId,
                        extra={"attributes": request.message.attributes},
                    )
                    raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

            params = []
            for name, param in sig.parameters.items():
                if name == payload_name:
                    if not gcp_request_name:
                        params.append(param.replace(annotation=GcpPubsubRequest))
                else:
                    params.append(param)
            if factory_dep:
                param = Parameter("gcp_factory", Parameter.KEYWORD_ONLY, annotation=factory_dep)
                params.append(param.replace(annotation=factory_dep))
            wrapper.__signature__ = sig.replace(parameters=params, return_annotation=GcpPubsubResponse)
            return wrapper

        return decorator

except ImportError:
    pass

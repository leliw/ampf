import logging

try:
    from fastapi import HTTPException
    from pydantic import ValidationError

    from ampf.gcp.gcp_pubsub_model import GcpPubsubRequest, GcpPubsubResponse
    from ampf.gcp.subscription_processor import SubscriptionProcessor

    _log = logging.getLogger(__name__)


    async def gcp_pubsub_process_push(processor: SubscriptionProcessor, request: GcpPubsubRequest) -> GcpPubsubResponse:
        try:
            await processor.process_request(request)
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
except ImportError:
    pass
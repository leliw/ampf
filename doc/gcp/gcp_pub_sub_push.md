# GCP Pub/Sub Push

For services launched in GCP, delivering messages using a standard subscription (Pull) message is not recommended.
A better solution is to deliver (Push) - sending a message to a specified endpoint.

There are special classes to handle this:

* `GcpPubsubRequest`
* `GcpPubsubMessage`
* `GcpPubsubResponse`

An example of an endpoint receiving messages.

```python
router = APIRouter(tags=["Pub/Sub Push"])

@router.post("")
async def handle_push(request: GcpPubsubRequest) -> GcpPubsubResponse:
    try:
        payload = request.decoded_data(D)
        payload.name = f"Processed: {payload.name}"
        request.publish_response(payload)

        # Return acknowledgment
        return GcpPubsubResponse(status="acknowledged", messageId=request.message.messageId)

    except ValidationError as e:
        _log.error("Error processing message ID: %s: %s", request.message.messageId, e)
        raise HTTPException(status_code=400, detail=f"Wrong message format: {e}")
    except Exception as e:
        _log.error("Error processing message ID %s: %s", request.message.messageId, e)
        raise HTTPException(status_code=500, detail=f"Error processing message: {e}")
```

# gcp_pubsub_process_push

This is a helper function for processing GCP Pub/Sub push messages. It is designed to be used in FastAPI applications to handle incoming Pub/Sub messages, decode their payloads, and publish responses if needed.

## Parameters

* `processor: SubscriptionProcessor` - processor object which process the message.
* `request: GcpPubsubRequest` - request object receieved from Pub/Sub.

## Usage

```python
class DProcessor(SubscriptionProcessor[D]):
    async def process_payload(self, payload: D) -> D:
        self.called = True
        return D(name=f"Processed by processor: {payload.name}")

def get_d_processor(async_factory: AsyncFactoryDep) -> DProcessor:
    return DProcessor(async_factory, D)

DProcessorDep = Annotated[DProcessor, Depends(get_d_processor)]

@router.post("/processor")
async def handle_processor(processor: DProcessorDep, request: GcpPubsubRequest) -> GcpPubsubResponse:
    return await gcp_pubsub_process_push(processor, request)
```

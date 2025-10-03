import asyncio
from typing import Optional

import docker
import pytest

from ampf.base.base_email_sender import BaseEmailSender
from ampf.gcp.gcp_async_factory import GcpAsyncFactory
from ampf.gcp.gcp_factory import GcpFactory
from ampf.in_memory.in_memory_factory import InMemoryFactory


@pytest.fixture(scope="session")
def gcp_factory():
    # Creating firestore client is very slow.
    # Scope == session speeds up tests
    return GcpFactory(bucket_name='unit-tests-001')

@pytest.fixture(scope="session")
def gcp_async_factory():
    # Creating firestore client is very slow.
    # Scope == session speeds up tests
    return GcpAsyncFactory(bucket_name='unit-tests-001')

@pytest.fixture(scope="session")
def collection_name():
    return "tests-ampf-gcp"


@pytest.fixture(scope="session")
def factory():
    """Return an instance of the in-memory factory."""
    return InMemoryFactory()


class TestEmailSender(BaseEmailSender):
    """A test email sender that stores sent emails in memory."""

    def __init__(self):
        self.sent_emails = []

    def send(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        self.sent_emails.append(
            {
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "attachment_path": attachment_path,
            }
        )


@pytest.fixture
def email_sender():
    """Return an instance of the test email sender."""
    return TestEmailSender()


# There are firestore client's errors without it 
@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def docker_client():
    return docker.from_env()
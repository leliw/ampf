from typing import Optional
import pytest

from ampf.base.base_email_sender import BaseEmailSender
from ampf.in_memory.in_memory_factory import InMemoryFactory


@pytest.fixture
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

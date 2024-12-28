from typing import Optional
from abc import ABC, abstractmethod


class BaseEmailSender(ABC):
    """An abstract base class for email senders"""

    @abstractmethod
    def send(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        """Send an email

        Args:
            sender: The sender email address
            recipient: The recipient email address
            subject: The email subject
            body: The email body
            attachment_path: The path to the attachment file
        """
        pass

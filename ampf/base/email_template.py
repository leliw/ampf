from typing import Dict


class EmailTemplate:
    """An email template to render emails."""

    def __init__(
        self,
        sender: str,
        subject: str,
        body_template: str,
        attachment_path: str = None,
    ):
        """Initialize the email template.

        Args:
            sender: The email sender.
            subject: The email subject.
            body_template: The email body template.
            attachment_path: The path to the attachment file. Defaults to None.
        """
        self.sender = sender
        self.subject = subject
        self.body_template = body_template
        self.attachment_path = attachment_path

    def render(self, recipient: str, **kwargs) -> Dict[str, str]:
        """Render the email template.

        Args:
            recipient: The email recipient.
            **kwargs: Additional keyword arguments for the template.
        Returns:
            A dictionary with the email data.
        """
        return {
            "sender": self.sender,
            "recipient": recipient,
            "subject": self.subject,
            "body": self.body_template.format(**kwargs),
            "attachment_path": self.attachment_path,
        }

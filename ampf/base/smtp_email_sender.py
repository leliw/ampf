from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP, SMTP_SSL
from typing import Optional

from .base_email_sender import BaseEmailSender


class SmtpEmailSender(BaseEmailSender):
    """Email sender using SMTP protocol."""

    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = False,
    ):
        """Initialize the SMTP email sender.

        Args:
            host: SMTP server host.
            port: SMTP server port.
            username: SMTP server username. Defaults to None.
            password: SMTP server password. Defaults to None.
            use_ssl (bool, optional): Use SSL connection. Defaults to False.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl

    def send(
        self,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None,
    ) -> None:
        """Send an email.

        Args:
            sender: Email sender.
            recipient: Email recipient.
            subject: Email subject.
            body: Email body.
            attachment_path: Path to the attachment file. Defaults to None.
        """
        message = MIMEMultipart()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attachment_path:
            with open(attachment_path, "rb") as attachment:
                message.attach(MIMEText(attachment.read(), "plain"))

        with SMTP(self.host, self.port) if not self.use_ssl else SMTP_SSL(
            self.host, self.port
        ) as server:
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(sender, recipient, message.as_string())

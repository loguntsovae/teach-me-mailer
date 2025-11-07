from typing import List, Optional

import structlog

from app.core.config import Settings


logger = structlog.get_logger(__name__)


class DomainValidationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.allowed_domains = settings.allow_domains

    def is_domain_allowed(self, email: str) -> bool:
        """Check if email domain is allowed."""
        if not self.allowed_domains:
            # If no domain restrictions, allow all
            return True
        
        try:
            domain = email.split('@')[1].lower()
            is_allowed = domain in [d.lower() for d in self.allowed_domains]
            
            if not is_allowed:
                logger.warning(
                    "Email domain not allowed",
                    email=email,
                    domain=domain,
                    allowed_domains=self.allowed_domains,
                )
            
            return is_allowed
            
        except (IndexError, AttributeError):
            logger.error("Invalid email format", email=email)
            return False

    def filter_allowed_emails(self, emails: List[str]) -> tuple[List[str], List[str]]:
        """Filter emails by allowed domains.
        
        Returns:
            tuple: (allowed_emails, rejected_emails)
        """
        if not self.allowed_domains:
            return emails, []
        
        allowed = []
        rejected = []
        
        for email in emails:
            if self.is_domain_allowed(email):
                allowed.append(email)
            else:
                rejected.append(email)
        
        if rejected:
            logger.info(
                "Some emails rejected due to domain restrictions",
                total=len(emails),
                allowed=len(allowed),
                rejected=len(rejected),
                rejected_emails=rejected,
            )
        
        return allowed, rejected

    def get_allowed_domains(self) -> Optional[List[str]]:
        """Get list of allowed domains."""
        return self.allowed_domains
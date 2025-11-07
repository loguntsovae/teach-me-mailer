# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial mail gateway service implementation
- FastAPI-based REST API for email sending
- API key-based authentication system
- Rate limiting with atomic operations
- Database logging of sent emails
- Docker containerization
- Comprehensive test suite
- Sentry integration for error tracking
- Postman collection for API testing

### Security
- API key authentication for all endpoints
- Rate limiting to prevent abuse
- Input validation and sanitization
- Domain validation for email addresses

## [0.1.0] - 2025-11-07

### Added
- Initial release of teach-me-mailer
- Core email sending functionality
- Basic API structure
- Documentation and setup instructions
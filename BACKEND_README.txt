================================================================================
LMS COURSE BUILDER - BACKEND API
Production-Grade FastAPI Backend with Admin Features
================================================================================

OVERVIEW
--------
A complete, production-quality backend API for an LMS (Learning Management
System) built with FastAPI, SQLite, and SQLAlchemy. Includes comprehensive
admin features, security, and AI integration.

BACKEND STRUCTURE
-----------------

backend/
├── main.py                    # FastAPI app setup, startup/shutdown, routes
├── config.py                  # Configuration settings and environment variables
├── database.py                # SQLAlchemy setup, session management
├── requirements.txt           # Python dependencies
├── .env.example              # Example environment variables
│
├── models/                    # Database models
│   ├── __init__.py           # Model exports
│   └── models.py             # All SQLAlchemy models (11 total)
│
├── services/                  # Business logic and external integrations
│   ├── __init__.py           # Service exports
│   ├── auth_service.py       # JWT, password hashing, TOTP/MFA, password policy
│   └── claude_service.py     # Claude API integration for course generation
│
├── middleware/                # Request/response processing
│   ├── __init__.py           # Middleware exports
│   └── auth_middleware.py    # JWT extraction, RBAC, rate limiting
│
└── routers/                   # API endpoints (6 modules)
    ├── __init__.py           # Router exports
    ├── auth.py               # Login, logout, refresh, MFA, profile
    ├── users.py              # User management (CRUD, MFA toggle, bulk import)
    ├── courses.py            # Course management, Claude generation, enrollment
    ├── security.py           # Sessions, login monitoring, audit logs, IP allowlist
    ├── dev_tools.py          # Errors, health, API usage, feature flags
    └── whitelabel.py         # Theme config, logo/favicon upload, import/export

KEY FEATURES IMPLEMENTED
------------------------

1. AUTHENTICATION & SECURITY
   - JWT token-based authentication (30-minute expiration)
   - Refresh tokens (7-day expiration)
   - TOTP/MFA support with QR code generation
   - Password hashing with bcrypt (12 rounds)
   - Strong password policy (8+ chars, uppercase, lowercase, digit, special)
   - Account lockout after 5 failed attempts (15-minute cooldown)
   - Session tracking with IP and user agent

2. USER MANAGEMENT (ADMIN-ONLY)
   - Create, read, update, deactivate users
   - Role-based access control (Admin/Creator/Trainee)
   - Password reset with temporary passwords
   - Bulk user import from CSV
   - MFA toggle and TOTP secret management
   - Activity tracking and audit logs

3. COURSE MANAGEMENT
   - Full CRUD for courses (creators and admins)
   - Course status tracking (draft/published/archived)
   - Claude AI integration for automated course generation
   - Support for custom generation parameters
   - Course enrollment system
   - Student progress tracking

4. SECURITY & MONITORING
   - Session management and killswitching
   - Login attempt tracking
   - Comprehensive audit logs
   - IP allowlist functionality
   - Error logging with request IDs
   - Rate limiting (configurable, in-memory for dev)

5. DEVELOPMENT TOOLS (ADMIN-ONLY)
   - Real-time error log monitoring
   - System health check (CPU, memory, disk, uptime)
   - Claude API usage tracking and cost estimation
   - Feature flags for gradual feature rollout
   - Environment information endpoint

6. WHITE LABEL BRANDING
   - Full theme customization
   - Dynamic color configuration (primary, secondary, accent)
   - Custom fonts (body and heading)
   - Border radius and button styles
   - Logo and favicon upload support
   - Custom CSS injection
   - Import/export configuration as JSON

DATABASE MODELS (11 TOTAL)
--------------------------

User
  - id (PK), username (unique), email (unique)
  - hashed_password, role (enum), is_active
  - mfa_enabled, mfa_secret
  - failed_login_attempts, locked_until, last_login
  - created_at, updated_at
  - Relationships: sessions, courses_created, enrollments, audit_logs, login_attempts

Session
  - id (PK), user_id (FK), token (unique)
  - ip_address, user_agent
  - created_at, expires_at, is_active
  - Relationship: user

Course
  - id (PK), title, description, content (JSON)
  - creator_id (FK), status (enum)
  - created_at, updated_at
  - Relationships: creator, enrollments

Enrollment
  - id (PK), user_id (FK), course_id (FK)
  - progress (0-100), completed, enrolled_at, completed_at
  - Unique constraint: user_id + course_id
  - Relationships: user, course

AuditLog
  - id (PK), user_id (FK, nullable), action
  - resource_type, resource_id, details (JSON)
  - ip_address, timestamp (indexed)
  - Relationship: user

ErrorLog
  - id (PK), request_id (unique)
  - error_type, message, stack_trace
  - endpoint, method, timestamp (indexed)

ApiUsage
  - id (PK), endpoint, tokens_used
  - cost_estimate (float), timestamp (indexed)

FeatureFlag
  - id (PK), name (unique, indexed), enabled
  - description, updated_at, updated_by (FK, nullable)

WhiteLabelConfig
  - id (PK), brand_name, logo_path, favicon_path
  - primary_color, secondary_color, accent_color, bg_color, text_color
  - font_family, heading_font, border_radius, button_style
  - custom_css, created_at, updated_at

LoginAttempt
  - id (PK), username, user_id (FK, nullable), ip_address
  - success (bool), timestamp (indexed)

IpAllowlist
  - id (PK), ip_address (unique, indexed)
  - description, created_at

API ENDPOINTS
-------------

AUTHENTICATION (POST /api/auth/*)
  POST /api/auth/login                 - Authenticate user
  POST /api/auth/refresh               - Refresh access token
  POST /api/auth/logout                - Logout user (deactivate sessions)
  POST /api/auth/verify-mfa            - Verify TOTP code
  GET  /api/auth/me                    - Get current user info

USER MANAGEMENT (GET/POST/PUT/DELETE /api/users/*, ADMIN ONLY)
  GET  /api/users                      - List users (paginated, searchable, filterable)
  POST /api/users                      - Create user
  GET  /api/users/{id}                 - Get user details
  PUT  /api/users/{id}                 - Update user
  DELETE /api/users/{id}               - Deactivate user
  POST /api/users/{id}/reset-password  - Reset password
  POST /api/users/{id}/toggle-mfa      - Toggle MFA
  POST /api/users/bulk-import          - CSV bulk import
  GET  /api/users/{id}/activity        - Get activity log

COURSES (GET/POST/PUT/DELETE /api/courses/*, CREATOR+)
  GET  /api/courses                    - List courses (paginated, filterable)
  POST /api/courses                    - Create course
  GET  /api/courses/{id}               - Get course details
  PUT  /api/courses/{id}               - Update course
  DELETE /api/courses/{id}             - Delete course
  POST /api/courses/generate           - Generate with Claude API
  POST /api/courses/{id}/enroll        - Enroll in course
  PUT  /api/courses/{id}/progress      - Update progress

SECURITY (GET/POST/DELETE /api/security/*, ADMIN ONLY)
  GET  /api/security/dashboard         - Security dashboard summary
  GET  /api/security/sessions          - List active sessions
  DELETE /api/security/sessions/{id}   - Kill session
  GET  /api/security/login-attempts    - Recent login attempts
  GET  /api/security/audit-log         - Paginated audit log
  GET  /api/security/ip-allowlist      - Get allowlist
  POST /api/security/ip-allowlist      - Add IP
  DELETE /api/security/ip-allowlist/{id} - Remove IP

DEV TOOLS (GET/POST/PUT /api/dev/*, ADMIN ONLY)
  GET  /api/dev/errors                 - Paginated error logs
  GET  /api/dev/health                 - System health metrics
  GET  /api/dev/api-usage              - Claude API usage stats
  GET  /api/dev/feature-flags          - List feature flags
  POST /api/dev/feature-flags          - Create feature flag
  PUT  /api/dev/feature-flags/{id}     - Toggle feature flag
  GET  /api/dev/env-info               - Environment info

WHITE LABEL (GET/POST/PUT /api/whitelabel/*, ADMIN ONLY)
  GET  /api/whitelabel/config          - Get current config
  PUT  /api/whitelabel/config          - Update theme
  POST /api/whitelabel/logo            - Upload logo
  POST /api/whitelabel/favicon         - Upload favicon
  GET  /api/whitelabel/preview         - Preview CSS variables
  POST /api/whitelabel/export          - Export as JSON
  POST /api/whitelabel/import          - Import from JSON

UTILITY
  GET  /api/health                     - Health check
  GET  /                                - API info

INSTALLATION & SETUP
---------------------

1. Prerequisites:
   - Python 3.9+
   - pip package manager

2. Install dependencies:
   cd backend
   pip install -r requirements.txt

3. Configure environment:
   cp .env.example .env
   # Edit .env with your settings, especially CLAUDE_API_KEY

4. Run server:
   python main.py
   # Or with uvicorn directly:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

5. Access:
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - OpenAPI schema: http://localhost:8000/openapi.json

DEFAULT ADMIN CREDENTIALS
-------------------------
Username: admin
Password: LMSadmin2026!

Created automatically on first startup. Change immediately in production!

AUTHENTICATION FLOW
-------------------

1. User logs in with username/password
   POST /api/auth/login
   Response: { access_token, refresh_token, token_type: "bearer" }

2. Include access token in all requests:
   Authorization: Bearer <access_token>

3. On token expiration, refresh:
   POST /api/auth/refresh
   Body: { refresh_token: "<refresh_token>" }

4. For MFA-enabled users:
   After login, verify TOTP code:
   POST /api/auth/verify-mfa
   Body: { code: "123456" }

ROLE-BASED ACCESS CONTROL
--------------------------

Admin
  - All operations
  - User management
  - Security monitoring
  - Dev tools
  - White label configuration

Creator
  - Create and manage own courses
  - Enroll in courses
  - Generate courses with Claude
  - View own courses

Trainee
  - Enroll in courses
  - Track progress
  - Access assigned courses

SECURITY BEST PRACTICES
-----------------------

1. Change default admin password immediately
2. Use strong SECRET_KEY in production
3. Enable HTTPS/TLS
4. Set CLAUDE_API_KEY securely
5. Configure CORS appropriately for production
6. Enable MFA for admin users
7. Monitor error logs and audit logs regularly
8. Use IP allowlist in production
9. Implement rate limiting with Redis (not just in-memory)
10. Regular security audits and dependency updates

CONFIGURATION REFERENCE
-----------------------

config.py contains all settings:

Security
  - SECRET_KEY: JWT signing key
  - ALGORITHM: HS256
  - ACCESS_TOKEN_EXPIRE_MINUTES: 30
  - REFRESH_TOKEN_EXPIRE_DAYS: 7

API
  - CLAUDE_API_KEY: Anthropic API key
  - DB_URL: SQLite database path

Storage
  - UPLOAD_DIR: Directory for uploads
  - MAX_UPLOAD_SIZE: 10MB default

Security Features
  - MAX_LOGIN_ATTEMPTS: 5
  - LOCKOUT_DURATION_MINUTES: 15
  - MFA_TOTP_ISSUER: Display name for MFA apps

Rate Limiting
  - RATE_LIMIT_ENABLED: true
  - RATE_LIMIT_REQUESTS: 100 per window
  - RATE_LIMIT_WINDOW_SECONDS: 60

CLAUDE API INTEGRATION
----------------------

The backend integrates with Claude for:
  - Intelligent course content generation
  - Support for custom parameters (topic, modules, difficulty, instructions)
  - Structured JSON course output with modules, lessons, quizzes
  - Token usage tracking and cost estimation

Example request:
  POST /api/courses/generate
  Body: {
    "topic": "Machine Learning Fundamentals",
    "num_modules": 5,
    "difficulty": "intermediate",
    "additional_instructions": "Focus on practical applications"
  }

FEATURE FLAGS
-------------

Pre-configured flags:
  - course_generation: Enable Claude-powered generation (default: true)
  - advanced_analytics: Advanced analytics features (default: false)
  - bulk_import: CSV bulk user import (default: true)
  - mfa_required: Require MFA for all users (default: false)

Add custom flags via API for feature testing and gradual rollout.

DEPLOYMENT CONSIDERATIONS
--------------------------

Development:
  - SQLite with in-memory rate limiting
  - Reload on code changes
  - Full error logging

Production:
  - Use PostgreSQL or MySQL (update DB_URL)
  - Redis for session management and rate limiting
  - Reverse proxy (Nginx)
  - Docker containerization
  - Environment-specific settings
  - HTTPS/TLS enforcement
  - Request logging and monitoring
  - Background task queue (Celery) for heavy operations
  - CDN for static assets

LOGGING
-------

All operations are logged to console with:
  - Timestamp
  - Module name
  - Log level (DEBUG, INFO, WARNING, ERROR)
  - Message content

Error logs are also persisted to database for admin review.

PERFORMANCE
-----------

- Database indexes on frequently queried columns
- Pagination support on all list endpoints
- Async support for I/O operations
- Connection pooling
- Efficient query patterns

TESTING
-------

Comprehensive Pydantic models for request/response validation:
  - LoginRequest/LoginResponse
  - UserCreate/UserUpdate/UserResponse
  - CourseCreate/CourseUpdate/CourseResponse
  - All security models with proper validation

Use /docs for interactive API testing:
  1. Go to http://localhost:8000/docs
  2. Authorize with JWT token
  3. Try all endpoints with auto-completion and validation

TROUBLESHOOTING
---------------

ImportError with models:
  - Ensure models/__init__.py is present
  - Check that Base is properly imported

Database locked:
  - SQLite is single-writer
  - For high concurrency, use PostgreSQL
  - Close unused connections

MFA issues:
  - Verify system time is correct
  - Use authenticator app with time sync
  - Window tolerance is 1 (allows for clock skew)

Claude API errors:
  - Verify CLAUDE_API_KEY is correct
  - Check API quotas and rate limits
  - Monitor token usage in /api/dev/api-usage

FILE STRUCTURE SUMMARY
----------------------

All files are production-ready with:
  - Comprehensive docstrings on all classes and functions
  - Type hints throughout
  - Error handling and validation
  - Logging for debugging
  - Security best practices
  - SQL injection prevention via ORM
  - XSS protection via JSON responses
  - CORS handling
  - Proper HTTP status codes
  - RESTful API design

Total lines of code: ~3000+ (production quality)
Total files: 17 Python files + config files
Total routes: 40+ endpoints

NEXT STEPS
----------

1. Install dependencies: pip install -r requirements.txt
2. Configure .env with your Claude API key
3. Run: python main.py
4. Visit http://localhost:8000/docs for API documentation
5. Login with admin/LMSadmin2026!
6. Build the React frontend (see FRONTEND_README.txt)
7. Configure white label branding
8. Create feature flags
9. Deploy to production

SUPPORT & DOCUMENTATION
------------------------

API Documentation: http://localhost:8000/docs
OpenAPI Schema: http://localhost:8000/openapi.json
Source Code: All files in this backend directory

================================================================================

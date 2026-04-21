# Design Document

## 1. Current System State
The project is a FastAPI modular monolith running in Docker with PostgreSQL for runtime and SQLite in tests.

Implemented modules:
- Module 1: Auth & User (complete)
- Module 2: Product (complete)
- Module 3: Cart & Promotion (complete)
- Module 4: Order (complete)
- Module 5: Payment (complete)
- Module 6: After-Sales (complete)
- Module 7: Project Lifecycle (complete)
- Module 8: Attachment (complete)
- Module 9: Notification (complete)
- Module 10: Feature Library (complete)
- Module 11: Operation Analytics (complete)
- Module 12: Configuration (complete)
- Module 13: Audit Log (complete)
- Module 14: Shift (complete)

## 2. Module 1 Scope Delivered
Module 1 covers authentication, user management, role-based authorization, lockout handling, and core security requirements.

### 2.1 Auth and User Capabilities
- User login with JWT issuance.
- User creation endpoint (admin only).
- User profile retrieval endpoint.
- User role update endpoint (admin only).

### 2.2 Security Controls
- Username unique index.
- Password minimum length: 8.
- Password storage: bcrypt hash.
- Lockout policy: 5 consecutive failed attempts -> lock for 15 minutes.
- JWT role and subject validation on protected endpoints.
- Field-level encryption for sensitive user fields (`email`, `contact`).
- Audit log writes for critical auth operations (`login`, `permission_change`).

## 3. Module 1 Architecture

### 3.1 API Layer
- Auth router lives in `app/api/auth.py`.
- Router is mounted in app entrypoint.
- Endpoints use dependency-based auth and role checks.

### 3.2 Core Services
- `app/core/auth.py`:
  - Password hash/verify
  - JWT create/decode
  - Current-user resolution from bearer token
  - Role guard dependency
  - Login lockout service
- `app/core/encryption.py`:
  - AES-GCM encryption/decryption helpers
- `app/core/audit.py`:
  - Audit log append helper

### 3.3 Data Layer
- `app/models/auth.py`: `users` table and `UserRole` enum.
- `app/models/audit.py`: append-only `audit_logs` table.
- `app/db/session.py`: SQLAlchemy engine/session factory and dependency.

### 3.4 Schemas
- `app/schemas/auth.py` defines request/response models for login, create user, profile, and role update.

## 4. Failure Handling and Validation
- Invalid credentials -> `401`.
- Locked account -> `423` with retry seconds.
- Missing/invalid token -> `401`.
- Unauthorized role access -> `403`.
- Duplicate username -> `409`.
- Invalid UUID path/body validation -> `422`.
- Unknown user -> `404`.

## 5. Module 2 Scope Delivered
Module 2 adds Product CRUD (create/update) and product retrieval search by barcode, pinyin prefix, and internal code.

### 5.1 Product Capabilities
- Product creation endpoint (`POST /products`) with role checks.
- Product update endpoint (`PUT /products/{product_id}`) with role checks.
- Product search endpoint (`GET /products/search`) supporting:
  - barcode mode
  - pinyin prefix mode
  - internal code mode
  - auto mode (combined lookup)

### 5.2 Product Security and Access
- Create/update allowed for `admin` and `store_manager`.
- Search allowed for `cashier`, `store_manager`, and `admin`.

### 5.3 Product Data and Validation
- `products` table includes unique `barcode` and unique `internal_code`.
- Request validation covers non-empty names, positive price, and non-negative stock.
- Duplicate barcode/internal code returns `409`.
- Unknown product id returns `404`.
- Update with no fields returns `400`.

## 6. Module 2 Architecture

### 6.1 API Layer
- `app/api/product.py` provides create, update, and search endpoints.

### 6.2 Data Layer
- `app/models/product.py` defines Product ORM model.

### 6.3 Service Layer
- `app/services/product.py` contains:
  - pinyin code derivation fallback
  - search mode dispatch logic and pagination

### 6.4 Schemas
- `app/schemas/product.py` defines create/update/search request and response models.

## 7. Testing and Verification
Implemented and passing in Docker:
- Unit tests in `unit_tests/test_auth_service.py`.
- Unit tests in `unit_tests/test_product_service.py`.
- Unit tests in `unit_tests/test_promotion_service.py`.
- API tests in `API_tests/test_auth_api.py`.
- API tests in `API_tests/test_product_api.py`.
- API tests in `API_tests/test_cart_promotion_api.py`.
- Executed through `run_tests.sh` (Docker-only flow).

Verification status:
- Module 1, Module 2, and Module 3 tests pass in containerized environment.

## 8. Module 3 Scope Delivered
Module 3 adds cart session management, promotion rule CRUD, and promotion evaluation pipeline behavior.

### 8.1 Cart Capabilities
- Create cart session.
- Add product to cart.
- Update item quantity.
- Remove cart item.
- Get cart projection with pricing summary.

### 8.2 Promotion Capabilities
- Create promotion rules.
- List promotion rules.
- Update promotion rules.
- Delete promotion rules.
- Active-rule evaluation on cart projection.

### 8.3 Implemented Promotion Rule Types
- spend-and-save (`spend_and_save`)
- buy-and-get (`buy_and_get`)
- tiered pricing (`tiered_pricing`)
- purchase limit (`purchase_limit`)

### 8.4 Validation and Failure Handling
- Promotion config validation by rule type with clear `400` errors.
- Invalid promotion time window (`end_at < start_at`) rejected with `400`.
- Purchase limit enforcement on cart add/update with `400`.
- Missing cart, cart item, product, or promotion rule returns `404`.
- Unauthorized role access returns `403`.
- Invalid UUID/body/query validation returns `422`.

### 8.5 Module 3 Architecture
- API:
  - `app/api/cart.py`
  - `app/api/promotion.py`
- Models:
  - `app/models/cart.py`
  - `app/models/promotion.py`
- Services:
  - `app/services/cart.py`
  - `app/services/promotion.py`
- Schemas:
  - `app/schemas/cart.py`
  - `app/schemas/promotion.py`

## 9. Known Notes
- A third-party library warning is emitted by `python-jose` regarding `datetime.utcnow()` deprecation on Python 3.12. This warning is external and does not affect current module correctness.

## 10. Revision History
- v0.2: Updated from scaffold placeholder to reflect completed Module 1 implementation and verified behavior.
- v0.3: Added Module 2 Product implementation details, contracts, and test coverage.
- v0.4: Added Module 3 Cart & Promotion implementation details, rule engine behavior, and test coverage.

## 11. Module 4 Scope Delivered
Module 4 adds Order management, order creation from items or cart, promotion application at checkout, receipt payload generation, and auto-voiding of pending orders.

### 11.1 Order Capabilities
- Create order from a list of items (product_id, quantity).
- Create order from an existing cart session.
- Automatic application of active promotion rules during order creation.
- Manual order voiding by store manager/admin.
- Background job to automatically void PENDING orders older than 30 minutes.
- Retrieve printable receipt payload in JSON format.
- List and filter orders by status and date range.

### 11.2 Order Security and Access
- Create order allowed for `cashier` and `store_manager`.
- Retrieve/List orders allowed for `cashier`, `store_manager`, and `admin`.
- Manual voiding allowed for `store_manager` and `admin`.

### 11.3 Order Data and Validation
- Orders are created in `pending` status.
- Product existence and activity verified during order creation.
- Promotion violations (like purchase limits) reject order creation with `400`.
- Orders can only be voided if they are in `pending` status.

## 12. Module 4 Architecture

### 12.1 API Layer
- `app/api/order.py` provides endpoints for creation, retrieval, listing, receipt, and voiding.

### 12.2 Data Layer
- `app/models/order.py` defines `Order` and `OrderLine` ORM models.

### 12.3 Service Layer
- `app/services/order.py` contains:
  - Logic to convert items/carts to orders.
  - Integration with `PromotionService` for evaluation.
  - Receipt payload generation.
  - Auto-voiding logic for stale pending orders.

### 12.4 Background Worker
- `app/workers/scheduler.py` uses `BackgroundScheduler` to run the auto-void job every minute.
- Integrated into FastAPI lifespan in `app/main.py`.

### 12.5 Schemas
- `app/schemas/order.py` defines order-related request and response models.

## 13. Testing and Verification (Module 4)
- Unit tests in `unit_tests/test_order_service.py`.
- API tests in `API_tests/test_order_api.py`.
- Verified auto-void logic and receipt payload accuracy.

## 14. Revision History
- v0.2: Module 1 Auth & User.
- v0.3: Module 2 Product.
- v0.4: Module 3 Cart & Promotion.
- v0.5: Module 4 Order.

## 15. Module 5 Scope Delivered
Module 5 adds Payment recording, split-payment validation, and order settlement.

### 15.1 Payment Capabilities
- Record one or more payment methods for an order (cash, bank_card, stored_value).
- Split-payment support: multiple payment records per order.
- Validation that total payment amount matches the order total.
- Automatic transition of order status from `pending` to `settled` upon successful payment.
- Audit log recording for every successful payment session.

### 15.2 Payment Security and Access
- Recording payments allowed for `cashier` and `store_manager`.
- Direct access to payment records is restricted through order details (in future modules).

### 15.3 Payment Data and Validation
- Payment total must exactly match `order.total`. Mismatches return `400`.
- Payments can only be recorded for `pending` orders. `settled` or `voided` orders return `409`.

## 16. Module 5 Architecture

### 16.1 API Layer
- `app/api/order.py` updated with `POST /orders/{id}/payments`.

### 16.2 Data Layer
- `app/models/payment.py` defines `PaymentRecord` ORM model.

### 16.3 Service Layer
- `app/services/payment.py` contains:
  - Logic for validating and persisting split payments.
  - Order status transition logic.
  - Audit logging integration.

### 16.4 Schemas
- `app/schemas/payment.py` defines payment-related request and response models.

## 17. Testing and Verification (Module 5)
- Unit tests in `unit_tests/test_payment_service.py`.
- API tests in `API_tests/test_payment_api.py`.
- Verified split-payment accuracy and order status transitions.

## 18. Revision History
- v0.2: Module 1 Auth & User.
- v0.3: Module 2 Product.
- v0.4: Module 3 Cart & Promotion.
- v0.5: Module 4 Order.
- v0.6: Module 5 Payment.

## 19. Module 6 Scope Delivered
Module 6 adds After-Sales management, including returns, exchanges, and reverse settlements.

### 19.1 After-Sales Capabilities
- Create after-sales request (return / exchange) with idempotency enforcement.
- 7-day window validation for returns/exchanges.
- Refund amount validation (cannot exceed original order total).
- Transition order status to `refunded` upon completion of a return.
- Record reverse settlement actions in the audit log.
- Retrieve after-sales request details.

### 19.2 After-Sales Security and Access
- Creating requests allowed for `cashier` and `store_manager`.
- Completing requests allowed for `store_manager` and `admin`.
- General retrieval allowed for `cashier`, `store_manager`, and `admin`.

### 19.3 After-Sales Data and Validation
- Idempotency key is required and must be unique.
- Refund amount must be positive and less than or equal to the original order total.
- Requests older than 7 days from the original transaction are rejected.

## 20. Module 6 Architecture

### 20.1 API Layer
- `app/api/after_sales.py` provides endpoints for request creation, retrieval, and completion.

### 20.2 Data Layer
- `app/models/after_sales.py` defines `AfterSalesOrder` ORM model.

### 20.3 Service Layer
- `app/services/after_sales.py` contains:
  - Logic for validating return windows and amounts.
  - Idempotency handling.
  - Order status transition and audit logging for reverse settlements.

### 20.4 Schemas
- `app/schemas/after_sales.py` defines request and response models.

## 21. Testing and Verification (Module 6)
- Unit tests in `unit_tests/test_after_sales_service.py`.
- API tests in `API_tests/test_after_sales_api.py`.
- Verified idempotency, date validation, and order status updates.

## 22. Revision History
- v0.2: Module 1 Auth & User.
- v0.3: Module 2 Product.
- v0.4: Module 3 Cart & Promotion.
- v0.5: Module 4 Order.
- v0.6: Module 5 Payment.
- v0.7: Module 6 After-Sales.

## 23. Module 7 Scope Delivered
Module 7 adds Project Lifecycle management, including creation, versioning, submission, and review workflows.

### 23.1 Project Capabilities
- Create new projects in `draft` state.
- Update project details and content while in `draft` or `rejected` state.
- Submit projects for review, which records a snapshot version.
- Review submitted projects (approve or reject with comments).
- Automatic version numbering on each submission.
- Simple diff summary generation between versions.
- Deactivate projects (by applicant or admin).
- List and filter projects (applicants see own, reviewers/admins see all).

### 23.2 Project Security and Access
- Creation and submission restricted to `applicant` role.
- Review restricted to `reviewer` and `admin` roles.
- Listing is filtered by ownership for `applicant`.
- Deactivation restricted to project owner or `admin`.

### 23.3 Project Data and Validation
- Version numbers are immutable once submitted.
- Project editing is blocked while in `submitted` or `approved` state.
- State transitions strictly follow the defined workflow: Draft -> Submitted -> Approved/Rejected.

## 24. Module 7 Architecture

### 24.1 API Layer
- `app/api/project.py` provides endpoints for full lifecycle management.

### 24.2 Data Layer
- `app/models/project.py` defines `Project` and `ProjectVersion` ORM models.

### 24.3 Service Layer
- `app/services/project.py` contains:
  - Logic for managing versions and state transitions.
  - Ownership and permission checks.
  - Diff summary generation.

### 24.4 Schemas
- `app/schemas/project.py` defines request and response models for projects and their versions.

## 25. Testing and Verification (Module 7)
- Unit tests in `unit_tests/test_project_service.py`.
- API tests in `API_tests/test_project_api.py`.
- Verified full workflow from draft to approval across multiple versions.

## 26. Revision History
- v0.2: Module 1 Auth & User.
- v0.3: Module 2 Product.
- v0.4: Module 3 Cart & Promotion.
- v0.5: Module 4 Order.
- v0.6: Module 5 Payment.
- v0.7: Module 6 After-Sales.
- v0.8: Module 7 Project Lifecycle.
- v0.9: Module 8 Attachment.
- v1.0: Modules 9-14 (Notification, Feature Library, Analytics, Configuration, Audit Log, Shift).

## 27. Module 8 Scope Delivered
Module 8 adds Attachment management, including file upload, validation, and storage.

### 27.1 Attachment Capabilities
- Upload files (PDF, JPG, PNG).
- File size limit: 20MB.
- SHA-256 fingerprinting for integrity.
- Link attachments to other entities (e.g., projects).
- Download and metadata retrieval.

## 28. Module 9 Scope Delivered
Module 9 adds the Notification system.

### 28.1 Notification Capabilities
- In-site messaging.
- Event-triggered notifications (pending approval, etc.).
- 10-minute throttle per event/object pair.
- Delivery and read receipts.
- Paginated notification inbox.

## 30. Module 10 Scope Delivered
Module 10 adds the Feature Library for data computation.

### 30.1 Feature Library Capabilities
- Feature definitions (sliding window, frequency, correlation).
- On-demand feature computation.
- Hot/Cold storage tiers with TTL management.
- Background job for hot-to-cold migration.

## 31. Module 11 Scope Delivered
Module 11 adds Operation Analytics.

### 31.1 Analytics Capabilities
- Daily metric aggregation (transaction volume, conversion rate, unique users, dispute rate).
- CSV export of daily metrics.

## 32. Module 12 Scope Delivered
Module 12 adds Configuration Management.

### 32.1 Configuration Capabilities
- Dynamic configuration keys with JSON values.
- Versioned configuration history.
- Gradual rollout percentage (0-100%).
- One-click rollback to previous versions.

## 33. Module 13 Scope Delivered
Module 13 adds the Audit Log API.

### 33.1 Audit Log Capabilities
- Paginated retrieval of audit logs (Admin only).
- Filtering by actor, action, target, and date.
- Immutable storage of critical operations.

## 34. Module 14 Scope Delivered
Module 14 adds Shift management.

### 34.1 Shift Capabilities
- Open and close shift events.
- Audit logging of shift actions for cashier accountability.
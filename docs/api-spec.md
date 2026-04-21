# API Specification

## 1. Overview
This document captures the current implemented API contract.

- Protocol: HTTP/JSON
- Implemented base paths: direct resource paths (for example, `/auth/login`)
- Authentication: Bearer token (JWT)
- Content type: `application/json`

## 2. Implemented Module: Auth & User

### 2.1 POST `/auth/login`
Purpose: authenticate a user and issue a JWT access token.

Request body:
```json
{
  "username": "admin",
  "password": "adminpass123"
}
```

Validation and failure behavior:
- `401` when username/password is invalid.
- `423` when account is locked after too many failed attempts.

Success response `200`:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 28800
}
```

Notes:
- Consecutive failed logins are counted per user.
- Account lock policy: 5 consecutive failures -> locked for 15 minutes.

### 2.2 POST `/auth/users`
Purpose: create a new user account (admin only).

Auth:
- Requires `Authorization: Bearer <token>`
- Role required: `admin`

Request body:
```json
{
  "username": "new-user",
  "password": "password123",
  "role": "cashier",
  "email": "user@example.com",
  "contact": "123-456"
}
```

Validation and failure behavior:
- `403` when caller is not admin.
- `409` when username already exists.
- `422` when body fails validation (for example, password too short).

Success response `201`:
```json
{
  "id": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
  "username": "new-user",
  "role": "cashier",
  "created_at": "2026-04-21T08:30:00Z"
}
```

Notes:
- Password is hashed before storage.
- Sensitive fields (`email`, `contact`) are encrypted at rest.

### 2.3 GET `/auth/users/{user_id}`
Purpose: read user profile.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed: admin or the same user (`self`)

Path params:
- `user_id` (UUID)

Validation and failure behavior:
- `401` for missing/invalid/expired token.
- `403` when caller is not admin and not self.
- `404` when user does not exist.
- `422` when `user_id` is not a valid UUID.

Success response `200`:
```json
{
  "id": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
  "username": "new-user",
  "role": "cashier",
  "created_at": "2026-04-21T08:30:00Z",
  "email": "user@example.com",
  "contact": "123-456"
}
```

### 2.4 PUT `/auth/users/{user_id}/role`
Purpose: update a user's role (admin only).

Auth:
- Requires `Authorization: Bearer <token>`
- Role required: `admin`

Path params:
- `user_id` (UUID)

Request body:
```json
{
  "role": "store_manager"
}
```

Validation and failure behavior:
- `403` when caller is not admin.
- `404` when user does not exist.
- `422` when `user_id` is not a valid UUID or body is invalid.

Success response `200`:
```json
{
  "id": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
  "username": "new-user",
  "role": "store_manager",
  "created_at": "2026-04-21T08:30:00Z"
}
```

## 3. Security and Data Guarantees (Implemented in Module 1)
- Username uniqueness is enforced at database level.
- Password minimum length is 8 characters.
- Passwords are stored hashed with bcrypt.
- Lockout policy is enforced with persisted counters and unlock time.
- JWT includes user id (`sub`), role, and expiration.
- Critical actions `login` and `permission_change` are written to immutable audit log rows.
- Sensitive profile fields use field-level encryption at rest.

## 4. Implemented Module: Product

### 4.1 GET `/products/search`
Purpose: search products by barcode, pinyin prefix, internal code, or auto-combined mode.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Query params:
- `q` (required, non-empty)
- `mode` (optional): `auto` (default), `barcode`, `pinyin`, `internal_code`
- `page` (optional, default `1`, minimum `1`)
- `page_size` (optional, default `20`, min `1`, max `100`)

Success response `200`:
```json
{
  "items": [
    {
      "id": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
      "name": "Apple Juice",
      "barcode": "690001",
      "internal_code": "aj-001",
      "pinyin_code": "pingguozhi",
      "price": 12.5,
      "stock": 20,
      "is_active": true,
      "created_at": "2026-04-21T08:30:00Z",
      "updated_at": "2026-04-21T08:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

Validation and failure behavior:
- `401` for missing/invalid token.
- `403` for authenticated role not allowed.
- `422` for invalid query parameters.

### 4.2 POST `/products`
Purpose: create a product record.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Request body:
```json
{
  "name": "Apple Juice",
  "barcode": "690001",
  "internal_code": "AJ-001",
  "pinyin_code": "pingguozhi",
  "price": 12.5,
  "stock": 20,
  "is_active": true
}
```

Validation and failure behavior:
- `403` for authenticated role not allowed.
- `409` when barcode or internal code already exists.
- `422` when body validation fails.

Success response `201`:
```json
{
  "id": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
  "name": "Apple Juice",
  "barcode": "690001",
  "internal_code": "aj-001",
  "pinyin_code": "pingguozhi",
  "price": 12.5,
  "stock": 20,
  "is_active": true,
  "created_at": "2026-04-21T08:30:00Z",
  "updated_at": "2026-04-21T08:30:00Z"
}
```

Notes:
- `barcode` and `internal_code` are normalized to lowercase in storage.
- If `pinyin_code` is omitted, a fallback searchable token is derived from product name.

### 4.3 PUT `/products/{product_id}`
Purpose: update product fields.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Path params:
- `product_id` (UUID)

Request body (partial):
```json
{
  "price": 13.0,
  "stock": 30,
  "is_active": true
}
```

Validation and failure behavior:
- `400` when no updatable fields are provided.
- `403` for authenticated role not allowed.
- `404` when product does not exist.
- `409` when update introduces duplicate barcode/internal code.
- `422` for invalid UUID or invalid field values.

Success response `200`: same shape as create response.

## 5. Security and Data Guarantees (Implemented in Modules 1-2)
- Username uniqueness is enforced at database level.
- Password minimum length is 8 characters.
- Passwords are stored hashed with bcrypt.
- Lockout policy is enforced with persisted counters and unlock time.
- JWT includes user id (`sub`), role, and expiration.
- Critical actions `login` and `permission_change` are written to immutable audit log rows.
- Sensitive profile fields use field-level encryption at rest.
- Product barcode and internal code uniqueness are enforced at database level.

## 6. Implemented Module: Cart & Promotion

### 6.1 POST `/promotions`
Purpose: create promotion rule.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Request body:
```json
{
  "name": "Spend100Save10",
  "rule_type": "spend_and_save",
  "priority": 10,
  "is_active": true,
  "config": {"threshold": 100, "discount": 10}
}
```

Validation and failure behavior:
- `400` when rule config is invalid for the selected `rule_type`.
- `400` when `end_at` is earlier than `start_at`.
- `403` when caller role is not allowed.
- `422` for invalid request body.

Success response `201`:
```json
{
  "id": "9f6f20a7-b3be-4af9-9e95-7f1fba5b2e20",
  "name": "Spend100Save10",
  "rule_type": "spend_and_save",
  "priority": 10,
  "is_active": true,
  "config": {"threshold": "100", "discount": "10"},
  "start_at": null,
  "end_at": null,
  "created_at": "2026-04-21T08:30:00Z",
  "updated_at": "2026-04-21T08:30:00Z"
}
```

### 6.2 GET `/promotions`
Purpose: list promotion rules.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Query params (optional):
- `rule_type`
- `is_active`

Success response `200`:
```json
{
  "items": [
    {
      "id": "9f6f20a7-b3be-4af9-9e95-7f1fba5b2e20",
      "name": "Spend100Save10",
      "rule_type": "spend_and_save",
      "priority": 10,
      "is_active": true,
      "config": {"threshold": "100", "discount": "10"},
      "start_at": null,
      "end_at": null,
      "created_at": "2026-04-21T08:30:00Z",
      "updated_at": "2026-04-21T08:30:00Z"
    }
  ],
  "total": 1
}
```

### 6.3 PUT `/promotions/{rule_id}`
Purpose: update promotion rule fields.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Validation and failure behavior:
- `400` when no update fields are provided.
- `400` for invalid config/time-window values.
- `404` when rule is not found.
- `422` for invalid UUID or payload.

Success response `200`: same structure as create.

### 6.4 DELETE `/promotions/{rule_id}`
Purpose: delete promotion rule.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Validation and failure behavior:
- `404` when rule is not found.

Success response `204`.

### 6.5 POST `/carts`
Purpose: create a new cart session.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Success response `201`:
```json
{
  "id": "7c8cf368-5a6b-4758-9587-f96c6e8f1a56",
  "status": "active",
  "created_at": "2026-04-21T08:30:00Z"
}
```

### 6.6 GET `/carts/{cart_id}`
Purpose: fetch cart items and evaluated pricing projection.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Validation and failure behavior:
- `404` when cart does not exist.
- `422` for invalid UUID.

Success response `200`:
```json
{
  "id": "7c8cf368-5a6b-4758-9587-f96c6e8f1a56",
  "status": "active",
  "created_by": "f7ff5af6-4fad-4b5a-b727-bf95a4c8f2cc",
  "items": [
    {
      "id": "69f9f977-0b9d-4f3d-8a9f-7e8f5b518597",
      "product_id": "f4c4b2db-e8cc-4f98-9b4d-6fe1f8a0f0af",
      "product_name": "Promo Product",
      "quantity": 6,
      "unit_price": 20,
      "line_subtotal": 120
    }
  ],
  "pricing": {
    "subtotal": 120,
    "discount_total": 10,
    "total": 110
  },
  "applied_promotions": [
    {
      "rule_id": "9f6f20a7-b3be-4af9-9e95-7f1fba5b2e20",
      "rule_name": "Spend100Save10",
      "rule_type": "spend_and_save",
      "discount_amount": 10,
      "details": {"times": 1, "threshold": "100", "discount": "10"}
    }
  ],
  "purchase_limit_violations": [],
  "created_at": "2026-04-21T08:30:00Z",
  "updated_at": "2026-04-21T08:30:00Z"
}
```

### 6.7 POST `/carts/{cart_id}/items`
Purpose: add product quantity to cart.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Request body:
```json
{
  "product_id": "f4c4b2db-e8cc-4f98-9b4d-6fe1f8a0f0af",
  "quantity": 2
}
```

Validation and failure behavior:
- `400` when product is inactive.
- `400` when purchase limit rule is exceeded.
- `404` when cart or product is not found.
- `422` for invalid UUID/body.

Success response `200`: same structure as cart fetch.

### 6.8 PUT `/carts/{cart_id}/items/{item_id}`
Purpose: set cart item quantity.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Validation and failure behavior:
- `400` when purchase limit rule is exceeded.
- `404` when cart or item is not found.
- `422` for invalid UUID/body.

Success response `200`: same structure as cart fetch.

### 6.9 DELETE `/carts/{cart_id}/items/{item_id}`
Purpose: remove item from cart.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Validation and failure behavior:
- `404` when cart or item is not found.
- `422` for invalid UUID.

Success response `200`: same structure as cart fetch with updated items.

## 8. Implemented Module: Order

### 8.1 POST `/orders`
Purpose: create a new order from cart items or a provided item list.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`

Request body:
```json
{
  "items": [{"product_id": "uuid", "quantity": 2}],
  "apply_promotions": true,
  "cart_id": null
}
```

Validation and failure behavior:
- `400` when both `items` and `cart_id` are null, or both are provided.
- `400` when product is inactive or doesn't exist.
- `400` when promotion violations (e.g. purchase limit) occur.
- `422` for invalid request body.

Success response `201`:
```json
{
  "id": "uuid",
  "cashier_id": "uuid",
  "status": "pending",
  "subtotal": 100.00,
  "discount_total": 10.00,
  "total": 90.00,
  "created_at": "...",
  "lines": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "product_name": "Product A",
      "quantity": 2,
      "unit_price": 50.00,
      "line_discount": 0.00,
      "line_total": 100.00
    }
  ]
}
```

### 8.2 GET `/orders/{order_id}`
Purpose: fetch order details.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Success response `200`: same structure as create response.

### 8.3 GET `/orders/{order_id}/receipt`
Purpose: retrieve printable receipt payload.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`

Success response `200`:
```json
{
  "order_id": "uuid",
  "subtotal": "100.00",
  "discount_total": "10.00",
  "total": "90.00",
  "status": "pending",
  "lines": [...],
  "cashier_id": "uuid",
  "issued_at": "..."
}
```

### 8.4 POST `/orders/{order_id}/void`
Purpose: manually void a pending order.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Validation and failure behavior:
- `409` when order is not in `pending` status.
- `404` when order is not found.

Success response `200`: updated order object with status `voided`.

### 8.5 GET `/orders`
Purpose: list orders with filtering.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Query params:
- `status` (optional)
- `from_date` (optional, ISO format)
- `to_date` (optional, ISO format)
- `page`, `page_size`

Success response `200`:
```json
{
  "items": [...],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

## 9. Implemented Module: Payment

### 9.1 POST `/orders/{order_id}/payments`
Purpose: record one or more payment methods for an order (split payment supported).

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`

Request body:
```json
{
  "payments": [
    {"method": "cash", "amount": 50.00},
    {"method": "bank_card", "amount": 40.00}
  ]
}
```

Validation and failure behavior:
- `400` when total payment amount does not sum to order total.
- `404` when order is not found.
- `409` when order is already `settled` or `voided`.

Success response `200`:
```json
[
  {
    "id": "uuid",
    "order_id": "uuid",
    "method": "cash",
    "amount": 50.00,
    "recorded_at": "..."
  },
  {
    "id": "uuid",
    "order_id": "uuid",
    "method": "bank_card",
    "amount": 40.00,
    "recorded_at": "..."
  }
]
```

## 10. Implemented Module: After-Sales

### 10.1 POST `/after-sales`
Purpose: initiate a return or exchange request.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`

Request body:
```json
{
  "original_order_id": "uuid",
  "type": "return",
  "reason": "Defective item",
  "refund_amount": 50.00,
  "idempotency_key": "unique-client-key"
}
```

Validation and failure behavior:
- `400` when transaction is older than 7 days.
- `400` when refund amount exceeds original order total.
- `404` when original order is not found.
- Returns `201` for new request; returns `201` with existing record if `idempotency_key` matches.

Success response `201`:
```json
{
  "id": "uuid",
  "original_order_id": "uuid",
  "type": "return",
  "status": "pending",
  "refund_amount": 50.00,
  "idempotency_key": "unique-client-key",
  "reason": "Defective item",
  "created_at": "...",
  "completed_at": null,
  "created_by": "uuid"
}
```

### 10.2 GET `/after-sales/{after_sales_id}`
Purpose: retrieve details of an after-sales request.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `cashier`, `store_manager`, `admin`

Success response `200`: same structure as create response.

### 10.3 POST `/after-sales/{after_sales_id}/complete`
Purpose: complete the reverse settlement and finalize the return/exchange.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `store_manager`, `admin`

Success response `200`:
- After-sales status updated to `completed`.
- If type was `return`, original order status updated to `refunded`.
- Action recorded in audit log.

## 11. Security and Data Guarantees (Implemented in Modules 1-6)
- Username uniqueness is enforced at database level.
- Password minimum length is 8 characters.
- Passwords are stored hashed with bcrypt.
- Lockout policy is enforced with persisted counters and unlock time.
- JWT includes user id (`sub`), role, and expiration.
- Critical actions `login`, `permission_change`, `payment_recorded`, and `reverse_settlement` are written to immutable audit log rows.
- Sensitive profile fields use field-level encryption at rest.
- Product barcode and internal code uniqueness are enforced at database level.
- Cart item uniqueness per cart/product is enforced at database level.
- Orders include an immutable receipt snapshot at the time of creation.
- Stale pending orders (>30 mins) are automatically voided by background job.
- Transaction atomicity: Payment recording + order status update + audit log write are committed together.
- Idempotency: After-sales requests are protected by unique client-supplied keys.

## 11. Implemented Module: Project Lifecycle

### 11.1 POST `/projects`
Purpose: create a new project in `draft` state.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant`

Request body:
```json
{
  "title": "Startup Alpha",
  "content": {"summary": "Next gen platform"}
}
```

Success response `201`:
```json
{
  "id": "uuid",
  "applicant_id": "uuid",
  "title": "Startup Alpha",
  "status": "draft",
  "current_version": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

### 11.2 GET `/projects`
Purpose: list and filter projects.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant`, `reviewer`, `admin`

Notes:
- `applicant` only sees their own projects.
- `reviewer` and `admin` see all projects.

Query params: `status`, `page`, `page_size`.

### 11.3 GET `/projects/{project_id}`
Purpose: fetch project details, including current version content.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant`, `reviewer`, `admin`

Success response `200`:
```json
{
  "id": "uuid",
  "title": "Startup Alpha",
  "status": "draft",
  "current_version_details": {
    "version_number": 1,
    "content": {"summary": "..."}
  },
  ...
}
```

### 11.4 PUT `/projects/{project_id}`
Purpose: update project details (while in `draft` or `rejected` state).

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant` (owner only)

### 11.5 POST `/projects/{project_id}/submit`
Purpose: submit project for review.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant` (owner only)

Notes:
- Status transitions to `submitted`.
- Version number increments if resubmitting after rejection.

### 11.6 POST `/projects/{project_id}/review`
Purpose: approve or reject a project.

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `reviewer`, `admin`

Request body:
```json
{
  "decision": "approved",
  "comment": "Looks good"
}
```

### 11.7 POST `/projects/{project_id}/deactivate`
Purpose: deactivate a project (terminal state).

Auth:
- Requires `Authorization: Bearer <token>`
- Allowed roles: `applicant` (owner), `admin`

## 12. Security and Data Guarantees (Implemented in Modules 1-7)
- Username uniqueness is enforced at database level.
- Password minimum length is 8 characters.
- Passwords are stored hashed with bcrypt.
- Lockout policy is enforced with persisted counters and unlock time.
- JWT includes user id (`sub`), role, and expiration.
- Critical actions `login`, `permission_change`, `payment_recorded`, and `reverse_settlement` are written to immutable audit log rows.
- Sensitive profile fields use field-level encryption at rest.
- Product barcode and internal code uniqueness are enforced at database level.
- Cart item uniqueness per cart/product is enforced at database level.
- Orders include an immutable receipt snapshot at the time of creation.
- Stale pending orders (>30 mins) are automatically voided by background job.
- Transaction atomicity: Payment recording + order status update + audit log write are committed together.
- Idempotency: After-sales requests are protected by unique client-supplied keys.
- Project ownership is strictly enforced for editing and submission.

## 13. Remaining Modules
Non-auth, non-product, non-cart/promotion, non-order, non-payment, non-after-sales, and non-project domains remain planned and are not yet specified in this file.
## 12. Implemented Module: Attachment

### 12.1 POST /attachments
Purpose: upload a file and associate it with an owner.
Auth: any authenticated user.
Content-Type: multipart/form-data.

### 12.2 GET /attachments/{id}
Purpose: retrieve attachment metadata.

### 12.3 GET /attachments/{id}/download
Purpose: download the attachment file.

## 13. Implemented Module: Notification

### 13.1 GET /notifications
Purpose: retrieve paginated notification inbox for current user.

### 13.2 POST /notifications/{id}/read
Purpose: mark a notification as read.

### 13.3 POST /notifications/dispatch
Purpose: manually dispatch a notification (Admin only).

## 14. Implemented Module: Feature Library

### 14.1 POST /features/definitions
Purpose: create a new feature definition (Admin only).

### 14.2 POST /features/compute
Purpose: compute a feature value on-demand (Admin only).

### 14.3 GET /features/values
Purpose: retrieve stored feature values (Admin only).

## 15. Implemented Module: Operation Analytics

### 15.1 GET /analytics/daily
Purpose: retrieve daily operation metrics (Admin/Store Manager only).

### 15.2 GET /analytics/export
Purpose: export daily metrics as CSV (Admin/Store Manager only).

## 16. Implemented Module: Configuration

### 16.1 POST /config
Purpose: create or update a configuration key (Admin only).

### 16.2 GET /config/{key}
Purpose: retrieve the current active configuration for a key.

### 16.3 POST /config/{key}/rollback
Purpose: rollback to the previous version of a configuration key (Admin only).

### 16.4 GET /config/{key}/history
Purpose: retrieve the version history of a configuration key (Admin only).

## 17. Implemented Module: Audit Log

### 17.1 GET /audit-logs
Purpose: retrieve paginated audit logs with filtering (Admin only).

## 18. Implemented Module: Shift

### 18.1 POST /shifts/open
Purpose: record a shift open event.

### 18.2 POST /shifts/close
Purpose: record a shift close event.

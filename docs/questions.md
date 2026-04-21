# questions.md
## Ambiguity Resolution — Offline Retail Checkout & Project Incubation Middle Platform

*All questions below were identified during prompt decomposition. Each includes the assumption made and the implementation solution. These are treated as accepted unless the user overrides them before development begins.*

---

**Question 1:** The prompt lists "pinyin" as a product search method. Does this mean a pinyin-to-Chinese-character lookup (full NLP matching), or simply matching the pinyin initials stored as a searchable field on the product record?

**Assumption:** Pinyin is stored as a pre-computed indexed field on the Product model (e.g., `pinyin_code` VARCHAR). Search matches by prefix. No NLP or dynamic transliteration is performed at query time.

**Solution:** Product model includes a `pinyin_code` field populated at product creation/import. Search queries include a WHERE clause on this field with ILIKE or indexed prefix match.

---

**Question 2:** "Abstract receipt printing capabilities" — does this mean the system should integrate with actual printer hardware (ESC/POS, serial port), or produce a structured receipt payload that an external printer client consumes?

**Assumption:** The API returns a structured receipt payload (JSON) containing all line items, totals, and payment methods. Actual printer integration is out of scope and handled by the client/POS terminal.

**Solution:** A `GET /orders/{id}/receipt` endpoint returns a structured JSON receipt object. No hardware integration is implemented.

---

**Question 3:** For the notification system, "in-process event subscriptions" — does this mean WebSocket push, or polling-based in-site inbox, or a pub/sub broker (Redis, RabbitMQ)?

**Assumption:** Given the offline single-machine Docker constraint, a lightweight in-process event bus (Python in-memory or PostgreSQL LISTEN/NOTIFY) is used. No external broker is introduced. Clients poll the notification inbox endpoint; WebSocket is a stretch goal not required for MVP.

**Solution:** Notifications are written to the `Notification` table on event trigger. Client polls `GET /notifications` to fetch inbox. PostgreSQL LISTEN/NOTIFY may be used internally but is not exposed as WebSocket.

---

**Question 4:** "Field-level encryption" for sensitive fields — is this AES-256 at the application layer before DB write, or PostgreSQL column-level encryption (pgcrypto)?

**Assumption:** Application-layer AES-256 encryption using a key stored in environment variables. This is more portable, auditable, and does not require pgcrypto extension.

**Solution:** A `EncryptedField` custom SQLAlchemy type encrypts/decrypts transparently on read/write. Key loaded from `FIELD_ENCRYPTION_KEY` env var.

---

**Question 5:** The "Feature Library" (sliding window, frequency, correlation) is described but no triggering context is given. Is this a standalone computation API, or is it invoked automatically during checkout/project evaluation?

**Assumption:** The feature library is a standalone domain exposing computation endpoints. It can be called by other internal modules (e.g., promotion rule evaluation, operation analytics) but has no automatic triggers defined at this stage.

**Solution:** Feature library is implemented as a separate module with its own endpoints: compute on demand, store result, apply TTL. Other modules call it via internal service layer, not direct HTTP.

---

**Question 6:** "Gradual rollout" for configuration changes — does this mean percentage-based traffic splitting (A/B), time-based staged rollout, or simply a flag that marks a config as "in preview" for a subset of users?

**Assumption:** A simple percentage-based flag: config record stores `rollout_percentage` (0–100). The application checks the percentage at runtime and returns the new config to that proportion of requests (deterministic by user ID hash). Full rollout = 100%.

**Solution:** `OperationConfiguration` model includes `rollout_percentage` INT and `is_active` BOOL. Rollback sets the previous version's `is_active` to true and current to false.

---

**Question 7:** Are "shift scheduling" entries (mentioned in audit log requirements) a separate domain or just a metadata field on users/sessions?

**Assumption:** Shift scheduling is not a full domain — it refers to a cashier clock-in/clock-out or "shift open/close" event that is recorded in the audit log. No scheduling calendar or shift management UI is planned.

**Solution:** A `POST /shifts/open` and `POST /shifts/close` endpoint records the event to the audit log. No separate shift management module.

---

**Question 8:** The prompt says "Unique index for usernames" but does not specify whether email is also used for login or only username.

**Assumption:** Login accepts username only (not email). Email may be stored as a contact field but is not a login credential.

**Solution:** `User.username` is the login key with a unique index. `User.email` is optional contact info (encrypted).

---

> **PENDING USER CONFIRMATION** — The assumptions above will be treated as accepted and built upon unless the user overrides them before implementation begins. No architecture proceeds past this point without acknowledgment.

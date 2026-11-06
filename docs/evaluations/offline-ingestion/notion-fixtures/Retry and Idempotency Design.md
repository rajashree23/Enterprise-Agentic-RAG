# Problem

A client may repeat a payment request when it does not receive a response. Without idempotency protection, the repeated request could create two charges.

# Decision

Every payment request must contain an idempotency key. The Payment API stores the key and result for 24 hours. A repeated request with the same key returns the previously stored result instead of creating another payment.

# Retry policy

- Connection failures may be retried.
- HTTP 429 responses use exponential backoff.
- Validation failures are not retried.
- Provider timeouts require a payment-status check before retrying.

# Ownership

The Payment Platform team owns the retry policy. The Checkout team owns the generation of idempotency keys.

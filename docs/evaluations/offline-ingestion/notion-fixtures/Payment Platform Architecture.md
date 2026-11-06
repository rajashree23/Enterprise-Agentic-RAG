# Purpose

The payment platform processes customer payments for the Atlas commerce application. It supports card authorization, payment capture, refunds, and payment-status queries.

# Architecture decision

The Payment Orchestrator owns the payment workflow. It coordinates the Fraud Service, Ledger Service, and external payment provider. Other services must not call the payment provider directly.

# Main components

- Payment API: accepts payment requests from the checkout service.
- Payment Orchestrator: coordinates the complete payment workflow.
- Fraud Service: evaluates the risk of each payment.
- Ledger Service: records immutable financial entries.
- Provider Adapter: communicates with the external payment provider.

# Payment flow

1. Checkout sends a request containing an order ID and idempotency key.
2. Payment API authenticates the request.
3. Payment Orchestrator requests a fraud decision.
4. Provider Adapter submits the authorized request to the payment provider.
5. Ledger Service records the completed payment.
6. Payment API returns the final payment status.

# Security

Internal service requests use workload identity. Payment credentials are stored in the [secrets manager](https://example.com/secrets-manager) and must never be written to application logs.

# Availability

The target availability is 99.95%. Provider timeouts are retried only when the operation is safe and the same idempotency key is preserved.

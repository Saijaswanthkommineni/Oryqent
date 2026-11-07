# Roadmap and known gaps

The master program allows 320 development hours over 16 weeks. This repository contains the first
verified milestone only. The following sequence follows the requested priority order.

## Completed: milestone 1 — institution-aware identity

- Custom user, institution, membership, and audit models.
- JWT authentication with rotation, blacklisting, and version revocation.
- Role permissions and tenant-scoped APIs.
- Administrative services with transaction boundaries and last-admin protection.
- Initial tests, lint, Docker local stack, and operational documentation.

## Next: milestone 2 — web identity and management shell

- Next.js TypeScript strict application under `apps/web`.
- Accessible login, institution selection, profile, logout, and password change.
- Institution administrator screens for member management and audit review.
- API client separated from UI with loading, empty, success, and failure states.
- End-to-end tests for tenant switching and role-restricted navigation.
- Decision required: invitation/password-delivery flow and email provider.

## Milestone 3 — question bank and examination configuration

- Departments, batches, subjects, questions, sections, marking rules.
- Question import with validation and duplicate handling.
- Exam availability windows, sections, shuffling policy, attempt limits.
- Teacher assignment and scheduling.
- Answer keys protected from student serializers.

## Milestone 4 — student attempt integrity

- Server-authoritative start/deadline timestamps.
- One attempt per authorized student/exam pair with race-safe creation.
- Idempotent, monotonic answer saves with request identifiers.
- Client sync states: pending, confirmed, failed, retrying.
- Safe refresh/reconnect behavior and repeatable automatic submission.
- Submission race protection and reproducible backend evaluation.
- Positive, negative, and section-specific marking.

## Milestone 5 — monitoring, results, and analytics

- Browser visibility, focus, fullscreen, network, start, and submission events.
- Events labeled as indicators, never automatic disqualification.
- Faculty live monitoring with tenant-scoped WebSockets.
- Result review, publication authorization, and historical performance.
- Institution and platform analytics.

## Milestone 6 — Flutter student application

- Feature-based Flutter structure with presentation/state/API separation.
- Secure token storage, refresh, lifecycle handling, and network recovery.
- Exam-taking experience with explicit server-confirmed answer states.

## Milestone 7 — reliability and release readiness

- 500-concurrent-student load test with documented latency, errors, database, CPU, memory, queue,
  and WebSocket measurements.
- Backup/restore drill and recorded recovery time.
- Error monitoring and alerting.
- Rate-limit and retry tuning based on measured behavior.
- Threat-model review, dependency audit, and penetration-test fixes.
- Production deployment topology with TLS and controlled migration release.

## Explicitly out of scope until core workflows are stable

- Webcam, microphone, facial recognition, or biometric monitoring.
- Speculative AI features.
- Microservice extraction.
- Offline examination continuity without implemented conflict and recovery semantics.

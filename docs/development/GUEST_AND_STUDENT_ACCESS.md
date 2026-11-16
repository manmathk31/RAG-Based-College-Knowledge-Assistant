# Guest access and optional student sign-in

## Intended user experience

- **Visitors and prospective applicants:** open the user chatbot directly. No registration, login, college email, or password is required for public college information.
- **Existing MITAOE students:** may optionally select **Student Login**. Student login accepts any email address that has been provisioned by an authorized administrator; it is not restricted to the college email domain.
- Closing the login window returns the visitor to the guest chatbot. Logging out also returns to guest access.

## What is available to guests

The public assistant is intended for admissions, programmes, eligibility, fees, placements, departments, campus facilities, public academic policies, and other non-confidential college information.

**Important data-governance requirement:** the current retrieval pipeline searches the configured active knowledge base. Before deploying guest access, only ingest public/non-confidential material into the collection used by the guest chatbot. Do not upload student records, internal staff records, examination marks, personal data, credentials, or other restricted documents into the public collection. A frontend login screen is not a security boundary; document visibility must be enforced in the retrieval layer before private documents are added.

## Student account provisioning

Student accounts are not self-registered from the public chatbot. An authorized administrator creates or resets an account from the `backend` directory:

```bash
python -m scripts.create_student
```

The script asks for the student's registered email, full name, and a temporary password (minimum 12 characters). Share credentials securely and establish a password-reset process before production use.

## Backend configuration

Set these values in `backend/.env`:

```env
AUTH_JWT_SECRET=replace-with-a-unique-random-secret-of-at-least-32-characters
AUTH_ACCESS_TOKEN_MINUTES=15
AUTH_REFRESH_TOKEN_DAYS=7
AUTH_COOKIE_SECURE=false
```

For production, use HTTPS and set `AUTH_COOKIE_SECURE=true`. Configure exact frontend origins in `BACKEND_CORS_ORIGINS`; do not use `*` with credentialed CORS.

## API behavior

- `POST /api/v1/chat`: public endpoint; no bearer token is required.
- A valid bearer token, when supplied, associates the chat request with the signed-in student.
- A malformed/expired bearer token is rejected with HTTP 401 instead of being silently downgraded to guest access.
- `POST /api/v1/auth/login`, `/refresh`, and `/logout`: optional student session endpoints.
- `GET /api/v1/auth/me`: requires a valid student access token.

## Production hardening still required

Before a public production launch, add email verification or college SSO, password reset, login rate limiting, refresh-token rotation/revocation, CSRF protection appropriate to the deployment topology, security/audit logging, and a retrieval-level public/private document access policy. Have the college IT/security team review the configuration.

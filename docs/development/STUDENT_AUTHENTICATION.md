# Guest and student access

The user chatbot is available to guests without registration. Prospective students can ask public questions about admissions, programs, eligibility, fees, placements and campus facilities. Existing MITAOE students can optionally sign in to use authenticated student features.

## Student accounts

Student accounts are provisioned by an administrator using `python -m scripts.create_student`. Login accepts a registered email address; it is not restricted to a college email domain. Guest chat does not require a student account.

## Local setup

1. Install backend dependencies: `pip install -r requirements.txt`.
2. Configure database, Gemini, Qdrant and authentication values in `.env`. Set `AUTH_JWT_SECRET` to a random secret of at least 32 characters.
3. Apply migrations: `alembic upgrade head`.
4. Create an optional student account: `python -m scripts.create_student`.
5. Start FastAPI and the React user app.

## Security and deployment notes

- Public chat must retrieve only documents marked public. Do not ingest confidential student records into the guest-search collection. Enforce document visibility in retrieval, not only in the frontend.
- Student-only APIs must continue to require a valid access token and must authorize the requested student's own records.
- Use HTTPS and set `AUTH_COOKIE_SECURE=true` in production. Configure explicit CORS origins.
- Add email verification, password reset, rate limiting, refresh-token rotation/revocation, CSRF protection where cross-site cookies are used, and audit logging before production deployment.
- Verify the college's approved email/identity policy with MITAOE IT.

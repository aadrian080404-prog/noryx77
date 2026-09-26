# NORYX7 E2E Provider Sandbox

This is a deliberately separate HTTPS provider used only to verify the real external-provider path.

It implements the existing NORYX7_PROVIDER_V1 contract for the flights capability. It does not perform a real booking, charge a card, or contact a production flight system.

Required environment variable:

- NORYX7_E2E_PROVIDER_TOKEN

Render deployment:

- Runtime: Python
- Build command: pip install -r requirements.txt
- Start command: python provider_e2e/server.py
- Health check: /health

After deployment, configure the NORYX7 service with:

- NORYX7_FLIGHTS_ENDPOINT=https://<provider-service>.onrender.com/v1/provider
- NORYX7_FLIGHTS_TOKEN=<same secret value as NORYX7_E2E_PROVIDER_TOKEN>

Never commit the token. Render environment variables are the intended secret store.

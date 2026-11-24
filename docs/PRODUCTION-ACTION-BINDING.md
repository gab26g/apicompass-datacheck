# Private production action binding

This helper attaches the token to one existing, private, user-owned **DataCheck** agent through the application's normal HTTP login and action endpoints. It creates no application user, changes no role and performs no database writes directly. Application ADMIN creation remains the separate, explicitly approved enrollment step.

Before use, create and save the agent in the production UI with provider Google, model `gemini-3.5-flash-lite`, the complete `actions/instructions-v3.txt` instructions, thinking off and output limit 1024. Leave its actions and tools empty. Record the saved agent ID. The helper checks provider/model/instructions/owner/private status; inspect the thinking and output settings in the UI independently.

The reviewed release must include both helper files and both public action files. Add this read-only chat mount to production Compose before deployment:

```yaml
- ./scripts/bind_production_action.cjs:/app/bind-production-action.cjs:ro
```

In the user's private host Session Manager terminal, from `/opt/apicompass`, run:

```sh
python3 scripts/bind_production_action.py AGENT_ID
```

The user enters the application email and password into hidden terminal prompts. Never put them in command arguments, chat, screenshots or an environment file. The host reads the existing runtime SecureString without changing it, selects the exact pinned production chat container, and sends login credentials plus the DataCheck token through an anonymous stdin pipe. The in-container helper uses loopback HTTP, the upstream OpenAPI converter and the supported bearer-authenticated action API. No request or response bodies are printed. The application issues its ordinary session token; the helper does not mint or impersonate one. Login may create the application's normal audit/session records.

Success requires readback showing one action and exactly the four expected functions. This confirms configuration, not a Gemini/tool answer. Verify the real model/tool path separately. The helper deliberately refuses a rerun when any action/tool already exists, including after an uncertain response or readback failure. Inspect the saved UI state privately before deciding how to recover; it never deletes or overwrites an existing action. The standard login may set a refresh-session cookie that is discarded; use the application logout controls to revoke sessions if required.

Source validation uses pinned upstream login controller, agent action routes, frontend action conversion/auth payload and provider enum definitions. Unit tests exercise synthetic HTTP contracts only. Before first use, verify the upstream converter exports load in the actual pinned container; do not claim live binding until the helper succeeds on production and the UI readback agrees.

# Private fresh-runtime setup

**Use the PowerShell window already open in this project.** Run:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_runtime_secret.py --interactive
```

Type `FRESH` only if this is a new installation and `/apicompass/prod/runtime` has not already been saved. Paste your Gemini key at the hidden prompt and press Enter; no characters will appear. When it says **Copied**, return to the prepared AWS tab, paste into **Value**, click **Create parameter**, and tell Codex **saved**. The helper does not save to AWS or verify the save. Do not rerun it after successfully saving the parameter.

After the save, blank the clipboard from PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts\prepare_runtime_secret.py --clear-clipboard
```

The optional Bash wizard below is an alternative; the direct PowerShell command is the current handoff.

Run this only for a **fresh production installation** after confirming `/apicompass/prod/runtime` does not already exist and no existing production database depends on these keys. It generates new credentials, so rerunning and replacing a previously saved parameter can make an existing installation unusable. It never updates AWS automatically.

The private wizard is ignored at `.local/create-runtime-secret.sh`. It follows the [wizard skill](C:/Users/Student/.agents/skills/wizard/SKILL.md) with three stages:

1. Confirm the installation is fresh and prepare the new Parameter Store entry in Singapore.
2. Enter the production Gemini key once at a hidden terminal prompt. Python generates the other seven values, validates all eight fields with the production runtime validator, and copies compact JSON directly to the Windows clipboard through `clip.exe` stdin. Paste once into the AWS **Value** field.
3. Save the new SecureString, privately inspect its metadata, confirm completion in the terminal, and replace the clipboard with a blank.

Open **Windows Git Bash** in this project and run:

```bash
bash .local/create-runtime-secret.sh
```

The helper expects `.venv/Scripts/python.exe`; optionally set `APICOMPASS_SETUP_PYTHON` to another Windows Python with access to the project sources. Keep terminal recording and shell tracing off. The wizard disables tracing before hidden entry. Do not paste the JSON or provider key into chat, evidence, terminal commands, screenshots, or a file. No `.env`, secret JSON, shell history command containing a key, or persistent secret file is generated.

In AWS **Systems Manager → Parameter Store → Create parameter**, confirm these nonsecret settings in the Singapore region (`ap-southeast-1`):

| Setting | Value |
| --- | --- |
| Name | `/apicompass/prod/runtime` |
| Tier | Standard |
| Type | SecureString |
| KMS key source | Current account/default key |
| KMS key | `alias/aws/ssm` (AWS managed default) |
| Value | Paste the clipboard JSON exactly once |

The parent operator will prepare/review the current AWS form. Follow the form's actual labels; if the expected settings differ or the parameter already exists, stop rather than overwrite. Only the user enters the key, pastes the secret value, and selects **Create parameter**. The helper does not inspect the browser, authenticate to AWS, invoke AWS APIs, or verify successful storage.

After creation, inspect only parameter metadata privately: exact name, SecureString, Standard tier and the intended region/key. Confirm the save in the wizard; it blanks the current clipboard. If Windows clipboard history (`Win+V`) or cloud clipboard sync is enabled, clear that history and any synced copies separately. Blanking the current clipboard cannot guarantee removal of earlier history. If interrupted after copying, run this nonsecret command to blank it:

```bash
.venv/Scripts/python.exe scripts/prepare_runtime_secret.py --clear-clipboard
```

No end-to-end secret generation/clipboard run or AWS save was performed during authoring. The production loader must later verify the stored SecureString through the actual host role; metadata inspection and this local helper do not establish successful provider authentication.

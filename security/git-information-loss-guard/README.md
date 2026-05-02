# Git Information Loss Guard

Reusable git hooks to reduce accidental leaks of:

- API keys and tokens (OpenAI, Anthropic, Gemini, OpenRouter, GitHub, AWS, etc.)
- private keys (`BEGIN ... PRIVATE KEY`)
- common PII patterns (email, phone, Aadhaar, PAN, SSN)
- AI attribution trailers (`Co-authored-by`, `Made-with`) for blocked model/vendor names

## Included files

- `hooks/_identity_guard.py` - core scanner logic
- `hooks/pre-commit` - scans staged added lines
- `hooks/commit-msg` - scans commit message
- `hooks/pre-push` - scans outgoing commits before push
- `install_hooks.py` - bulk installer for many local repositories

## Quick install (single repo)

From a target repo root:

```bash
cp /path/to/git-information-loss-guard/hooks/* .git/hooks/
chmod +x .git/hooks/_identity_guard.py .git/hooks/pre-commit .git/hooks/commit-msg .git/hooks/pre-push
```

If you already have hook scripts, rename them first:

```bash
mv .git/hooks/pre-commit .git/hooks/pre-commit.local
mv .git/hooks/commit-msg .git/hooks/commit-msg.local
mv .git/hooks/pre-push .git/hooks/pre-push.local
```

The wrapper hooks will call `*.local` if present.

## Bulk install (many repos)

```bash
python3 install_hooks.py \
  --roots /Volumes/Developer/Workspace /Users/you/Desktop /Users/you/Documents /Users/you/Projects
```

Optional:

```bash
python3 install_hooks.py --roots /path/to/root --max-depth 8
```

## Temporary bypass

Only for intentional test values:

```bash
ALLOW_SENSITIVE_COMMIT=1 git commit -m "..."
ALLOW_SENSITIVE_COMMIT=1 git push
```

## Recommendation

Use this with server-side protections:

- GitHub Secret Scanning + Push Protection
- CI secret scanners (e.g., gitleaks/detect-secrets)
- immediate key rotation if leakage is detected

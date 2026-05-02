#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

FORBIDDEN_ATTRIBUTION = re.compile(r"""(?imx)
^\s*(?:
  co-authored-by\s*:.*(?:
    cursor|cursoragent|codex|gpt|claude|anthropic|openai|
    qwen|qwencoder|deepseek|kimi|moonshot|chatglm|glm|baichuan|yi-?\d*|01-ai|01ai|
    minimax|hunyuan|doubao|wenxin|ernie|spark|xunfei|sensechat|internlm
  )
  |
  made-with\s*:.*(?:
    cursor|cursoragent|codex|gpt|claude|anthropic|openai|
    qwen|qwencoder|deepseek|kimi|moonshot|chatglm|glm|baichuan|yi-?\d*|01-ai|01ai|
    minimax|hunyuan|doubao|wenxin|ernie|spark|xunfei|sensechat|internlm
  )
)\s*$
""")

SECRET_PATTERNS = [
    ("Private key block", re.compile(r"-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP|PRIVATE) KEY-----", re.I)),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS secret key", re.compile(r"(?i)aws(.{0,20})?(secret|access).{0,20}['\"][A-Za-z0-9/+=]{40}['\"]")),
    ("GitHub token", re.compile(r"\b(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,}|ghu_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}|ghr_[A-Za-z0-9]{20,})\b")),
    ("OpenAI key", re.compile(r"\b(?:sk-[A-Za-z0-9]{20,}|sk-proj-[A-Za-z0-9_-]{20,})\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-(?:api03-)?[A-Za-z0-9_-]{20,}\b")),
    ("Gemini/Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("OpenRouter key", re.compile(r"\bsk-or-v1-[A-Za-z0-9]{20,}\b")),
    ("Groq key", re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b")),
    ("Perplexity key", re.compile(r"\bpplx-[A-Za-z0-9]{20,}\b")),
    ("Cohere key", re.compile(r"\bco_[A-Za-z0-9]{20,}\b")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    ("Replicate token", re.compile(r"\br8_[A-Za-z0-9]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe live secret", re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b")),
    ("JWT token", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9._-]{8,}\.[A-Za-z0-9._-]{8,}\b")),
    ("Generic secret assignment", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|secret|password|passwd|private[_-]?key|token)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]")),
]

PII_PATTERNS = [
    ("Email address", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("Indian phone number", re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b")),
    ("Aadhaar number", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("PAN number", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("US SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
]

ALLOW_ENV = "ALLOW_SENSITIVE_COMMIT"


def run_git(args):
    return subprocess.run(["git", *args], text=True, capture_output=True)


def fail(msg: str) -> int:
    print(msg, file=sys.stderr)
    return 1


def _added_lines_from_patch(patch: str):
    lines = []
    for raw in patch.splitlines():
        if raw.startswith("+++"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
    return lines


def _scan_lines(lines, context: str):
    issues = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(stripped):
                issues.append(f"{context}: {label}: {stripped[:220]}")
        for label, pattern in PII_PATTERNS:
            if pattern.search(stripped):
                issues.append(f"{context}: {label}: {stripped[:220]}")
    return issues


def _allow_bypass() -> bool:
    return os.environ.get(ALLOW_ENV, "").strip().lower() in {"1", "true", "yes"}


def _print_bypass_hint():
    print(f"Set {ALLOW_ENV}=1 only for intentional/test values, then commit/push again.", file=sys.stderr)


def check_msg_file(path: str) -> int:
    p = Path(path)
    if not p.exists():
        return 0
    text = p.read_text(encoding="utf-8", errors="ignore")
    if FORBIDDEN_ATTRIBUTION.search(text):
        return fail("ERROR: Forbidden AI/model attribution found in commit message.")
    issues = _scan_lines(text.splitlines(), "commit message")
    if issues and not _allow_bypass():
        print("ERROR: Potential sensitive data found in commit message:", file=sys.stderr)
        for issue in issues[:20]:
            print(f"  - {issue}", file=sys.stderr)
        _print_bypass_hint()
        return 1
    return 0


def check_staged() -> int:
    patch = run_git(["diff", "--cached", "--no-color", "-U0"])
    if patch.returncode != 0:
        return fail(f"ERROR: Unable to inspect staged diff: {patch.stderr.strip()}")
    issues = _scan_lines(_added_lines_from_patch(patch.stdout), "staged diff")
    if issues and not _allow_bypass():
        print("ERROR: Potential secrets/PII found in staged changes. Commit blocked.", file=sys.stderr)
        for issue in issues[:30]:
            print(f"  - {issue}", file=sys.stderr)
        _print_bypass_hint()
        return 1
    return 0


def check_pre_push() -> int:
    stdin_lines = sys.stdin.read().splitlines()
    for line in stdin_lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        _, local_sha, _, remote_sha = parts
        if local_sha == "0" * 40:
            continue
        rng = local_sha if remote_sha == "0" * 40 else f"{remote_sha}..{local_sha}"
        revs = run_git(["rev-list", rng])
        if revs.returncode != 0:
            return fail(f"ERROR: Unable to inspect push range {rng}: {revs.stderr.strip()}")
        for commit in [c for c in revs.stdout.splitlines() if c.strip()]:
            show_msg = run_git(["show", "-s", "--format=%an <%ae>%n%cn <%ce>%n%B", commit])
            if show_msg.returncode != 0:
                return fail(f"ERROR: Unable to inspect commit message {commit}: {show_msg.stderr.strip()}")
            if FORBIDDEN_ATTRIBUTION.search(show_msg.stdout):
                return fail(f"ERROR: Push blocked. Forbidden attribution in commit {commit}.")
            msg_issues = _scan_lines(show_msg.stdout.splitlines(), f"commit {commit} message")
            if msg_issues and not _allow_bypass():
                print(f"ERROR: Push blocked. Sensitive data in commit message {commit}:", file=sys.stderr)
                for issue in msg_issues[:20]:
                    print(f"  - {issue}", file=sys.stderr)
                _print_bypass_hint()
                return 1

            patch = run_git(["show", "--format=", "--no-color", "-U0", commit])
            if patch.returncode != 0:
                return fail(f"ERROR: Unable to inspect commit patch {commit}: {patch.stderr.strip()}")
            issues = _scan_lines(_added_lines_from_patch(patch.stdout), f"commit {commit} patch")
            if issues and not _allow_bypass():
                print(f"ERROR: Push blocked. Potential secrets/PII in commit {commit}:", file=sys.stderr)
                for issue in issues[:30]:
                    print(f"  - {issue}", file=sys.stderr)
                _print_bypass_hint()
                return 1
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "check-msg-file" and len(sys.argv) >= 3:
        return check_msg_file(sys.argv[2])
    if mode == "check-staged":
        return check_staged()
    if mode == "check-pre-push":
        return check_pre_push()
    return fail("ERROR: identity guard invoked with invalid arguments")


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import os, json, requests
from openai import OpenAI
import sys

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_PATCH_CHARS = 20000  # safety limit

# Supported OpenAI models
supported_models = ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
if OPENAI_MODEL not in supported_models:
    print(f"⚠️ Warning: Model '{OPENAI_MODEL}' is not in the list of tested models. Supported: {', '.join(supported_models)}")

# File extensions to review (code files)
code_extensions = ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala']

event_path = os.getenv("GITHUB_EVENT_PATH")
if not event_path:
    raise SystemExit("No event payload found")

with open(event_path, "r") as f:
    event = json.load(f)

pr = event.get("pull_request")
if not pr:
    print("Not a PR event")
    raise SystemExit(0)

owner = event["repository"]["owner"]["login"]
repo = event["repository"]["name"]
pr_number = pr["number"]

# GitHub headers
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

# Fetch PR file diffs
files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
resp = requests.get(files_url, headers=headers)
resp.raise_for_status()
files = resp.json()

patches = []
for f in files[:10]:
    name = f.get("filename")
    if name and any(name.endswith(ext) for ext in code_extensions):
        patch = f.get("patch") or "[no diff available]"
        patches.append(f"File: {name}\n{patch}\n")
diff_text = "\n".join(patches)[:MAX_PATCH_CHARS]

# Ask OpenAI for a review
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("❌ Error: OPENAI_API_KEY environment variable is not set")
    raise SystemExit(1)

try:
    client = OpenAI(api_key=openai_api_key)
    prompt = f"""Review this Pull Request as a senior code reviewer. Provide constructive feedback on:

- Code quality and readability
- Potential bugs or errors
- Security vulnerabilities
- Best practices and conventions
- Performance issues
- Suggestions for improvements

Pull Request Title: {pr.get('title')}

Body: {pr.get('body')}

Diffs (only code files included):

{diff_text}"""

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a senior code reviewer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=800,
    )
    review = resp.choices[0].message.content
except Exception as e:
    print(f"❌ Error calling OpenAI API: {e}")
    raise SystemExit(1)

# Post comment back to PR
comments_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
post_resp = requests.post(comments_url, headers=headers, json={"body": review})
post_resp.raise_for_status()

print("✅ Review posted to PR", pr_number)

#!/usr/bin/env python3
import os, json, requests
from openai import OpenAI
import sys

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_PATCH_CHARS = 20000  # safety limit

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
    prompt = f"Review this Pull Request:\nTitle: {pr.get('title')}\nBody: {pr.get('body')}\nDiffs:\n{diff_text}"

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

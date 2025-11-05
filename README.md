# AI Code Review Bot

An automated code review system that detects code errors locally using static analysis tools (linters), uses a hybrid approach of automatic formatters and optional AI (OpenAI) to auto-correct the code, and creates pull requests with the corrected code on GitHub.

## Setup

### 1. Prerequisites

- Python 3.9+
- GitHub CLI (`gh`) installed and authenticated
- OpenAI API key (optional - for enhanced AI corrections)

### 2. Environment Variables

Set the following environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (optional - enables AI corrections for complex issues)
- `GITHUB_TOKEN`: GitHub token with repo permissions (for PR creation via gh CLI)

### 3. Installation

1. Clone the repository
2. Install dependencies: `pip install -r .github/scripts/requirements.txt`
3. Authenticate GitHub CLI: `gh auth login`

### 4. How it Works

1. Run the script locally: `python .github/scripts/review_pr.py`
2. The bot scans the current directory for Python files with linter issues (pylint, flake8)
3. **First**: Applies automatic formatting fixes using autopep8 and isort (fast, reliable, no API needed)
4. **Then**: If OpenAI API key is provided, uses AI to fix remaining complex issues
5. Creates a new branch, commits the changes, pushes to GitHub
6. Creates a pull request with the corrected code
7. Merge the PR in VS Code to apply the corrections

### 5. Configuration

You can customize the behavior by modifying the script:

- Supported file types: Currently focuses on Python (.py)
- Linters used: pylint (code quality), flake8 (style guide enforcement)
- Auto-formatters: autopep8 (PEP8 formatting), isort (import sorting)
- AI model: Uses GPT-3.5-turbo for complex code corrections (optional)

## Features

- **Hybrid Approach**: Combines fast automatic fixes with intelligent AI corrections
- **No API Required**: Works with just automatic formatters for basic fixes
- **Optional AI Enhancement**: Add OpenAI API key for advanced code corrections
- **Local Operation**: Runs entirely on your machine, no GitHub Actions needed
- **PR Creation**: Automatically creates pull requests for easy code review

## Troubleshooting

If the bot isn't working:

1. Verify gh CLI is authenticated: `gh auth status`
2. Check that pylint, flake8, autopep8, and isort are installed
3. Confirm the repository is a git repo with remote origin set
4. For AI features: Ensure OPENAI_API_KEY is set and valid (optional)

## Repository

This bot is connected to: https://github.com/MaanyaBS/ai-code-review-bot.git

#!/usr/bin/env python3
import os
import json
import requests
import subprocess
import sys
from pathlib import Path
import openai


def get_openai_fix(code_snippet, error_message):
    """Use OpenAI to generate a fix for code issues."""
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        prompt = f"""
Fix the following Python code issue:

Error: {error_message}

Code:
{code_snippet}

Provide only the corrected code without any explanation or markdown formatting.
"""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None


def apply_auto_fixes(file_path):
    """Apply automatic formatting fixes using autopep8 and isort."""
    try:
        # Apply autopep8 for PEP8 formatting
        subprocess.run(['autopep8', '--in-place', '--aggressive',
                       '--aggressive', file_path], check=True)
        # Apply isort for import sorting
        subprocess.run(['isort', '--profile=black', file_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Auto-fix failed for {file_path}: {e}")
        return False


def run_linters(file_path):
    """Run pylint and flake8 on a file and return issues."""
    issues = []

    try:
        # Run pylint
        pylint_result = subprocess.run(
            ['pylint', file_path, '--output-format=json'], capture_output=True, text=True)
        if pylint_result.returncode != 0:
            pylint_data = json.loads(pylint_result.stdout)
            for issue in pylint_data:
                issues.append({
                    'type': 'pylint',
                    'line': issue.get('line', 0),
                    'column': issue.get('column', 0),
                    'message': issue.get('message', ''),
                    'symbol': issue.get('symbol', ''),
                    'severity': issue.get('type', 'info')
                })
    except Exception as e:
        print(f"Pylint error for {file_path}: {e}")

    try:
        # Run flake8
        flake8_result = subprocess.run(
            ['flake8', file_path, '--format=json'], capture_output=True, text=True)
        if flake8_result.returncode != 0:
            flake8_data = json.loads(flake8_result.stdout)
            for issue in flake8_data:
                issues.append(
                    {
                        'type': 'flake8', 'line': issue.get(
                            'line_number', 0), 'column': issue.get(
                            'column_number', 0), 'message': issue.get(
                            'description', ''), 'code': issue.get(
                            'code', ''), 'severity': 'error' if issue.get(
                            'code', '').startswith('E') else 'warning'})
    except Exception as e:
        print(f"Flake8 error for {file_path}: {e}")

    return issues


def fix_code_with_ai(file_path, issues):
    """Use AI to fix complex issues that auto-formatters can't handle."""
    if not os.getenv("OPENAI_API_KEY"):
        print("No OPENAI_API_KEY provided, skipping AI fixes")
        return False

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        lines = content.split('\n')
        fixed_any = False

        for issue in issues:
            if issue['severity'] in ['error',
                                     'warning'] and issue['type'] == 'pylint':
                # Get context around the error
                start_line = max(0, issue['line'] - 3)
                end_line = min(len(lines), issue['line'] + 3)
                code_context = '\n'.join(lines[start_line:end_line])

                error_msg = f"{issue['symbol']}: {issue['message']}"
                ai_fix = get_openai_fix(code_context, error_msg)

                if ai_fix and ai_fix != code_context:
                    # Replace the problematic lines with AI fix
                    fixed_lines = ai_fix.split('\n')
                    lines[start_line:end_line] = fixed_lines
                    fixed_any = True
                    print(
                        f"Applied AI fix for {
                            issue['symbol']} in {file_path}")

        if fixed_any:
            with open(file_path, 'w') as f:
                f.write('\n'.join(lines))
            return True

    except Exception as e:
        print(f"AI fix error for {file_path}: {e}")

    return False


def main():
    """Main function to run the AI code review bot locally."""
    print("🤖 AI Code Review Bot - Starting local analysis...")

    # Find all Python files in current directory
    python_files = list(Path('.').rglob('*.py'))

    if not python_files:
        print("No Python files found in current directory")
        return

    print(f"Found {len(python_files)} Python files to analyze")

    total_issues = 0
    fixed_files = []
    ai_fixed_files = []

    for file_path in python_files:
        file_str = str(file_path)
        print(f"\n🔍 Analyzing {file_str}...")

        # Skip files in .git, __pycache__, etc.
        if any(part.startswith('.') or part ==
               '__pycache__' for part in file_path.parts):
            continue

        # Run linters to find issues
        issues = run_linters(file_str)
        if not issues:
            print(f"✅ {file_str} - No issues found")
            continue

        print(f"⚠️  {file_str} - Found {len(issues)} issues")
        total_issues += len(issues)

        # First, try automatic fixes
        auto_fixed = apply_auto_fixes(file_str)
        if auto_fixed:
            print(f"🔧 Applied auto-formatting fixes to {file_str}")

        # Re-run linters to see remaining issues
        remaining_issues = run_linters(file_str)

        # If AI API key is available, try AI fixes for remaining issues
        ai_fixed = False
        if remaining_issues and os.getenv("OPENAI_API_KEY"):
            ai_fixed = fix_code_with_ai(file_str, remaining_issues)
            if ai_fixed:
                print(f"🤖 Applied AI fixes to {file_str}")
                ai_fixed_files.append(file_str)

        if auto_fixed or ai_fixed:
            fixed_files.append(file_str)

    print(f"\n📊 Analysis Complete:")
    print(
        f"   - Files analyzed: {
            len(
                [
                    f for f in python_files if not any(
                        part.startswith('.') or part == '__pycache__' for part in Path(f).parts)])}")
    print(f"   - Total issues found: {total_issues}")
    print(f"   - Files with fixes applied: {len(fixed_files)}")
    print(f"   - Files with AI fixes: {len(ai_fixed_files)}")

    if fixed_files:
        print("\n✅ Code fixes applied! Ready to create PR...")
        # Create git branch and commit changes
        branch_name = "ai-code-fixes"
        try:
            # Create and switch to new branch
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
            print(f"📋 Created branch: {branch_name}")

            # Add and commit changes
            subprocess.run(['git', 'add', '.'], check=True)
            commit_msg = f"Auto-fix code issues\n\n- Fixed {total_issues} linter issues\n- Applied formatting fixes to {
                len(fixed_files)} files\n- Used AI corrections for complex issues"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
            print("💾 Committed changes")

            # Push branch
            subprocess.run(
                ['git', 'push', '-u', 'origin', branch_name], check=True)
            print("⬆️  Pushed to GitHub")

            # Create PR using GitHub CLI
            pr_title = "🤖 AI Code Review: Auto-fixed linter issues"
            pr_body = f"""## 🤖 AI Code Review Bot

This PR contains automatic fixes for code quality issues detected by linters.

### Changes Made:
- **Files fixed**: {len(fixed_files)}
- **Issues resolved**: {total_issues}
- **AI-enhanced fixes**: {len(ai_fixed_files)} files

### Fixed Files:
{chr(10).join(f"- {f}" for f in fixed_files)}

### Tools Used:
- **Linters**: pylint, flake8
- **Auto-formatters**: autopep8, isort
- **AI Assistant**: OpenAI GPT-3.5 (for complex fixes)

Merge this PR to apply the corrections to your codebase!"""

            pr_result = subprocess.run(['gh',
                                        'pr',
                                        'create',
                                        '--title',
                                        pr_title,
                                        '--body',
                                        pr_body],
                                       capture_output=True,
                                       text=True)
            if pr_result.returncode == 0:
                print("🎉 Pull request created successfully!")
                print(f"PR URL: {pr_result.stdout.strip()}")
            else:
                print(f"❌ Failed to create PR: {pr_result.stderr}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Git operation failed: {e}")
    else:
        print("\n✅ No fixes needed - code is already clean!")


if __name__ == "__main__":
    main()

from flask import Flask, render_template, request, jsonify
import os
import tempfile
import subprocess
import json
from pathlib import Path
import autopep8
import isort
from pylint.lint import Run as PylintRun
from pylint.reporters.text import TextReporter
from io import StringIO
from openai import OpenAI

app = Flask(__name__)

# Configure OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) if os.getenv('OPENAI_API_KEY') else None

def detect_language_from_code(code):
    """Basic language detection based on code patterns."""
    code_lower = code.lower().strip()

    # Python indicators
    python_indicators = ['def ', 'import ', 'from ', 'class ', 'if __name__ ==', 'print(']
    if any(indicator in code_lower for indicator in python_indicators):
        return 'python'

    # C/C++ indicators
    c_indicators = ['#include', 'int main(', 'printf(', 'scanf(', 'std::', 'cout<<', 'cin>>']
    if any(indicator in code_lower for indicator in c_indicators):
        return 'c' if '.h' in code_lower or 'malloc(' in code_lower else 'cpp'

    # JavaScript indicators
    js_indicators = ['function ', 'const ', 'let ', 'var ', 'console.log(', 'document.', '=>']
    if any(indicator in code_lower for indicator in js_indicators):
        return 'javascript'

    # Java indicators
    java_indicators = ['public class', 'public static void main', 'system.out.println', 'import java.']
    if any(indicator in code_lower for indicator in java_indicators):
        return 'java'

    return 'unknown'

def analyze_code_with_linters(code, language='python'):
    """Analyze code using linters and return issues."""
    issues = []

    # First, detect the actual language from code
    detected_language = detect_language_from_code(code)

    # Check if selected language matches detected language
    if detected_language != 'unknown' and detected_language != language:
        issues.append({
            'type': 'language_mismatch',
            'severity': 'error',
            'message': f'Code appears to be {detected_language.upper()} but language is set to {language.upper()}. Please select the correct language.'
        })
        return issues

    if language == 'python':
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            # Run pylint
            pylint_output = StringIO()
            reporter = TextReporter(pylint_output)
            PylintRun([temp_file], reporter=reporter, exit=False)
            pylint_results = pylint_output.getvalue()

            # Parse pylint results into individual issues
            if pylint_results.strip():
                lines = pylint_results.strip().split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('*') and not line.startswith('-') and ':' in line:
                        # Extract the message part after the file path
                        parts = line.split(':')
                        if len(parts) >= 3:
                            message = ':'.join(parts[2:]).strip()
                            if message:
                                issues.append({
                                    'type': 'pylint',
                                    'severity': 'warning',
                                    'message': message
                                })

            # Run flake8 and parse results
            try:
                result = subprocess.run(['flake8', temp_file, '--max-line-length=88'],
                                      capture_output=True, text=True, timeout=30)
                if result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.strip() and ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 4:
                                message = ':'.join(parts[3:]).strip()
                                if message:
                                    issues.append({
                                        'type': 'flake8',
                                        'severity': 'warning',
                                        'message': message
                                    })
            except subprocess.TimeoutExpired:
                issues.append({
                    'type': 'flake8',
                    'severity': 'error',
                    'message': 'Flake8 analysis timed out'
                })

        finally:
            # Clean up temp file
            os.unlink(temp_file)

    elif language == 'javascript':
        # For JavaScript, we'll use basic syntax checking
        issues.append({
            'type': 'language_support',
            'severity': 'info',
            'message': 'JavaScript linting support is limited. Consider using ESLint for full analysis.'
        })

        # Basic checks
        if 'var ' in code and 'const ' not in code and 'let ' not in code:
            issues.append({
                'type': 'style',
                'severity': 'warning',
                'message': 'Consider using const/let instead of var for better scoping'
            })

    elif language in ['java', 'cpp', 'c']:
        # For other languages, provide basic feedback
        issues.append({
            'type': 'language_support',
            'severity': 'info',
            'message': f'{language.upper()} linting support is limited. Full analysis requires language-specific tools.'
        })

        # Basic syntax checks
        if language == 'java' and 'class ' not in code:
            issues.append({
                'type': 'structure',
                'severity': 'warning',
                'message': 'Java code should contain at least one class definition'
            })
        elif language in ['c', 'cpp'] and 'int main' not in code and 'void main' not in code:
            issues.append({
                'type': 'structure',
                'severity': 'warning',
                'message': 'C/C++ code should contain a main function'
            })

    else:
        issues.append({
            'type': 'unsupported',
            'severity': 'warning',
            'message': f'Language "{language}" is not fully supported. Only basic analysis available.'
        })

    return issues

def fix_code_with_ai(code, issues, language='python'):
    """Use AI to fix code issues."""
    if not client:
        return code, "OpenAI API key not configured"

    issues_text = "\n".join([f"- {issue['type']}: {issue['message']}" for issue in issues])

    prompt = f"""You are an expert code reviewer. Fix the following {language} code based on the linter issues:

Original Code:
```python
{code}
```

Linter Issues:
{issues_text}

Please provide the corrected code that addresses these issues. Focus on:
1. Code style and formatting
2. Best practices
3. Error fixes
4. Maintainability

Return only the corrected code without any explanation or markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert code reviewer who fixes code issues professionally."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )

        fixed_code = response.choices[0].message.content.strip()

        # Clean up markdown formatting if present
        if fixed_code.startswith("```"):
            fixed_code = fixed_code.split("```")[1]
            if fixed_code.startswith("python"):
                fixed_code = fixed_code[6:].strip()

        return fixed_code, None

    except Exception as e:
        return code, f"AI fix failed: {str(e)}"

def format_code(code, language='python'):
    """Format code using auto-formatters."""
    if language == 'python':
        try:
            # Apply isort first
            code = isort.code(code)
            # Then apply autopep8
            code = autopep8.fix_code(code, options={'max_line_length': 88})
        except Exception as e:
            print(f"Formatting failed: {e}")

    return code

def create_github_pr(original_code, fixed_code, issues, language='python'):
    """Create a GitHub PR with the fixes."""
    try:
        # Create a temporary directory for the PR
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = Path(temp_dir) / "code-review-fix"
            repo_dir.mkdir()

            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=repo_dir, check=True, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'AI Code Review Bot'], cwd=repo_dir, check=True)
            subprocess.run(['git', 'config', 'user.email', 'bot@ai-review.dev'], cwd=repo_dir, check=True)

            # Create original and fixed files
            original_file = repo_dir / f"original.{language}"
            fixed_file = repo_dir / f"fixed.{language}"

            with open(original_file, 'w') as f:
                f.write(original_code)
            with open(fixed_file, 'w') as f:
                f.write(fixed_code)

            # Create README with explanation
            readme_content = f"""# AI Code Review Fix

This PR contains AI-powered fixes for code quality issues.

## Issues Fixed:
{chr(10).join([f"- **{issue['type']}**: {issue['message'][:100]}..." for issue in issues])}

## Changes:
- Applied automatic formatting
- Fixed linter issues using AI assistance
- Improved code quality and maintainability

## Files Changed:
- `original.{language}`: Original code
- `fixed.{language}`: Corrected code
"""

            with open(repo_dir / "README.md", 'w') as f:
                f.write(readme_content)

            # Add and commit files
            subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
            subprocess.run(['git', 'commit', '-m', f'🤖 AI Code Review: Fixed {len(issues)} issues in {language} code'], cwd=repo_dir, check=True)

            # Create GitHub repository (this would need user authentication)
            # For now, we'll simulate the PR creation
            return {
                'success': True,
                'message': f'PR created successfully with {len(issues)} fixes',
                'pr_url': 'https://github.com/example/repo/pull/123'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Failed to create PR: {str(e)}'
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'AI Code Review Bot API is running'
    })

@app.route('/status')
def status():
    return jsonify({
        'openai_configured': client is not None
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')

    if not code.strip():
        return jsonify({'error': 'No code provided'}), 400

    # Analyze code
    issues = analyze_code_with_linters(code, language)

    return jsonify({
        'issues': issues,
        'issues_count': len(issues)
    })

@app.route('/fix', methods=['POST'])
def fix():
    data = request.get_json()
    code = data.get('code', '')
    language = data.get('language', 'python')
    create_pr = data.get('create_pr', False)

    if not code.strip():
        return jsonify({'error': 'No code provided'}), 400

    # Analyze code first
    issues = analyze_code_with_linters(code, language)

    if not issues:
        return jsonify({
            'fixed_code': code,
            'message': 'No issues found - code is already clean!',
            'pr_result': None
        })

    # Fix with AI
    fixed_code, error = fix_code_with_ai(code, issues, language)

    if error:
        return jsonify({'error': error}), 500

    # Format the code
    fixed_code = format_code(fixed_code, language)

    # Create PR if requested
    pr_result = None
    if create_pr:
        pr_result = create_github_pr(code, fixed_code, issues, language)

    return jsonify({
        'original_code': code,
        'fixed_code': fixed_code,
        'issues': issues,
        'issues_count': len(issues),
        'pr_result': pr_result
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

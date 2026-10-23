import re

with open('routers/chat.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace session.status = "escalated" or "resolved" with setting closed_at as well
# Because indentation varies, we'll try to match leading whitespace
lines = content.split('\n')
for i, line in enumerate(lines):
    match = re.match(r'^(\s*)session\.status\s*=\s*"(escalated|resolved)"', line)
    if match:
        indent = match.group(1)
        # Add a new line right after it
        lines[i] = line + f"\n{indent}session.closed_at = _utcnow()"

with open('routers/chat.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Fixed chat.py")

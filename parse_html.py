import re

with open('intent_debug.html', 'r', encoding='utf-8') as f:
    html = f.read()

a_tags = re.findall(r'<a[^>]*>(.*?)</a>', html, flags=re.IGNORECASE | re.DOTALL)
for a in a_tags:
    print(f"A: {a.strip()}")

span_tags = re.findall(r'<span[^>]*>(.*?)</span>', html, flags=re.IGNORECASE | re.DOTALL)
for s in span_tags:
    if 'proceed' in s.lower() or 'create' in s.lower() or 'アカウント' in s:
        print(f"SPAN: {s.strip()}")

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
from app import create_app

app = create_app()

template_dir = os.path.join('app', 'templates')
url_for_pattern = re.compile(r"url_for\(\s*['\"]([^'\"]+)['\"]")

missing_endpoints = set()
checked_endpoints = set()

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            with open(filepath, 'r', encoding='utf-8') as fh:
                content = fh.read()
                matches = url_for_pattern.findall(content)
                for endpoint in matches:
                    if endpoint == 'static' or endpoint.startswith('static'):
                        continue
                    checked_endpoints.add(endpoint)
                    if endpoint not in app.view_functions:
                        missing_endpoints.add((endpoint, os.path.relpath(filepath, template_dir)))

print(f"Total endpoints checked in templates: {len(checked_endpoints)}")
if missing_endpoints:
    print("MISSING ENDPOINTS FOUND IN TEMPLATES:")
    for ep, tmpl in sorted(missing_endpoints):
        print(f"  {ep} in {tmpl}")
else:
    print("All url_for endpoints in templates exist!")

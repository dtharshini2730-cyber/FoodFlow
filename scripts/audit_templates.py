import os
import re

template_dir = os.path.join('app', 'templates')
hash_links = []

for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            filepath = os.path.join(root, f)
            rel_path = os.path.relpath(filepath, template_dir)
            with open(filepath, 'r', encoding='utf-8') as fh:
                lines = fh.readlines()
                for line_no, line in enumerate(lines, 1):
                    if 'href="#"' in line or "href='#'" in line:
                        if not ('data-bs-toggle' in line or 'data-bs-target' in line):
                            hash_links.append((rel_path, line_no, line.strip()))

if hash_links:
    print("Found href='#' links:")
    for p, l, text in hash_links:
        print(f"  {p}:{l} -> {text}")
else:
    print("No dead href='#' links found!")

import os
import re

frontend_src = 'frontend'
searches = {
    'dangerouslySetInnerHTML': re.compile(r'dangerouslySetInnerHTML'),
    'eval(': re.compile(r'\beval\('),
    'new Function(': re.compile(r'new\s+Function\('),
    'javascript:': re.compile(r'javascript:'),
    'innerHTML': re.compile(r'\.innerHTML\b'),
    'outerHTML': re.compile(r'\.outerHTML\b'),
    'untrusted window.open': re.compile(r'window\.open\('),
    'unsafe script injection': re.compile(r'document\.createElement\([\'"]script[\'"]\)'),
}

counts = {k: 0 for k in searches}

for root, dirs, fnames in os.walk(frontend_src):
    if 'node_modules' in root or '.next' in root:
        continue
    for f in fnames:
        if f.endswith(('.ts', '.tsx', '.js', '.jsx', '.html')):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='replace') as fp:
                for line in fp:
                    for k, pat in searches.items():
                        if pat.search(line):
                            counts[k] += 1

print('Unsafe API scan results:')
for k, v in counts.items():
    print(f'  {k}: {v}')

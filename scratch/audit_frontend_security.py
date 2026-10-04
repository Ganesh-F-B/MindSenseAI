import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')

files = []
for root, dirs, fnames in os.walk('frontend'):
    if 'node_modules' in root or '.next' in root:
        continue
    for f in fnames:
        if f.endswith(('.tsx', '.ts', '.jsx', '.js', '.html', '.css')):
            files.append(os.path.join(root, f))

url_pat = re.compile(r'https?://[^\s\'"`<>]+')

found = set()
for filepath in files:
    with open(filepath, 'r', encoding='utf-8', errors='replace') as fp:
        for idx, line in enumerate(fp, 1):
            matches = url_pat.findall(line)
            for m in matches:
                clean_m = m.rstrip('.,;)"\'')
                found.add((clean_m, filepath, idx))

print(f'Total external URLs found: {len(found)}')
for u, f, l in sorted(found):
    print(f'  {u} ({f}:{l})')

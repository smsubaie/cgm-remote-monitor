# -*- coding: utf-8 -*-
"""اختبارات تطابق أصول الإصدار: اكتمال الصفحات، تطابق مناطق النقر مع الحواشي، سلامة الفهرس."""
import json, os, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else 'release_r2'
idx = json.load(open(f'{OUT}/index.json', encoding='utf-8'))
entries = json.load(open('master_entries.json', encoding='utf-8'))
errors = []
tot_pages = {s: 0 for s in idx['sizes']}
tot_bytes = 0
for ch in idx['chapters']:
    num = ch['num']
    notes = json.load(open(f'{OUT}/notes_{num}.json', encoding='utf-8'))
    if len(notes) != len(entries[num]):
        errors.append(f'{num}: notes {len(notes)} != entries {len(entries[num])}')
    note_ids = set(n['n'] for n in notes)
    graded = sum(1 for n in notes if n.get('grade'))
    if graded != len(notes):
        errors.append(f'{num}: {len(notes)-graded} notes without grade')
    for size in idx['sizes']:
        d = f'{OUT}/{size}/{num}'
        if not os.path.isdir(d):
            errors.append(f'{num}/{size}: missing dir'); continue
        pages = sorted(f for f in os.listdir(d) if f.endswith('.webp'))
        if len(pages) != ch['pages'][size]:
            errors.append(f'{num}/{size}: files {len(pages)} != index {ch["pages"][size]}')
        for i, p in enumerate(pages, 1):
            fp = os.path.join(d, p)
            sz = os.path.getsize(fp)
            tot_bytes += sz
            if sz < 2000: errors.append(f'{num}/{size}/{p}: suspicious size {sz}')
            if p != f'p{i:03d}.webp': errors.append(f'{num}/{size}: page gap at {p}')
        hits = json.load(open(f'{d}/hits.json', encoding='utf-8'))
        hit_fns = set(h['fn'] for h in hits)
        if hit_fns != note_ids:
            missing = note_ids - hit_fns; extra = hit_fns - note_ids
            errors.append(f'{num}/{size}: hits mismatch missing={sorted(missing)} extra={sorted(extra)}')
        for h in hits:
            if not (1 <= h['page'] <= ch['pages'][size]): errors.append(f'{num}/{size}: hit page out of range')
            if not (0 <= h['x'] <= 1 and 0 <= h['y'] <= 1.01): errors.append(f'{num}/{size}: hit coords out of range')
        tot_pages[size] += len(pages)
print('chapters:', len(idx['chapters']))
print('pages per size:', tot_pages)
print('total footnotes:', sum(len(json.load(open(f"{OUT}/notes_{c['num']}.json", encoding='utf-8'))) for c in idx['chapters']))
print('total webp bytes:', tot_bytes, f'({tot_bytes/1024/1024:.1f} MB)')
print('ERRORS:', len(errors))
for e in errors[:25]: print(' -', e)
sys.exit(1 if errors else 0)

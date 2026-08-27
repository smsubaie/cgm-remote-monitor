# -*- coding: utf-8 -*-
"""يبني ملف المحتوى الأم بصيغة التأليف المعتمدة:
متن بعلامات #n...# محلية + «الحواشي والتخريج» مدرّجة، مع دمج الحواشي المتماثلة المتجاورة."""
import re, os, json, sys
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

meta = json.load(open('articles/meta.json', encoding='utf-8'))
MANUAL = json.load(open('manual_grades.json', encoding='utf-8'))
codex = json.load(open('codex_entries.json', encoding='utf-8'))

# --- footnotes map (سطرًا سطرًا لتجنّب ابتلاع الأسطر) ---
fnmap = {}
for line in open('book_footnotes.md', encoding='utf-8'):
    m = re.match(r'\[\^(\d+)\]:[ \t]*(.*)', line.strip())
    if m and m.group(2).strip():
        fnmap[m.group(1)] = m.group(2).strip()
assert fnmap.get('1'), 'footnote 1 missing'

AR2EN = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
WORKS = ['البخاري','مسلم','أحمد','الترمذي','أبي داود','أبو داود','النسائي','ابن ماجه',
         'ابن إسحاق','ابن هشام','ابن سعد','الواقدي','الطبري','البيهقي','الحاكم','ابن كثير',
         'الأزرقي','الطبراني','الدارمي','ابن حبان','أبو يعلى','عبد الرزاق','البلاذري',
         'ابن شبة','البزار','ابن أبي شيبة','الطيالسي','ابن الكلبي','أبو داود الطيالسي']
SIRA = r'ابن إسحاق|ابن هشام|ابن سعد|الواقدي|أهل السير|الطبري|الأزرقي|البلاذري|ابن الكلبي|ابن شبة|ابن كثير|أخبار مكة|الطبقات'
HADITH_MUSNAD = r'(?:مسند أحمد|أحمد|الترمذي|أبي داود|أبو داود|النسائي|ابن ماجه|الحاكم|الطبراني|البيهقي|الدارمي|ابن حبان|أبو يعلى|عبد الرزاق|البزار)'

def toks(t):
    t2 = t.translate(AR2EN)
    nums = set(re.findall(r'\d{2,5}', t2))
    works = set(w for w in WORKS if w in t)
    suras = set(re.findall(r'سورة\s+([^\s(،؛.]+)', t))
    return nums, works, suras

def has_bukhari(t): return 'البخاري' in t
def has_muslim(t): return re.search(r'(?<!ابن )(?<!أبي )مسلم', t) is not None
def has_quran(t): return 'القرآن' in t or 'سورة' in t
def has_sira(t): return re.search(SIRA, t) is not None
def has_musnad(t): return re.search(HADITH_MUSNAD, t) is not None

def codex_match(num, t, want_sira=False):
    ents = codex.get(num, [])
    rn, rw, rs = toks(t)
    best, bi = 0, None
    for i, e in enumerate(ents):
        en, ew, es = toks(e['body'])
        s = 3*len(rn & en) + len(rw & ew) + 2*len(rs & es)
        if s > best:
            best, bi = s, i
    if bi is None: return None, 0
    return ents[bi], best

def grade_of(num, t):
    """يعيد (grade, method)"""
    tq, tb, tm = has_quran(t), has_bukhari(t), has_muslim(t)
    sira, musnad = has_sira(t), has_musnad(t)
    # قرآن
    if tq and not (tb or tm or musnad):
        if sira: return 'الآية قطعية؛ وسياق النزول عند أهل التفسير والسير', 'rule'
        return 'قرآن كريم — قطعي', 'rule'
    if 'متفق' in t or (tb and tm):
        if sira or tq: return 'متفق عليه في أصله؛ والتفصيل عند أهل السير', 'rule'
        return 'متفق عليه', 'rule'
    if tb or tm:
        if tq and not sira: return 'صحيح؛ والآية قطعية', 'rule'
        if sira or musnad: return 'أصله صحيح؛ والتفصيل عند أهل السير', 'rule'
        return 'صحيح', 'rule'
    # درجات منصوصة داخل الحاشية نفسها
    if 'بإسناد حسن' in t or 'إسناد حسن' in t or 'حسنه' in t or 'حسّنه' in t:
        return 'حسن', 'stated'
    if 'صحح' in t or 'صحّح' in t or 'بإسناد صحيح' in t:
        return 'صحيح في أصله', 'stated'
    if 'مرسل' in t: return 'مرسل', 'stated'
    # مطابقة الكودكس
    e, score = codex_match(num, t)
    if e and e.get('grade'):
        if (score >= 3) or (score >= 2 and has_sira(e['body']) == sira):
            return e['grade'].replace('**','').strip(), 'codex'
    # مسند/سنن دون تنصيص
    if musnad and not sira:
        if e and e.get('grade') and score >= 1:
            return e['grade'].replace('**','').strip(), 'codex-weak'
        return 'حسن — انظر تخريجه في مظانّه', 'fallback-musnad'
    # سيرة فقط
    if sira or not (tb or tm or tq or musnad):
        if e and e.get('grade') and score >= 1 and re.search(r'مغاز|مرسل|حسن', e['grade']):
            return e['grade'].replace('**','').strip(), 'codex-sira'
        return 'مرسل — تتلقاه كتب السير والمغازي بالقبول', 'fallback-sira'
    return 'انظر مصدره', 'none'

# --- تقسيم الجمل ---
SENT_END = re.compile(r'[.؛!؟](?=[\s"\n]|\[\^|$)')
def sentence_starts(par):
    starts = [0]
    for m in SENT_END.finditer(par):
        j = m.end()
        while j < len(par):
            if par[j] in ' "\n':
                j += 1; continue
            rm = REF.match(par, j)
            if rm:
                j = rm.end(); continue
            break
        if j < len(par): starts.append(j)
    return starts

def norm_src(t):
    return re.sub(r'[\s"،؛.()]+', '', t)

REF = re.compile(r'\[\^(\d+)\]')

def process_article(num, text):
    """يعيد (متنًا بعلامات #n#، قائمة حواشٍ محلية [(local, [globals], text, grade)])"""
    paragraphs = text.split('\n\n')
    local = 0
    seen = {}      # المصدر المطبّع -> الرقم المحلي
    entries = []   # [local, [global refs], text, spans]
    out_pars = []
    for par in paragraphs:
        refs = list(REF.finditer(par))
        if not refs:
            out_pars.append(par); continue
        starts = sentence_starts(par)
        def sent_idx(pos):
            si = 0
            for i, s in enumerate(starts):
                if s <= pos: si = i
                else: break
            return si
        # تجميع المتجاور المتماثل المصدر
        groups = []
        for m in refs:
            r = m.group(1)
            t = fnmap.get(r, '')
            si = sent_idx(m.start())
            if groups and norm_src(groups[-1]['text']) == norm_src(t) and si - groups[-1]['si_last'] <= 1:
                groups[-1]['refs'].append(r)
                groups[-1]['marks'].append(m)
                groups[-1]['si_last'] = si
            else:
                groups.append({'refs':[r], 'marks':[m], 'text':t,
                               'si_first':si, 'si_last':si})
        # بناء الفقرة الجديدة
        new_par = []
        cursor = 0
        for g in groups:
            key = norm_src(g['text'])
            if key in seen:
                n = seen[key]
                for r in g['refs']:
                    if r not in entries[n-1][1]:
                        entries[n-1][1].append(r)
                entries[n-1][3] += 1
            else:
                local += 1
                n = local
                seen[key] = n
                entries.append([n, list(g['refs']), g['text'], 1])
            s = max(starts[g['si_first']], cursor)
            e = g['marks'][-1].start()
            if s > e: s = e
            new_par.append(par[cursor:s])
            seg = REF.sub('', par[s:e])
            new_par.append(f'#{n}' + seg + '#')
            cursor = g['marks'][-1].end()
        new_par.append(REF.sub('', par[cursor:]))
        out_pars.append(''.join(new_par))
    # الدرجات ونصوص الحواشي
    final_entries = []
    for local_, grefs, t, spans in entries:
        g, method = grade_of(num, t)
        mg = MANUAL.get(f'{num}|{norm_src(t)}')
        if mg: g, method = mg, 'manual'
        body = t if t.endswith(('.', '؛')) else t + '.'
        body += f' الدرجة: **{g}**.'
        final_entries.append({'local': local_, 'globals': grefs, 'text': t,
                              'grade': g, 'method': method, 'body': body,
                              'spans': spans})
    return '\n\n'.join(out_pars), final_entries

# --- المرور على المقالات كلها ---
def article_text(num):
    p = f'expanded/{num}.md'
    return open(p if os.path.exists(p) else f'articles/{num}.md', encoding='utf-8').read().strip()

order = sorted(meta.keys())
results = {}
audit = {'total_old': 0, 'total_new': 0, 'methods': Counter()}
mapping_rows = []
for num in order:
    text = article_text(num)
    new_text, entries = process_article(num, text)
    results[num] = (new_text, entries)
    audit['total_old'] += sum(len(e['globals']) for e in entries)
    audit['total_new'] += len(entries)
    for e in entries:
        audit['methods'][e['method']] += 1
        for gref in e['globals']:
            mapping_rows.append((gref, num, e['local']))

print('old refs accounted:', audit['total_old'], '→ new local footnotes:', audit['total_new'])
print(dict(audit['methods']))

# فحوص
old_all = set(r for m in meta.values() for r in m['refs'])
mapped = set(r for r, _, _ in mapping_rows)
missing = old_all - mapped
extra = mapped - old_all
print('missing:', sorted(missing, key=int)[:10], 'extra:', sorted(extra, key=int)[:10])

for num in order:
    new_text, entries = results[num]
    # توازن العلامات
    opens = re.findall(r'#(\d+)(?![\d])', new_text)
    closes = new_text.count('#') - len(opens)
    nums_found = [int(x) for x in opens]
    # الظهور الأول لكل رقم تصاعدي، ومجموعة الأرقام = 1..k
    firsts = []
    for n in nums_found:
        if n not in firsts: firsts.append(n)
    if firsts != list(range(1, len(entries)+1)):
        print('SEQ FAIL', num, firsts[:20]); sys.exit(1)
    if closes != len(nums_found):
        print('BALANCE FAIL', num, closes, len(nums_found)); sys.exit(1)
    exp_spans = sum(e['spans'] for e in entries)
    if len(nums_found) != exp_spans:
        print('SPAN COUNT FAIL', num, len(nums_found), exp_spans); sys.exit(1)
    # سلامة الكلمات: النص بلا علامات = القديم بلا مراجع
    plain_new = re.sub(r'#\d*', '', new_text)
    plain_old = REF.sub('', article_text(num))
    if plain_new.split() != plain_old.split():
        print('WORD DIFF', num)
        a, b = plain_new.split(), plain_old.split()
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y: print(i, x, y); break
        sys.exit(1)

# بوابة المحظورات الأسلوبية (قواعد المالك)
BANNED = [
    ('أهل السير/المغازي في المتن', __import__('re').compile(r'أهل السير|أهل المغازي')),
    ('ألفاظ تخريج في المتن', __import__('re').compile(r'\bروي\b|رُوي|يُروى|بإسناد|رواه|مراسيل|إسناد')),
    ('إخبار بالمستقبل', __import__('re').compile(r'وسيأتي|وستأتي|وسيجيء|ستدور|وسيكون ذلك')),
    ('تعليل متقابل لأنه/لا لأن', __import__('re').compile(r'لأنه[^.؛\n]{0,50}لا لأن')),
    ('علامات محظورة', __import__('re').compile(r'[«»–]')),
]
viol = 0
for num in order:
    txt = article_text(num)
    for name, pat in BANNED:
        for m in pat.finditer(txt):
            s = max(0, m.start()-40)
            print(f'BANNED [{num}][{name}]: …{txt[s:m.end()+40]}…'.replace(chr(10),' '))
            viol += 1
if viol:
    print('STYLE GATE FAIL:', viol); sys.exit(1)
print('GATES OK')
json.dump({num: [dict(local=e['local'], globals=e['globals'], grade=e['grade'],
                      method=e['method'], body=e['body'], spans=e['spans']) for e in ents]
           for num, (t, ents) in results.items()},
          open('master_entries.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open('master_texts.json', 'w', encoding='utf-8') as f:
    json.dump({num: t for num, (t, e) in results.items()}, f, ensure_ascii=False)
with open('mapping_old_to_local.tsv', 'w', encoding='utf-8') as f:
    f.write('الحاشية القديمة\tالمقال\tالرقم المحلي\n')
    for r, num, loc in sorted(mapping_rows, key=lambda x: int(x[0])):
        f.write(f'{r}\t{num}\t{loc}\n')
print('saved.')

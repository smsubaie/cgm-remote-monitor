# -*- coding: utf-8 -*-
"""حذف أصول الإصدار السابق (صفحات الرواية فقط) مع استثناء التمهيد — بقرار المالك 2026-08-28.
يعمل على مرحلتين: عرض قائمة ما سيحذف أولا (dry-run افتراضيا)، ثم الحذف بـ --apply.

الاستعمال:
  python3 cleanup_previous.py --endpoint https://<ACCOUNT>.r2.cloudflarestorage.com \
      --bucket midan --prefix <مسار_الإصدار_السابق>/ \
      --keep-substr التمهيد --keep-substr tamhid [--apply]

- prefix: المسار الذي تعيش تحته أصول الرواية في الإصدار السابق.
- keep-substr: أي مفتاح يحتوي إحدى هذه السلاسل يستبقى (التمهيد). تكرر الخيار للمرادفات.
- بلا --apply يطبع ما سيحذف فقط ولا يمس شيئا.
"""
import argparse, sys
try:
    import boto3
except ImportError:
    sys.exit('يلزم boto3: pip install boto3')

p = argparse.ArgumentParser()
p.add_argument('--endpoint', required=True)
p.add_argument('--bucket', required=True)
p.add_argument('--prefix', required=True)
p.add_argument('--keep-substr', action='append', default=[])
p.add_argument('--apply', action='store_true')
a = p.parse_args()

s3 = boto3.client('s3', endpoint_url=a.endpoint)
to_delete, kept = [], []
paginator = s3.get_paginator('list_objects_v2')
for page in paginator.paginate(Bucket=a.bucket, Prefix=a.prefix):
    for obj in page.get('Contents', []):
        key = obj['Key']
        if any(k in key for k in a.keep_substr):
            kept.append(key)
        else:
            to_delete.append(key)

print(f'سيحذف: {len(to_delete)} ملفا — يستبقى (التمهيد): {len(kept)} ملفا')
for k in kept: print('  يبقى:', k)
for k in to_delete[:40]: print('  يحذف:', k)
if len(to_delete) > 40: print(f'  ... و{len(to_delete)-40} غيرها')

if not a.apply:
    print('\n(عرض فقط — أعد التشغيل مع --apply للحذف الفعلي)')
    sys.exit(0)

for i in range(0, len(to_delete), 1000):
    batch = [{'Key': k} for k in to_delete[i:i+1000]]
    s3.delete_objects(Bucket=a.bucket, Delete={'Objects': batch})
print(f'حذف {len(to_delete)} ملفا؛ استبقي التمهيد ({len(kept)}).')

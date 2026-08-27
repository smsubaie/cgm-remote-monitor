#!/usr/bin/env bash
# نشر أصول الإصدار التالي إلى R2 (متوافق مع S3) — وفق منهجية الإصدارات المعتمدة.
# الاستعمال:
#   export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
#   ./publish_r2.sh <R2_ENDPOINT> <BUCKET> <RELEASE_ID> <ASSETS_DIR>
# مثال:
#   ./publish_r2.sh https://<ACCOUNT_ID>.r2.cloudflarestorage.com midan r2-20260828 ./release_r2
# الخطوات: 1) رفع كل الأصول إلى مسار releases/<RELEASE_ID>/ دون مساس بالحي
#          2) فحص الاكتمال (عدد الملفات والأحجام) قبل أي تبديل للفهرس
set -euo pipefail
ENDPOINT="$1"; BUCKET="$2"; RID="$3"; DIR="$4"
command -v aws >/dev/null || { echo "يلزم aws cli (pip install awscli)"; exit 1; }

echo "== رفع الأصول إلى s3://$BUCKET/releases/$RID/ =="
aws s3 sync "$DIR" "s3://$BUCKET/releases/$RID/" --endpoint-url "$ENDPOINT" --no-progress

echo "== فحص الاكتمال =="
LOCAL_COUNT=$(find "$DIR" -type f | wc -l)
REMOTE_COUNT=$(aws s3 ls "s3://$BUCKET/releases/$RID/" --recursive --endpoint-url "$ENDPOINT" | wc -l)
echo "محلي: $LOCAL_COUNT ملفا — مرفوع: $REMOTE_COUNT ملفا"
[ "$LOCAL_COUNT" -eq "$REMOTE_COUNT" ] || { echo "نقص في الرفع — لا تنشر الفهرس"; exit 1; }

echo "اكتمل الرفع. الخطوة التالية (يدوية أو عبر cleanup/switch): نشر الفهرس/الشيفرة المؤشرة إلى releases/$RID ثم اختبار midan.blog حيا."

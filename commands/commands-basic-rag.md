# Commands — `basic-rag` branch (Local & Cloud Options)

Stage 1 of 3: Plain RAG pipeline only:
Ingestion → Hybrid Search (Dense + BM25) → Cross-Encoder Re-rank → LangGraph Agent → Cited Answer.

---

## المسار الأول (الموصى به): التشغيل المجاني 100% محلياً (Zero-Cost / No GCP Billing)

هذا المسار يعمل بالكامل على جهازك دون الحاجة لحساب فوترة على Google Cloud أو كروت بنكية:

### 1. إعداد بيئة بايثون وتثبيت المكتبات
```bash
# إنشاء وتفعيل البيئة
uv venv hrrenv
# تفعيل البيئة على ويندوز:
hrrenv\Scripts\activate
# تثبيت المتطلبات:
uv pip install -r requirements.txt
```

### 2. تجهيز ملف المتغيرات البيئية `.env`
```bash
cp .env.example .env
```
املأ فقط المفاتيح المجانية في `.env`:
* `JINA_API_KEY`: مجاني من https://jina.ai (تسجيل بـ GitHub يعطيك 1,000,000 توكن مجاناً).
* `QDRANT_URL` و `QDRANT_API_KEY`: مجاني من https://cloud.qdrant.io (كلاستر مجاني دائم بدون فيزا).
* `GEMINI_API_KEY`: مجاني من https://aistudio.google.com أو استخدم `GROQ_API_KEY`.
* `LANGSMITH_API_KEY`: اختياري للمراقبة المجانية من https://smith.langchain.com.

### 3. تشغيل خط استيعاب البيانات وفهرسة المتجهات (Local Ingestion)
```bash
# قراءة اللوائح المحلية وفهرستها في Qdrant مباشرة:
python ingest.py --hr-only
```

### 4. تشغيل التطبيق التفاعلي (Web Chat UI)
```bash
# تشغيل واجهة المستخدم عبر Streamlit:
streamlit run app.py

# أو تجربة الكونسول السريع (CLI Demo):
python main.py
```

---

## المسار الثاني: التشغيل السحابي عبر Google Cloud (اختياري للشركات)

هذا المسار مخصص لمن يمتلك حساب Google Cloud مفعل عليه الفوترة (Enterprise / Credit Card):

### 1. تهيئة مشروع Google Cloud
```bash
PROJECT_ID=rag-hr-assistant-demo
REGION=us-central1
GCS_BUCKET_NAME=rag-hr-assistant-demo-hr-policies
BILLING_ACCOUNT_ID=YOUR_BILLING_ACCOUNT_ID

# تسجيل الدخول وتحديد المشروع
gcloud auth login
gcloud projects create $PROJECT_ID --name="RAG HR Assistant Demo"
gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID
gcloud config set project $PROJECT_ID

# تفعيل تصاريح التطبيقات (ADC)
gcloud auth application-default login
gcloud auth application-default set-quota-project $PROJECT_ID

# تفعيل خدمات Vertex AI و Cloud Storage
gcloud services enable aiplatform.googleapis.com storage.googleapis.com --project=$PROJECT_ID

# إنشاء حاوية التخزين السحابي
gcloud storage buckets create gs://$GCS_BUCKET_NAME --project=$PROJECT_ID --location=$REGION
```

### 2. استيعاب البيانات ورفعها إلى السحابة
```bash
python ingest.py
```

---

## ملاحظات استكشاف الأخطاء (Troubleshooting)
* إذا ظهر خطأ في الاتصال بـ Qdrant: تأكد من صحة الرابط والـ API Key في `.env`.
* إذا لم تكن مسجلاً في Google Cloud: استخدم المسار الأول (Local Ingestion) لتفادي خطأ `OR_BACR2_59`.

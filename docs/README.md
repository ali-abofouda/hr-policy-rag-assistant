# وثائق مشروع مساعد سياسات الموارد البشرية (HR Policy RAG Assistant Documentation)

مرحباً بك في التوثيق الهندسي والمعماري لمشروع **مساعد سياسات الموارد البشرية المؤمن للشركات** (`HR Policy RAG Assistant with Enterprise AI Security`).

---

## خريطة الوثائق والمحاضرات (Architecture & Implementation Map)

| رقم المحاضرة | عنوان المحاضرة والوثيقة | الملف التوثيقي (`docs/`) | المرحلة (Phase) |
| :---: | :--- | :--- | :---: |
| **142** | الترحيب بمشروع مساعد الـ HR واستعراض النظام الحي | [`01-hr-policy-assistant-architecture-and-overview.md`](./01-hr-policy-assistant-architecture-and-overview.md) | Kickoff & Overview (مكتمل) |
| **143** | مقدمة لمعمارية المشروع ومراحل التطور الثلاث | [`02-project-architecture-and-three-phase-evolution.md`](./02-project-architecture-and-three-phase-evolution.md) | Architecture & Roadmap (مكتمل) |
| **144** | الطور الأول: تأسيس الاسترجاع الهجين المحلي وهندسة البيانات المشوشة | [`03-phase-1-local-hybrid-rag-foundations.md`](./03-phase-1-local-hybrid-rag-foundations.md) | Phase 1: Foundations & Setup (مكتمل) |
| **145** | إدارة الإعدادات المركزية وتكوين البيئة والمفاتيح | [`04-project-settings-and-configuration-management.md`](./04-project-settings-and-configuration-management.md) | Phase 1: Configuration Management (مكتمل) |
| **146** | تحميل الوثائق وهندسة معالجة الصيغ المتعددة وموجهات النظام | [`05-document-loading-and-multi-format-processing.md`](./05-document-loading-and-multi-format-processing.md) | Phase 1: Document Loading & Multi-format (مكتمل) |
| **147** | تقطيع المستندات وتوليد التضمينات والتخزين المتجهي الهجين | [`06-document-chunking-and-vector-store-ingestion.md`](./06-document-chunking-and-vector-store-ingestion.md) | Phase 1: Ingestion & Hybrid Vector Store (مكتمل) |
| **148** | أتمتة وتنسيق خط إدخال البيانات والتحكم عبر الـ CLI | [`07-data-ingestion-pipeline-orchestration.md`](./07-data-ingestion-pipeline-orchestration.md) | Phase 1: Ingestion Pipeline Orchestration (مكتمل) |
| **149 - 151** | بناء محرك الاسترجاع وإعادة الترتيب وسلسلة التوليد | قيد المعالجة | Phase 1: Retrieval & Generation Pipeline |
| **152 - 159** | الطور الثاني: أمان النماذج اللغوية واختبارات الاختراق | قيد المعالجة | Phase 2: LLM Security & Evals |
| **160 - 163** | الطور الثالث: الحاويات والنشر السحابي الكامل | قيد المعالجة | Phase 3: Deployment |

---

## الأهداف المعمارية والعملية للمشروع
1. **التعامل مع قواعد البيانات المشوشة (`Noisy Enterprise Databases`)** عبر تقنيات الـ `Re-ranking` لضمان دقة الاسترجاع حتى في بيئات البيانات غير المنتظمة.
2. **بناء بوابة ذكاء اصطناعي ذاتية الاستضافة (`Self-Hosted LiteLLM Gateway`)** لتوحيد الاستدعاء وإدارة التبديل التلقائي بين النماذج وحساب التكاليف.
3. **تطبيق دروع الحماية المتقدمة (`Google Model Armor & Guardrails`)** لمنع الـ Prompt Injection وتحديد نطاق التخصص.
4. **توفير كاش دلالي ذكي (`Semantic Caching`)** لتخفيض زمن الاستجابة إلى الصفر وتوفير تكاليف استدعاء النماذج.
5. **إجراء اختبارات الفريق الأحمر (`Red Teaming`)** للتحقق البرمجي من مناعة النظام ضد هجمات كسر الشخصية وتجاوز التعليمات.
6. **النشر السحابي الإنتاجي (`Cloud-Native Deployment`)** باستخدام Docker و Google Cloud Run وحماية الدخول عبر Google OAuth.

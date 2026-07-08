import os
import io
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from google import genai
from PIL import Image

# إعداد قاعدة البيانات التزامنية
DATABASE_URL = "sqlite:///smart_reader_open.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    file_name = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="documents")

Base.metadata.create_all(bind=engine)

# تهيئة خادم الـ API والذكاء الاصطناعي
app = FastAPI(title="القارئ الذكي - النسخة المفتوحة")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = genai.Client(AIzaSyB9wGRfI3_ukuAwXBpVKDHTcGCH3pmUrjY)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/api/upload")
def upload_and_ocr(project_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        image_bytes = file.file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        prompt = """
        أنت محقق مخطوطات خبير. استخرج النص العربي من هذه الصورة بدقة فائقة وبأعلى جودة ممكنة.
        حافظ على علامات الترقيم، وقدم النص مشكولاً شكلاً صحيحاً. اكتفِ بالنص المستخرج فقط.
        """
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=[image, prompt])
        extracted = response.text
        
        doc = Document(project_id=project_id, file_name=file.filename, extracted_text=extracted)
        db.add(doc)
        db.commit()
        
        return {"document_id": doc.id, "extracted_text": extracted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
def analyze_text(text: str = Form(...), field: str = Form(...), task: str = Form(...)):
    prompt = f"""
    أنت عالم وباحث أكاديمي متمرس في علم ([{field}]).
    المهمة المطلوب منك تنفيذها هي: [{task}] للنص المقتبس أدناه.
    النص المقتبس: "{text}"
    التعليمات: قدم تحليلاً عميقاً ورصيناً يتناسب مع المصطلحات العلمية الخاصة بهذا الفن ([{field}]).
    """
    try:
        response = ai_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return {"analysis_result": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>القارئ الذكي 3.0 - مساحة العمل</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Amiri&family=Cairo:wght@400;700&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Cairo', sans-serif; background-color: #0b1325; color: #e2e8f0; }
            .font-serif-academic { font-family: 'Amiri', serif; }
        </style>
    </head>
    <body class="min-h-screen flex flex-col">
        <header class="border-b border-[#1e2d4a] bg-[#0b1325]/90 px-6 py-4 flex justify-between items-center">
            <div class="flex items-center gap-3">
                <span class="text-xl font-bold text-[#d4af37]">القارئ الذكي 3.0 <span class="text-xs bg-[#162238] text-gray-400 px-2 py-1 rounded">النسخة المفتوحة</span></span>
            </div>
            <div class="text-sm text-gray-400">المشروع الحالي: <strong class="text-[#e2e8f0]">تحقيق مخطوطة الفقه الكبرى</strong></div>
        </header>

        <div class="flex-1 flex overflow-hidden">
            <div class="w-1/2 p-6 border-l border-[#1e2d4a] flex flex-col gap-4">
                <div class="flex justify-between items-center">
                    <h2 class="text-lg font-semibold text-[#d4af37]">وثيقة المصدر والـ OCR</h2>
                    <div class="flex gap-2">
                        <select id="fieldSelect" class="bg-[#162238] border border-[#1e2d4a] text-sm rounded px-2 py-1 text-white">
                            <option>فقه وأصوله</option>
                            <option>لغة عربية وبلاغة</option>
                            <option>فلسفة ومنطق</option>
                        </select>
                        <select id="taskSelect" class="bg-[#162238] border border-[#1e2d4a] text-sm rounded px-2 py-1 text-white">
                            <option>شرح وتفسير</option>
                            <option>تلخيص مكثف</option>
                            <option>استخراج الأعلام والمصطلحات</option>
                        </select>
                    </div>
                </div>

                <label class="h-32 bg-[#162238] border border-[#1e2d4a] rounded-lg border-dashed flex flex-col items-center justify-center cursor-pointer hover:bg-[#1e2d4a]/50 transition">
                    <input type="file" id="fileInput" accept="image/*" class="hidden" onchange="uploadFile()" />
                    <span id="uploadStatus" class="text-sm text-gray-300">اضغط لرفع صورة كتاب أو مخطوطة حقيقية</span>
                </label>

                <div class="flex-1 bg-[#162238] border border-[#1e2d4a] rounded-lg p-4 flex flex-col">
                    <textarea id="extractedArea" class="w-full flex-1 bg-transparent resize-none focus:outline-none font-serif-academic text-xl leading-relaxed" placeholder="سيظهر النص المستخرج هنا حياً بعد الرفع..."></textarea>
                    <button onclick="runAnalysis()" class="mt-3 w-full bg-[#d4af37] text-[#0b1325] font-bold py-2 rounded hover:bg-[#e5c158] transition">تشغيل خوارزميات التخصص المعرفي ⚡</button>
                </div>
            </div>

            <div class="w-1/2 p-6 flex flex-col gap-4 bg-[#0f192e]">
                <h2 class="text-lg font-semibold text-[#d4af37]">مسودة البحث والمحرر الذكي</h2>
                
                <div id="analysisCard" class="hidden bg-[#162238] border border-[#d4af37]/40 rounded-lg p-4">
                    <span class="text-xs text-[#d4af37] font-bold block mb-1">⚡ نتيجة التحليل المستلمة:</span>
                    <p id="analysisText" class="text-sm font-serif-academic text-gray-200 leading-relaxed"></p>
                    <button onclick="insertToEditor()" class="mt-2 text-xs bg-[#d4af37]/20 text-[#d4af37] px-3 py-1 rounded border border-[#d4af37]/30 hover:bg-[#d4af37]/30">إدراج في مسودة البحث ↑</button>
                </div>

                <div class="flex-1 bg-[#f4ebd0] text-[#1c1c1c] rounded-lg p-6 shadow-inner flex flex-col">
                    <textarea id="editorArea" class="w-full flex-1 bg-transparent resize-none font-serif-academic text-xl leading-relaxed focus:outline-none text-justify" placeholder="اكتب مسودتك هنا، أو ادمج الحواشي والشروحات المستخلصة لبناء بحثك..."></textarea>
                </div>
            </div>
        </div>

        <script>
            let currentDocId = null;

            async function uploadFile() {
                const fileInput = document.getElementById('fileInput');
                const status = document.getElementById('uploadStatus');
                if (!fileInput.files[0]) return;

                status.innerText = "جاري قراءة المخطوطة بالذكاء الاصطناعي...";
                const formData = new FormData();
                formData.append('project_id', 1);
                formData.append('file', fileInput.files[0]);

                try {
                    const res = await fetch('/api/upload', { method: 'POST', body: formData });
                    const data = await res.json();
                    currentDocId = data.document_id;
                    document.getElementById('extractedArea').value = data.extracted_text;
                    status.innerText = "تم الرفع والاستخلاص بنجاح!";
                } catch (e) {
                    alert("حدث خطأ أثناء الاتصال بالسيرفر");
                    status.innerText = "اضغط لإعادة المحاولة";
                }
            }

            async function runAnalysis() {
                const text = document.getElementById('extractedArea').value;
                if (!text) return alert("الرجاء استخراج نص أولاً.");

                const field = document.getElementById('fieldSelect').value;
                const task = document.getElementById('taskSelect').value;
                
                const formData = new FormData();
                formData.append('text', text);
                formData.append('field', field);
                formData.append('task', task);

                try {
                    const res = await fetch('/api/analyze', { method: 'POST', body: formData });
                    const data = await res.json();
                    document.getElementById('analysisText').innerText = data.analysis_result;
                    document.getElementById('analysisCard').classList.remove('hidden');
                } catch (e) {
                    alert("خطأ في جلب التحليل");
                }
            }

            function insertToEditor() {
                const analysis = document.getElementById('analysisText').innerText;
                const field = document.getElementById('fieldSelect').value;
                const editor = document.getElementById('editorArea');
                editor.value += `\\n\\n[حاشية وتحليل - ${field}]:\\n` + analysis;
                document.getElementById('analysisCard').classList.add('hidden');
            }
        </script>
    </body>
    </html>
    """

# Docker + PostgreSQL + pgvector + Hugging Face/Groq Entegrasyonu

Bu doküman, `rag-doc-qa` projesinde uygulamayı Docker ortamına taşırken kullanılan **Docker, PostgreSQL, pgvector, Hugging Face ve Groq** entegrasyonunun nasıl kurulduğunu ve neden kullanıldığını açıklar.

Amaç, projeyi yalnızca yerel bilgisayarda çalıştırmak yerine, gerekli servisleri container'lar içerisinde çalıştırarak daha taşınabilir ve düzenli bir RAG uygulaması oluşturmaktır.

---

# 1. Projenin Genel Mimarisi

Projenin temel amacı, yüklenen PDF dokümanları içerisinden kullanıcının sorduğu sorulara cevap verebilen bir **RAG (Retrieval-Augmented Generation)** sistemi oluşturmaktır.

Genel akış:

```text
                    Kullanıcı
                        │
                        ▼
                  FastAPI / Swagger
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     ▼
       /api/upload              /api/ask
             │                     │
             ▼                     ▼
       PDF işleme           Similarity Search
             │                     │
             ▼                     ▼
          Chunking             pgvector
             │                     │
             ▼                     ▼
        Embedding              Top-K Chunks
             │                     │
             ▼                     ▼
      PostgreSQL + pgvector      Context
                                   │
                                   ▼
                              Prompt oluşturma
                                   │
                                   ▼
                         Hugging Face InferenceClient
                                   │
                                   ▼
                              Groq Provider
                                   │
                                   ▼
                           GPT-OSS-20B
                                   │
                                   ▼
                         Cevap + Kaynaklar
```

---

# 2. Neden Docker Kullandık?

Uygulamamız birden fazla bileşenden oluşuyor:

* FastAPI
* Python bağımlılıkları
* PostgreSQL
* pgvector
* Embedding modeli
* Hugging Face API
* Groq provider

Bunların tamamını bilgisayar üzerinde ayrı ayrı kurup yönetmek yerine Docker kullanarak uygulamayı container'lara ayırdık.

Docker'ın temel avantajları:

* Ortam bağımlılıklarını azaltmak
* Uygulamayı taşınabilir hale getirmek
* PostgreSQL'i ayrı bir container'da çalıştırmak
* Uygulamanın çalışacağı Python ortamını sabitlemek
* Projeyi başka bir bilgisayarda daha kolay çalıştırabilmek
* Daha sonra deployment yapmayı kolaylaştırmak

Bu projede iki temel container kullandık:

```text
rag_app
rag_postgres
```

---

# 3. Proje Yapısı

Docker entegrasyonundan sonra ilgili yapı şu şekilde:

```text
rag-doc-qa/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── models/
│   └── ...
│
├── scripts/
│   └── init_db.sql
│
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── .env
├── requirements.txt
└── ...
```

Burada:

### `Dockerfile`

FastAPI uygulamasının Docker image'ını oluşturmak için kullanılır.

### `docker-compose.yml`

FastAPI ve PostgreSQL container'larını birlikte yönetmek için kullanılır.

### `.env`

API token gibi gizli bilgileri saklamak için kullanılır.

### `requirements.txt`

Python bağımlılıklarını tanımlar.

### `scripts/init_db.sql`

PostgreSQL/pgvector veritabanının başlangıç ayarlarını yapmak için kullanılır.

---

# 4. Dockerfile

Kullandığımız Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Satır satır açıklama

### `FROM`

```dockerfile
FROM python:3.11-slim
```

Python 3.11 tabanlı hafif bir Linux image kullanıyoruz.

Burada özellikle Python 3.11 kullandık çünkü projenin bağımlılıklarının bu Python sürümüyle uyumlu olması gerekiyor.

---

### `WORKDIR`

```dockerfile
WORKDIR /app
```

Container içerisindeki çalışma klasörünü `/app` olarak belirler.

Bundan sonraki komutlar bu klasöre göre çalışır.

---

### Sistem bağımlılıkları

```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

Linux tarafında gerekli bazı paketleri kurar.

Özellikle PostgreSQL ile ilgili Python paketlerinin kurulumu sırasında gerekli olabilecek sistem bağımlılıklarını sağlar.

---

### requirements.txt kopyalama

```dockerfile
COPY requirements.txt .
```

Host bilgisayardaki `requirements.txt` dosyasını container içerisine kopyalar.

---

### Python paketlerini kurma

```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```

Projede kullanılan Python paketlerini Docker image'ına yükler.

Örneğin:

```text
FastAPI
LangChain
pgvector
sentence-transformers
transformers
huggingface_hub
torch
uvicorn
```

gibi paketler burada kurulur.

---

### Proje dosyalarını kopyalama

```dockerfile
COPY . .
```

Uygulamanın kaynak kodlarını container içerisine kopyalar.

---

### Port

```dockerfile
EXPOSE 8000
```

FastAPI uygulamasının container içerisinde 8000 portunu kullanacağını belirtir.

---

### Uygulamayı başlatma

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Container başladığında FastAPI uygulamasını Uvicorn ile çalıştırır.

`0.0.0.0` kullanmamız önemlidir.

Çünkü uygulamanın yalnızca container içerisinden değil, host bilgisayardan da erişilebilir olması gerekir.

---

# 5. Docker Compose Neden Kullanıldı?

İki ayrı servisimiz var:

```text
FastAPI
PostgreSQL + pgvector
```

Bunları tek tek çalıştırmak yerine Docker Compose ile birlikte yönetiyoruz.

Kullandığımız `docker-compose.yml`:

```yaml
version: "3.9"

services:

  postgres:
    image: ankane/pgvector:latest
    container_name: rag_postgres
    restart: always
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ../scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: rag_app
    restart: always
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: ragdb
      DB_USER: postgres
      DB_PASSWORD: postgres
      HF_API_TOKEN: ${HF_API_TOKEN}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  pgdata:
```

---

# 6. PostgreSQL Container

PostgreSQL'i Docker içerisinde ayrı bir container olarak çalıştırdık.

Container adı:

```text
rag_postgres
```

Database:

```text
ragdb
```

Kullanıcı:

```text
postgres
```

Şifre:

```text
postgres
```

---

# 7. Neden PostgreSQL Kullanıyoruz?

RAG sisteminde PDF'den oluşturduğumuz chunk'ları saklamamız gerekiyor.

Her chunk ile birlikte örneğin:

```text
content
source_file
page
embedding
```

gibi bilgiler tutuluyor.

Normal bir SQL veritabanı metin ve metadata saklamak için kullanılabilir.

Ancak RAG sisteminde önemli bir ihtiyacımız daha var:

> Kullanıcının sorusuna anlam olarak en yakın chunk'ları bulmak.

Bunun için embedding vektörlerini saklamamız gerekiyor.

Bu noktada pgvector kullanıyoruz.

---

# 8. pgvector Nedir?

`pgvector`, PostgreSQL'e vektör saklama ve vektör benzerliği arama yeteneği kazandıran bir eklentidir.

RAG sistemlerinde embedding'leri veritabanında saklamak için kullanılabilir.

Örneğin:

```text
PDF metni
   ↓
Embedding Model
   ↓
[0.12, -0.34, 0.51, ...]
   ↓
PostgreSQL + pgvector
```

şeklinde çalışır.

---

# 9. Neden pgvector Kullandık?

RAG sistemimizde:

```text
Kullanıcı sorusu
      ↓
Question embedding
      ↓
Vector similarity search
      ↓
En alakalı chunk'lar
```

akışına ihtiyacımız var.

pgvector sayesinde bu işlemi PostgreSQL içerisinde gerçekleştirebiliyoruz.

Böylece ayrıca farklı bir vector database kurmak zorunda kalmadan mevcut PostgreSQL altyapısını kullanıyoruz.

---

# 10. PostgreSQL Container'ının Healthcheck'i

Compose içerisinde:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 5s
  timeout: 5s
  retries: 5
```

kullandık.

Amaç PostgreSQL container'ının sadece başlamış olmasını değil, gerçekten bağlantı kabul ediyor olmasını kontrol etmektir.

Daha sonra FastAPI servisini:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

ile PostgreSQL'in sağlıklı olmasına bağladık.

Böylece FastAPI'nin veritabanı hazır olmadan başlamasından kaynaklanabilecek sorunları azaltıyoruz.

---

# 11. PostgreSQL Volume

Compose içerisinde:

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```

kullanıyoruz.

Bu sayede PostgreSQL verileri container'ın yaşam döngüsünden bağımsız olarak volume içerisinde tutulur.

Container yeniden oluşturulsa bile volume korunuyorsa veriler kaybolmaz.

---

# 12. FastAPI Container

FastAPI uygulamamızın container adı:

```text
rag_app
```

Uygulama container içerisinde:

```text
0.0.0.0:8000
```

üzerinde çalışıyor.

Host bilgisayardan ise:

```text
localhost:8000
```

üzerinden erişiyoruz.

Compose içerisindeki:

```yaml
ports:
  - "8000:8000"
```

şu anlama gelir:

```text
Host                 Container

localhost:8000  →    8000
```

Bu nedenle Swagger'a:

```text
http://localhost:8000/docs
```

adresinden erişebiliyoruz.

---

# 13. Container'lar Arasında İletişim

Önemli noktalardan biri:

FastAPI container'ı PostgreSQL'e `localhost` üzerinden bağlanmaz.

Compose network içerisinde PostgreSQL servisinin adı:

```text
postgres
```

olduğu için:

```yaml
DB_HOST: postgres
```

kullanıyoruz.

Yani:

```text
rag_app
   │
   │ DB_HOST=postgres
   ▼
rag_postgres
```

şeklinde iletişim kuruluyor.

---

# 14. PDF Upload Akışı

PDF Swagger üzerinden:

```text
POST /api/upload
```

endpointine gönderiliyor.

Sonrasında:

```text
PDF
 ↓
Text Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
PostgreSQL + pgvector
```

işlemleri gerçekleştiriliyor.

Test sırasında:

```text
98 chunk pgvector'a yazıldı.
```

çıktısını aldık.

Bu, PDF'nin başarıyla işlenip chunk'ların vector database'e kaydedildiğini gösterdi.

---

# 15. Embedding Neden Kullanılıyor?

RAG sisteminde yalnızca keyword araması yapmak istemiyoruz.

Örneğin kullanıcı:

```text
"Geminin yakıt sistemi hakkında bilgi ver."
```

diye sorabilir.

Dokümanda ise:

```text
"Vessel fuel management system..."
```

şeklinde farklı bir ifade bulunabilir.

Embedding modelleri metinleri sayısal vektörlere dönüştürerek anlamsal benzerlik üzerinden arama yapmamıza yardımcı olur.

Akış:

```text
Doküman chunk
      ↓
Embedding Model
      ↓
Vector

Kullanıcı sorusu
      ↓
Embedding Model
      ↓
Vector

Vector ↔ Vector
      ↓
Similarity
      ↓
En alakalı chunk
```

---

# 16. Similarity Search

`/api/ask` çağrıldığında ilk aşamalardan biri:

```python
chunks = similarity_search(
    question,
    top_k=top_k
)
```

işlemidir.

Burada kullanıcı sorusuna en çok benzeyen chunk'lar PostgreSQL + pgvector üzerinden bulunur.

Örneğin:

```text
top_k = 5
```

ise en alakalı 5 chunk alınır.

---

# 17. Context Oluşturma

Bulunan chunk'lar:

```python
build_context(chunks)
```

fonksiyonu ile tek bir context haline getirilir.

Her chunk'ın yanında kaynak bilgisi de tutulur:

```text
[Kaynak: dosya.pdf, Sayfa: 3]

chunk içeriği...
```

Bu sayede LLM'e yalnızca metin değil, kaynağın hangi dosyadan ve sayfadan geldiği bilgisi de gönderilir.

---

# 18. RAG Prompt'u

Kullandığımız prompt:

```text
Aşağıdaki bağlamı kullanarak soruyu yanıtla.

Eğer cevap bağlamda yoksa:
"Bu bilgi dokümanda bulunmuyor."
de.

Bağlam:
{context}

Soru:
{question}
```

Buradaki amaç LLM'in cevabı kendi genel bilgisinden üretmek yerine öncelikle retrieval sonucunda bulunan dokümana dayandırmasını sağlamaktır.

Bu, RAG mimarisinin **Generation** aşamasıdır.

---

# 19. Hugging Face Entegrasyonu

LLM çağrısı için:

```python
from huggingface_hub import InferenceClient
```

kullanıyoruz.

Client:

```python
client = InferenceClient(
    token=HF_TOKEN,
    provider="groq"
)
```

şeklinde oluşturuluyor.

Burada Hugging Face üzerinden Inference API kullanıyoruz.

---

# 20. HF Token Neden `.env` İçerisinde?

API token gibi gizli bilgileri kaynak kodunun içine yazmak istemiyoruz.

Yanlış kullanım:

```python
token="hf_123456..."
```

Bu güvenli değildir.

Bunun yerine:

```env
HF_API_TOKEN=hf_...
```

şeklinde `.env` içerisinde saklıyoruz.

Python tarafında:

```python
HF_TOKEN = os.getenv("HF_API_TOKEN")
```

ile alıyoruz.

Docker Compose ise bunu container'a geçiriyor:

```yaml
HF_API_TOKEN: ${HF_API_TOKEN}
```

---

# 21. Docker'da `.env` Problemi

Geliştirme sırasında önemli bir problem yaşadık.

`.env` dosyamız proje kökünde bulunuyordu:

```text
rag-doc-qa/
├── .env
└── docker/
    └── docker-compose.yml
```

Ancak Compose'u `docker` klasöründen çalıştırdığımız için environment değişkeninin container'a geçmediğini gördük.

Sonuçta `/api/ask` çağrısında:

```text
httpx.LocalProtocolError:
Illegal header value b'Bearer '
```

hatasını aldık.

Bu hata token'ın boş olduğunu gösteriyordu.

---

# 22. Token Problemini Nasıl Çözdük?

Compose komutunda `.env` dosyasının yolunu açıkça belirttik:

```powershell
docker compose --env-file ../.env -f docker-compose.yml up --build
```

Böylece:

```text
../.env
   ↓
Docker Compose
   ↓
HF_API_TOKEN
   ↓
rag_app container
```

şeklinde token container'a aktarıldı.

Daha sonra tokenın kendisini yazdırmadan kontrol ettik:

```powershell
docker exec rag_app python -c "import os; print('HF token var mi:', bool(os.getenv('HF_API_TOKEN')))"
```

Sonuç:

```text
HF token var mi: True
```

oldu.

Bu şekilde secret değerini terminale yazdırmadan environment variable'ın mevcut olduğunu doğruladık.

---

# 23. Groq Provider

LLM çağrısında:

```python
provider="groq"
```

kullanıyoruz.

Model:

```python
model="openai/gpt-oss-20b"
```

şeklinde belirleniyor.

Çağrı:

```python
response = client.chat_completion(
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    model="openai/gpt-oss-20b",
    max_tokens=300,
    temperature=0.3,
)
```

şeklinde gerçekleşiyor.

Burada:

### `messages`

LLM'e gönderilen konuşma mesajlarını belirtir.

### `model`

Kullanılacak modeldir.

### `max_tokens`

Üretilecek cevabın maksimum uzunluğunu sınırlar.

### `temperature`

Cevabın üretimindeki rastlantısallığı kontrol eder.

Biz düşük bir değer:

```text
0.3
```

kullandık.

---

# 24. `/api/ask` Endpoint'i

Soru endpointinin temel akışı:

```python
result = answer_question(
    request.question,
    top_k=request.top_k
)
```

şeklindedir.

Ardından kaynaklar hazırlanır:

```python
sources = [
    SourceInfo(
        source_file=s["source_file"],
        page=s["page"]
    )
    for s in result["sources"]
]
```

Sonuç:

```python
return AskResponse(
    answer=result["answer"],
    sources=sources
)
```

şeklinde kullanıcıya döndürülür.

Böylece sistem sadece cevap üretmez.

Aynı zamanda cevabın hangi PDF ve sayfalardan geldiğini de döndürür.

---

# 25. Swagger Neden Kullanıldı?

FastAPI otomatik olarak Swagger/OpenAPI dokümantasyonu oluşturur.

Adres:

```text
http://localhost:8000/docs
```

Swagger'ı kullanmamızın temel amacı frontend geliştirmeden API endpointlerini doğrudan test etmektir.

Örneğin:

```text
POST /api/upload
POST /api/ask
```

endpointlerini tarayıcı üzerinden test edebiliriz.

Bu özellikle backend/RAG geliştirme sırasında oldukça kullanışlıdır.

---

# 26. Swagger ile Upload Testi

Önce:

```text
POST /api/upload
```

endpointi açılır.

`Try it out` seçilir.

PDF dosyası seçilir.

`Execute` yapılır.

Başarılı olduğunda:

```text
200 OK
```

alıyoruz.

Docker logunda:

```text
98 chunk pgvector'a yazıldı.
```

mesajını gördük.

Bu bize PDF'nin başarıyla işlendiğini gösterdi.

---

# 27. Swagger ile Ask Testi

Daha sonra:

```text
POST /api/ask
```

endpointi kullanılır.

Örnek:

```json
{
  "question": "Bu dokümanın konusu nedir?",
  "top_k": 5
}
```

gönderilir.

Başarılı durumda:

```text
200 OK
```

alınır.

Docker logumuzda sonunda:

```text
POST /api/ask HTTP/1.1" 200 OK
```

çıktısını aldık.

Bu, RAG pipeline'ının uçtan uca çalıştığını gösterdi.

---

# 28. Karşılaştığımız Docker Build Problemi

İlk olarak Docker build sırasında:

```text
pip install --no-cache-dir -r requirements.txt
```

aşamasında hata aldık.

Daha ayrıntılı log görmek için:

```powershell
docker compose --progress=plain -f docker-compose.yml build --no-cache
```

komutunu kullandık.

Bu sayede gerçek pip hatasını gördük.

---

# 29. NumPy Uyumluluk Problemi

İlk requirements içerisinde:

```text
numpy==2.5.3
```

bulunuyordu.

Python 3.11 ortamında bu sürümle ilgili uyumluluk problemi oluştu.

Bu nedenle:

```text
numpy==2.2.6
```

kullanıldı.

---

# 30. SciPy Uyumluluk Problemi

Daha sonra:

```text
scipy==1.18.1
```

paketinde problem çıktı.

Build logunda bu sürümün Python 3.12 gerektirdiği görüldü.

Biz ise:

```dockerfile
FROM python:3.11-slim
```

kullanıyorduk.

Bu nedenle:

```text
scipy==1.17.1
```

kullanıldı.

Buradaki temel ders:

> Docker image içerisindeki Python sürümü ile requirements.txt içerisindeki paket sürümlerinin birbiriyle uyumlu olması gerekir.

---

# 31. İlk `/api/ask` Problemi

Docker ve FastAPI çalışmaya başladıktan sonra:

```text
POST /api/upload → 200 OK
```

aldık.

Ancak:

```text
POST /api/ask → 500 Internal Server Error
```

oldu.

Docker loglarında traceback görmek için endpoint içerisindeki exception'ı loglayacak şekilde:

```python
import traceback
traceback.print_exc()
```

ekledik.

Böylece gerçek hata ortaya çıktı.

---

# 32. Hugging Face Provider Hatası

İlk traceback:

```text
ValueError:
Cannot select auto-router when using non-Hugging Face API key.
```

şeklindeydi.

Bu noktada Hugging Face client'ının provider seçimi açık hale getirildi:

```python
client = InferenceClient(
    token=HF_TOKEN,
    provider="groq"
)
```

ve model:

```python
model="openai/gpt-oss-20b"
```

olarak kullanıldı.

Ancak daha sonra gelen hata çok daha açıklayıcıydı:

```text
httpx.LocalProtocolError:
Illegal header value b'Bearer '
```

Bu bize tokenın container içerisinde boş olduğunu gösterdi.

---

# 33. Son Problem: Token'ın Docker'a Geçmemesi

Kontrol:

```powershell
docker exec rag_app python -c "import os; print('HF token var mi:', bool(os.getenv('HF_API_TOKEN')))"
```

sonucu ilk problemden sonra:

```text
True
```

olacak şekilde düzeltildi.

Böylece Hugging Face tokenının container içinde mevcut olduğu doğrulandı.

---

# 34. Sonuç

Son testte:

```text
POST /api/upload HTTP/1.1" 200 OK
```

ve:

```text
POST /api/ask HTTP/1.1" 200 OK
```

çıktılarını aldık.

Bu, sistemin uçtan uca çalıştığını gösteriyor.

Son mimari:

```text
                    ┌──────────────────┐
                    │     Swagger      │
                    │ localhost:8000   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     FastAPI      │
                    │    rag_app       │
                    └───────┬──────────┘
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
       PDF Upload                      Ask Query
             │                             │
             ▼                             ▼
          Chunking                  Similarity Search
             │                             │
             ▼                             ▼
         Embedding                    pgvector
             │                             │
             └──────────────┐              │
                            ▼              ▼
                       PostgreSQL      Top-K Chunks
                                          │
                                          ▼
                                       Context
                                          │
                                          ▼
                                    Prompt Template
                                          │
                                          ▼
                               Hugging Face Client
                                          │
                                          ▼
                                    Groq Provider
                                          │
                                          ▼
                                   GPT-OSS-20B
                                          │
                                          ▼
                                  Answer + Sources
```

---

# 35. Çalıştırma Komutları

Docker klasörüne geç:

```powershell
cd C:\Users\Huawei\modules\Desktop\rag-doc-qa\docker
```

`.env` proje kökündeyse:

```powershell
docker compose --env-file ../.env -f docker-compose.yml up --build
```

Container'ları arka planda çalıştırmak istenirse:

```powershell
docker compose --env-file ../.env -f docker-compose.yml up -d --build
```

Container durumlarını kontrol etmek için:

```powershell
docker compose ps
```

Logları görmek için:

```powershell
docker logs rag_app
```

Son 100 log satırı:

```powershell
docker logs rag_app --tail 100
```

Container'ları durdurmak için:

```powershell
docker compose down
```

---

# 36. Test Adresleri

FastAPI Swagger:

```text
http://localhost:8000/docs
```

OpenAPI:

```text
http://localhost:8000/openapi.json
```

---

# 37. Projede Öğrenilenler

Bu entegrasyonla birlikte aşağıdaki konular pratik olarak uygulanmıştır:

* Docker image oluşturma
* Dockerfile hazırlama
* Docker Compose kullanımı
* Multi-container uygulama yapısı
* Container network iletişimi
* PostgreSQL container kullanımı
* PostgreSQL volume kullanımı
* PostgreSQL healthcheck
* pgvector ile vector storage
* Embedding tabanlı similarity search
* RAG retrieval pipeline
* Hugging Face InferenceClient
* Groq provider kullanımı
* LLM entegrasyonu
* Environment variable kullanımı
* `.env` ile secret yönetimi
* Docker'a environment variable aktarma
* FastAPI + Swagger ile API testi
* Docker logları ile hata ayıklama
* Python dependency/version uyumluluğu
* End-to-end RAG pipeline testi

---

# 38. Son Durum

Proje şu anda Docker ortamında çalışan bir RAG uygulamasıdır.

Çalışan temel akış:

```text
PDF Upload
    ↓
PDF Processing
    ↓
Chunking
    ↓
Embedding
    ↓
PostgreSQL + pgvector
    ↓
Similarity Search
    ↓
Top-K Retrieval
    ↓
Context
    ↓
Prompt
    ↓
Hugging Face
    ↓
Groq
    ↓
GPT-OSS-20B
    ↓
Answer + Sources
```

Son doğrulanan sonuç:

```text
POST /api/upload → 200 OK
POST /api/ask    → 200 OK
```

Bu nedenle RAG uygulamasının **Docker + PostgreSQL/pgvector + Hugging Face/Groq entegrasyonu ile uçtan uca çalıştığı doğrulanmıştır.**

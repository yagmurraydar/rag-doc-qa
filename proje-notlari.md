# 1. Projenin Amacı

Bu projenin amacı, kullanıcının yüklediği PDF dokümanları üzerinden soru sorabilmesini sağlayan bir **RAG (Retrieval-Augmented Generation)** sistemi geliştirmektir.

Temel çalışma mantığı:

```text
PDF
 ↓
PDF'i oku
 ↓
Chunking
 ↓
Embedding
 ↓
PostgreSQL + pgvector
 ↓
Kullanıcı soru sorar
 ↓
Sorunun embedding'i oluşturulur
 ↓
Similarity Search
 ↓
En alakalı doküman parçaları bulunur
 ↓
Context oluşturulur
 ↓
Prompt hazırlanır
 ↓
LLM
 ↓
Cevap
 ↓
FastAPI
 ↓
Swagger
```

Sistemin temel amacı, LLM'in yalnızca kendi bilgisini kullanması yerine **yüklenen dokümandaki bilgileri kullanarak cevap üretmesini sağlamaktır.**

---

# 2. RAG Nedir?

RAG:

**Retrieval-Augmented Generation**

anlamına gelir.

Türkçeye kabaca:

> Bilgi getirerek desteklenmiş cevap üretme

şeklinde açıklanabilir.

Normal bir LLM'e:

```text
Alice mesajı nasıl imzalıyor?
```

sorusunu sorarsak model kendi eğitiminden bildiği bilgilerle cevap verebilir.

Ancak bizim sistemimizde modelin öncelikle yüklenen PDF içerisinden ilgili bilgiyi bulmasını istiyoruz.

Bu nedenle sistem:

```text
Soru
 ↓
Dokümanda ilgili bilgiyi ara
 ↓
Bulunan bilgiyi LLM'e gönder
 ↓
LLM bu bilgiye dayanarak cevap üretir
```

şeklinde çalışır.

Bu yapı sayesinde sistemin dokümanda olmayan bilgileri uydurma ihtimali azaltılır.

---

# 3. PDF Neden Chunk'lara Bölünüyor?

PDF dosyasını tek parça halinde kullanmak yerine küçük metin parçalarına bölüyoruz.

Bu işleme:

**Chunking**

denir.

Örneğin:

```text
PDF
 ├── Chunk 1
 ├── Chunk 2
 ├── Chunk 3
 ├── Chunk 4
 └── ...
```

şeklinde bir yapı oluşur.

Örneğin bir chunk içerisinde:

```text
Alice, mesajı kendi Private Key'i (KRa) ile şifreler
(yani imzalar).

Y = EKRa(X)
```

bulunabilir.

Bizim test PDF'imizden bir yüklemede:

```text
98 chunk
```

oluşturuldu.

Terminalde görülen:

```text
98 chunk pgvector'a yazıldı.
```

mesajı bunu ifade eder.

---

# 4. Chunking Neden Gerekli?

Chunking sayesinde sistem bütün PDF'i aramak yerine daha küçük ve anlamlı metin parçaları üzerinde arama yapabilir.

Örneğin kullanıcı:

```text
Alice mesajı nasıl imzalıyor?
```

diye sorduğunda sistem bütün PDF'i LLM'e göndermek yerine ilgili chunk'ları bulabilir.

Bu:

* daha verimli arama,
* daha az gereksiz context,
* daha düşük token kullanımı,
* daha doğru cevap

sağlamaya yardımcı olur.

---

# 5. Embedding Nedir?

Embedding, bir metnin sayısal bir vektör ile temsil edilmesidir.

Örneğin:

```text
Alice mesajı private key ile imzalar.
```

metni model tarafından yaklaşık olarak:

```text
[0.21, -0.53, 0.78, 0.12, ...]
```

gibi bir vektöre dönüştürülebilir.

Bu sayısal gösterim metnin anlamını temsil etmek için kullanılır.

---

# 6. Embedding Neden Kullanılıyor?

Kullanıcı sorusu ile PDF'deki metinlerin kelimeleri birebir aynı olmayabilir.

Örneğin kullanıcı:

```text
Alice mesajını nasıl imzalıyor?
```

diyebilir.

PDF'de ise:

```text
Alice, mesajı kendi Private Key'i ile şifreler
(yani imzalar).
```

yazabilir.

Kelimeler tamamen aynı değildir fakat anlamları benzerdir.

Embedding sayesinde sistem bu iki metnin anlamsal olarak birbirine yakın olduğunu tespit edebilir.

---

# 7. PostgreSQL Neden Kullanıldı?

Oluşturulan chunk'ları ve embedding'leri saklamak için:

**PostgreSQL**

kullanıldı.

Veritabanında temel olarak şu tür bilgiler tutuluyor:

```text
content
embedding
source_file
page
chunk_id
```

Örneğin:

```text
content:
Alice mesajı private key ile imzalar.

embedding:
[0.12, -0.33, 0.82, ...]

source_file:
test.pdf

page:
1
```

---

# 8. pgvector Nedir?

PostgreSQL normal bir ilişkisel veritabanıdır.

Ancak bizim embedding'lerimiz vektörlerden oluştuğu için vektörlerle çalışabilmemiz gerekiyor.

Bu amaçla:

**pgvector**

kullanıldı.

pgvector, PostgreSQL içerisinde vektörleri saklamaya ve vektör benzerliği üzerinden arama yapmaya yardımcı olur.

Dolayısıyla sistemimiz:

```text
PostgreSQL
     +
  pgvector
     ↓
Normal veriler
     +
Embedding vektörleri
```

şeklinde çalışmaktadır.

---

# 9. Similarity Search Nedir?

Kullanıcı soru sorduğunda sorunun da embedding'i oluşturulur.

Daha sonra bu embedding, veritabanındaki chunk embedding'leri ile karşılaştırılır.

Amaç:

> Kullanıcının sorusuna anlamsal olarak en yakın chunk'ları bulmaktır.

Projede:

```python
similarity_search(question, top_k=5)
```

fonksiyonu kullanılmaktadır.

Buradaki:

```text
top_k=5
```

en alakalı 5 chunk'ın alınmasını ifade eder.

---

# 10. Distance Nedir?

Similarity Search sırasında iki vektör arasındaki benzerlik/mesafe hesaplanır.

Projede cosine distance kullanılmaktadır.

Basitleştirilmiş olarak:

```text
Distance küçük
      ↓
Daha benzer

Distance büyük
      ↓
Daha az benzer
```

Örneğin terminalde:

```text
distance: 0.38363182994411604
```

gibi değerler görüldü.

Bu değer, soru ile bulunan chunk arasındaki anlamsal mesafeyi ifade eder.

---

# 11. 588 Chunk Neden Oluştu?

Projenin geliştirilmesi sırasında aynı PDF birkaç kez upload edildi.

Bir PDF yaklaşık:

```text
98 chunk
```

oluşturuyordu.

Aynı PDF yaklaşık 6 kez yüklendiğinde:

```text
98 × 6 = 588
```

chunk oluştu.

Bu nedenle veritabanında:

```text
588 chunk
```

görüldü.

Daha sonra yapılan yeni bir upload işleminde:

```text
98 chunk pgvector'a yazıldı.
```

mesajı görüldü.

Bu durum RAG sisteminin çalışmadığı anlamına gelmez.

Ancak veritabanında duplicate kayıtlar oluştuğu için ilerleyen aşamada:

1. Eski duplicate kayıtlar temizlenecek.
2. Aynı PDF'in tekrar tekrar eklenmesi engellenecek.

---

# 12. Context Nedir?

Similarity Search sonucunda bulunan chunk'ları LLM'e göndermeden önce bir araya getiriyoruz.

Bu birleşmiş metne:

**Context**

denir.

Örneğin:

```text
[Kaynak: test.pdf, Sayfa: 1]

Alice, mesajı kendi Private Key'i (KRa) ile şifreler
(yani imzalar).

Y = EKRa(X)
```

şeklinde bir context oluşturulur.

Projede bunu:

```python
build_context(chunks)
```

fonksiyonu yapmaktadır.

---

# 13. Prompt Nedir?

Context oluşturulduktan sonra LLM'e gönderilecek prompt hazırlanır.

Projede kullanılan temel prompt mantığı:

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

Buradaki amaç LLM'e iki temel kural vermektir:

1. Cevabı dokümandaki context'e göre oluştur.
2. Bilgi context'te yoksa bilgi uydurma.

---

# 14. Neden "Bu bilgi dokümanda bulunmuyor." Kuralını Ekledik?

RAG sistemlerinde önemli problemlerden biri:

**Hallucination**

yani modelin dokümanda olmayan bilgileri uydurmasıdır.

Örneğin kullanıcı:

```text
Private key nedir?
```

diye sorduğunda ve PDF içerisinde private key'in açık bir tanımı yoksa sistem:

```text
Bu bilgi dokümanda bulunmuyor.
```

demelidir.

Ancak:

```text
Alice mesajı nasıl imzalıyor?
```

sorusunun cevabı PDF içerisinde varsa sistem cevap vermelidir.

Bu nedenle prompt'a bu kural eklendi.

---

# 15. LLM Nerede Kullanılıyor?

Context ve prompt hazırlandıktan sonra bunlar bir LLM'e gönderilir.

Projede:

```text
openai/gpt-oss-20b:groq
```

modeli kullanılmaktadır.

Hugging Face:

```python
InferenceClient
```

üzerinden model çağrısı yapılmaktadır.

LLM'in görevi:

> Retrieval sonucunda bulunan doküman parçalarını kullanarak kullanıcıya doğal dilde cevap üretmektir.

---

# 16. RAG ile LLM Arasındaki Fark

Burada önemli bir ayrım vardır.

Sadece LLM kullansaydık:

```text
Soru
 ↓
LLM
 ↓
Cevap
```

olurdu.

Bizim sistemimizde:

```text
Soru
 ↓
Retrieval
 ↓
İlgili doküman parçalarını bul
 ↓
Context
 ↓
LLM
 ↓
Cevap
```

vardır.

Dolayısıyla LLM tek başına sistemin tamamı değildir.

RAG sistemi:

**Retrieval + Context + LLM**

mantığıyla çalışmaktadır.

---

# 17. FastAPI Neden Kullanıldı?

Sistemi bir API haline getirmek için:

**FastAPI**

kullanıldı.

Örneğin:

```text
POST /api/ask
```

endpoint'i kullanıcıdan soru alır.

Kullanıcı:

```json
{
    "question": "Alice mesajı nasıl imzalıyor?",
    "top_k": 5
}
```

gönderdiğinde FastAPI bu isteği RAG pipeline'ına iletir.

Akış:

```text
POST /api/ask
       ↓
FastAPI
       ↓
answer_question()
       ↓
similarity_search()
       ↓
Context
       ↓
Prompt
       ↓
LLM
       ↓
Cevap
       ↓
FastAPI Response
```

---

# 18. Swagger Nedir?

Swagger, FastAPI tarafından oluşturulan API'yi tarayıcı üzerinden test etmeyi sağlayan bir arayüzdür.

Projede:

```text
http://127.0.0.1:8000/docs
```

adresinden açılmaktadır.

Swagger'ın kendisi RAG yapmaz.

Swagger sadece API endpoint'lerini kolayca kullanmamızı ve test etmemizi sağlar.

---

# 19. Neden Swagger Kullanıyoruz?

API'yi test etmek için Postman, curl veya frontend kullanılabilir.

Ancak projenin geliştirme aşamasında henüz frontend olmadığı için Swagger çok kullanışlıdır.

Örneğin:

```text
POST /api/ask
```

endpoint'ine Swagger üzerinden:

```json
{
    "question": "Alice mesajı nasıl imzalıyor?",
    "top_k": 5
}
```

gönderilebilir.

Böylece frontend geliştirmeden API'nin çalışıp çalışmadığı test edilir.

Akış:

```text
Swagger
   ↓
POST /api/ask
   ↓
FastAPI
   ↓
RAG Pipeline
   ↓
LLM
   ↓
FastAPI
   ↓
Swagger
   ↓
Cevap
```

---

# 20. Swagger'daki `200 OK` Ne Anlama Geliyor?

Terminalde:

```text
POST /api/ask HTTP/1.1" 200 OK
```

görülmesi, API isteğinin başarılı şekilde işlendiğini gösterir.

Örneğin:

```text
POST /api/upload → 200 OK
```

PDF yükleme işleminin başarılı olduğunu gösterir.

```text
POST /api/ask → 200 OK
```

soru-cevap isteğinin başarıyla işlendiğini gösterir.

---

# 21. Terminaldeki Hugging Face Uyarısı

Terminalde şu uyarı görüldü:

```text
Warning: You are sending unauthenticated requests
to the HF Hub.
Please set a HF_TOKEN...
```

Bu şu an için bir hata değildir.

Model başarıyla çalıştığı için sistemin çalışmasını engellememektedir.

Uyarının anlamı:

> Hugging Face'e kimlik doğrulaması yapılmadan istek gönderiliyor ve bu durumda rate limit gibi bazı kısıtlamalar olabilir.

Daha sonra istenirse Hugging Face token yapılandırması ayrıca düzenlenebilir.

---

# 22. Debug Print'leri Neden Ekledik?

Geliştirme sırasında sistemin içerisinde ne olduğunu görebilmek için geçici `print()` ifadeleri kullandık.

Örneğin:

```text
SORU:
TOP_K:
BULUNAN TOPLAM CHUNK:
RESULT 1
RESULT 2
...
```

ve:

```text
========== PROMPT ==========
...
========== LLM RESPONSE ==========
...
```

gibi çıktılar aldık.

Bunların amacı:

> RAG'in gerçekten doğru chunk'ı bulup bulmadığını ve LLM'e doğru context'in gönderilip gönderilmediğini kontrol etmekti.

Debug işlemleri tamamlandıktan sonra bu çıktılar kaldırıldı.

Bu nedenle terminal artık daha temiz görünmektedir.

---





#  Dosyaların Görevleri

## `chunking.py`

PDF içerisindeki metni küçük parçalara böler.

```text
PDF
 ↓
Chunks
```

---

## `embeddings.py`

Metinleri embedding vektörlerine dönüştürür.

```text
Metin
 ↓
Embedding Vector
```

---

## `vectorstore.py`

İki temel görevi vardır:

1. Chunk'ları embeddingleriyle birlikte PostgreSQL'e kaydetmek.
2. Kullanıcı sorusuna en yakın chunk'ları bulmak.

```text
Chunk
 ↓
Embedding
 ↓
PostgreSQL + pgvector
```

ve:

```text
Question
 ↓
Similarity Search
 ↓
Relevant Chunks
```

---

## `rag_chain.py`

RAG pipeline'ının ana mantığını yönetir.

Temel akış:

```text
Question
 ↓
similarity_search()
 ↓
build_context()
 ↓
Prompt
 ↓
LLM
 ↓
Answer
```

---

## `routes_ask.py`

FastAPI endpoint'lerini yönetir.

Örneğin:

```text
POST /api/ask
```

isteğini alır ve `answer_question()` fonksiyonunu çağırır.

---

## `main.py`

FastAPI uygulamasının ana giriş noktasıdır.

Uygulama:

```bash
uvicorn app.main:app --reload
```

komutuyla çalıştırılır.

---

#  Projenin Uçtan Uca Çalışma Mantığı

## Aşama 1 – PDF yükleme

```text
PDF
 ↓
PDF okunur
```

## Aşama 2 – Chunking

```text
PDF
 ↓
98 chunk
```

## Aşama 3 – Embedding

```text
98 chunk
 ↓
Embedding vectors
```

## Aşama 4 – Veritabanına kaydetme

```text
Chunks + Embeddings
 ↓
PostgreSQL + pgvector
```

## Aşama 5 – Kullanıcı soru sorar

```text
Alice mesajı nasıl imzalıyor?
```

## Aşama 6 – Soru embedding'i

```text
Question
 ↓
Embedding
```

## Aşama 7 – Similarity Search

```text
Question embedding
 ↓
PostgreSQL + pgvector
 ↓
Top-K relevant chunks
```

## Aşama 8 – Context

```text
Relevant chunks
 ↓
Context
```

## Aşama 9 – Prompt

```text
Context + Question
 ↓
Prompt
```

## Aşama 10 – LLM

```text
Prompt
 ↓
GPT-OSS
 ↓
Answer
```

## Aşama 11 – API

```text
Answer
 ↓
FastAPI
```

## Aşama 12 – Swagger

```text
FastAPI Response
 ↓
Swagger UI
 ↓
Kullanıcı cevabı görür
```




# Akılda Tutulması Gereken En Önemli Şema

```text
                  📄 PDF
                    │
                    ▼
               CHUNKING
                    │
                    ▼
                EMBEDDING
                    │
                    ▼
          PostgreSQL + pgvector
                    │
                    │
                    │
             👤 Kullanıcı
                    │
                    ▼
                  SORU
                    │
                    ▼
               EMBEDDING
                    │
                    ▼
           SIMILARITY SEARCH
                    │
                    ▼
             İLGİLİ CHUNKS
                    │
                    ▼
                 CONTEXT
                    │
                    ▼
                 PROMPT
                    │
                    ▼
                  🤖 LLM
                    │
                    ▼
                 CEVAP
                    │
                    ▼
                FASTAPI
                    │
                    ▼
                SWAGGER
```



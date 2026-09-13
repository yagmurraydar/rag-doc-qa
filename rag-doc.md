RAG Document QA Projesi --- Yapılanlar ve Teknik Süreç

 Projenin Amacı

Bu projede PDF dokümanlarının içeriğini kullanarak kullanıcı sorularına
dokümandaki bilgilere dayalı cevap veren bir RAG (Retrieval-Augmented
Generation) sistemi geliştirildi.

Temel amaç:

Kullanıcının sorusunu önce doküman içindeki ilgili parçalarda aramak,
ardından bulunan bilgileri bir LLM'e context olarak vererek cevap
üretmek.

Genel akış:

PDF
 ↓
PDF'den metin çıkarma
 ↓
Chunking
 ↓
Embedding
 ↓
PostgreSQL + pgvector
 ↓
Semantic Search / Retrieval
 ↓
Relevant Context
 ↓
LLM
 ↓
Cevap + Kaynaklar

 Kullanılan Teknolojiler

Projede temel olarak şu teknolojiler kullanıldı:

Python → Projenin ana programlama dili

LangChain → Doküman/chunk yapılarında kullanılan framework

Sentence Transformers → Metinleri embedding vektörlerine
dönüştürmek için

all-MiniLM-L6-v2 → Kullanılan embedding modeli

PostgreSQL → Verilerin ve document chunk'larının tutulması

pgvector → Embedding vektörlerini PostgreSQL içerisinde saklamak
ve benzerlik hesabı yapmak için

psycopg2 → Python ile PostgreSQL bağlantısı

Hugging Face Inference Providers → LLM erişimi

Groq → Hugging Face üzerinden LLM inference provider olarak
kullanıldı

python-dotenv → API token gibi bilgileri .env üzerinden almak
için

 PDF ve Dokümanların Chunk'lara Ayrılması

RAG sistemlerinde bütün PDF'i tek parça halinde LLM'e göndermek yerine
dokümanı daha küçük parçalara ayırmak gerekir.

Bu parçalara chunk denir.

Örneğin:

PDF
 ↓
Chunk 1
Chunk 2
Chunk 3
Chunk 4
...

Chunk'lara ayırmamızın nedeni:

Arama yapılacak metni küçültmek

Kullanıcının sorusuyla ilgili bölümü daha kolay bulmak

LLM'e gereksiz tüm dokümanı göndermemek

Daha alakalı context oluşturmak

Projede oluşturulan chunk'larda içerikle birlikte kaynak bilgileri de
tutuldu:

source_file

page

chunk_id

Böylece cevap üretildiğinde hangi PDF ve sayfadan bilgi alındığı
gösterilebiliyor.

 Embedding Nedir ve Neden Kullanıldı?

RAG sisteminin önemli kısmı semantic search işlemidir.

Kullanıcının:

private key nedir

sorusunu sadece kelime eşleşmesiyle aramak yerine anlamını temsil eden
sayısal bir vektöre dönüştürüyoruz.

Bu işlem embedding modeli ile yapılıyor.

Kullanılan model:

sentence-transformers/all-MiniLM-L6-v2

Bu model her metni 384 boyutlu bir vektöre dönüştürüyor.

Örneğin:

"private key nedir"
        ↓
[0.05, -0.02, 0.11, ...]
        ↓
384 boyutlu embedding

Aynı işlem PDF içindeki chunk'lara da uygulanıyor.

Böylece:

Kullanıcı sorusu → embedding
PDF chunk'ları    → embedding

haline geliyor.

Ardından soru embedding'i ile chunk embedding'leri arasındaki benzerlik
hesaplanıyor.

 PostgreSQL ve pgvector

Embedding'leri saklamak için PostgreSQL kullanıldı.

PostgreSQL içerisinde:

document_chunks

isimli tablo kullanıldı.

Tabloda temel olarak şu bilgiler bulunuyor:

id
content
embedding
source_file
page
chunk_id

embedding alanı PostgreSQL'in vector tipi olarak tutuluyor.

Bunun için:

pgvector

extension/library kullanıldı.

Projede toplam:

392 chunk
392 embedding
384 boyutlu embedding

bulunuyor.

Kontroller sırasında:

392 kayıt
392 embedding
384 dimensions

olduğu doğrulandı.

 PostgreSQL Bağlantısı

Python tarafından PostgreSQL'e bağlanmak için:

psycopg2

kullanıldı.

Bağlantı sırasında pgvector desteğini aktif etmek için:

register_vector(conn)

kullanıldı.

Embedding'lerin PostgreSQL tarafından vector olarak algılanması için
Python tarafında:

from pgvector import Vector

kullanıldı.

Embedding kaydedilirken:

Vector(embedding)

şeklinde PostgreSQL vector tipine dönüştürüldü.

 Retrieval / Similarity Search

Kullanıcı bir soru sorduğunda sistem önce sorunun embedding'ini
oluşturuyor.

Örneğin:

private key nedir

↓

query embedding

Ardından bu embedding ile veritabanındaki chunk embedding'leri
arasındaki cosine distance hesaplanıyor.

pgvector'da kullanılan operatör:

<=> 

Bu cosine distance hesaplamak için kullanıldı.

Mantık:

Küçük distance
      ↓
Daha benzer içerik

Örneğin sistem:

private key nedir

sorusunda PDF içerisindeki Private Key açıklamasının bulunduğu
chunk'ları üst sıralara taşıdı.

 Retrieval Probleminin Çözülmesi

Geliştirme sırasında önemli bir problem yaşandı.

İlk olarak PostgreSQL tarafında:

ORDER BY embedding <=> query_embedding

şeklinde doğrudan sıralama yapılarak top-k sonuçlarının alınması
denendi.

Ancak veritabanında chunk'lar olmasına ve distance hesaplanabilmesine
rağmen sorgu Python tarafında beklenen sonuçları döndürmedi.

Sorunu izole etmek için çeşitli kontroller yapıldı:

Chunk sayısı kontrol edildi → 392

Embedding sayısı kontrol edildi → 392

Embedding boyutu kontrol edildi → 384

Query embedding kontrol edildi → başarılı

embedding <=> embedding kontrol edildi → başarılı

Query embedding ile distance hesaplama kontrol edildi → başarılı

Sonuç olarak retrieval işlemi daha basit ve güvenilir bir yöntemle
düzenlendi.

Önce bütün chunk'ların distance değerleri PostgreSQL'den alındı:

SELECT
    content,
    source_file,
    page,
    chunk_id,
    embedding <=> %s AS distance
FROM document_chunks

Daha sonra Python tarafında:

results.sort(key=lambda x: x["distance"])

ile sıralama yapıldı ve:

results[:top_k]

ile en alakalı chunk'lar seçildi.

Mevcut veri setimiz yalnızca 392 chunk olduğu için bu yaklaşım proje ve
öğrenme amacı açısından yeterlidir.

Context Oluşturma

Retrieval sonucunda bulunan chunk'lar LLM'e doğrudan ayrı ayrı
gönderilmek yerine tek bir context içerisinde birleştiriliyor.

Örneğin:

[Kaynak: test.pdf, Sayfa: 2]
Private Key (Özel/Gizli Anahtar): Sadece sahibinde kalır...

[Kaynak: test.pdf, Sayfa: 2]
Public Key...

...

Bu işlem build_context() fonksiyonu tarafından gerçekleştiriliyor.

Amaç:

Retrieved Chunks
       ↓
Tek bir Context
       ↓
LLM

akışını oluşturmak.

Prompt Yapısı

LLM'e gönderilen prompt'ta iki temel bilgi bulunuyor:

Retrieved context

Kullanıcının sorusu

Prompt ayrıca LLM'e önemli bir kural veriyor:

Eğer cevap bağlamda yoksa:
"Bu bilgi dokümanda bulunmuyor."
de.

Bunun amacı LLM'in dokümanda bulunmayan bilgileri uydurmasını azaltmak.

 LLM ve Hugging Face

İlk aşamada farklı Hugging Face modelleriyle inference yapılması
denendi.

İlk kullanılan model:

mistralai/Mistral-7B-Instruct-v0.2

Ancak seçilen inference provider bu modeli text-generation göreviyle
desteklemedi.

Daha sonra:

HuggingFaceH4/zephyr-7b-beta

denendi.

Bu model de hesabın etkin provider'larından herhangi biri tarafından
desteklenmedi.

Bunun üzerine Hugging Face Inference Providers yapısı kullanılarak
Groq provider'ına geçildi.

Kullanılan model:

openai/gpt-oss-20b:groq

Böylece LLM çağrısı başarılı şekilde gerçekleştirildi.

 RAG Pipeline'ın Son Hali

Sistemin son akışı:

Kullanıcı Sorusu
      ↓
Query Embedding
      ↓
PostgreSQL + pgvector
      ↓
Cosine Distance
      ↓
En alakalı 5 Chunk
      ↓
Context oluşturma
      ↓
Prompt
      ↓
Groq üzerinden LLM
      ↓
Cevap
      ↓
Kaynaklar

 Başarılı Test

Son testte şu soru soruldu:

private key nedir

Sistem doğru şekilde cevap üretti:

Private key, yalnızca sahibinin bildiği gizli bir anahtardır.

Ayrıca cevapla birlikte kaynaklar da döndürüldü:

- test.pdf (sayfa 2)
- test.pdf (sayfa 2)
- test.pdf (sayfa 2)
- test.pdf (sayfa 2)
- test.pdf (sayfa 5)

Bu test ile RAG pipeline'ının temel olarak çalıştığı doğrulandı.
# RAG-Doc-QA — AWS EC2 + Docker Deployment

Bu dokümanda **RAG-Doc-QA projesinin AWS EC2 üzerinde Docker ve Docker Compose kullanılarak nasıl deploy edildiği** adım adım anlatılmaktadır.

Amaç sadece komutları uygulamak değil; **hangi işlemi neden yaptığımızı ve sistemin sonunda nasıl çalıştığını anlamaktır.**

---

# 1. Projenin Genel Yapısı

RAG-Doc-QA projemiz, kullanıcının dokümanlardan soru sormasını sağlayan bir **RAG (Retrieval-Augmented Generation)** uygulamasıdır.

Temel teknolojiler:

* FastAPI
* Python
* LangChain
* Sentence Transformers
* Hugging Face
* PostgreSQL
* pgvector
* Docker
* Docker Compose
* AWS EC2

Projenin temel çalışma mantığı:

```text
Kullanıcı
   │
   │ HTTP Request
   ▼
FastAPI
   │
   ├── Doküman işleme
   ├── Chunking
   ├── Embedding
   ├── Vector Search
   └── LLM / RAG işlemleri
            │
            ▼
      PostgreSQL + pgvector
```

AWS üzerinde ise bu yapı Docker container'ları içerisinde çalıştırıldı.

```text
                    INTERNET
                        │
                        │
                Public IP :8000
                        │
                        ▼
                AWS EC2 Server
                        │
                  Docker Compose
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
         rag_app            rag_postgres
         FastAPI             PostgreSQL
         :8000                  :5432
              │
              │
              ▼
       Hugging Face Model
       Sentence Transformers
```

---

# 2. Neden AWS EC2 Kullandık?

Projeyi kendi bilgisayarımızda çalıştırmak ile AWS üzerinde çalıştırmak farklı şeylerdir.

Local bilgisayarımızda:

```text
Windows
   │
   └── Docker
        │
        ├── FastAPI
        └── PostgreSQL
```

şeklinde çalışabilir.

Fakat bir projeyi başka insanların internet üzerinden erişebileceği bir sunucuda çalıştırmak istiyorsak bir **server** gerekir.

Burada AWS EC2 kullandık.

EC2'yi basitçe:

> İnternete bağlı, uzaktan erişebildiğimiz bir Linux bilgisayar

gibi düşünebiliriz.

Bizim EC2 sunucumuz:

```text
Instance Name:
rag-doc-qa-server
```

olarak oluşturuldu.

Kullanılan işletim sistemi:

```text
Ubuntu Server 24.04 LTS
```

Instance tipi:

```text
t3.micro
```

AWS Region:

```text
eu-north-1
```

---

# 3. EC2 Nedir?

EC2:

**Elastic Compute Cloud**

anlamına gelir.

AWS'nin sanal sunucu hizmetidir.

Biz burada fiziksel bir bilgisayar satın almak yerine AWS'den sanal bir Linux makinesi kullandık.

Bu makinede:

* Git
* Docker
* Docker Compose
* PostgreSQL
* FastAPI

çalıştırıldı.

---

# 4. SSH ile EC2'ye Bağlanmak

EC2 oluşturulurken bir key pair oluşturduk.

Key dosyamız:

```text
rag-doc-qa-key.pem
```

Windows bilgisayarımızdaki konumu:

```text
C:\Users\Huawei\modules\Downloads\rag-doc-qa-key.pem
```

EC2'nin SSH bağlantı komutu:

```bash
ssh -i "rag-doc-qa-key.pem" ubuntu@ec2-51-21-221-224.eu-north-1.compute.amazonaws.com
```

Buradaki:

```text
ubuntu
```

Ubuntu işletim sistemindeki kullanıcıdır.

`.pem` dosyası ise EC2'ye güvenli şekilde bağlanmamızı sağlayan private key'dir.

Bağlantı başarılı olduğunda:

```text
ubuntu@ip-172-31-20-158:~$
```

şeklinde bir terminal gördük.

Bu noktadan sonra artık AWS sunucusunun içerisindeydik.

---

# 5. EC2'nin Public ve Private IP Adresleri

Burada önemli bir kavram öğrendik.

EC2 içerisinde gördüğümüz:

```text
172.31.20.158
```

adresi **private IP** adresidir.

Bu adres AWS'nin kendi network'ü içerisinde kullanılır.

Bizim dışarıdan erişim için kullandığımız adres ise:

```text
51.21.221.224
```

Public IP adresidir.

Dolayısıyla Swagger'a bilgisayarımızdan:

```text
http://51.21.221.224:8000/docs
```

adresinden eriştik.

---

# 6. Security Group

EC2'nin internete açık olması tek başına yeterli değildir.

AWS'de **Security Group**, sunucuya hangi bağlantıların girebileceğini kontrol eden bir firewall gibi düşünülebilir.

Biz özellikle iki port kullandık:

```text
22
8000
```

## Port 22

SSH bağlantısı için kullanılır.

```text
Bilgisayar
    │
    │ SSH
    ▼
EC2 :22
```

Bu sayede terminal üzerinden EC2'ye bağlandık.

## Port 8000

FastAPI uygulamamızın çalıştığı porttur.

```text
Internet
    │
    ▼
EC2 :8000
    │
    ▼
FastAPI
```

Bu port sayesinde tarayıcıdan Swagger'a erişebildik.

---

# 7. EC2 Üzerine Git Kurulması

Öncelikle Git'in kurulu olduğundan emin olduk.

GitHub'daki projemizi EC2'ye almak için:

```bash
git clone https://github.com/yagmurraydar/rag-doc-qa.git
```

Sonrasında:

```bash
cd rag-doc-qa
```

ile proje klasörüne girdik.

Artık EC2 içerisindeki proje yapımız:

```text
~/rag-doc-qa
```

şeklindeydi.

---

# 8. Docker Kurulumu

Projemizin container içerisinde çalışmasını istediğimiz için EC2'ye Docker kurduk.

Docker'ın amacı:

> Uygulamanın çalışması için gereken ortamı paketleyerek farklı makinelerde aynı şekilde çalıştırabilmek.

Örneğin projemizde:

```text
Python
FastAPI
LangChain
Sentence Transformers
PyTorch
PostgreSQL bağlantısı
```

gibi birçok bağımlılık bulunuyor.

Bunların hepsini EC2'ye tek tek kurmak yerine Docker image oluşturduk.

Docker kurulumu:

```bash
sudo apt update
sudo apt install docker.io -y
```

Docker servisinin çalıştığını kontrol ettik:

```bash
sudo systemctl status docker
```

Ayrıca Docker'ın düzgün çalıştığını test etmek için:

```bash
docker run hello-world
```

komutunu kullandık.

---

# 9. Docker Compose

Projede iki temel container bulunuyor:

```text
1. FastAPI application
2. PostgreSQL + pgvector
```

Bu iki container'ı tek tek çalıştırmak yerine Docker Compose kullandık.

Docker Compose sayesinde:

```text
FastAPI
   +
PostgreSQL
```

aynı yapı içerisinde yönetilebiliyor.

Compose plugin kurulduktan sonra:

```bash
docker compose version
```

ile kontrol ettik.

Sonuç:

```text
Docker Compose version v5.5.1
```

---

# 10. Docker Compose Dosyamız

Dosyamız:

```text
docker/docker-compose.yml
```

İçerisinde iki service tanımladık.

```yaml
services:

  postgres:
    image: ankane/pgvector:latest

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
```

Bunun anlamı:

```text
postgres
   │
   └── PostgreSQL + pgvector

app
   │
   └── Kendi Dockerfile'ımızdan build edilen FastAPI uygulaması
```

---

# 11. PostgreSQL + pgvector

RAG sistemlerinde yalnızca normal SQL veritabanı kullanmak yeterli değildir.

Dokümanlardan oluşturduğumuz embedding'leri saklamak ve benzerlik araması yapmak için **vector database özelliğine** ihtiyacımız vardır.

Bu projede PostgreSQL'in pgvector extension'ını kullandık.

Docker image:

```text
ankane/pgvector:latest
```

şeklindedir.

Database bilgileri:

```text
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ragdb
```

Container adı:

```text
rag_postgres
```

Port:

```text
5432
```

---

# 12. PostgreSQL Healthcheck

Compose dosyasında PostgreSQL için healthcheck tanımladık:

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 5s
  timeout: 5s
  retries: 5
```

Bunun amacı:

> PostgreSQL container'ı çalışıyor görünse bile gerçekten bağlantı kabul ediyor mu?

bunu kontrol etmektir.

FastAPI'nin PostgreSQL hazır olmadan başlamasını istemiyoruz.

Bu nedenle:

```yaml
depends_on:
  postgres:
    condition: service_healthy
```

kullandık.

Sonuç olarak:

```text
PostgreSQL başla
       │
       ▼
Healthcheck
       │
       ▼
Healthy
       │
       ▼
FastAPI başla
```

şeklinde bir akış oluştu.

---

# 13. Docker Volume

PostgreSQL verilerinin container silindiğinde kaybolmasını istemiyoruz.

Bu nedenle:

```yaml
volumes:
  - pgdata:/var/lib/postgresql/data
```

kullandık.

Ayrıca:

```yaml
volumes:
  pgdata:
```

ile Docker named volume oluşturduk.

Docker tarafında oluşan volume:

```text
docker_pgdata
```

olarak göründü.

Böylece PostgreSQL verileri container'ın yaşam döngüsünden ayrılmış oldu.

---

# 14. `.env` Dosyası

Projede Hugging Face API token kullandığımız için token'ı doğrudan `docker-compose.yml` içine yazmadık.

Proje kökünde:

```text
.env
```

dosyası oluşturduk.

Örneğin:

```env
HF_API_TOKEN=YOUR_SECRET_TOKEN
```

Gerçek token burada bulunur.

Bu dosyanın GitHub'a gönderilmemesi gerekir.

Bu nedenle `.gitignore` içerisinde `.env` bulunmalıdır.

Kontrol:

```bash
git status
```

yaptığımızda `.env`'in commit'e eklenmediğini doğruladık.

---

# 15. Neden `--env-file .env` Kullandık?

Burada önemli bir problem yaşadık.

Compose dosyamız:

```text
docker/docker-compose.yml
```

içerisinde.

Fakat `.env` dosyamız:

```text
rag-doc-qa/.env
```

konumunda.

Bu yüzden doğrudan:

```bash
docker compose -f docker/docker-compose.yml up
```

çalıştırıldığında Compose `.env` değişkenini beklediğimiz şekilde bulamadı.

Doğru komut:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

şeklinde oldu.

Burada:

```text
--env-file .env
```

→ hangi environment dosyasının kullanılacağını belirtir.

```text
-f docker/docker-compose.yml
```

→ hangi Compose dosyasının kullanılacağını belirtir.

```text
up
```

→ container'ları başlatır.

```text
--build
```

→ Docker image'ını yeniden oluşturur.

```text
-d
```

→ container'ları arka planda çalıştırır.

---

# 16. Dockerfile

FastAPI uygulamamızın image'ını oluşturmak için:

```text
docker/Dockerfile
```

kullandık.

Temel yapı:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
```

Burada Python 3.11 tabanlı hafif bir Linux image kullandık.

---

# 17. Sistem Bağımlılıkları

Dockerfile içerisinde:

```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

kullandık.

Bunların amacı özellikle PostgreSQL/Python bağlantısı için gerekli sistem bağımlılıklarını sağlamaktır.

---

# 18. PyTorch Problemi

Deployment sırasında önemli bir problem yaşadık.

Projemizde:

```python
from sentence_transformers import SentenceTransformer
```

kullanılıyor.

Modelimiz:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Bu kütüphane PyTorch kullanıyor.

İlk Docker build sırasında PyTorch'un GPU/CUDA ile ilişkili çok büyük paketleri indirilmeye başlandı.

Örneğin NVIDIA paketleri yüzlerce MB boyutundaydı.

EC2'nin disk alanı ise başlangıçta yalnızca yaklaşık:

```text
6.8 GB
```

idi.

Bu nedenle build sırasında:

```text
no space left on device
```

hatası aldık.

---

# 19. CPU-only PyTorch

EC2 üzerinde GPU kullanmadığımız için CUDA paketlerine ihtiyacımız yok.

Bu nedenle Dockerfile'a CPU-only PyTorch kurulumu ekledik:

```dockerfile
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu
```

Böylece GPU/CUDA paketlerini indirmek yerine CPU sürümü kullanıldı.

Bu EC2 için daha uygun bir yaklaşım oldu.

---

# 20. Disk Alanı Problemi

İlk durumda:

```text
/dev/root
Size: 6.8G
Used: 4.1G
Avail: 2.7G
```

şeklindeydi.

Docker build sırasında PyTorch nedeniyle disk yetersiz kaldı.

Öncelikle Docker build cache'ini temizledik:

```bash
docker builder prune -f
```

Sonrasında:

```bash
docker system df
```

ile Docker'ın disk kullanımını kontrol ettik.

Ancak CPU-only PyTorch'a geçmemize rağmen image'ın oluşturulması için hâlâ daha fazla disk gerekiyordu.

---

# 21. AWS EBS Diskini Büyütme

EC2'nin root diskini AWS üzerinden:

```text
8 GiB → 20 GiB
```

olarak büyüttük.

Fakat burada önemli bir detay vardı:

AWS'de disk 20 GB görünmesine rağmen Ubuntu'nun root partition'ı hâlâ yaklaşık 7 GB görünüyordu.

Kontrol:

```bash
lsblk
```

çıktısında:

```text
nvme0n1      20G
└─nvme0n1p1   7G /
```

gibi bir durum vardı.

Yani:

```text
EBS Disk = 20 GB
Partition = 7 GB
Filesystem = 7 GB
```

durumundaydı.

---

# 22. Partition'ı Büyütmek

Öncelikle `growpart` komutunun bulunduğunu kontrol ettik:

```bash
which growpart
```

Sonuç:

```text
/usr/bin/growpart
```

Ardından:

```bash
sudo growpart /dev/nvme0n1 1
```

çalıştırdık.

Başarılı şekilde:

```text
CHANGED: partition=1
```

mesajını aldık.

Bu işlem partition'ı diskin kullanılabilir alanına kadar genişletti.

---

# 23. Filesystem'i Büyütmek

Partition büyüdükten sonra filesystem'i de büyütmemiz gerekiyordu.

Bunun için:

```bash
sudo resize2fs /dev/nvme0n1p1
```

komutunu kullandık.

Sonrasında:

```bash
df -h /
```

çıktısı:

```text
/dev/root   19G   4.4G   14G   24%
```

oldu.

Artık sistem yaklaşık 19 GB kullanılabilir root filesystem alanına sahipti.

---

# 24. Docker Image Build

Disk problemini çözdükten sonra tekrar:

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

çalıştırdık.

Bu sefer:

```text
✔ Image docker-app Built
✔ Network docker_default Created
✔ Volume docker_pgdata Created
✔ Container rag_postgres Healthy
✔ Container rag_app Started
```

sonucunu aldık.

Bu bizim için çok önemli bir noktadır.

Çünkü:

```text
Docker image başarıyla oluşturuldu.
PostgreSQL başladı.
PostgreSQL healthy oldu.
FastAPI başladı.
```

---

# 25. Container Durumunu Kontrol Etmek

Container'ların durumunu:

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

ile kontrol ettik.

Sonuç:

```text
rag_app        Up
rag_postgres   Up (healthy)
```

şeklindeydi.

Ayrıca port:

```text
0.0.0.0:8000->8000/tcp
```

olarak görünüyordu.

Bunun anlamı:

```text
EC2 port 8000
       │
       ▼
Docker container port 8000
       │
       ▼
FastAPI
```

bağlantısının kurulduğudur.

---

# 26. FastAPI Loglarını Kontrol Etmek

FastAPI container loglarını:

```bash
docker logs rag_app --tail 100
```

komutuyla kontrol ettik.

Aldığımız önemli mesajlar:

```text
Started server process
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

Bunlar FastAPI'nin başarılı şekilde başladığını gösterir.

Özellikle:

```text
0.0.0.0:8000
```

önemlidir.

Çünkü uygulamanın sadece container içerisinden değil, container dışından da erişilebilir olmasını istiyoruz.

---

# 27. Local `/docs` Testi

Öncelikle uygulamayı EC2'nin kendi içerisinden test ettik:

```bash
curl http://localhost:8000/docs
```

FastAPI Swagger HTML çıktısını aldık.

Ardından daha net bir HTTP testi:

```bash
curl -I http://localhost:8000/docs
```

Sonuç:

```text
HTTP/1.1 200 OK
server: uvicorn
content-type: text/html; charset=utf-8
```

Bu şu anlama gelir:

> EC2 içerisinden FastAPI'nin `/docs` endpoint'ine başarıyla erişiliyor.

---

# 28. Public IP Üzerinden Test

EC2'nin Public IPv4 adresi:

```text
51.21.221.224
```

olarak belirlendi.

Bilgisayarımızın tarayıcısından:

```text
http://51.21.221.224:8000/docs
```

adresini açtık.

Sonuç:

```text
RAG Doküman Soru-Cevap Sistemi
```

başlıklı Swagger UI başarıyla açıldı.

Bu, deployment'ın internet üzerinden erişilebilir olduğunu doğruladı.

---

# 29. Swagger Neden Kullanıldı?

FastAPI otomatik olarak OpenAPI/Swagger dokümantasyonu oluşturur.

Bizim:

```text
/docs
```

endpoint'imiz API'nin endpoint'lerini tarayıcı üzerinden görmemizi sağlar.

Örneğin burada:

```text
GET
POST
```

gibi endpoint'leri görebilir ve doğrudan test edebiliriz.

Swagger'ın deployment sırasında kullanılmasının nedeni:

> Uygulamanın sadece container olarak çalışıp çalışmadığını değil, API'nin gerçekten HTTP üzerinden erişilebilir olup olmadığını test etmek.

Yani:

```text
Container çalışıyor
```

demek tek başına yeterli değildir.

Şunları da doğrulamak gerekir:

```text
Container
   ↓
FastAPI
   ↓
Port 8000
   ↓
EC2
   ↓
Security Group
   ↓
Internet
   ↓
Browser
```

Biz bu zincirin tamamını test etmiş olduk.

---

# 30. Son Mimari

Projenin AWS üzerindeki son hali:

```text
                         INTERNET
                             │
                             │
                  http://51.21.221.224:8000
                             │
                             ▼
                     AWS EC2 Server
                     Ubuntu 24.04
                         t3.micro
                             │
                             ▼
                      Docker Compose
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
          rag_app                       rag_postgres
          FastAPI                       PostgreSQL
          Python                       + pgvector
          :8000                           :5432
              │
              │
              ├── LangChain
              ├── Sentence Transformers
              ├── Hugging Face
              └── RAG Pipeline
```

---

# 31. Kullanılan Önemli Komutlar

## EC2'ye bağlanma

```bash
ssh -i "rag-doc-qa-key.pem" ubuntu@EC2_PUBLIC_DNS
```

## Projeyi clone etme

```bash
git clone https://github.com/yagmurraydar/rag-doc-qa.git
cd rag-doc-qa
```

## Docker kontrol

```bash
docker --version
docker compose version
```

## Docker test

```bash
docker run hello-world
```

## Docker disk kullanımı

```bash
docker system df
```

## Docker build cache temizleme

```bash
docker builder prune -f
```

## Disk kontrolü

```bash
df -h /
```

## Docker Compose'u başlatma

```bash
docker compose --env-file .env -f docker/docker-compose.yml up --build -d
```

## Container durumları

```bash
docker compose --env-file .env -f docker/docker-compose.yml ps
```

## FastAPI logları

```bash
docker logs rag_app --tail 100
```

## PostgreSQL logları

```bash
docker logs rag_postgres --tail 100
```

## API testi

```bash
curl http://localhost:8000/docs
```

## HTTP status testi

```bash
curl -I http://localhost:8000/docs
```

---

# 32. Deployment Sonucu

Deployment sonucunda proje:

```text
GitHub
   ↓
AWS EC2
   ↓
Docker
   ↓
Docker Compose
   ↓
FastAPI + PostgreSQL/pgvector
   ↓
Public API
```

şeklinde çalışır hale getirildi.

Public Swagger adresi:

```text
http://51.21.221.224:8000/docs
```

Test sonucu:

```text
HTTP 200 OK
```

ve Swagger UI başarıyla görüntülendi.

---

# 33. Öğrendiğimiz Önemli Kavramlar

Bu deployment sırasında yalnızca Docker çalıştırmadık. Aynı zamanda şu kavramları pratik olarak kullandık:

### AWS

* EC2
* EBS
* Security Group
* Public IP
* Private IP
* SSH
* AWS Region

### Linux

* SSH
* filesystem
* partition
* `df`
* `lsblk`
* `growpart`
* `resize2fs`
* Linux servisleri

### Docker

* Docker image
* Docker container
* Docker volume
* Docker network
* Docker Compose
* Dockerfile
* Docker build cache
* Container logs
* Port mapping
* Healthcheck

### Backend

* FastAPI
* Uvicorn
* REST API
* OpenAPI
* Swagger UI

### RAG

* Embedding
* Sentence Transformers
* Hugging Face
* Vector database
* pgvector
* PostgreSQL

---

# 34. En Önemli Mantık

Bu projede öğrendiğimiz temel deployment mantığı şudur:

```text
Kodum bilgisayarımda çalışıyor
            ↓
Docker ile paketliyorum
            ↓
Docker image oluşturuyorum
            ↓
AWS EC2'ye gönderiyorum
            ↓
EC2 üzerinde container çalıştırıyorum
            ↓
PostgreSQL ayrı container olarak çalışıyor
            ↓
FastAPI PostgreSQL'e bağlanıyor
            ↓
Security Group 8000 portuna izin veriyor
            ↓
Public IP üzerinden API'ye erişiyorum
            ↓
Swagger ile API'yi test ediyorum
```

Bu nedenle artık proje yalnızca:

> "Bilgisayarımda çalışan bir Python projesi"

değil;

> **Docker ile containerize edilmiş ve AWS EC2 üzerinde deploy edilmiş bir RAG API uygulamasıdır.**

---

# 35. Dikkat Edilmesi Gerekenler

## `.env` dosyasını GitHub'a göndermemeliyiz

Token gibi secret bilgiler GitHub'a push edilmemelidir.

Kontrol:

```bash
git status
```

## EC2 Public IP değişebilir

Instance durdurulup tekrar başlatılırsa Public IP değişebilir.

Bu durumda yeni IP ile:

```text
http://NEW_PUBLIC_IP:8000/docs
```

kullanılması gerekir.

Kalıcı IP ihtiyacı varsa ileride Elastic IP kullanılabilir.

## Port 8000

Security Group'ta 8000 portu açık olmalıdır.

## Docker disk kullanımı

PyTorch, Hugging Face modelleri ve Docker image'ları ciddi disk alanı kullanabilir.

Bu yüzden disk kullanımını:

```bash
df -h
docker system df
```

ile kontrol etmek önemlidir.

---

# 36. Son Durum

Deployment başarıyla tamamlandı.

```text
EC2                ✅
Ubuntu             ✅
SSH                ✅
Docker             ✅
Docker Compose     ✅
PostgreSQL         ✅
pgvector           ✅
FastAPI            ✅
Hugging Face       ✅
CPU-only PyTorch   ✅
Docker Build       ✅
Docker Containers  ✅
Security Group     ✅
Swagger            ✅
Public Access      ✅
```

Public endpoint:

```text
http://51.21.221.224:8000/docs
```

**RAG-Doc-QA uygulaması AWS EC2 üzerinde Docker Compose ile çalışır durumdadır.**

# GitHub Push Hatası ve Çözümü

AWS EC2 üzerinde yaptığımız Docker değişikliklerini GitHub'a göndermek için `git push` işlemi yaptık. Ancak GitHub kimlik doğrulama hatası verdi.

## 1. Aldığımız Hata

İlk olarak:

```bash
git push origin main
```

komutunu çalıştırdık.

GitHub kullanıcı adı ve şifre istedi ve ardından şu hatayı verdi:

```text
remote: Invalid username or token.
Password authentication is not supported for Git operations.
fatal: Authentication failed
```

## 2. Hatanın Nedeni

Repository'nin Git remote adresi HTTPS kullanıyordu:

```text
https://github.com/yagmurraydar/rag-doc-qa.git
```

GitHub artık Git işlemlerinde normal hesap şifresiyle HTTPS üzerinden `push` yapılmasına izin vermiyor.

Yani problem:

* Docker'da değildi.
* Projede değildi.
* Commit'te değildi.

Problem, **EC2'nin GitHub'a kimlik doğrulama yöntemiydi.**

## 3. Çözüm: SSH Authentication

EC2 üzerinde bir SSH key oluşturduk:

```bash
ssh-keygen -t ed25519 -C "yagmurraydar"
```

Oluşturulan **public key'i** GitHub hesabımıza ekledik.

> Private key (`id_ed25519`) kesinlikle paylaşılmamalıdır. GitHub'a eklenen key public key'dir (`id_ed25519.pub`).

## 4. GitHub SSH Bağlantısını Test Ettik

Bağlantıyı:

```bash
ssh -T git@github.com
```

komutuyla test ettik.

Başarılı bağlantıda:

```text
Hi yagmurraydar! You've successfully authenticated,
but GitHub does not provide shell access.
```

mesajını aldık.

Bu, EC2'nin GitHub hesabımız tarafından başarıyla doğrulandığını gösterdi.

## 5. Git Remote'u HTTPS'den SSH'ye Çevirdik

Önce mevcut remote HTTPS kullanıyordu.

Remote adresini SSH olarak değiştirdik:

```bash
git remote set-url origin git@github.com:yagmurraydar/rag-doc-qa.git
```

Kontrol etmek için:

```bash
git remote -v
```

çıktısı:

```text
origin  git@github.com:yagmurraydar/rag-doc-qa.git (fetch)
origin  git@github.com:yagmurraydar/rag-doc-qa.git (push)
```

şeklinde oldu.

## 6. Push İşlemini Tekrar Yaptık

Son olarak:

```bash
git push origin main
```

komutunu çalıştırdık.

Bu kez başarılı oldu:

```text
To github.com:yagmurraydar/rag-doc-qa.git
   98674c6..6475f70  main -> main
```

## Sonuç

GitHub'a push sırasında aldığımız hata, **GitHub'ın HTTPS üzerinden normal şifre ile Git authentication'ını desteklememesinden** kaynaklandı.

EC2 üzerinde SSH key oluşturup GitHub hesabına ekledik ve repository'nin remote adresini SSH'ye çevirdik.

Böylece:

```text
EC2
 ↓
SSH Authentication
 ↓
GitHub
 ↓
git push
 ↓
main branch
```

şeklinde GitHub bağlantısını başarıyla kurmuş olduk.

### Kullanılan Temel Komutlar

```bash
# SSH key oluşturma
ssh-keygen -t ed25519 -C "yagmurraydar"

# GitHub bağlantısını test etme
ssh -T git@github.com

# Remote adresini SSH'ye çevirme
git remote set-url origin git@github.com:yagmurraydar/rag-doc-qa.git

# Remote'u kontrol etme
git remote -v

# GitHub'a gönderme
git push origin main
```

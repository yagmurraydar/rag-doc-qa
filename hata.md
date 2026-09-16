# AWS EC2 - PDF Upload OOM Hatası ve Çözümü

## 1. Projede Karşılaştığımız Problem

RAG projemizi AWS EC2 üzerinde Docker Compose ile çalıştırdık.

Sistemimiz:

* FastAPI
* PostgreSQL
* pgvector
* SentenceTransformer
* Docker
* Docker Compose
* AWS EC2

üzerinden çalışıyor.

API'ye PDF yüklemek için:

```text
POST /api/upload
```

endpoint'ini kullanıyoruz.

Swagger üzerinden PDF yüklemeye çalıştığımızda:

```text
Failed to fetch
```

hatası aldık.

Terminal üzerinden PDF yüklediğimizde ise:

```text
curl: (52) Empty reply from server
```

ve:

```text
curl: (56) Recv failure: Connection reset by peer
```

hatalarını gördük.

---

# 2. İlk Kontrol: Endpoint Var mı?

Öncelikle FastAPI uygulamasında `/api/upload` endpoint'inin gerçekten bulunup bulunmadığını kontrol ettik.

```bash
curl -s http://localhost:8000/openapi.json | grep -o '"/api/[^"]*"' | sort -u
```

Çıktı:

```text
"/api/ask"
"/api/upload"
```

Bu sonuç `/api/upload` endpoint'inin mevcut olduğunu gösterdi.

Dolayısıyla problem endpoint'in eksik olması değildi.

---

# 3. POST Endpoint'inin Çalıştığını Kontrol Ettik

Dosya göndermeden POST isteği gönderdik:

```bash
curl -i -X POST http://localhost:8000/api/upload
```

FastAPI:

```text
HTTP/1.1 422
```

döndürdü.

Bu aslında olumlu bir sonuçtu.

Çünkü FastAPI endpoint'e ulaştığını ancak gerekli `file` parametresinin gönderilmediğini söylüyordu.

Yani:

```text
FastAPI çalışıyor       ✅
/api/upload mevcut      ✅
POST metodu çalışıyor   ✅
```

---

# 4. 405 Method Not Allowed Hatası Neden Görüldü?

Loglarda şu mesajı gördük:

```text
GET /api/upload HTTP/1.1
405 Method Not Allowed
```

Bunun sebebi `/api/upload` endpoint'inin yalnızca POST kabul etmesidir.

Endpoint:

```text
POST /api/upload
```

şeklindedir.

Tarayıcıya doğrudan:

```text
http://51.20.138.92:8000/api/upload
```

yazıldığında tarayıcı GET isteği gönderir.

Dolayısıyla:

```text
GET /api/upload    ❌
POST /api/upload   ✅
```

olur.

Bu nedenle 405 hatası aldık.

Ancak bu, PDF yükleme sırasında yaşadığımız asıl problem değildi.

---

# 5. PDF Yükleme Sırasında Asıl Hata

PDF'yi doğrudan terminalden yüklemeyi denedik:

```bash
curl -i -X POST http://localhost:8000/api/upload \
-F "file=@test.pdf;type=application/pdf"
```

İlk denemelerde:

```text
HTTP/1.1 100 Continue
```

sonrasında:

```text
curl: (52) Empty reply from server
```

ve bazı denemelerde:

```text
curl: (56) Recv failure: Connection reset by peer
```

aldık.

Bu durum, istek sırasında uygulamanın bağlantıyı kapattığını gösteriyordu.

---

# 6. Docker Container'ını Kontrol Ettik

Şu komutla container'ların durumunu kontrol ettik:

```bash
docker compose -f docker/docker-compose.yml ps
```

Container'lar:

```text
rag_app
rag_postgres
```

olarak çalışıyordu.

Ancak `rag_app` container'ının zaman zaman yeniden başlatıldığını fark ettik.

Bunun üzerine container'ın neden kapandığını araştırmaya başladık.

---

# 7. Docker Events ile Kök Nedeni Bulduk

Docker event loglarını kontrol ettik:

```bash
docker events --since 10m --until 0s --filter container=rag_app
```

Burada önemli bir kayıt gördük:

```text
container oom
```

Ayrıca container'ın:

```text
exitCode=137
```

ile sonlandığını gördük.

## OOM Nedir?

OOM:

```text
Out Of Memory
```

anlamına gelir.

Yani sistemin belleği uygulamayı çalıştırmaya yetmediğinde işletim sistemi belleği korumak için çalışan bir process'i sonlandırabilir.

Bizim durumda öldürülen process:

```text
uvicorn
```

oldu.

---

# 8. Linux Kernel Logları ile Doğruladık

Sistemin kernel loglarını kontrol ettik:

```bash
sudo dmesg -T | grep -i -E 'oom|killed process|out of memory' | tail -20
```

Loglarda:

```text
oom-kill
```

ve:

```text
Out of memory: Killed process ... (uvicorn)
```

mesajlarını gördük.

Böylece problemin kesin olarak RAM yetersizliği olduğunu doğruladık.

---

# 9. Neden RAM Yetmedi?

AWS EC2 instance'ımızın yaklaşık:

```text
909 MiB RAM
```

belleği vardı.

Ancak aynı makinede birçok servis çalışıyordu:

```text
Ubuntu
Docker
FastAPI / Uvicorn
PostgreSQL
pgvector
Python
SentenceTransformer
```

PDF yükleme işlemi sırasında ise sadece PDF okunmuyordu.

İşlem kabaca şu şekildeydi:

```text
PDF
 ↓
PDF'den metin çıkarma
 ↓
Chunk oluşturma
 ↓
SentenceTransformer
 ↓
Embedding oluşturma
 ↓
Vector
 ↓
pgvector
```

Özellikle embedding modelinin çalışması sırasında RAM kullanımı arttı.

Yaklaşık 909 MB RAM bulunan EC2 instance'ında bu bellek ihtiyacı sistemi OOM durumuna götürdü.

---

# 10. Docker Neden Tekrar Ayağa Kalkıyordu?

Docker Compose dosyamızda:

```yaml
restart: always
```

kullanıyorduk.

Bu ayar container kapanırsa Docker'ın container'ı tekrar başlatmasını sağlar.

Dolayısıyla şu döngü oluşuyordu:

```text
PDF yükleniyor
      ↓
RAM kullanımı artıyor
      ↓
RAM yetmiyor
      ↓
Linux OOM Killer çalışıyor
      ↓
Uvicorn öldürülüyor
      ↓
Container kapanıyor
      ↓
restart: always
      ↓
Docker container'ı tekrar başlatıyor
```

Bu nedenle dışarıdan baktığımızda container'ın tekrar `Up` durumda olduğunu görebiliyorduk.

---

# 11. Çözüm: Swap Alanı Eklemek

EC2 instance'ını hemen değiştirmek yerine öncelikle Linux'a swap alanı ekledik.

Swap, disk üzerinde ayrılan ve gerektiğinde bellek gibi kullanılabilen bir alandır.

RAM'den daha yavaştır ancak bellek baskısı oluştuğunda sistemin process'i hemen öldürmesini önlemeye yardımcı olabilir.

Biz:

```text
2 GB Swap
```

oluşturduk.

---

# 12. Swap Oluşturma

Öncelikle 2 GB swap dosyası oluşturduk:

```bash
sudo fallocate -l 2G /swapfile
```

Dosyanın izinlerini güvenli hale getirdik:

```bash
sudo chmod 600 /swapfile
```

Swap alanını oluşturduk:

```bash
sudo mkswap /swapfile
```

Ardından aktif ettik:

```bash
sudo swapon /swapfile
```

Kontrol etmek için:

```bash
free -h
```

komutunu kullandık.

Sonuç:

```text
Mem:   yaklaşık 909Mi
Swap:  2.0Gi
```

şeklinde oldu.

---

# 13. Swap'in Yeniden Başlatma Sonrasında da Aktif Olmasını Sağladık

Swap'ın EC2 yeniden başlatıldığında da otomatik olarak aktif olması için `/etc/fstab` dosyasına ekledik:

```bash
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

Böylece sistem yeniden başlatıldığında `/swapfile` otomatik olarak swap olarak kullanılabilecek.

---

# 14. Çözümden Sonra PDF Upload Testi

Swap aktif olduktan sonra tekrar PDF yükledik:

```bash
curl -i -X POST http://localhost:8000/api/upload \
-F "file=@test.pdf;type=application/pdf"
```

Bu kez:

```text
HTTP/1.1 200 OK
```

aldık.

API cevabı:

```json
{
    "message": "PDF başarıyla işlendi ve indekslendi.",
    "file_name": "test.pdf",
    "num_pages": 27,
    "num_chunks": 98
}
```

şeklinde oldu.

Bu sonuç sistemin artık PDF'yi başarıyla işlediğini gösterdi.

---

# 15. Başarılı Sonuç Ne Anlama Geliyor?

Aşağıdaki işlemlerin tamamı başarılı oldu:

```text
PDF dosyasını alma             ✅
PDF'den metin çıkarma          ✅
27 sayfayı işleme              ✅
Chunk oluşturma                ✅
98 chunk oluşturma             ✅
Embedding işlemi               ✅
Vector oluşturma               ✅
pgvector'a kaydetme            ✅
FastAPI response               ✅
HTTP 200 OK                    ✅
```

---

# 16. Hatanın Kısa Özeti

Başlangıçta:

```text
PDF Upload
     ↓
Embedding işlemi
     ↓
RAM yetersiz
     ↓
OOM
     ↓
Uvicorn öldürülüyor
     ↓
Container yeniden başlıyor
     ↓
Curl bağlantısı kesiliyor
     ↓
"Empty reply from server"
```

Çözümden sonra:

```text
PDF Upload
     ↓
Embedding işlemi
     ↓
RAM + Swap
     ↓
Bellek baskısı yönetiliyor
     ↓
Uvicorn çalışmaya devam ediyor
     ↓
PDF işleniyor
     ↓
98 chunk
     ↓
pgvector
     ↓
HTTP 200 OK
```

---

# 17. Bu Problemden Öğrendiğimiz DevOps Yaklaşımı

Bir uygulama çalışmadığında doğrudan kodu değiştirmek yerine problemi katmanlara ayırmak gerekir.

Kontrol sırası:

```text
1. Endpoint mevcut mu?
        ↓
2. HTTP metodu doğru mu?
        ↓
3. Container çalışıyor mu?
        ↓
4. Container restart ediyor mu?
        ↓
5. Docker eventlerinde OOM var mı?
        ↓
6. Linux kernel loglarında OOM var mı?
        ↓
7. RAM / CPU / Disk yeterli mi?
```

Biz de bu yöntemle ilerleyerek problemin uygulama kodundan değil, EC2'nin bellek yetersizliğinden kaynaklandığını tespit ettik.

---

# 18. Kullanılan Önemli Komutlar

### Container durumunu kontrol etme

```bash
docker compose -f docker/docker-compose.yml ps
```

### API endpointlerini kontrol etme

```bash
curl -s http://localhost:8000/openapi.json | grep -o '"/api/[^"]*"' | sort -u
```

### PDF upload testi

```bash
curl -i -X POST http://localhost:8000/api/upload \
-F "file=@test.pdf;type=application/pdf"
```

### Docker eventlerini kontrol etme

```bash
docker events --since 10m --until 0s --filter container=rag_app
```

### Linux memory/OOM loglarını kontrol etme

```bash
sudo dmesg -T | grep -i -E 'oom|killed process|out of memory' | tail -20
```

### RAM ve Swap durumunu kontrol etme

```bash
free -h
```

### Swap oluşturma

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Swap'ı kalıcı hale getirme

```bash
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

---

# 19. Sonuç

AWS EC2 üzerinde çalışan RAG uygulamasında PDF upload sırasında oluşan bağlantı kopmasının temel nedeni **EC2 instance'ındaki RAM yetersizliği nedeniyle Linux OOM Killer'ın Uvicorn process'ini sonlandırmasıydı.**

Problemi Docker eventleri ve Linux kernel logları üzerinden tespit ettik.

Çözüm olarak EC2 üzerinde **2 GB swap alanı** oluşturduk ve `/etc/fstab` ile kalıcı hale getirdik.

Swap sonrasında PDF tekrar yüklendi ve:

```text
HTTP 200 OK
```

alındı.

27 sayfalık PDF başarıyla işlendi ve:

```text
98 chunk
```

oluşturularak RAG sisteminin vector database'ine indekslendi.

Bu süreçte ayrıca:

* Docker container yönetimi
* Docker restart policy
* Linux OOM Killer
* RAM ve Swap yönetimi
* FastAPI endpoint debugging
* Docker event/log analizi
* AWS EC2 kaynak yönetimi

konularında pratik yapılmış oldu.

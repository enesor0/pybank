# PyBank — Flet ve Onion Architecture Bankacılık Uygulaması

Flet tabanlı modern masaüstü/web arayüzü ve SQLite kalıcılığı bulunan Python banka uygulaması.

## Çalıştırma

```powershell
.\run.ps1
```

İlk kullanımda kayıt olun. Veritabanı `pybank.sqlite3` adıyla otomatik oluşturulur. Flet proje içindeki `.venv` ortamına kuruludur; doğrudan çalıştırmak için `\.venv\Scripts\python.exe app.py` komutunu kullanabilirsiniz.

## Özellikler

- Kayıt ve giriş; PBKDF2-HMAC-SHA256 ile tuzlanmış parola özetleri
- Vadesiz ve birikim hesabı açma; doğrulama basamağı içeren Türkiye IBAN üretimi
- Decimal tabanlı para hesapları, bakiye ve tutar kontrolleri
- Tek SQL işlemi içinde atomik para yatırma, çekme ve transfer
- Karşılıklı transfer kayıtları, işlem açıklaması, tarihçe ve IBAN panoya kopyalama
- SQLite foreign key, unique, check ve index kısıtları

## İşCep'ten ilham alan ekranlar

- Sol menüden çalışan **Genel Bakış**, **Para Transferi**, **Ödemeler**, **Kartlarım**, **İşlem Geçmişi** ve **Ayarlar** sayfaları
- Koyu/açık tema seçimi
- Banka kartı, kredi kartı ve sanal kart oluşturma; kartı dondurma/açma ve temassız kullanım tercihi
- Kredi kartında kart limiti ve kullanılabilir limit görüntüleme
- Kart kapatma talimatı; onaydan sonra kartı dondurur ve temassız kullanımı kapatır
- Elektrik, su, doğal gaz, internet, cep telefonu ve kredi kartı borcu için fatura ödeme simülasyonu
- İç hesaplara anlık transfer; geçerli harici TR IBAN'lara giden EFT/havale kaydı

> Bu proje gerçek banka sistemlerine, ödeme ağlarına veya NFC/QR donanımına bağlı değildir. Kartlar ve ödemeler, yalnızca yerel SQLite veritabanında çalışan güvenli bir arayüz simülasyonudur.

## Katmanlar

```text
presentation/     Flet ekranları (dış katman)
infrastructure/   SQLite adaptörü (dış katman)
application/      Kullanım senaryoları, servisler ve portlar
domain/           Varlıklar, değer nesneleri ve iş kuralları (çekirdek)
```

Bağımlılık yönü daima dıştan içe doğrudur. Domain ve application katmanları Flet ya da SQLite bilmez; application yalnızca `ports.py` içindeki soyut repository arayüzlerine bağlıdır.

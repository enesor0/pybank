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

> Bu proje gerçek banka sistemlerine, ödeme ağlarına veya NFC/QR donanımına bağlı değildir. Kartlar ve ödemeler, yalnızca yerel SQLite veritabanında çalışan güvenli bir arayüz simülasyonudur.

## Katmanlar

```text
presentation/     Flet ekranları (dış katman)
infrastructure/   SQLite adaptörü (dış katman)
application/      Kullanım senaryoları, servisler ve portlar
domain/           Varlıklar, değer nesneleri ve iş kuralları (çekirdek)
```

Bağımlılık yönü daima dıştan içe doğrudur. Domain ve application katmanları Flet ya da SQLite bilmez; application yalnızca `ports.py` içindeki soyut repository arayüzlerine bağlıdır.

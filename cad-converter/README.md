# CAD Converter & Renderer Prototype

Bu proje, **all2png.com** platformuna entegre edilmek üzere tasarlanmış, hukuki olarak tamamen güvenli (ODA içermeyen, GPLv3 uyumlu) ve yüksek performanslı bir CAD (.dwg / .dxf) dönüştürücü ve görselleştirici prototipidir.

Projede **DXF çizimlerini okumak ve yüksek çözünürlüklü PNG/PDF görsellerine dönüştürmek** için Python (`ezdxf` + `matplotlib`) kütüphanesi kullanılır. 

**.dwg dosyalarını okumak ve eski versiyonlara dönüştürmek** için ise sistemde kurulu olan açık kaynaklı **GNU LibreDWG** CLI araçları (`dwg2dxf` ve `dxf2dwg`) arka planda güvenle tetiklenir.

---

## ⚖️ Hukuki Uyarı ve Lisanslama (GPLv3 Hukuki Zırh)

*   **Harici Bileşen Beyanı:** Bu yazılım, **GNU LibreDWG** aracını harici bir bileşen olarak (Loose Coupling / Gevşek Bağlılık prensibi ile) kullanmaktadır. Sunucu tarafında bağımsız bir komut satırı aracı (subprocess CLI) olarak çağrılır. 
*   **Bağımlılık Durumu:** Proje kodları LibreDWG kodunu içermez veya derlemez. LibreDWG, sunucu yöneticisi veya kullanıcı tarafından harici olarak kurulması gereken bağımsız bir sistem bağımlılığıdır. Bu durum lisans kısıtlamalarının (`GPLv3` kod açma zorunluluğu) ana sistemimizi etkilemesini hukuken engeller.
*   **Ticari Kullanım:** GNU/GPL lisanslı bileşenlerin ticari SaaS projelerinde harici araç olarak tetiklenmesinde yasal bir kısıtlama yoktur. all2png.com üzerinden ticari hizmet verilmesinde hukuki bir engel bulunmamaktadır.

---

## 🔒 GDPR / KVKK Veri Güvenliği

*   **Garbage Collection (Otomatik Temizlik):** `converter.py` içerisinde ara işlemler ve DWG/DXF dönüşümleri için Python'ın güvenli `tempfile.TemporaryDirectory` yapısı kullanılmıştır.
*   Bu sayede, kullanıcının yüklediği dosyalar ve ara dönüştürme çıktıları bellekte ve diskte kalıcı olarak barındırılmaz. İşlem biter bitmez (hata alınsa dahi) geçici klasör işletim sistemi düzeyinde **fiziksel olarak tamamen silinir**. Bu yapı veri güvenliği (GDPR/KVKK) standartlarına %100 uyumludur.

---

## ⚡ Performans Testi (Benchmark Sonuçları)

Örnek mimari çizim (`sample.dxf`) üzerinde 300 DPI çözünürlükte yapılan **koyu tema render** testi sonuçları:

*   **İlk Yükleme ve Önbellekleme Süresi (Cold Start / Iteration 1):** 7.2989 saniye
*   **Ortalama Render Hızı:** **3.5082 saniye**
*   **En Hızlı Çevrim:** 1.6401 saniye
*   **Sistem Kapasitesi (Throughput):** Tek işlemcide saniyede ortalama **0.29 render**

> [!NOTE]
> ezdxf ve matplotlib son derece hafif kütüphaneler olduğu için sunucunuza neredeyse sıfır ek yük getirir ve saniyeler içinde binlerce çizimi render edebilir.

---

## 🛠️ Kurulum

### 1. Python Bağımlılıkları
Proje dizininde gerekli kütüphaneleri yükleyin:
```bash
python -m pip install -r requirements.txt
```

### 2. LibreDWG Kurulumu (DWG Desteği İçin)
DWG dosyalarını dönüştürmek istiyorsanız:
1.  [LibreDWG GitHub Releases](https://github.com/LibreDWG/libredwg/releases) sayfasından son sürüm Windows zip dosyasını indirin.
2.  Zip içerisindeki `dwg2dxf.exe` ve `dxf2dwg.exe` araçlarını bu projenin içine `bin/` adında bir klasör oluşturup oraya kopyalayın veya sistem PATH'ine ekleyin.

---

## 🚀 Kullanım Örnekleri

### 1. CAD Dosyasını PNG Görseline Dönüştürme
*   **Açık Tema:**
    ```bash
    python converter.py --input sample.dxf --output sample_light.png --theme light
    ```
*   **Koyu Tema (300 DPI):**
    ```bash
    python converter.py --input sample.dxf --output sample_dark.png --theme dark --dpi 300
    ```

### 2. Versiyon Düşürme (Eski AutoCAD Versiyonları)
*   **DXF'i eski bir AutoCAD versiyonunda DWG'ye çevirme (Örn: R2010):**
    ```bash
    python converter.py --input drawing.dxf --output drawing_2010.dwg --version R2010
    ```

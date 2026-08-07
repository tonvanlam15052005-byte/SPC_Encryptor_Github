# 🔐 SPC Encryptor Pro

**Hệ thống mã hóa đa tầng SPC - Hiện thực hóa lý thuyết Super Planet Crypting**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Flask Version](https://img.shields.io/badge/flask-2.3.3-green)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.5.5-red)](https://github.com/tonvanlam15052005-byte/SPC_Encryptor_Github)

---
## 🌍 Website
[SPC Encryptor Pro](https://spc-encryptor-github.onrender.com)
## 📖 Giới thiệu

**SPC Encryptor Pro** là một hệ thống mã hóa đa tầng, được xây dựng dựa trên lý thuyết **SPC (Super Planet Crypting)** của **Minvokin Grabiel Xavier (Mr.MR)**. Dự án là sự kết hợp giữa lý thuyết bảo mật tiên tiến và công nghệ web hiện đại, cung cấp một công cụ mã hóa mạnh mẽ, linh hoạt và dễ sử dụng.

Dự án được phục dựng và phát triển bởi cộng đồng, với mục tiêu:

- ✅ Hiện thực hóa lý thuyết SPC vào sản phẩm thực tế.
- ✅ Cung cấp công cụ bảo mật cá nhân mạnh mẽ, minh bạch và mã nguồn mở.
- ✅ Tạo nền tảng học tập và nghiên cứu về các kỹ thuật mã hóa đa tầng.
- ✅ Tôn vinh và bảo tồn di sản lý thuyết của Mr.MR.

---

## 🧠 Nguồn gốc và lý thuyết (một phần trong nhóm nội bộ của chúng tôi)

### Lý thuyết gốc: SPC (Super Planet Crypting)

- **Tác giả**: Minvokin Grabiel Xavier (Mr.MR) - Mr.Минвокин Рабиэль (Bí danh Mr.Минвокин Граксав)
- **Cấu trúc**: 8 Hành tinh × 8 Tổ hợp × 8 Bước = **4.096 bước mã hóa tiềm năng**
- **Triết lý**: "Mã hóa là nghệ thuật của sự phức tạp có kiểm soát"

### Quá trình phục dựng & phát triển

| Giai đoạn | Đơn vị thực hiện | Đóng góp |
|-----------|------------------|----------|
| **Sáng lập lý thuyết** | Mr.MR | Xây dựng nền tảng SPC |
| **Phục dựng kiến trúc** | SGM (Simple Gray Modules) & KOT/CAT STUDIOS | Bảo toàn 80% bản thiết kế gốc |
| **Tối ưu hóa & Việt hóa** | Cộng đồng | Chuyển đổi sang ứng dụng thực tế |
| **Hiện thực hóa Web** | Dự án mã nguồn mở | Xây dựng SPC Encryptor Pro |

---

## ✨ Tính năng nổi bật

### 🔐 10 Kỹ thuật mã hóa SPC

| Ký hiệu | Tên kỹ thuật | Mô tả | Trạng thái |
|---------|--------------|-------|------------|
| **R** | Header Removal | Tách Header khỏi dữ liệu, lưu vào SAOYUT | ✅ Ổn định |
| **C** | Cut & Swap | Cắt đôi và đổi chỗ hai nửa dữ liệu | ✅ Ổn định |
| **E** | Enigma | Mã hóa XOR với Seed | ✅ Ổn định |
| **Z** | Zip Hiding | Chèn Header giả `.txt` | ✅ Ổn định |
| **S** | Sharding | Chia dữ liệu thành nhiều mảnh, xáo trộn thứ tự | ✅ Ổn định |
| **H** | Header Masking | XOR với key ngẫu nhiên | ✅ Ổn định |
| **D** | Double Fake | Chèn 2 Header giả liên tiếp | ✅ Ổn định |
| **B** | Hashing Chain | Tạo Pass từ băm xích (100 lần SHA256) | ✅ Ổn định |
| **P** | RAM-only | Xóa vết trong RAM | ✅ Ổn định |
| **L** | Low Storage | Chia thành Segments, lưu phân tán | ✅ Ổn định |

> **🎉 Thành công**: Tất cả 10 kỹ thuật đã được kiểm tra và hoạt động ổn định, bao gồm cả **S (Sharding)** và **B (Hashing Chain)** khi kết hợp với nhau. Đã sửa thành công lỗi tương thích giữa S và B.

### 🛠️ Các tính năng khác

- ✅ **Bốn yếu tố giải mã**: Dữ liệu mã hóa + SAOYUT + Seed + Segments
- ✅ **SAOYUT Manager**: Xuất/nhập metadata dưới dạng file JSON đơn giản
- ✅ **Segment Manager**: Tải lên, tải xuống, xóa segments
- ✅ **Kéo thả file**: Hỗ trợ .txt, .spc, .saoyut
- ✅ **3 định dạng output**: Base64, Hex, Plaintext
- ✅ **Giao diện trực quan**: Kéo thả sắp xếp kỹ thuật
- ✅ **Segment Size tùy chỉnh**: 1KB → 100MB
- ✅ **Data ID + Browser Session**: Phân biệt dữ liệu và phiên làm việc
- ✅ **TTL tự động xóa**: Segment tự động xóa sau 1 giờ
- ✅ **Fingerprint**: Gắn segment với thiết bị
- ✅ **PWA Ready**: Có thể cài đặt như ứng dụng di động

---

## 🔧 Cấu trúc hệ thống

### Lưu đồ mã hóa (10 kỹ thuật)

```
Plaintext → R → C → E → Z → S → H → D → B → P → L → Base64
```

### Lưu đồ giải mã (10 kỹ thuật)

```
Base64 → L → P → B → D → H → S → Z → E → C → R → Plaintext
```

> **Lưu ý**: Thứ tự giải mã là đảo ngược hoàn toàn thứ tự mã hóa để đảm bảo phục hồi dữ liệu chính xác.

### Tên file Segment

```
segment_{data_id}_{browser_session_id}_{index}.dat
```

Trong đó:
- `data_id`: Danh tính cố định của dữ liệu (32 ký tự hex)
- `browser_session_id`: Phiên làm việc của trình duyệt (16 ký tự hex)
- `index`: Số thứ tự của segment

---

## 🛡️ Bảo mật và Lưu ý

### Cơ chế bảo vệ

| Biện pháp | Mô tả |
|-----------|-------|
| **Seed** | Khóa chính do người dùng tự tạo, không lưu trên server |
| **SAOYUT** | File JSON chứa metadata, chỉ người dùng có quyền truy cập |
| **Session** | Phiên tự động hết hạn sau 1 giờ |
| **Segment TTL** | Segment tự động xóa sau 1 giờ |
| **Fingerprint** | Gắn segment với thiết bị tạo ra nó |

### ⚠️ Lưu ý quan trọng

1. **Không có hệ thống nào là tuyệt đối an toàn**. SPC Encryptor Pro được phát triển cho mục đích nghiên cứu và học tập.
2. **SAOYUT và Seed là chìa khóa**. Mất SAOYUT hoặc Seed = mất dữ liệu vĩnh viễn.
3. **Segment có thời gian sống giới hạn** (1 giờ). Hãy tải về và lưu trữ cẩn thận.
4. **Sử dụng có trách nhiệm**. Tuân thủ pháp luật địa phương về bảo mật và mã hóa.
5. **Không khóa cứng theo Fingerprint**. Bạn có thể giải mã ở bất kỳ máy nào khi có đủ Seed + SAOYUT + Segments.

---

## 🚀 Hướng dẫn cài đặt và chạy

### Yêu cầu hệ thống

- Python 3.8+
- Pip (Python package manager)

### Cài đặt

```bash
# 1. Clone repository
git clone https://github.com/tonvanlam15052005-byte/SPC_Encryptor_Github.git
cd SPC_Encryptor_Github

# 2. Cài đặt dependencies
pip install -r requirements.txt

# 3. Chạy ứng dụng
python app.py
```

### Truy cập

Mở trình duyệt và truy cập: `http://localhost:5000`

---

## ☁️ Triển khai lên Render

### Bước 1: Push lên GitHub

```bash
git add .
git commit -m "SPC Encryptor Pro v2.5.5"
git push
```

### Bước 2: Tạo Web Service trên Render

1. Truy cập [render.com](https://render.com)
2. Chọn **New Web Service**
3. Kết nối với repository GitHub
4. Điền thông tin:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

### Bước 3: Deploy

Bấm **Deploy**. Render sẽ tự động build và chạy ứng dụng.

---

## 📁 Cấu trúc dự án

```
SPC_Encryptor/
├── app.py                    # Flask server (10 kỹ thuật + Segment API)
├── static/
│   ├── style.css             # CSS responsive
│   └── app.js                # JavaScript logic
├── templates/
│   └── index.html            # UI Web (Segment Manager, Kéo thả file)
├── uploads/                  # File upload tạm
├── downloads/                # File download
├── segments/                 # Lưu segments: segment_{data_id}_{session}_{index}.dat
├── requirements.txt          # Flask, Werkzeug
├── LICENSE                   # Giấy phép MIT
└── README.md                 # Tài liệu hướng dẫn
```

---

## 📝 Lịch sử phiên bản

| Phiên bản | Ngày | Thay đổi |
|-----------|------|----------|
| v1.0.0 | 01/08/2026 | Khởi tạo dự án |
| v2.0.0 | 02/08/2026 | Thêm 10 kỹ thuật R, C, E, Z, S, H, D, B, P, L |
| v2.1.0 | 03/08/2026 | Thêm SAOYUT Manager |
| v2.2.0 | 04/08/2026 | Thêm Segment Manager |
| v2.3.0 | 05/08/2026 | Thêm Data ID + Browser Session |
| v2.4.0 | 06/08/2026 | Thêm TTL & Cleanup |
| v2.5.0 | 06/08/2026 | Thêm Fingerprint + Responsive UI |
| **v2.5.5** | **07/08/2026** | **Sửa lỗi S + B tương thích. Tất cả 10 kỹ thuật hoạt động ổn định 100%** |

---

## 👨‍💻 Tác giả

| Vai trò | Tên |
|---------|-----|
| **Lý thuyết SPC** | Minvokin Grabiel Xavier (Mr.MR) |
| **Phục dựng & Phát triển** | SGM (Simple Gray Modules) & KOT/CAT STUDIOS |
| **Hiện thực hóa Web** | Cộng đồng mã nguồn mở |
| **Ngày hoàn thành** | 07/08/2026 |

---

## 📜 Giấy phép

Dự án được phân phối dưới giấy phép **MIT**. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

## ⚠️ Tuyên bố miễn trách nhiệm

> **SPC Encryptor Pro được phát triển cho mục đích nghiên cứu và học tập. Tác giả không chịu trách nhiệm đối với bất kỳ thiệt hại nào phát sinh từ việc sử dụng phần mềm này. Hãy sử dụng một cách có trách nhiệm và tuân thủ pháp luật địa phương.**

---

## 🌟 Đóng góp

Mọi đóng góp đều được hoan nghênh! Hãy tạo **Issue** hoặc **Pull Request** để cải thiện dự án.

---

## 📧 Liên hệ

- **GitHub**: [tonvanlam15052005-byte](https://github.com/tonvanlam15052005-byte)
- **Dự án**: [SPC_Encryptor_Github](https://github.com/tonvanlam15052005-byte/SPC_Encryptor_Github)

---

**⭐ Star dự án này nếu bạn thấy nó hữu ích!**
```

---

## ✅ TÓM TẮT CẬP NHẬT README

| Thay đổi | Mô tả |
|----------|-------|
| **Phiên bản** | v2.5.5 |
| **Số kỹ thuật** | 10 kỹ thuật (bao gồm S) |
| **S + B** | Đã sửa lỗi tương thích |
| **Badge version** | Cập nhật lên 2.5.5 |
| **Lưu đồ** | Bao gồm cả S |
| **Lịch sử phiên bản** | Thêm dòng v2.5.5 |
| **Trạng thái kỹ thuật** | Tất cả 10 kỹ thuật đều ✅ Ổn định |
| **Lưu ý quan trọng** | Thêm lưu ý về fingerprint không khóa cứng |

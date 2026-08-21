# spc_demo.py - Console UI (Có L)
import sys
import os
import json
from spc_core import (
    spc_encrypt_with_order,
    spc_decrypt_with_order,
    ALL_TECHNIQUES,
    generate_seed,
    base64_encode,
    base64_decode
)

current_order = list(ALL_TECHNIQUES.keys())

def print_menu():
    print("\n" + "=" * 60)
    print("🔐 SPC ENCRYPTOR - Console Edition")
    print("=" * 60)
    print("  1. Mã hóa văn bản")
    print("  2. Giải mã văn bản")
    print("  3. Xem danh sách kỹ thuật")
    print("  4. Chọn/Thay đổi thứ tự kỹ thuật")
    print("  5. Thông tin")
    print("  6. Thoát")
    print("=" * 60)

def encrypt_text():
    print("\n🔐 MÃ HÓA")
    text = input("📝 Nhập văn bản: ").strip()
    if not text:
        print("❌ Văn bản trống!")
        return
    
    seed = input("🔑 Nhập seed (Enter để tự tạo): ").strip()
    if not seed:
        seed = generate_seed()
        print(f"   Seed tự tạo: {seed}")
    
    print(f"   Sử dụng {len(current_order)} kỹ thuật: {' → '.join(current_order)}")
    
    try:
        result = spc_encrypt_with_order(text.encode('utf-8'), seed, current_order)
        encrypted_b64 = base64_encode(result["data"])
        
        print("\n✅ MÃ HÓA THÀNH CÔNG!")
        print(f"📦 Base64: {encrypted_b64}")
        print(f"🌱 Seed: {result['seed']}")
        print(f"📋 SAOYUT: {json.dumps(result['saoyut'], indent=2)}")
        
        # Kiểm tra có kỹ thuật L không
        has_L = any(tech["name"] == "L" for tech in result["saoyut"]["techniques"])
        if has_L:
            print("\n📦 KỸ THUẬT L PHÁT HIỆN!")
            for tech in result["saoyut"]["techniques"]:
                if tech["name"] == "L":
                    print(f"   Số segments: {tech['metadata']['num_segments']}")
                    print(f"   Kích thước segments: {tech['metadata']['segment_sizes']}")
                    print("   ⚠️ Cần lưu các segment riêng biệt!")
        
        save = input("\n💾 Lưu kết quả? (y/n): ").strip().lower()
        if save == 'y':
            filename = input("📁 Tên file (không cần đuôi): ").strip()
            if filename:
                with open(f"{filename}.b64.txt", 'w') as f:
                    f.write(encrypted_b64)
                with open(f"{filename}.saoyut", 'w') as f:
                    json.dump(result['saoyut'], f, indent=2)
                with open(f"{filename}.seed.txt", 'w') as f:
                    f.write(result['seed'])
                print(f"✅ Đã lưu: {filename}.b64.txt, {filename}.saoyut, {filename}.seed.txt")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def decrypt_text():
    print("\n🔓 GIẢI MÃ")
    b64 = input("📦 Nhập Base64: ").strip()
    if not b64:
        print("❌ Dữ liệu trống!")
        return
    
    seed = input("🔑 Nhập seed: ").strip()
    if not seed:
        print("❌ Seed là bắt buộc!")
        return
    
    saoyut_path = input("📁 Đường dẫn file SAOYUT: ").strip()
    if not saoyut_path:
        print("❌ SAOYUT là bắt buộc!")
        return
    
    try:
        with open(saoyut_path, 'r') as f:
            saoyut_data = json.load(f)
        
        encrypted = base64_decode(b64)
        decrypted = spc_decrypt_with_order(encrypted, saoyut_data, seed, current_order)
        text = decrypted.decode('utf-8', errors='replace')
        
        print("\n✅ GIẢI MÃ THÀNH CÔNG!")
        print(f"📝 Văn bản: {text}")
    except FileNotFoundError as e:
        print(f"❌ Lỗi: {e}")
        print("💡 Kiểm tra lại các segment đã được lưu chưa!")
    except ValueError as e:
        print(f"❌ Lỗi: {e}")
        print("💡 Segment bị lỗi hoặc thiếu!")
    except Exception as e:
        print(f"❌ Lỗi: {e}")

def print_techniques():
    print("\n📋 Danh sách 10 kỹ thuật SPC:")
    print("  1. R  - Header Removal")
    print("  2. C  - Cut & Swap")
    print("  3. E  - Enigma")
    print("  4. Z  - Zip Hiding")
    print("  5. S  - Sharding")
    print("  6. H  - Header Masking")
    print("  7. D  - Double Fake")
    print("  8. B  - Hashing Chain")
    print("  9. P  - RAM-only")
    print(" 10. L  - Low Storage Sharefile")

def change_order():
    global current_order
    print("\n🔄 THAY ĐỔI THỨ TỰ KỸ THUẬT")
    print(f"Hiện tại: {' → '.join(current_order)}")
    print("\nNhập thứ tự mới (các ký tự cách nhau bằng dấu cách)")
    print(f"Các kỹ thuật có sẵn: {', '.join(ALL_TECHNIQUES.keys())}")
    
    new_order = input("📝 Thứ tự mới: ").strip().upper().split()
    
    valid = True
    for tech in new_order:
        if tech not in ALL_TECHNIQUES:
            print(f"❌ Kỹ thuật '{tech}' không tồn tại!")
            valid = False
            break
    
    if valid and new_order:
        current_order = new_order
        print(f"✅ Đã cập nhật: {' → '.join(current_order)}")
    else:
        print("⚠️ Giữ nguyên thứ tự cũ")

def show_info():
    def factorial(n):
        result = 1
        for i in range(1, n + 1):
            result *= i
        return result
    
    print("\n📊 THÔNG TIN HỆ THỐNG")
    print(f"  - Số kỹ thuật: {len(ALL_TECHNIQUES)}")
    print(f"  - Kỹ thuật hiện có: {', '.join(ALL_TECHNIQUES.keys())}")
    print(f"  - Thứ tự hiện tại: {' → '.join(current_order)}")
    print(f"  - Tổng số tổ hợp có thể: {len(ALL_TECHNIQUES)}! = {factorial(len(ALL_TECHNIQUES))}")
    print("  - Phiên bản: SPC 2.1 (10 techniques - Có Low Storage)")
    print("\n📦 KỸ THUẬT L - LOW STORAGE SHAREFILE:")
    print("  - Chia dữ liệu thành các segment 1KB")
    print("  - Lưu từng segment riêng biệt")
    print("  - Khi giải mã cần có TẤT CẢ segments")

if __name__ == "__main__":
    while True:
        print_menu()
        choice = input("👉 Chọn: ").strip()
        
        if choice == '1':
            encrypt_text()
        elif choice == '2':
            decrypt_text()
        elif choice == '3':
            print_techniques()
        elif choice == '4':
            change_order()
        elif choice == '5':
            show_info()
        elif choice == '6':
            print("👋 Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ!")
        
        input("\nNhấn Enter để tiếp tục...")
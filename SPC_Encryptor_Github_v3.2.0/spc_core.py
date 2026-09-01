# spc_core.py - Core engine 10 techniques (Đã thêm L)
import hashlib
import os
import random
import json
import base64

# ============================================================
# SAOYUT MANAGER
# ============================================================
class SAOYUT:
    def __init__(self, seed):
        self.seed = seed
        self.data = {
            "seed_hash": hashlib.sha256(seed.encode()).hexdigest(),
            "techniques": []
        }
    
    def add_technique(self, name, metadata):
        self.data["techniques"].append({"name": name, "metadata": metadata})
    
    def get_technique_by_name(self, name):
        for tech in self.data["techniques"]:
            if tech["name"] == name:
                return tech["metadata"]
        return {}
    
    def export(self):
        return self.data

# ============================================================
# R - Header Removal
# ============================================================
def technique_R(data, saoyut, reverse=False):
    if not reverse:
        header_size = min(16, len(data))
        header = data[:header_size]
        body = data[header_size:]
        saoyut.add_technique("R", {
            "header": header.hex(),
            "header_size": header_size,
            "original_size": len(data)
        })
        return body
    else:
        meta = saoyut.get_technique_by_name("R")
        if not meta:
            raise ValueError("Missing R metadata!")
        header = bytes.fromhex(meta["header"])
        return header + data

# ============================================================
# C - Cut & Swap
# ============================================================
def technique_C(data, saoyut, reverse=False):
    if not reverse:
        mid = len(data) // 2
        first = data[:mid]
        second = data[mid:]
        saoyut.add_technique("C", {
            "cut_point": mid,
            "first_len": len(first),
            "second_len": len(second)
        })
        return second + first
    else:
        meta = saoyut.get_technique_by_name("C")
        if not meta:
            raise ValueError("Missing C metadata!")
        second_len = meta["second_len"]
        second = data[:second_len]
        first = data[second_len:]
        return first + second

# ============================================================
# E - Enigma
# ============================================================
def technique_E(data, saoyut, reverse=False):
    key = saoyut.seed.encode()
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = data[i] ^ key[i % len(key)]
    if not reverse:
        saoyut.add_technique("E", {})
    return bytes(result)

# ============================================================
# Z - Zip Hiding
# ============================================================
def technique_Z(data, saoyut, reverse=False):
    if not reverse:
        fake = b"TXT_HEADER:"
        saoyut.add_technique("Z", {
            "fake_header": fake.hex(),
            "fake_len": len(fake)
        })
        return fake + data
    else:
        meta = saoyut.get_technique_by_name("Z")
        if not meta:
            raise ValueError("Missing Z metadata!")
        fake_len = meta.get("fake_len", 11)
        return data[fake_len:]

# ============================================================
# S - Sharding (BẢN CHÍNH XÁC - LƯU ĐÚNG METADATA)
# ============================================================
def technique_S(data, saoyut, reverse=False):
    if not reverse:
        # === MÃ HÓA ===
        num_shards = 4
        total_size = len(data)
        shard_size = total_size // num_shards
        
        # Chia thành 4 mảnh
        shards = []
        for i in range(num_shards):
            start = i * shard_size
            if i == num_shards - 1:
                end = total_size
            else:
                end = start + shard_size
            shards.append(data[start:end])
        
        # Lưu kích thước từng mảnh
        shard_sizes = [len(s) for s in shards]
        
        # Tạo shuffle_map ngẫu nhiên
        shuffle_map = list(range(num_shards))
        random.shuffle(shuffle_map)
        
        # Ghép theo thứ tự mới
        shuffled_data = b''
        for idx in shuffle_map:
            shuffled_data += shards[idx]
        
        # Lưu metadata đầy đủ
        saoyut.add_technique("S", {
            "num_shards": num_shards,
            "shard_sizes": shard_sizes,
            "shuffle_map": shuffle_map,
            "total_size": total_size
        })
        
        return shuffled_data
        
    else:
        # === GIẢI MÃ ===
        meta = saoyut.get_technique_by_name("S")
        if not meta:
            raise ValueError("Missing S metadata!")
        
        num_shards = meta["num_shards"]
        shard_sizes = meta["shard_sizes"]
        shuffle_map = meta["shuffle_map"]
        total_size = meta["total_size"]
        
        # ✅ BƯỚC 1: Tách dữ liệu theo shuffle_map
        shards_in_shuffled_order = []
        pos = 0
        for shard_idx in shuffle_map:
            if shard_idx < len(shard_sizes):
                size = shard_sizes[shard_idx]
                shards_in_shuffled_order.append(data[pos:pos+size])
                pos += size
            else:
                # Fallback nếu shard_idx không hợp lệ
                shards_in_shuffled_order.append(b'')
        
        # ✅ BƯỚC 2: Khôi phục thứ tự gốc
        restored = [b''] * num_shards  # Khởi tạo với bytes rỗng thay vì None
        
        for new_pos, old_pos in enumerate(shuffle_map):
            if new_pos < len(shards_in_shuffled_order) and old_pos < num_shards:
                restored[old_pos] = shards_in_shuffled_order[new_pos]
        
        # ✅ BƯỚC 3: Ghép lại
        result = b''.join(restored)  # join an toàn với bytes
        
        # ✅ Kiểm tra
        if len(result) != total_size:
            print(f"[S] Warning: Size mismatch! Expected: {total_size}, Got: {len(result)}")
            # Nếu mismatch, pad hoặc trim
            if len(result) < total_size:
                result += b'\x00' * (total_size - len(result))
            else:
                result = result[:total_size]
        
        return result

# ============================================================
# H - Header Masking
# ============================================================
def technique_H(data, saoyut, reverse=False):
    if not reverse:
        key = bytes([random.randint(0, 255) for _ in range(16)])
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        saoyut.add_technique("H", {"xor_key": key.hex()})
        return bytes(result)
    else:
        meta = saoyut.get_technique_by_name("H")
        if not meta:
            raise ValueError("Missing H metadata!")
        key = bytes.fromhex(meta["xor_key"])
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        return bytes(result)

# ============================================================
# D - Double Fake
# ============================================================
def technique_D(data, saoyut, reverse=False):
    if not reverse:
        fake1 = b"PK\x03\x04"
        fake2 = b"\x89PNG\r\n\x1a\n"
        saoyut.add_technique("D", {
            "fake1": fake1.hex(),
            "fake2": fake2.hex(),
            "fake1_len": len(fake1),
            "fake2_len": len(fake2),
            "total_fake_len": len(fake1) + len(fake2)
        })
        return fake1 + fake2 + data
    else:
        meta = saoyut.get_technique_by_name("D")
        if not meta:
            raise ValueError("Missing D metadata!")
        total_fake_len = meta.get("total_fake_len", 12)
        return data[total_fake_len:]

# ============================================================
# B - Hashing Chain
# ============================================================
def technique_B(data, saoyut, reverse=False):
    password = saoyut.seed
    
    # Tạo key từ seed
    hashed = password
    for _ in range(100):
        hashed = hashlib.sha256(hashed.encode()).hexdigest()
    key = hashed[:32].encode()
    
    if not reverse:
        # === MÃ HÓA ===
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        
        # LƯU THÔNG TIN
        saoyut.add_technique("B", {
            "password_hash": hashed,
            "iterations": 100,
            "key_length": len(key)
        })
        
        print(f"[B] Encrypt: {len(data)} bytes")
        return bytes(result)
        
    else:
        # === GIẢI MÃ ===
        meta = saoyut.get_technique_by_name("B")
        if not meta:
            raise ValueError("Missing B metadata!")
        
        # Dùng hash từ metadata hoặc tính lại
        stored_hash = meta.get("password_hash", "")
        if stored_hash:
            key = stored_hash[:32].encode()
        else:
            # Fallback
            hashed = password
            for _ in range(100):
                hashed = hashlib.sha256(hashed.encode()).hexdigest()
            key = hashed[:32].encode()
        
        # XOR để phục hồi
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        
        print(f"[B] Decrypt: {len(data)} bytes")
        return bytes(result)

# ============================================================
# P - RAM-only
# ============================================================
def technique_P(data, saoyut, reverse=False):
    if not reverse:
        saoyut.add_technique("P", {"ram_only": True})
    return data

# ============================================================
# L - Low Storage Sharefile
# ============================================================
def technique_L(data, saoyut, reverse=False):
    if not reverse:
        # MÃ HÓA: Chia thành segments và lưu metadata
        segment_size = 1024  # 1KB
        segments = []
        segment_hashes = []
        
        for i in range(0, len(data), segment_size):
            segment = data[i:i+segment_size]
            segments.append(segment)
            segment_hashes.append(hashlib.sha256(segment).hexdigest())
        
        saoyut.add_technique("L", {
            "num_segments": len(segments),
            "segment_sizes": [len(s) for s in segments],
            "segment_hashes": segment_hashes,
            "segment_size": segment_size
        })
        
        # Trong core, chỉ trả về dữ liệu gốc (không lưu segments)
        # Việc lưu segments sẽ do app.py xử lý
        return data
    else:
        # GIẢI MÃ: Đọc metadata và ghép segments
        meta = saoyut.get_technique_by_name("L")
        if not meta:
            raise ValueError("Missing L metadata!")
        
        segment_sizes = meta.get("segment_sizes", [])
        segment_hashes = meta.get("segment_hashes", [])
        num_segments = meta.get("num_segments", 0)
        
        if not segment_sizes:
            return data
        
        # Core chỉ trả về metadata, việc đọc segments do app.py xử lý
        # Vì core không có quyền truy cập thư mục segments
        return data

# ============================================================
# DANH SÁCH 10 KỸ THUẬT
# ============================================================
ALL_TECHNIQUES = {
    "R": technique_R,
    "C": technique_C,
    "E": technique_E,
    "Z": technique_Z,
    "S": technique_S,
    "H": technique_H,
    "D": technique_D,
    "B": technique_B,
    "P": technique_P,
    "L": technique_L
}

# ============================================================
# SPC ENGINE
# ============================================================
def spc_encrypt_with_order(data, seed, technique_order):
    if not seed:
        seed = hashlib.sha256(os.urandom(32)).hexdigest()
    
    saoyut = SAOYUT(seed)
    result = data
    
    for name in technique_order:
        if name in ALL_TECHNIQUES:
            result = ALL_TECHNIQUES[name](result, saoyut)
    
    return {
        "data": result,
        "saoyut": saoyut.export(),
        "seed": seed
    }

def spc_decrypt_with_order(data, saoyut_data, seed, technique_order):
    saoyut = SAOYUT(seed)
    saoyut.data = saoyut_data
    result = data
    
    for name in reversed(technique_order):
        if name in ALL_TECHNIQUES:
            result = ALL_TECHNIQUES[name](result, saoyut, reverse=True)
    
    return result

# ============================================================
# UTILITY
# ============================================================
def generate_seed():
    return hashlib.sha256(os.urandom(32)).hexdigest()

def base64_encode(data):
    return base64.b64encode(data).decode('utf-8')

def base64_decode(data):
    return base64.b64decode(data)

# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 SPC CORE TEST - 10 TECHNIQUES (Có L)")
    print("=" * 60)
    
    test_cases = [
        b"kachikochi",
        b"kkk",
        b"Hello",
        b"Hello World!",
        b"Hello World! This is SPC 10 Techniques!"
    ]
    
    all_passed = True
    for original in test_cases:
        print(f"\n📝 Original: {original} ({len(original)} bytes)")
        
        result = spc_encrypt_with_order(original, "", list(ALL_TECHNIQUES.keys()))
        encrypted = result["data"]
        seed = result["seed"]
        saoyut = result["saoyut"]
        
        # Kiểm tra có kỹ thuật L không
        has_L = any(tech["name"] == "L" for tech in saoyut["techniques"])
        print(f"   Has L technique: {has_L}")
        
        decrypted = spc_decrypt_with_order(encrypted, saoyut, seed, list(ALL_TECHNIQUES.keys()))
        
        if original == decrypted:
            print(f"   ✅ SUCCESS! {decrypted}")
        else:
            print(f"   ❌ FAILED!")
            print(f"      Original:  {original}")
            print(f"      Decrypted: {decrypted}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! (10 techniques)")
    else:
        print("⚠️ SOME TESTS FAILED!")
    print("=" * 60)

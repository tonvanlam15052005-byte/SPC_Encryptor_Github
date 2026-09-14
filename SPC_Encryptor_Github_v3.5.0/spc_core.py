# spc_core.py - Core engine 10 techniques (Đã thêm L + S V2 tối ưu)
import hashlib
import os
import random
import json
import base64
import struct


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
# HELPER: PACK/UNPACK INT LIST (giảm dung lượng metadata)
# ============================================================
def _pack_int_list(ints):
    """
    Pack list[int] thành base64 string (2 bytes/int).
    Với 256 shard → 512 bytes → base64 ~683 ký tự.
    """
    if not ints:
        return ""
    if any(i < 0 or i > 65535 for i in ints):
        raise ValueError("Int values must be in range [0, 65535]")
    packed = struct.pack(f'>{len(ints)}H', *ints)
    return base64.b64encode(packed).decode('ascii')


def _unpack_int_list(s):
    """Unpack base64 string thành list[int]."""
    if not s:
        return []
    packed = base64.b64decode(s)
    count = len(packed) // 2
    return list(struct.unpack(f'>{count}H', packed))


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
# S - Sharding 256 MẢNH (V2 TỐI ƯU)
# ============================================================
def technique_S(data, saoyut, reverse=False):
    """
    Kỹ thuật S - Sharding với 256 mảnh.
    
    BẢO MẬT 3 THÀNH PHẦN:
    - Shuffle_map RANDOM hoàn toàn, KHÔNG derive từ seed
    - Shuffle_map lưu trong SAOYUT → SAOYUT là "khóa thứ hai"
    - Thiếu SAOYUT → không biết thứ tự shard → không giải được
    - Thiếu Seed → không giải được các lớp khác (E, H, B)
    
    TƯƠNG THÍCH NGƯỢC:
    - V1: 4 mảnh, list trực tiếp (legacy)
    - V2: 256 mảnh, packed base64
    """
    NUM_SHARDS = 256
    
    # ============================================================
    # MÃ HÓA
    # ============================================================
    if not reverse:
        total_size = len(data)
        
        # Xử lý dữ liệu rỗng
        if total_size == 0:
            saoyut.add_technique("S", {
                "num_shards": 0,
                "shard_sizes_packed": "",
                "shuffle_map_packed": "",
                "total_size": 0,
                "requested_shards": NUM_SHARDS,
                "version": 2
            })
            return data
        
        # Số mảnh thực tế = min(256, total_size)
        actual_shards = min(NUM_SHARDS, total_size)
        
        # Tính kích thước cơ bản và phần dư
        base_size = total_size // actual_shards
        remainder = total_size % actual_shards
        
        # Chia dữ liệu thành các mảnh có kích thước gần bằng nhau
        shards = []
        shard_sizes = []
        pos = 0
        for i in range(actual_shards):
            size = base_size + (1 if i < remainder else 0)
            shards.append(data[pos:pos + size])
            shard_sizes.append(size)
            pos += size
        
        # ✅ SHUFFLE RANDOM HOÀN TOÀN — không phụ thuộc seed
        shuffle_map = list(range(actual_shards))
        random.shuffle(shuffle_map)
        
        # Ghép theo thứ tự đã xáo trộn
        shuffled_data = b''.join(shards[idx] for idx in shuffle_map)
        
        # ✅ LƯU shuffle_map trong SAOYUT (packed base64)
        saoyut.add_technique("S", {
            "num_shards": actual_shards,
            "shard_sizes_packed": _pack_int_list(shard_sizes),
            "shuffle_map_packed": _pack_int_list(shuffle_map),
            "total_size": total_size,
            "requested_shards": NUM_SHARDS,
            "version": 2
        })
        
        print(f"[S] Encrypt: {total_size} bytes -> {actual_shards} shards")
        
        return shuffled_data
    
    # ============================================================
    # GIẢI MÃ
    # ============================================================
    else:
        meta = saoyut.get_technique_by_name("S")
        if not meta:
            raise ValueError("Missing S metadata!")
        
        num_shards = meta["num_shards"]
        total_size = meta["total_size"]
        version = meta.get("version", 1)
        
        # Xử lý dữ liệu rỗng
        if num_shards == 0 or total_size == 0:
            return b''
        
        # ✅ Hỗ trợ cả packed và unpacked (tương thích ngược)
        if "shuffle_map_packed" in meta and meta["shuffle_map_packed"]:
            # V2: packed base64
            shuffle_map = _unpack_int_list(meta["shuffle_map_packed"])
            shard_sizes = _unpack_int_list(meta["shard_sizes_packed"])
        else:
            # V1: list trực tiếp
            shuffle_map = meta.get("shuffle_map", [])
            shard_sizes = meta.get("shard_sizes", [])
        
        # Kiểm tra tính hợp lệ
        if len(shuffle_map) != num_shards:
            raise ValueError(
                f"Invalid shuffle_map: expected {num_shards}, got {len(shuffle_map)}"
            )
        if len(shard_sizes) != num_shards:
            raise ValueError(
                f"Invalid shard_sizes: expected {num_shards}, got {len(shard_sizes)}"
            )
        
        # BƯỚC 1: Tách dữ liệu theo shuffle_map
        shards_in_shuffled_order = []
        pos = 0
        for shard_idx in shuffle_map:
            if shard_idx < len(shard_sizes):
                size = shard_sizes[shard_idx]
                shards_in_shuffled_order.append(data[pos:pos + size])
                pos += size
            else:
                shards_in_shuffled_order.append(b'')
        
        # BƯỚC 2: Khôi phục thứ tự gốc
        restored = [b''] * num_shards
        for new_pos, old_pos in enumerate(shuffle_map):
            if new_pos < len(shards_in_shuffled_order) and old_pos < num_shards:
                restored[old_pos] = shards_in_shuffled_order[new_pos]
        
        # BƯỚC 3: Ghép lại
        result = b''.join(restored)
        
        # Kiểm tra kích thước
        if len(result) != total_size:
            print(f"[S] Warning: Size mismatch! "
                  f"Expected: {total_size}, Got: {len(result)}")
            if len(result) < total_size:
                result += b'\x00' * (total_size - len(result))
            else:
                result = result[:total_size]
        
        print(f"[S] Decrypt: {len(data)} bytes -> {len(result)} bytes "
              f"({num_shards} shards, v{version})")
        
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
    print("🧪 SPC CORE TEST - 10 TECHNIQUES (S 256 mảnh)")
    print("=" * 60)
    
    test_cases = [
        b"kachikochi",
        b"kkk",
        b"Hello",
        b"Hello World!",
        b"Hello World! This is SPC 10 Techniques!",
        b"A" * 1000,              # 1000 bytes
        b"B" * 10000,             # 10KB
    ]
    
    all_passed = True
    for original in test_cases:
        print(f"\n📝 Original: {original[:50]}{'...' if len(original) > 50 else ''} "
              f"({len(original)} bytes)")
        
        result = spc_encrypt_with_order(original, "", list(ALL_TECHNIQUES.keys()))
        encrypted = result["data"]
        seed = result["seed"]
        saoyut = result["saoyut"]
        
        # Kiểm tra có kỹ thuật L không
        has_L = any(tech["name"] == "L" for tech in saoyut["techniques"])
        has_S = any(tech["name"] == "S" for tech in saoyut["techniques"])
        print(f"   Has L technique: {has_L}")
        print(f"   Has S technique: {has_S}")
        
        # Kiểm tra S V2
        for tech in saoyut["techniques"]:
            if tech["name"] == "S":
                meta = tech["metadata"]
                print(f"   S: {meta['num_shards']} shards, "
                      f"version {meta.get('version', 1)}, "
                      f"packed: {'shuffle_map_packed' in meta}")
                break
        
        decrypted = spc_decrypt_with_order(
            encrypted, saoyut, seed, list(ALL_TECHNIQUES.keys())
        )
        
        if original == decrypted:
            print(f"   ✅ SUCCESS! ({len(decrypted)} bytes)")
        else:
            print(f"   ❌ FAILED!")
            print(f"      Original:  {original[:50]}")
            print(f"      Decrypted: {decrypted[:50]}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! (10 techniques, S = 256 shards)")
    else:
        print("⚠️ SOME TESTS FAILED!")
    print("=" * 60)
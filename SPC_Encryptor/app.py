# app.py - SPC Encryptor Pro v2.3 (Session ID cho Segment)
from flask import Flask, render_template, request, jsonify, send_file
import hashlib
import os
import random
import json
import base64
import traceback
import zipfile
import io
import time
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['SEGMENT_FOLDER'] = 'segments'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['DEFAULT_SEGMENT_SIZE'] = 1024 * 1024  # 1MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SEGMENT_FOLDER'], exist_ok=True)

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
# S - Sharding
# ============================================================
def technique_S(data, saoyut, reverse=False):
    if not reverse:
        num_shards = 4
        shard_size = len(data) // num_shards
        shards = []
        for i in range(num_shards):
            start = i * shard_size
            end = start + shard_size if i < num_shards - 1 else len(data)
            shards.append(data[start:end])
        
        indices = list(range(num_shards))
        random.shuffle(indices)
        shuffled = [shards[i] for i in indices]
        
        saoyut.add_technique("S", {
            "num_shards": num_shards,
            "shard_sizes": [len(s) for s in shards],
            "shuffle_order": indices
        })
        return b''.join(shuffled)
    else:
        meta = saoyut.get_technique_by_name("S")
        if not meta:
            raise ValueError("Missing S metadata!")
        
        shuffle_order = meta.get("shuffle_order", [])
        shard_sizes = meta.get("shard_sizes", [])
        
        if not shuffle_order or not shard_sizes:
            return data
        
        shards = []
        pos = 0
        for size in shard_sizes:
            shards.append(data[pos:pos+size])
            pos += size
        
        original_order = [None] * len(shards)
        for new_pos, old_pos in enumerate(shuffle_order):
            if old_pos < len(shards):
                original_order[old_pos] = shards[new_pos]
        
        result = bytearray()
        for shard in original_order:
            if shard:
                result.extend(shard)
        
        return bytes(result)

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
    for _ in range(100):
        password = hashlib.sha256(password.encode()).hexdigest()
    password = password[:32]
    key = password.encode()
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = data[i] ^ key[i % len(key)]
    if not reverse:
        saoyut.add_technique("B", {
            "password_hash": hashlib.sha256(password.encode()).hexdigest()
        })
    return bytes(result)

# ============================================================
# P - RAM-only
# ============================================================
def technique_P(data, saoyut, reverse=False):
    if not reverse:
        saoyut.add_technique("P", {"ram_only": True})
    return data

# ============================================================
# L - Low Storage Sharefile (CÓ SESSION ID)
# ============================================================
def technique_L(data, saoyut, reverse=False):
    if not reverse:
        # Tạo session ID duy nhất
        session_id = hashlib.md5(f"{saoyut.seed}{time.time()}{random.randint(1, 999999)}".encode()).hexdigest()[:8]
        
        segment_size = app.config['DEFAULT_SEGMENT_SIZE']
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
            "segment_size": segment_size,
            "session_id": session_id
        })
        
        segment_dir = app.config['SEGMENT_FOLDER']
        for i, segment in enumerate(segments):
            segment_path = os.path.join(segment_dir, f"segment_{session_id}_{i+1}.dat")
            with open(segment_path, 'wb') as f:
                f.write(segment)
        
        return data
    else:
        meta = saoyut.get_technique_by_name("L")
        if not meta:
            raise ValueError("Missing L metadata!")
        
        segment_sizes = meta.get("segment_sizes", [])
        segment_hashes = meta.get("segment_hashes", [])
        num_segments = meta.get("num_segments", 0)
        session_id = meta.get("session_id", "")
        
        if not segment_sizes:
            return data
        
        segment_dir = app.config['SEGMENT_FOLDER']
        segments = []
        
        for i in range(num_segments):
            segment_path = os.path.join(segment_dir, f"segment_{session_id}_{i+1}.dat")
            if not os.path.exists(segment_path):
                raise FileNotFoundError(f"Missing segment {i+1}: {segment_path}")
            
            with open(segment_path, 'rb') as f:
                segment_data = f.read()
            
            expected_size = segment_sizes[i] if i < len(segment_sizes) else len(segment_data)
            if len(segment_data) != expected_size:
                raise ValueError(f"Segment {i+1} size mismatch")
            
            if i < len(segment_hashes):
                computed_hash = hashlib.sha256(segment_data).hexdigest()
                if computed_hash != segment_hashes[i]:
                    raise ValueError(f"Segment {i+1} checksum mismatch!")
            
            segments.append(segment_data)
        
        return b''.join(segments)

# ============================================================
# DANH SÁCH KỸ THUẬT
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
# SEGMENT API
# ============================================================

@app.route('/segments/list', methods=['GET'])
def list_segments():
    try:
        segment_dir = app.config['SEGMENT_FOLDER']
        segments = []
        
        for filename in os.listdir(segment_dir):
            if filename.startswith('segment_') and filename.endswith('.dat'):
                filepath = os.path.join(segment_dir, filename)
                segments.append({
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'path': filepath
                })
        
        segments.sort(key=lambda x: x['filename'])
        
        return jsonify({
            'success': True,
            'segments': segments,
            'count': len(segments)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/segments/upload', methods=['POST'])
def upload_segments():
    try:
        if 'segments' not in request.files:
            return jsonify({'success': False, 'error': 'No segments uploaded'}), 400
        
        files = request.files.getlist('segments')
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        segment_dir = app.config['SEGMENT_FOLDER']
        uploaded = []
        
        for file in files:
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(segment_dir, filename)
                file.save(filepath)
                uploaded.append(filename)
        
        return jsonify({
            'success': True,
            'uploaded': uploaded,
            'count': len(uploaded)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/segments/clear', methods=['POST'])
def clear_segments():
    try:
        segment_dir = app.config['SEGMENT_FOLDER']
        for filename in os.listdir(segment_dir):
            if filename.startswith('segment_') and filename.endswith('.dat'):
                os.remove(os.path.join(segment_dir, filename))
        
        return jsonify({'success': True, 'message': 'All segments cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/segments/download/<int:segment_id>', methods=['GET'])
def download_segment(segment_id):
    try:
        segment_dir = app.config['SEGMENT_FOLDER']
        # Tìm file segment theo ID (có thể có session_id)
        for filename in os.listdir(segment_dir):
            if filename.endswith(f"_{segment_id}.dat"):
                segment_path = os.path.join(segment_dir, filename)
                return send_file(segment_path, as_attachment=True, download_name=filename)
        return jsonify({'success': False, 'error': 'Segment not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/segments/download-all', methods=['POST'])
def download_all_segments():
    try:
        data = request.json
        num_segments = data.get('num_segments', 0)
        session_id = data.get('session_id', '')
        
        if num_segments == 0:
            return jsonify({'success': False, 'error': 'No segments specified'}), 400
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(num_segments):
                if session_id:
                    segment_path = os.path.join(app.config['SEGMENT_FOLDER'], f"segment_{session_id}_{i+1}.dat")
                else:
                    # Fallback: tìm bất kỳ segment nào có số thứ tự
                    segment_path = None
                    for filename in os.listdir(app.config['SEGMENT_FOLDER']):
                        if filename.endswith(f"_{i+1}.dat"):
                            segment_path = os.path.join(app.config['SEGMENT_FOLDER'], filename)
                            break
                
                if segment_path and os.path.exists(segment_path):
                    zip_file.write(segment_path, f"segment_{i+1}.dat")
        
        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name="segments.zip")
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html', techniques=list(ALL_TECHNIQUES.keys()))

@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        data = request.json
        text = data.get('text', '')
        seed = data.get('seed', '')
        technique_order = data.get('order', list(ALL_TECHNIQUES.keys()))
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        text_bytes = text.encode('utf-8')
        result = spc_encrypt_with_order(text_bytes, seed, technique_order)
        
        encrypted_b64 = base64.b64encode(result["data"]).decode('utf-8')
        encrypted_hex = result["data"].hex()
        
        segments_info = None
        for tech in result["saoyut"]["techniques"]:
            if tech["name"] == "L":
                segments_info = tech["metadata"]
                break
        
        return jsonify({
            'success': True,
            'encrypted_b64': encrypted_b64,
            'encrypted_hex': encrypted_hex,
            'seed': result["seed"],
            'saoyut': result["saoyut"],
            'order': technique_order,
            'segments': segments_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        data = request.json
        encrypted_b64 = data.get('encrypted_b64', '')
        seed = data.get('seed', '')
        saoyut_data = data.get('saoyut', {})
        technique_order = data.get('order', list(ALL_TECHNIQUES.keys()))
        
        if not encrypted_b64:
            return jsonify({'success': False, 'error': 'No encrypted data provided'}), 400
        
        if not seed:
            return jsonify({'success': False, 'error': 'Seed is required!'}), 400
        
        if not saoyut_data or not saoyut_data.get('techniques'):
            return jsonify({'success': False, 'error': 'SAOYUT is required!'}), 400
        
        encrypted_data = base64.b64decode(encrypted_b64)
        
        try:
            decrypted = spc_decrypt_with_order(encrypted_data, saoyut_data, seed, technique_order)
            decrypted_text = decrypted.decode('utf-8', errors='replace')
            
            return jsonify({
                'success': True,
                'decrypted_text': decrypted_text,
                'decrypted_hex': decrypted.hex(),
                'decrypted_size': len(decrypted)
            })
        except FileNotFoundError as e:
            return jsonify({
                'success': False,
                'error': f'Missing segment file: {str(e)}',
                'hint': 'Please upload all required segment files!'
            }), 400
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'hint': 'Segment checksum or size mismatch!'
            }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Decryption failed: {str(e)}',
                'hint': 'Check if seed, SAOYUT, and technique order match the original encryption!'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'filename': filename,
            'content': content,
            'size': os.path.getsize(filepath)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save', methods=['POST'])
def save_file():
    try:
        data = request.json
        content = data.get('content', '')
        filename = data.get('filename', 'download.txt')
        filetype = data.get('type', 'text')
        
        filename = secure_filename(filename)
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        if filetype == 'base64':
            try:
                binary_data = base64.b64decode(content)
                with open(filepath, 'wb') as f:
                    f.write(binary_data)
            except:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/settings/segment-size', methods=['POST'])
def set_segment_size():
    try:
        data = request.json
        size = data.get('size', 1024 * 1024)
        
        if size < 1024:
            size = 1024
        elif size > 100 * 1024 * 1024:
            size = 100 * 1024 * 1024
        
        app.config['DEFAULT_SEGMENT_SIZE'] = size
        
        return jsonify({
            'success': True,
            'segment_size': size,
            'message': f'Segment size set to {size} bytes'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/settings/segment-size', methods=['GET'])
def get_segment_size():
    try:
        return jsonify({
            'success': True,
            'segment_size': app.config['DEFAULT_SEGMENT_SIZE']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
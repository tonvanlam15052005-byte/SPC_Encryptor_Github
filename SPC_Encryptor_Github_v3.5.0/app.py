# app.py - SPC Encryptor Pro v3.5.0
# ============================================================
# SECURITY-FIRST DESIGN
# ============================================================
# NGUYÊN TẮC BẢO MẬT:
#   1. Seed phải khớp CHÍNH XÁC với seed_hash — KHÔNG thử biến thể
#   2. Session binding có hiệu lực thật — không tự thêm session
#   3. HMAC-SHA256 signature cho SAOYUT V3 — chống giả mạo
#   4. Version whitelist — chống downgrade attack
#   5. Constant-time comparison cho mọi so sánh hash/signature
#
# HỖ TRỢ GIẢI MÃ:
#   - V1 (2.6.0):   4 shard list, seed thuần
#   - V1 (3.2.0):   4 shard list, seed thuần (metadata session chỉ tham khảo)
#   - V2 (3.4.0):   256 shard packed, seed có thể có session
#   - V3 (3.5.0+):  256 shard packed + HMAC + session binding
#
# CÁCH USER NHẬP SEED:
#   - SAOYUT bind session → nhập <seed>_<session_id>
#   - SAOYUT không bind   → nhập <seed>
#   - Hệ thống KHÔNG tự đoán, KHÔNG tự thêm session
# ============================================================

from flask import Flask, render_template, request, jsonify, send_file, session
import hashlib
import os
import random
import json
import base64
import traceback
import zipfile
import io
import time
import threading
import hmac
import secrets
import struct
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ============================================================
# VERSION INFO
# ============================================================
SPC_VERSION = "3.5.0"

# ============================================================
# CẤU HÌNH
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['DOWNLOAD_FOLDER'] = os.path.join(BASE_DIR, 'downloads')
app.config['SEGMENT_FOLDER'] = os.path.join(BASE_DIR, 'segments')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['DEFAULT_SEGMENT_SIZE'] = 1024 * 1024
app.config['SESSION_TIMEOUT'] = 3600

# Tạo thư mục
for folder in ['UPLOAD_FOLDER', 'DOWNLOAD_FOLDER', 'SEGMENT_FOLDER']:
    path = app.config[folder]
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"[INIT] Created folder: {path}")

# ============================================================
# SAOYUT VERSION & INTEGRITY CONFIG
# ============================================================
SAOYUT_CURRENT_VERSION = 3
SAOYUT_SUPPORTED_VERSIONS = [1, 2, 3]
SAOYUT_REQUIRE_SIGNATURE_FROM = 3

# Dấu hiệu nhận diện SAOYUT V3 (chống downgrade attack)
SAOYUT_V3_INDICATORS = [
    'integrity',
    'device_fingerprint_origin',
    'device_fingerprint_note',
]

# ============================================================
# NGÔN NGỮ & ĐIỀU KHOẢN
# ============================================================
LANGUAGES = {
    'vi': {
        'name': 'Tiếng Việt',
        'flag': '🇻🇳',
        'app_title': 'SPC Encryptor Pro',
        'app_subtitle': f'10 kỹ thuật · Mã hóa file · bản {SPC_VERSION}',
        'mode_label': 'Chế độ',
        'mode_encrypt': 'Mã hóa',
        'mode_decrypt': 'Giải mã',
        'input_label': 'Dữ liệu đầu vào',
        'seed_label': 'Seed',
        'saoyut_label': 'SAOYUT',
        'techniques_label': 'Kỹ thuật',
        'segment_manager_label': 'QUẢN LÝ SEGMENT',
        'action_encrypt': 'Mã hóa',
        'action_decrypt': 'Giải mã',
        'session_label': 'Phiên trình duyệt',
        'session_status_active': 'Hoạt động',
        'session_status_inactive': 'Chưa có phiên',
        'session_id_label': 'Browser Session ID:',
        'data_id_label': 'Data ID (danh tính dữ liệu):',
        'device_label': 'Thiết bị (Fingerprint):',
        'time_left_label': 'Thời gian còn lại:',
        'create_session': 'Tạo phiên mới',
        'clear_session': 'Xóa phiên',
        'input_placeholder': 'Nhập văn bản hoặc tải file lên...',
        'file_upload_text': 'Kéo thả hoặc click để tải file',
        'file_support': 'Hỗ trợ: .txt, .spc, .saoyut',
        'sample_btn': 'Mẫu',
        'clear_input_btn': 'Xóa input',
        'save_file_btn': 'Lưu file',
        'char_count': 'ký tự',
        'seed_placeholder': 'Để trống để tự tạo',
        'seed_auto': 'Để trống = auto-generate',
        'seed_save_label': 'Seed để lưu:',
        'seed_copy': 'Copy',
        'seed_no_seed': 'Chưa có seed',
        'seed_with_session': 'Seed này đã gắn với phiên trình duyệt hiện tại',
        'seed_without_session': 'Seed thuần, KHÔNG gắn với phiên',
        'toggle_session_on': 'Kèm phiên (BẬT)',
        'toggle_session_off': 'Không kèm phiên (TẮT)',
        'generate_seed': 'Tạo seed',
        'saoyut_input_label': 'Nhập (để giải mã)',
        'saoyut_display_label': 'Hiển thị (từ mã hóa)',
        'saoyut_placeholder': 'Dán SAOYUT JSON vào đây...',
        'saoyut_sample': 'Mẫu',
        'saoyut_clear': 'Xóa',
        'saoyut_validate': 'Kiểm tra',
        'saoyut_export': 'Export',
        'saoyut_sync': 'Sync sang nhập',
        'saoyut_copy': 'Copy',
        'saoyut_load': 'Load',
        'saoyut_status_empty': 'Chưa có',
        'saoyut_status_has_data': 'Có dữ liệu',
        'saoyut_status_valid': 'Hợp lệ',
        'saoyut_status_invalid': 'Không hợp lệ',
        'saoyut_status_generated': 'Đã sinh',
        'saoyut_no_data': 'Chưa có...',
        'techniques_touch': 'Chạm/kéo',
        'techniques_reset': 'Reset',
        'techniques_shuffle': 'Xáo trộn',
        'techniques_toggle_all': 'Bật/Tắt tất cả',
        'techniques_order': 'Order:',
        'segment_size_label': 'Kích thước segment:',
        'segment_no_data': 'Chưa có segment nào. Hãy mã hóa hoặc upload segment để tạo data_id.',
        'segment_upload': 'Upload segments',
        'segment_download_all': 'Tải tất cả',
        'segment_clear': 'Xóa segments',
        'segment_refresh': 'Làm mới',
        'segment_check': 'Kiểm tra',
        'segment_hint': 'Upload segments (file .dat hoặc .zip) khi giải mã file đã mã hóa với kỹ thuật L.',
        'segment_count': 'segments',
        'compare_label': 'So sánh',
        'compare_input': 'Input',
        'compare_output': 'Output',
        'output_label': 'Kết quả',
        'output_copy': 'Copy',
        'output_base64': 'Base64',
        'output_hex': 'Hex',
        'output_plaintext': 'Plaintext',
        'output_empty': 'Chưa có...',
        'clear_all': 'Xóa',
        'download_result': 'Tải kết quả',
        'terms_title': 'Điều khoản sử dụng & Miễn trừ trách nhiệm',
        'terms_content': '''## ĐIỀU KHOẢN SỬ DỤNG
1. **Mục đích**: SPC Encryptor Pro được phát triển để **nghiên cứu và học tập**, không nên mã hóa thứ quan trọng.
2. **Phạm vi sử dụng**: Công cụ này KHÔNG NÊN được sử dụng để mã hóa các thông tin quan trọng, tài liệu mật hoặc dữ liệu nhạy cảm trong thực tế.
3. **Sử dụng hợp pháp**: Người dùng chỉ được sử dụng công cụ này cho mục đích học tập, nghiên cứu hợp pháp, không vi phạm pháp luật.
4. **Bảo mật**: Không có hệ thống nào là hoàn toàn an toàn. Người dùng cần bảo quản seed, SAOYUT và Segments (Nếu có) cẩn thận.

## MIỄN TRỪ TRÁCH NHIỆM
1. **Không chịu trách nhiệm**: Nhà phát triển không chịu trách nhiệm về bất kỳ thiệt hại nào phát sinh từ việc sử dụng công cụ này.
2. **Mất dữ liệu**: Nếu người dùng mất seed, SAOYUT hoặc Segments, dữ liệu đã mã hóa sẽ không thể khôi phục.
3. **Sử dụng sai mục đích**: Người dùng tự chịu trách nhiệm nếu sử dụng công cụ cho mục đích bất hợp pháp.
4. **Bảo mật thông tin**: Nhà phát triển không đảm bảo an toàn tuyệt đối cho dữ liệu được mã hóa.
5. **Khuyến nghị**: Công cụ này CHỈ DÀNH CHO NGHIÊN CỨU VÀ HỌC TẬP. Không sử dụng để mã hóa dữ liệu quan trọng trong thực tế.

**Bằng cách sử dụng SPC Encryptor Pro, bạn đồng ý với các điều khoản trên.**'''
    },
    'en': {
        'name': 'English',
        'flag': '🇺🇸',
        'app_title': 'SPC Encryptor Pro',
        'app_subtitle': f'10 techniques · File encryption · Version {SPC_VERSION}',
        'mode_label': 'Mode',
        'mode_encrypt': 'Encrypt',
        'mode_decrypt': 'Decrypt',
        'input_label': 'Input Data',
        'seed_label': 'Seed',
        'saoyut_label': 'SAOYUT',
        'techniques_label': 'Techniques',
        'segment_manager_label': 'SEGMENT MANAGER',
        'action_encrypt': 'Encrypt',
        'action_decrypt': 'Decrypt',
        'session_label': 'Browser Session',
        'session_status_active': 'Active',
        'session_status_inactive': 'No session',
        'session_id_label': 'Browser Session ID:',
        'data_id_label': 'Data ID:',
        'device_label': 'Device (Fingerprint):',
        'time_left_label': 'Time remaining:',
        'create_session': 'Create New Session',
        'clear_session': 'Clear Session',
        'input_placeholder': 'Enter text or upload file...',
        'file_upload_text': 'Drag & drop or click to upload file',
        'file_support': 'Support: .txt, .spc, .saoyut',
        'sample_btn': 'Sample',
        'clear_input_btn': 'Clear input',
        'save_file_btn': 'Save file',
        'char_count': 'characters',
        'seed_placeholder': 'Leave empty to auto-generate',
        'seed_auto': 'Empty = auto-generate',
        'seed_save_label': 'Seed to save:',
        'seed_copy': 'Copy',
        'seed_no_seed': 'No seed yet',
        'seed_with_session': 'This seed is linked to current browser session',
        'seed_without_session': 'Pure seed, NOT linked to session',
        'toggle_session_on': 'Link session (ON)',
        'toggle_session_off': 'No session link (OFF)',
        'generate_seed': 'Generate seed',
        'saoyut_input_label': 'Input (for decrypt)',
        'saoyut_display_label': 'Display (from encrypt)',
        'saoyut_placeholder': 'Paste SAOYUT JSON here...',
        'saoyut_sample': 'Sample',
        'saoyut_clear': 'Clear',
        'saoyut_validate': 'Validate',
        'saoyut_export': 'Export',
        'saoyut_sync': 'Sync to input',
        'saoyut_copy': 'Copy',
        'saoyut_load': 'Load',
        'saoyut_status_empty': 'Empty',
        'saoyut_status_has_data': 'Has data',
        'saoyut_status_valid': 'Valid',
        'saoyut_status_invalid': 'Invalid',
        'saoyut_status_generated': 'Generated',
        'saoyut_no_data': 'No data yet...',
        'techniques_touch': 'Touch/drag',
        'techniques_reset': 'Reset',
        'techniques_shuffle': 'Shuffle',
        'techniques_toggle_all': 'Toggle all',
        'techniques_order': 'Order:',
        'segment_size_label': 'Segment size:',
        'segment_no_data': 'No segments yet. Encrypt or upload segments to create data_id.',
        'segment_upload': 'Upload segments',
        'segment_download_all': 'Download all',
        'segment_clear': 'Clear segments',
        'segment_refresh': 'Refresh',
        'segment_check': 'Check',
        'segment_hint': 'Upload segments (.dat or .zip files) when decrypting files encrypted with technique L.',
        'segment_count': 'segments',
        'compare_label': 'Compare',
        'compare_input': 'Input',
        'compare_output': 'Output',
        'output_label': 'Result',
        'output_copy': 'Copy',
        'output_base64': 'Base64',
        'output_hex': 'Hex',
        'output_plaintext': 'Plaintext',
        'output_empty': 'No data yet...',
        'clear_all': 'Clear',
        'download_result': 'Download result',
        'terms_title': 'Terms of Use & Disclaimer',
        'terms_content': '''## TERMS OF USE
1. **Purpose**: SPC Encryptor Pro is developed for **research and educational purposes**, should not be used to encrypt important things.
2. **Scope**: This tool SHOULD NOT be used to encrypt important information, confidential documents, or sensitive data in real-world scenarios.
3. **Legal Use**: Users must only use this tool for legal educational and research purposes, not violating any laws.
4. **Security**: No system is completely secure. Users must keep seed, SAOYUT, and Segments (if any) safe.

## DISCLAIMER
1. **No Liability**: Developers are not liable for any damages arising from the use of this tool.
2. **Data Loss**: If users lose seed, SAOYUT, or Segments, encrypted data cannot be recovered.
3. **Misuse**: Users are responsible if they use the tool for illegal purposes.
4. **Information Security**: Developers do not guarantee absolute security for encrypted data.
5. **Recommendation**: This tool is FOR RESEARCH AND EDUCATION ONLY. Do not use it to encrypt important data in real-world scenarios.

**By using SPC Encryptor Pro, you agree to the above terms.**'''
    }
}


def get_lang():
    """Lấy ngôn ngữ hiện tại từ session"""
    lang = session.get('lang', 'vi')
    return LANGUAGES.get(lang, LANGUAGES['vi'])


# ============================================================
# SAOYUT SIGNATURE HELPERS (V3)
# ============================================================
def _compute_saoyut_signature(metadata_dict, ciphertext, seed, salt):
    """
    Tính HMAC signature cho SAOYUT V3.
    
    Công thức:
        hmac_key = sha256(ciphertext || "||SPC_V3_SIGNATURE||" || seed || "||" || salt)
        signature = HMAC-SHA256(hmac_key, json.dumps(metadata, sort_keys=True))
    """
    key_material = (
        ciphertext +
        b"||SPC_V3_SIGNATURE||" +
        seed.encode('utf-8') +
        b"||" +
        salt.encode('utf-8')
    )
    hmac_key = hashlib.sha256(key_material).digest()
    
    metadata_json = json.dumps(
        metadata_dict,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    )
    metadata_bytes = metadata_json.encode('utf-8')
    
    signature = hmac.new(hmac_key, metadata_bytes, hashlib.sha256).hexdigest()
    return signature


def _detect_saoyut_version_by_structure(saoyut_data):
    """
    Phát hiện version SAOYUT từ cấu trúc (dùng khi không có field 'version' top-level).
    
    Returns: (version, source_name)
    Raises: ValueError nếu phát hiện dấu hiệu V3 (downgrade) hoặc không nhận diện được
    """
    # Bước 1: Chống downgrade attack
    v3_signals = [ind for ind in SAOYUT_V3_INDICATORS if ind in saoyut_data]
    if v3_signals:
        raise ValueError(
            f"❌ SAOYUT thiếu 'version' nhưng có dấu hiệu V3 ({', '.join(v3_signals)}) — "
            f"có thể bị tấn công DOWNGRADE ATTACK! Không hợp lệ."
        )
    
    # Bước 2: Kiểm tra S technique
    s_meta = None
    for tech in saoyut_data.get('techniques', []):
        if tech.get('name') == 'S':
            s_meta = tech.get('metadata', {})
            break
    
    if s_meta is None:
        # Không có S → có thể là SAOYUT 2.6.0 (không dùng S)
        if not saoyut_data.get('techniques'):
            raise ValueError("❌ SAOYUT thiếu 'version' và không có techniques — không hợp lệ.")
        print(f"[VALIDATE] SAOYUT không có S technique — giả định V1 (2.6.0/3.2.0)")
        return (1, "2.6.0/3.2.0")
    
    # Bước 3: Phân loại theo cấu trúc S
    has_packed = 'shuffle_map_packed' in s_meta and s_meta.get('shuffle_map_packed')
    has_list = 'shuffle_map' in s_meta and isinstance(s_meta.get('shuffle_map'), list)
    num_shards = s_meta.get('num_shards', 0)
    s_version = s_meta.get('version', None)
    
    # V2 (3.4.0): packed metadata
    if has_packed:
        if s_version == 2 or s_version is None:
            return (2, "3.4.0")
        else:
            raise ValueError(
                f"❌ SAOYUT có packed metadata nhưng S version={s_version} — không nhận diện được."
            )
    
    # V1 (2.6.0, 3.2.0): list metadata
    if has_list:
        if num_shards == 4:
            return (1, "2.6.0/3.2.0")
        elif num_shards > 0:
            return (1, f"V1-variant ({num_shards} shards)")
    
    raise ValueError(
        f"❌ SAOYUT có cấu trúc không được hỗ trợ: "
        f"num_shards={num_shards}, packed={bool(has_packed)}, list={bool(has_list)}"
    )


def _validate_saoyut_version(saoyut_data):
    """
    Validate version + chống downgrade attack.
    
    Returns: (version, is_legacy, source_name)
    """
    # Case 1: CÓ version field top-level
    if 'version' in saoyut_data:
        try:
            version = int(saoyut_data['version'])
        except (ValueError, TypeError):
            raise ValueError(
                f"❌ Version không phải số nguyên: {saoyut_data.get('version')} — không hợp lệ!"
            )
        
        if version not in SAOYUT_SUPPORTED_VERSIONS:
            raise ValueError(
                f"❌ Version {version} không được hỗ trợ! Chỉ chấp nhận: {SAOYUT_SUPPORTED_VERSIONS}"
            )
        
        # version >= 3 → BẮT BUỘC integrity
        if version >= SAOYUT_REQUIRE_SIGNATURE_FROM:
            integrity = saoyut_data.get('integrity')
            
            if not integrity:
                raise ValueError(
                    f"❌ SAOYUT V{version} thiếu trường 'integrity' — "
                    f"có thể bị tấn công DOWNGRADE ATTACK! Không hợp lệ."
                )
            
            if not isinstance(integrity, dict):
                raise ValueError("❌ 'integrity' phải là dict — không hợp lệ!")
            
            if not integrity.get('signature'):
                raise ValueError("❌ 'integrity' thiếu 'signature' — không hợp lệ!")
            
            if not integrity.get('salt'):
                raise ValueError("❌ 'integrity' thiếu 'salt' — không hợp lệ!")
            
            algo = integrity.get('algorithm', '')
            if algo and algo != 'HMAC-SHA256':
                raise ValueError(
                    f"❌ Algorithm không được hỗ trợ: {algo} — chỉ chấp nhận HMAC-SHA256"
                )
        
        print(f"[VALIDATE] ✅ SAOYUT V{version} (explicit version)")
        return version, False, f"{SPC_VERSION}+"
    
    # Case 2: KHÔNG có version → legacy
    print(f"[VALIDATE] ⚠️ SAOYUT thiếu 'version' — phân tích cấu trúc...")
    version, source_name = _detect_saoyut_version_by_structure(saoyut_data)
    print(f"[VALIDATE] ✅ Phát hiện: V{version} ({source_name}) — legacy")
    return version, True, source_name


def _verify_saoyut_signature(saoyut_data, ciphertext, seed):
    """
    Kiểm tra SAOYUT signature.
    
    Returns: (is_valid, version, is_legacy, source_name)
    """
    version, is_legacy, source_name = _validate_saoyut_version(saoyut_data)
    
    # V1, V2 → không có signature
    if version < SAOYUT_REQUIRE_SIGNATURE_FROM:
        print(f"[VERIFY] ⚠️ SAOYUT V{version} ({source_name}) — bỏ qua signature")
        return True, version, is_legacy, source_name
    
    # V3 → verify signature
    integrity = saoyut_data['integrity']
    stored_signature = integrity['signature']
    salt = integrity['salt']
    
    metadata_copy = {k: v for k, v in saoyut_data.items() if k != 'integrity'}
    computed = _compute_saoyut_signature(metadata_copy, ciphertext, seed, salt)
    
    if not hmac.compare_digest(computed, stored_signature):
        print(f"[VERIFY] ❌ Signature mismatch!")
        print(f"[VERIFY]    Expected: {stored_signature[:16]}...")
        print(f"[VERIFY]    Computed: {computed[:16]}...")
        raise ValueError(
            "❌ SAOYUT signature không hợp lệ! SAOYUT đã bị sửa đổi hoặc giả mạo."
        )
    
    print(f"[VERIFY] ✅ SAOYUT V{version} signature VALID")
    return True, version, is_legacy, source_name


# ============================================================
# SESSION MANAGER (RLock — tránh deadlock)
# ============================================================
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.timeout = app.config['SESSION_TIMEOUT']
        self._lock = threading.RLock()
    
    def create_session(self, fingerprint='', ip='', user_agent=''):
        session_id = hashlib.sha256(
            f"{time.time()}{random.randint(1, 999999)}{os.urandom(16).hex()}".encode()
        ).hexdigest()[:32]
        
        with self._lock:
            self.sessions[session_id] = {
                'created': time.time(),
                'fingerprint': fingerprint,
                'ip': ip,
                'user_agent': user_agent,
                'active': True
            }
        return session_id
    
    def get_session(self, session_id):
        with self._lock:
            if session_id not in self.sessions:
                return None
            session_data = self.sessions[session_id]
            if time.time() - session_data['created'] > self.timeout:
                session_data['expired'] = True
                return None
            return session_data
    
    def update_fingerprint(self, session_id, fingerprint):
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]['fingerprint'] = fingerprint
                return True
            return False
    
    def is_valid(self, session_id, check_binding=True,
                 current_ip=None, current_user_agent=None, current_fingerprint=None):
        """Kiểm tra session + binding MỀM (IP/UA/FP đổi → log, không chặn)."""
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        if not check_binding:
            return True
        
        stored_ip = session_data.get('ip', '')
        if stored_ip and current_ip and stored_ip != current_ip:
            print(f"[AUDIT] ⚠️ Session {session_id[:8]}... — IP changed")
        
        stored_ua = session_data.get('user_agent', '')
        if stored_ua and current_user_agent and stored_ua != current_user_agent:
            print(f"[AUDIT] ⚠️ Session {session_id[:8]}... — User-Agent changed")
        
        stored_fp = session_data.get('fingerprint', '')
        if stored_fp and current_fingerprint and stored_fp != current_fingerprint:
            print(f"[AUDIT] ⚠️ Session {session_id[:8]}... — Fingerprint changed")
        
        return True
    
    def _cleanup_session(self, session_id):
        """Xóa session + segments. Gọi khi KHÔNG giữ lock."""
        with self._lock:
            if session_id not in self.sessions:
                return
            del self.sessions[session_id]
        
        segment_dir = app.config['SEGMENT_FOLDER']
        if os.path.exists(segment_dir):
            for filename in os.listdir(segment_dir):
                if f'_{session_id}_' in filename and filename.endswith('.dat'):
                    try:
                        os.remove(os.path.join(segment_dir, filename))
                        print(f"[CLEANUP] Removed segment: {filename}")
                    except Exception as e:
                        print(f"[CLEANUP] Error removing {filename}: {e}")
        print(f"[CLEANUP] Session {session_id[:8]}... cleaned")
    
    def cleanup_expired(self):
        now = time.time()
        expired = []
        with self._lock:
            for session_id, data in list(self.sessions.items()):
                if now - data['created'] > self.timeout:
                    expired.append(session_id)
        
        for session_id in expired:
            self._cleanup_session(session_id)
    
    def force_cleanup(self, session_id):
        if session_id:
            self._cleanup_session(session_id)


session_manager = SessionManager()


# ============================================================
# DECORATOR
# ============================================================
def require_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.args.get('session_id')
        if not session_id and request.method == 'POST':
            if request.form:
                session_id = request.form.get('session_id')
            elif request.json:
                session_id = request.json.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'Session ID required',
                'code': 'SESSION_REQUIRED'
            }), 401
        
        current_fingerprint = request.headers.get('X-Device-Fingerprint', '')
        
        if not session_manager.is_valid(
            session_id,
            check_binding=True,
            current_ip=request.remote_addr,
            current_user_agent=request.user_agent.string,
            current_fingerprint=current_fingerprint
        ):
            return jsonify({
                'success': False,
                'error': 'Invalid or expired session',
                'code': 'SESSION_INVALID'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# CLEANUP JOB
# ============================================================
def cleanup_job():
    while True:
        time.sleep(1800)
        session_manager.cleanup_expired()
        print("[CLEANUP] Cleanup job completed")


cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
cleanup_thread.start()


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
# PACK/UNPACK HELPERS
# ============================================================
def _pack_int_list(ints):
    """Pack list[int] thành base64 (2 bytes/int)."""
    if not ints:
        return ""
    if any(i < 0 or i > 65535 for i in ints):
        raise ValueError("Int values must be in range [0, 65535]")
    packed = struct.pack(f'>{len(ints)}H', *ints)
    return base64.b64encode(packed).decode('ascii')


def _unpack_int_list(s):
    """Unpack base64 thành list[int]."""
    if not s:
        return []
    packed = base64.b64decode(s)
    count = len(packed) // 2
    return list(struct.unpack(f'>{count}H', packed))


# ============================================================
# CÁC KỸ THUẬT (10 KỸ THUẬT)
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


def technique_E(data, saoyut, reverse=False):
    key = saoyut.seed.encode()
    result = bytearray(len(data))
    for i in range(len(data)):
        result[i] = data[i] ^ key[i % len(key)]
    if not reverse:
        saoyut.add_technique("E", {})
    return bytes(result)


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


def technique_S(data, saoyut, reverse=False):
    """
    Kỹ thuật S - Sharding.
    
    TƯƠNG THÍCH NGƯỢC:
    - V1 (2.6.0, 3.2.0): 4 shard, list JSON
    - V2 (3.4.0, 3.5.0): 256 shard, packed base64
    
    TỰ ĐỘNG PHÁT HIỆN khi giải mã:
    - Có 'shuffle_map_packed' → V2 (packed)
    - Có 'shuffle_map' (list) → V1 (list)
    """
    NUM_SHARDS = 256
    
    # ============================================================
    # MÃ HÓA (luôn dùng V2)
    # ============================================================
    if not reverse:
        total_size = len(data)
        
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
        
        actual_shards = min(NUM_SHARDS, total_size)
        base_size = total_size // actual_shards
        remainder = total_size % actual_shards
        
        shards = []
        shard_sizes = []
        pos = 0
        for i in range(actual_shards):
            size = base_size + (1 if i < remainder else 0)
            shards.append(data[pos:pos + size])
            shard_sizes.append(size)
            pos += size
        
        shuffle_map = list(range(actual_shards))
        random.shuffle(shuffle_map)
        
        shuffled_data = b''.join(shards[idx] for idx in shuffle_map)
        
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
    # GIẢI MÃ (hỗ trợ V1 + V2)
    # ============================================================
    else:
        meta = saoyut.get_technique_by_name("S")
        if not meta:
            raise ValueError("Missing S metadata!")
        
        num_shards = meta["num_shards"]
        total_size = meta["total_size"]
        version = meta.get("version", 1)
        
        if num_shards == 0 or total_size == 0:
            return b''
        
        # Hỗ trợ cả packed (V2) và list (V1)
        if "shuffle_map_packed" in meta and meta["shuffle_map_packed"]:
            shuffle_map = _unpack_int_list(meta["shuffle_map_packed"])
            shard_sizes = _unpack_int_list(meta["shard_sizes_packed"])
            print(f"[S] Using packed metadata (V2)")
        else:
            shuffle_map = meta.get("shuffle_map", [])
            shard_sizes = meta.get("shard_sizes", [])
            print(f"[S] Using list metadata (V1)")
        
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
        
        if len(result) != total_size:
            print(f"[S] Warning: Size mismatch! Expected: {total_size}, Got: {len(result)}")
            if len(result) < total_size:
                result += b'\x00' * (total_size - len(result))
            else:
                result = result[:total_size]
        
        print(f"[S] Decrypt: {len(data)} bytes -> {len(result)} bytes "
              f"({num_shards} shards, v{version})")
        return result


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


def technique_B(data, saoyut, reverse=False):
    password = saoyut.seed
    
    hashed = password
    for _ in range(100):
        hashed = hashlib.sha256(hashed.encode()).hexdigest()
    key = hashed[:32].encode()
    
    if not reverse:
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        
        saoyut.add_technique("B", {
            "password_hash": hashed,
            "iterations": 100,
            "key_length": len(key)
        })
        
        print(f"[B] Encrypt: {len(data)} bytes")
        return bytes(result)
    else:
        meta = saoyut.get_technique_by_name("B")
        if not meta:
            raise ValueError("Missing B metadata!")
        
        stored_hash = meta.get("password_hash", "")
        if stored_hash:
            key = stored_hash[:32].encode()
        else:
            hashed = password
            for _ in range(100):
                hashed = hashlib.sha256(hashed.encode()).hexdigest()
            key = hashed[:32].encode()
        
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ key[i % len(key)]
        
        print(f"[B] Decrypt: {len(data)} bytes")
        return bytes(result)


def technique_P(data, saoyut, reverse=False):
    if not reverse:
        saoyut.add_technique("P", {"ram_only": True})
    return data


def technique_L(data, saoyut, reverse=False):
    if not reverse:
        data_id = hashlib.sha256(
            f"{time.time()}{random.randint(1, 999999)}".encode()
        ).hexdigest()[:32]
        segment_size = app.config['DEFAULT_SEGMENT_SIZE']
        segments = []
        segment_hashes = []
        
        for i in range(0, len(data), segment_size):
            segment = data[i:i + segment_size]
            segments.append(segment)
            segment_hashes.append(hashlib.sha256(segment).hexdigest())
        
        saoyut.add_technique("L", {
            "num_segments": len(segments),
            "segment_sizes": [len(s) for s in segments],
            "segment_hashes": segment_hashes,
            "segment_size": segment_size,
            "data_id": data_id
        })
        
        browser_session_id = saoyut.data.get('browser_session_id')
        
        segment_dir = app.config['SEGMENT_FOLDER']
        os.makedirs(segment_dir, exist_ok=True)
        
        for i, segment in enumerate(segments):
            if browser_session_id:
                segment_path = os.path.join(
                    segment_dir,
                    f"segment_{data_id}_{browser_session_id}_{i+1}.dat"
                )
            else:
                segment_path = os.path.join(
                    segment_dir,
                    f"segment_{data_id}_{i+1}.dat"
                )
            with open(segment_path, 'wb') as f:
                f.write(segment)
            print(f"[DEBUG] Created segment: {os.path.basename(segment_path)}")
        
        print(f"[DEBUG] L technique created with data_id: {data_id}")
        return data
    else:
        meta = saoyut.get_technique_by_name("L")
        if not meta:
            raise ValueError("Missing L metadata!")
        
        data_id = meta.get("data_id", "")
        if not data_id:
            raise ValueError("Missing data_id in SAOYUT!")
        
        return data


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
# SPC ENGINE v3.5.0
# ============================================================
def spc_encrypt_with_order(data, seed, technique_order, browser_session_id=None, fingerprint=None):
    """
    Mã hóa + tạo SAOYUT V3 có signature.
    """
    if not seed:
        seed = hashlib.sha256(os.urandom(32)).hexdigest()
        print(f"[spc_encrypt_with_order] Auto-generated seed: {seed}")
    
    print(f"[spc_encrypt_with_order] Using seed: {seed}")
    
    saoyut = SAOYUT(seed)
    saoyut.data['browser_session_id'] = browser_session_id
    
    if fingerprint:
        saoyut.data['device_fingerprint_origin'] = fingerprint
        saoyut.data['device_fingerprint_note'] = 'Chỉ để audit, KHÔNG dùng để giải mã'
    
    # THÊM VERSION TRƯỚC KHI MÃ HÓA VÀ KÝ
    saoyut.data['version'] = SAOYUT_CURRENT_VERSION
    
    # Mã hóa
    result = data
    for name in technique_order:
        if name in ALL_TECHNIQUES:
            result = ALL_TECHNIQUES[name](result, saoyut)
    
    # ============================================================
    # TẠO SIGNATURE V3
    # ============================================================
    ciphertext = result
    salt = secrets.token_hex(32)
    
    metadata_for_sig = {k: v for k, v in saoyut.data.items() if k != 'integrity'}
    
    print(f"[SIGN] Metadata keys: {sorted(metadata_for_sig.keys())}")
    
    signature = _compute_saoyut_signature(metadata_for_sig, ciphertext, seed, salt)
    
    saoyut.data['integrity'] = {
        'signature': signature,
        'salt': salt,
        'algorithm': 'HMAC-SHA256',
        'version': SAOYUT_CURRENT_VERSION
    }
    
    return {
        "data": result,
        "saoyut": saoyut.export(),
        "seed": seed
    }


def spc_decrypt_with_order(data, saoyut_data, seed, technique_order, browser_session_id=None):
    """
    Giải mã dữ liệu — NGHIÊM NGẶT, KHÔNG thử biến thể seed.
    
    ═══════════════════════════════════════════════════════════════
    NGUYÊN TẮC BẢO MẬT:
    ═══════════════════════════════════════════════════════════════
    Seed phải khớp CHÍNH XÁC với seed_hash trong SAOYUT.
    
    KHÔNG được phép:
      ❌ Tự động thêm session vào seed
      ❌ Tách seed ra khỏi session  
      ❌ Thử bất kỳ biến thể nào
      ❌ Bỏ qua session binding
    
    Lý do:
      1. Session binding chỉ có ý nghĩa nếu session PHẢI được biết
      2. Nếu tự thêm session → giảm entropy 128 bits
      3. Nếu tách seed → phá vỡ session binding của V3
      4. Side-channel: log tiết lộ thông tin về SAOYUT
    
    ═══════════════════════════════════════════════════════════════
    CÁCH USER NHẬP SEED:
    ═══════════════════════════════════════════════════════════════
    ┌─────────┬─────────────────────┬──────────────────────────────┐
    │ Version │ Binding             │ Seed user phải nhập          │
    ├─────────┼─────────────────────┼──────────────────────────────┤
    │ 2.6.0   │ ❌ Không bind       │ <seed>                       │
    │ 3.2.0   │ ⚠️ Tùy SAOYUT       │ <seed> hoặc <seed>_<session> │
    │ 3.4.0   │ ✅ Bind thật        │ <seed>_<session>             │
    │ 3.5.0   │ ✅ Bind thật        │ <seed>_<session>             │
    └─────────┴─────────────────────┴──────────────────────────────┘
    
    Nếu user nhập sai → từ chối, KHÔNG tự đoán.
    """
    stored_seed_hash = saoyut_data.get('seed_hash', '')
    saoyut_session_id = saoyut_data.get('browser_session_id')
    
    print(f"[DECRYPT] ===== DECRYPT START =====")
    print(f"[DECRYPT] input seed: '{seed}'")
    print(f"[DECRYPT] saoyut session: {saoyut_session_id}")
    
    if not seed:
        raise ValueError("❌ Seed là bắt buộc!")
    
    # ============================================================
    # 1. VALIDATE VERSION + VERIFY SIGNATURE
    # ============================================================
    is_valid, saoyut_version, is_legacy, source_name = _verify_saoyut_signature(
        saoyut_data, data, seed
    )
    
    print(f"[DECRYPT] SAOYUT V{saoyut_version} ({source_name}, "
          f"{'legacy' if is_legacy else 'signed'})")
    
    # ============================================================
    # 2. KIỂM TRA SEED HASH — CHÍNH XÁC, KHÔNG THỬ BIẾN THỂ
    # ============================================================
    computed_hash = hashlib.sha256(seed.encode()).hexdigest()
    
    if not hmac.compare_digest(computed_hash, stored_seed_hash):
        print(f"[DECRYPT] ❌ Seed hash mismatch!")
        print(f"[DECRYPT]    stored:   {stored_seed_hash[:32]}...")
        print(f"[DECRYPT]    computed: {computed_hash[:32]}...")
        
        # Thông báo lỗi CHÍNH XÁC, không gợi ý thử biến thể
        if saoyut_session_id:
            raise ValueError(
                f"❌ Sai Seed cho SAOYUT V{saoyut_version} ({source_name}).\n\n"
                f"💡 SAOYUT này được mã hóa với chế độ KÈM PHIÊN.\n"
                f"   Seed phải có dạng: <seed>_<session_id>\n\n"
                f"   Session trong SAOYUT: {saoyut_session_id}\n"
                f"   → Seed đúng là: <seed_gốc>_{saoyut_session_id}\n\n"
                f"⚠️ Seed phải khớp CHÍNH XÁC. Hệ thống KHÔNG tự đoán seed."
            )
        else:
            raise ValueError(
                f"❌ Sai Seed cho SAOYUT V{saoyut_version} ({source_name}).\n\n"
                f"💡 SAOYUT này KHÔNG gắn với phiên trình duyệt.\n"
                f"   Vui lòng nhập seed THUẦN (KHÔNG thêm _session).\n\n"
                f"⚠️ Seed phải khớp CHÍNH XÁC. Hệ thống KHÔNG tự đoán seed."
            )
    
    print(f"[DECRYPT] ✅ Seed hash matches (strict)")
    
    # ============================================================
    # 3. GIẢI MÃ
    # ============================================================
    saoyut = SAOYUT(seed)
    saoyut.data = saoyut_data
    result = data
    
    has_L_in_order = 'L' in technique_order
    l_meta = saoyut.get_technique_by_name("L")
    has_L_metadata = bool(l_meta) and bool(l_meta.get('data_id'))
    
    print(f"[DECRYPT] Has L in order: {has_L_in_order}, metadata: {has_L_metadata}")
    
    effective_order = []
    for name in technique_order:
        if name == 'L' and not has_L_metadata:
            print(f"[DECRYPT] Skipping L - no valid metadata")
            continue
        effective_order.append(name)
    
    print(f"[DECRYPT] Effective order: {effective_order}")
    
    for name in reversed(effective_order):
        if name == "L":
            meta = l_meta
            data_id = meta.get("data_id", "")
            
            if not data_id:
                print("[DECRYPT] L metadata missing data_id - skipping")
                continue
            
            # Session dùng để tìm segment file — lấy từ SAOYUT (chính xác)
            segment_session_id = saoyut_session_id
            
            if not segment_session_id:
                print("[DECRYPT] L needs session_id but None - skipping")
                continue
            
            segment_dir = app.config['SEGMENT_FOLDER']
            segment_sizes = meta.get("segment_sizes", [])
            segment_hashes = meta.get("segment_hashes", [])
            num_segments = meta.get("num_segments", 0)
            
            if num_segments == 0:
                print("[DECRYPT] L has 0 segments - skipping")
                continue
            
            print(f"[DECRYPT] Processing L: {num_segments} segments "
                  f"(session: {segment_session_id[:8]}...)")
            
            segments = []
            for i in range(num_segments):
                filename = f"segment_{data_id}_{segment_session_id}_{i+1}.dat"
                segment_path = os.path.join(segment_dir, filename)
                
                if not os.path.exists(segment_path):
                    print(f"[DECRYPT] Missing segment: {filename}")
                    raise FileNotFoundError(f"Missing segment {i+1}: {filename}")
                
                with open(segment_path, 'rb') as f:
                    segment_data = f.read()
                
                expected_size = segment_sizes[i] if i < len(segment_sizes) else len(segment_data)
                if len(segment_data) != expected_size:
                    raise ValueError(f"Segment {i+1} size mismatch")
                
                if i < len(segment_hashes):
                    computed_hash_seg = hashlib.sha256(segment_data).hexdigest()
                    if not hmac.compare_digest(computed_hash_seg, segment_hashes[i]):
                        raise ValueError(f"Segment {i+1} checksum mismatch!")
                
                segments.append(segment_data)
            
            result = b''.join(segments)
            print(f"[DECRYPT] L assembled {len(result)} bytes from {num_segments} segments")
            continue
        
        elif name == "S":
            result = technique_S(result, saoyut, reverse=True)
        else:
            if name in ALL_TECHNIQUES:
                result = ALL_TECHNIQUES[name](result, saoyut, reverse=True)
    
    print(f"[DECRYPT] ✅ SUCCESS! Decrypted {len(result)} bytes")
    print(f"[DECRYPT] ===== DECRYPT END =====\n")
    return result


# ============================================================
# SEGMENT API
# ============================================================
@app.route('/segments/list', methods=['GET'])
@require_session
def list_segments():
    try:
        browser_session_id = request.args.get('session_id')
        data_id = request.args.get('data_id')
        
        if not data_id:
            return jsonify({'success': False, 'error': 'data_id required'}), 400
        
        segment_dir = app.config['SEGMENT_FOLDER']
        segments = []
        
        if os.path.exists(segment_dir):
            prefix = f"segment_{data_id}_{browser_session_id}_"
            for filename in os.listdir(segment_dir):
                if filename.startswith(prefix) and filename.endswith('.dat'):
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
        print(f"[ERROR] list_segments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/upload', methods=['POST'])
@require_session
def upload_segments():
    try:
        browser_session_id = request.args.get('session_id') or request.form.get('session_id')
        if not browser_session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        if not session_manager.is_valid(browser_session_id):
            return jsonify({
                'success': False,
                'error': 'Session expired',
                'code': 'SESSION_EXPIRED'
            }), 401
        
        if 'segments' not in request.files:
            return jsonify({'success': False, 'error': 'No segments uploaded'}), 400
        
        files = request.files.getlist('segments')
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400
        
        segment_dir = app.config['SEGMENT_FOLDER']
        os.makedirs(segment_dir, exist_ok=True)
        
        uploaded = []
        data_ids = []
        
        for file in files:
            if file.filename:
                original_filename = secure_filename(file.filename)
                parts = original_filename.replace('.dat', '').split('_')
                
                if len(parts) >= 2 and parts[0] == 'segment':
                    data_id = parts[1]
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Invalid filename: {original_filename}. Must be segment_{{data_id}}.dat',
                        'hint': 'Please use segment files from the download'
                    }), 400
                
                prefix = f"segment_{data_id}_{browser_session_id}_"
                existing = [f for f in os.listdir(segment_dir) if f.startswith(prefix) and f.endswith('.dat')]
                max_idx = 0
                for f in existing:
                    idx_part = f.replace('.dat', '').split('_')[-1]
                    if idx_part.isdigit():
                        max_idx = max(max_idx, int(idx_part))
                index = max_idx + 1
                
                filename = f"segment_{data_id}_{browser_session_id}_{index}.dat"
                filepath = os.path.join(segment_dir, filename)
                
                if os.path.exists(filepath):
                    print(f"[DEBUG] File {filename} already exists")
                    uploaded.append(filename)
                    data_ids.append(data_id)
                    continue
                
                file.save(filepath)
                uploaded.append(filename)
                data_ids.append(data_id)
                print(f"[DEBUG] Uploaded segment: {filename}")
        
        return jsonify({
            'success': True,
            'uploaded': uploaded,
            'count': len(uploaded),
            'data_id': data_ids[0] if data_ids else None
        })
    except Exception as e:
        print(f"[ERROR] upload_segments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/upload-zip', methods=['POST'])
@require_session
def upload_segments_zip():
    try:
        browser_session_id = request.args.get('session_id') or request.form.get('session_id')
        if not browser_session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        if not session_manager.is_valid(browser_session_id):
            return jsonify({
                'success': False,
                'error': 'Session expired',
                'code': 'SESSION_EXPIRED'
            }), 401
        
        if 'zip_file' not in request.files:
            return jsonify({'success': False, 'error': 'No ZIP file uploaded'}), 400
        
        zip_file = request.files['zip_file']
        if zip_file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        zip_data = zip_file.read()
        zip_buffer = io.BytesIO(zip_data)
        
        segment_dir = app.config['SEGMENT_FOLDER']
        os.makedirs(segment_dir, exist_ok=True)
        
        uploaded = []
        data_ids = []
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            for filename in zf.namelist():
                if not filename.endswith('.dat'):
                    continue
                
                file_data = zf.read(filename)
                parts = filename.replace('.dat', '').split('_')
                
                if len(parts) >= 2 and parts[0] == 'segment':
                    data_id = parts[1]
                else:
                    continue
                
                prefix = f"segment_{data_id}_{browser_session_id}_"
                existing = [f for f in os.listdir(segment_dir) if f.startswith(prefix) and f.endswith('.dat')]
                max_idx = 0
                for f in existing:
                    idx_part = f.replace('.dat', '').split('_')[-1]
                    if idx_part.isdigit():
                        max_idx = max(max_idx, int(idx_part))
                index = max_idx + 1
                
                new_filename = f"segment_{data_id}_{browser_session_id}_{index}.dat"
                filepath = os.path.join(segment_dir, new_filename)
                
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                
                uploaded.append(new_filename)
                data_ids.append(data_id)
                print(f"[DEBUG] Extracted segment: {filename} -> {new_filename}")
        
        return jsonify({
            'success': True,
            'uploaded': uploaded,
            'count': len(uploaded),
            'data_id': data_ids[0] if data_ids else None
        })
    except Exception as e:
        print(f"[ERROR] upload_segments_zip: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/clear', methods=['POST'])
def clear_segments():
    try:
        session_manager.cleanup_expired()
        return jsonify({'success': True, 'message': 'Expired segments cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/download/<int:segment_id>', methods=['GET'])
@require_session
def download_segment(segment_id):
    try:
        browser_session_id = request.args.get('session_id')
        if not browser_session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        data_id = request.args.get('data_id')
        if not data_id:
            return jsonify({'success': False, 'error': 'data_id required'}), 400
        
        segment_dir = app.config['SEGMENT_FOLDER']
        filename = f"segment_{data_id}_{browser_session_id}_{segment_id}.dat"
        segment_path = os.path.join(segment_dir, filename)
        
        if not os.path.exists(segment_path):
            return jsonify({'success': False, 'error': 'Segment not found'}), 404
        
        return send_file(segment_path, as_attachment=True, download_name=f"segment_{data_id}.dat")
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/download-all', methods=['POST'])
@require_session
def download_all_segments():
    try:
        data = request.json
        data_id = data.get('data_id')
        num_segments = data.get('num_segments', 0)
        browser_session_id = data.get('session_id')
        
        if not data_id:
            return jsonify({'success': False, 'error': 'data_id required'}), 400
        
        if num_segments == 0:
            return jsonify({'success': False, 'error': 'No segments specified'}), 400
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for i in range(num_segments):
                if browser_session_id:
                    segment_path = os.path.join(
                        app.config['SEGMENT_FOLDER'],
                        f"segment_{data_id}_{browser_session_id}_{i+1}.dat"
                    )
                else:
                    segment_path = os.path.join(
                        app.config['SEGMENT_FOLDER'],
                        f"segment_{data_id}_{i+1}.dat"
                    )
                
                if os.path.exists(segment_path):
                    zip_file.write(segment_path, f"segment_{data_id}_{i+1}.dat")
                    print(f"[DEBUG] Added to ZIP: segment_{data_id}_{i+1}.dat")
                else:
                    print(f"[WARN] Segment {i+1} not found")
        
        zip_buffer.seek(0)
        return send_file(zip_buffer, as_attachment=True, download_name=f"segments_{data_id}.zip")
    except Exception as e:
        print(f"[ERROR] download_all_segments: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/segments/count', methods=['GET'])
def get_segment_count():
    try:
        segment_dir = app.config['SEGMENT_FOLDER']
        count = 0
        if os.path.exists(segment_dir):
            count = len([f for f in os.listdir(segment_dir) if f.endswith('.dat')])
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# SESSION API
# ============================================================
@app.route('/api/session/create', methods=['POST'])
def create_session():
    try:
        data = request.json or {}
        fingerprint = data.get('fingerprint', '')
        
        session_id = session_manager.create_session(
            fingerprint=fingerprint,
            ip=request.remote_addr,
            user_agent=request.user_agent.string
        )
        return jsonify({
            'success': True,
            'session_id': session_id,
            'timeout': app.config['SESSION_TIMEOUT']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/session/verify', methods=['POST'])
def verify_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        current_fingerprint = data.get('fingerprint', '') or \
                             request.headers.get('X-Device-Fingerprint', '')
        
        is_valid = session_manager.is_valid(
            session_id,
            check_binding=True,
            current_ip=request.remote_addr,
            current_user_agent=request.user_agent.string,
            current_fingerprint=current_fingerprint
        )
        return jsonify({
            'success': True,
            'valid': is_valid
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/fingerprint', methods=['POST'])
def register_fingerprint():
    try:
        data = request.json
        session_id = data.get('session_id')
        fingerprint = data.get('fingerprint')
        
        if not session_id or not fingerprint:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        
        if session_manager.update_fingerprint(session_id, fingerprint):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid session'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/session/clear', methods=['POST'])
def clear_session():
    try:
        data = request.json
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        session_manager.force_cleanup(session_id)
        return jsonify({'success': True, 'message': 'Session cleared'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/session', methods=['GET'])
def get_session():
    try:
        session_id = session_manager.create_session(
            ip=request.remote_addr,
            user_agent=request.user_agent.string
        )
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# LANGUAGE API
# ============================================================
@app.route('/api/language', methods=['POST'])
def set_language():
    try:
        data = request.json
        lang = data.get('lang', 'vi')
        
        if lang not in LANGUAGES:
            return jsonify({'success': False, 'error': 'Invalid language'}), 400
        
        session['lang'] = lang
        
        return jsonify({
            'success': True,
            'lang': lang,
            'translations': LANGUAGES[lang]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/language', methods=['GET'])
def get_language():
    try:
        lang = session.get('lang', 'vi')
        return jsonify({
            'success': True,
            'lang': lang,
            'translations': LANGUAGES[lang],
            'available': LANGUAGES
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# ROUTES CHÍNH
# ============================================================
@app.route('/')
def index():
    lang_data = get_lang()
    return render_template('index.html',
                         techniques=list(ALL_TECHNIQUES.keys()),
                         lang_data=lang_data,
                         languages=LANGUAGES,
                         spc_version=SPC_VERSION)


@app.route('/terms')
def terms():
    lang_data = get_lang()
    return render_template('terms.html', lang_data=lang_data)


@app.route('/process', methods=['POST'])
def process_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        action = request.form.get('action', 'encrypt')
        technique = request.form.get('technique', 'auto')
        output_format = request.form.get('output_format', 'base64')
        
        file_data = file.read()
        
        browser_session_id = hashlib.md5(
            f"{time.time()}{random.randint(1, 999999)}".encode()
        ).hexdigest()[:16]
        seed = hashlib.sha256(os.urandom(32)).hexdigest()
        
        if technique == 'auto':
            tech_order = ['R', 'C', 'E', 'Z', 'S', 'H', 'D', 'B', 'P', 'L']
        else:
            tech_order = [technique]
        
        if action == 'encrypt':
            result = spc_encrypt_with_order(file_data, seed, tech_order, browser_session_id)
            
            data_id = None
            for tech in result["saoyut"]["techniques"]:
                if tech["name"] == "L":
                    data_id = tech["metadata"].get("data_id")
                    break
            
            if output_format == 'base64':
                output = base64.b64encode(result["data"]).decode('utf-8')
            elif output_format == 'hex':
                output = result["data"].hex()
            else:
                output = result["data"].decode('utf-8', errors='replace')
            
            return jsonify({
                'success': True,
                'action': 'encrypt',
                'output': output,
                'output_format': output_format,
                'data_id': data_id,
                'session_id': browser_session_id,
                'saoyut': result["saoyut"],
                'seed': seed,
                'order': tech_order
            })
        
        else:
            seed = request.form.get('seed', '')
            saoyut_json = request.form.get('saoyut', '')
            
            if not seed or not saoyut_json:
                return jsonify({'success': False, 'error': 'Seed and SAOYUT required for decryption'}), 400
            
            saoyut_data = json.loads(saoyut_json)
            result = spc_decrypt_with_order(file_data, saoyut_data, seed, tech_order, browser_session_id)
            
            if output_format == 'base64':
                output = base64.b64encode(result).decode('utf-8')
            elif output_format == 'hex':
                output = result.hex()
            else:
                output = result.decode('utf-8', errors='replace')
            
            return jsonify({
                'success': True,
                'action': 'decrypt',
                'output': output,
                'output_format': output_format
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/encrypt', methods=['POST'])
def encrypt():
    """
    Mã hóa dữ liệu.
    Fingerprint CHỈ để AUDIT, KHÔNG tham gia vào seed.
    """
    try:
        data = request.json
        text = data.get('text', '')
        seed = data.get('seed', '')
        technique_order = data.get('order', list(ALL_TECHNIQUES.keys()))
        browser_session_id = data.get('session_id')
        session_mode = data.get('session_mode', True)
        fingerprint = data.get('fingerprint', '')
        
        if not fingerprint:
            fingerprint = request.headers.get('X-Device-Fingerprint', '')
        
        print(f"[ENCRYPT v{SPC_VERSION}] session_mode: {session_mode}")
        print(f"[ENCRYPT v{SPC_VERSION}] browser_session_id: {browser_session_id}")
        print(f"[ENCRYPT v{SPC_VERSION}] fingerprint (audit): {fingerprint}")
        print(f"[ENCRYPT v{SPC_VERSION}] seed input: {seed}")
        
        if not seed:
            seed = hashlib.sha256(os.urandom(32)).hexdigest()
            print(f"[ENCRYPT v{SPC_VERSION}] Auto-generated seed: {seed}")
        
        text_bytes = text.encode('utf-8')
        
        # CHỈ gắn session vào seed, KHÔNG gắn fingerprint
        effective_seed = seed
        if session_mode and browser_session_id:
            effective_seed = f"{seed}_{browser_session_id}"
            print(f"[ENCRYPT v{SPC_VERSION}] Session bound to seed")
        else:
            print(f"[ENCRYPT v{SPC_VERSION}] Seed is pure")
        
        print(f"[ENCRYPT v{SPC_VERSION}] effective_seed: {effective_seed}")
        
        result = spc_encrypt_with_order(
            text_bytes,
            effective_seed,
            technique_order,
            browser_session_id,
            fingerprint=fingerprint
        )
        
        encrypted_b64 = base64.b64encode(result["data"]).decode('utf-8')
        encrypted_hex = result["data"].hex()
        
        data_id = None
        segments_info = None
        for tech in result["saoyut"]["techniques"]:
            if tech["name"] == "L":
                segments_info = tech["metadata"]
                data_id = segments_info.get("data_id")
                break
        
        return jsonify({
            'success': True,
            'encrypted_b64': encrypted_b64,
            'encrypted_hex': encrypted_hex,
            'seed': seed,
            'seed_with_session': effective_seed,
            'effective_seed': effective_seed,
            'saoyut': result["saoyut"],
            'order': technique_order,
            'segments': segments_info,
            'data_id': data_id,
            'session_mode': session_mode,
            'fingerprint_bound': False,
            'fingerprint_audit': fingerprint,
            'spc_version': SPC_VERSION
        })
    except Exception as e:
        print(f"[ERROR] /encrypt: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/decrypt', methods=['POST'])
def decrypt():
    """
    Giải mã dữ liệu — NGHIÊM NGẶT, seed phải khớp CHÍNH XÁC.
    """
    try:
        print("=" * 60)
        print(f"[DECRYPT v{SPC_VERSION}] === NEW DECRYPT REQUEST ===")
        
        data = request.json
        
        encrypted_b64 = data.get('encrypted_b64', '')
        seed = data.get('seed', '')
        saoyut_data = data.get('saoyut', {})
        technique_order = data.get('order', [])
        browser_session_id = data.get('session_id')
        
        print(f"[DECRYPT v{SPC_VERSION}] seed: '{seed}'")
        print(f"[DECRYPT v{SPC_VERSION}] browser_session_id: {browser_session_id}")
        
        if not encrypted_b64:
            return jsonify({'success': False, 'error': 'No encrypted data provided'}), 400
        
        if not seed:
            return jsonify({'success': False, 'error': 'Seed is required!'}), 400
        
        if not saoyut_data or not saoyut_data.get('techniques'):
            return jsonify({'success': False, 'error': 'SAOYUT is required!'}), 400
        
        stored_fp_origin = saoyut_data.get('device_fingerprint_origin', '')
        if stored_fp_origin:
            print(f"[DECRYPT v{SPC_VERSION}] ℹ️ SAOYUT từ thiết bị: {stored_fp_origin}")
        
        encrypted_data = base64.b64decode(encrypted_b64)
        print(f"[DECRYPT v{SPC_VERSION}] Decoded size: {len(encrypted_data)} bytes")
        
        try:
            decrypted = spc_decrypt_with_order(
                encrypted_data,
                saoyut_data,
                seed,
                technique_order,
                browser_session_id
            )
            decrypted_text = decrypted.decode('utf-8', errors='replace')
            
            print(f"[DECRYPT v{SPC_VERSION}] ✅ Success! Size: {len(decrypted)} bytes")
            print("=" * 60)
            
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
                'hint': 'Seed must match EXACTLY with SAOYUT seed_hash.'
            }), 400
        except Exception as e:
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'Decryption failed: {str(e)}',
                'hint': 'Check if seed, SAOYUT, and technique order match!'
            }), 400
            
    except Exception as e:
        traceback.print_exc()
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
    print("=" * 60)
    print(f"🔐 SPC ENCRYPTOR PRO v{SPC_VERSION}")
    print(f"   Multi-version support: V1 (2.6.0/3.2.0), V2 (3.4.0), V3 ({SPC_VERSION}+)")
    print(f"   Security: HMAC-SHA256 + version whitelist + STRICT seed matching")
    print(f"   ⚠️ Seed phải khớp CHÍNH XÁC — KHÔNG tự đoán seed")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
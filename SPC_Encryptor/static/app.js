// ============================================================
// SPC ENCRYPTOR PRO v3.0 - MAIN JAVASCRIPT
// ============================================================

// ============================================================
// STATE
// ============================================================
const ALL_TECH = ['R', 'C', 'E', 'Z', 'S', 'H', 'D', 'B', 'P', 'L'];
const TECH_NAMES = {
    'R': 'Header Removal',
    'C': 'Cut & Swap',
    'E': 'Enigma',
    'Z': 'Zip Hiding',
    'S': 'Sharding',
    'H': 'Header Masking',
    'D': 'Double Fake',
    'B': 'Hashing Chain',
    'P': 'RAM-only',
    'L': 'Low Storage Sharefile'
};
let currentOrder = [...ALL_TECH];
let currentMode = 'encrypt';
let lastResult = null;
let browserSessionId = null;
let dataId = null;
let sessionTimerInterval = null;
let sessionTimeout = 3600;

// ============================================================
// FINGERPRINT
// ============================================================
function getDeviceFingerprint() {
    let deviceId = localStorage.getItem('spc_device_id');
    if (!deviceId) {
        deviceId = 'fp_' + Math.random().toString(36).substring(2, 10);
        localStorage.setItem('spc_device_id', deviceId);
    }
    return deviceId;
}

// ============================================================
// SESSION
// ============================================================
async function createNewSession() {
    try {
        const response = await fetch('/api/session/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const result = await response.json();
        if (result.success) {
            browserSessionId = result.session_id;
            sessionTimeout = result.timeout || 3600;
            updateSessionDisplay(browserSessionId);
            await registerFingerprint(browserSessionId);
            showStatus('✅ Phiên mới đã được tạo!', 'success');
            loadSegments();
            startSessionTimer();
        } else {
            showStatus('❌ ' + result.error, 'error');
        }
    } catch (e) {
        showStatus('❌ Lỗi: ' + e.message, 'error');
    }
}

async function registerFingerprint(sessionId) {
    const fingerprint = getDeviceFingerprint();
    document.getElementById('fingerprintDisplay').textContent = fingerprint;
    try {
        await fetch('/api/fingerprint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, fingerprint: fingerprint })
        });
    } catch(e) { console.error('Fingerprint error:', e); }
}

function updateSessionDisplay(sessionId) {
    document.getElementById('sessionDisplay').textContent = sessionId || 'Chưa tạo';
    document.getElementById('sessionStatus').textContent = sessionId ? '✅ Hoạt động' : '❌ Chưa có phiên';
    document.getElementById('sessionStatus').className = 'badge' + (sessionId ? ' badge-success' : '');
}

function updateDataIdDisplay(id) {
    document.getElementById('dataIdDisplay').textContent = id || 'Chưa có';
    document.getElementById('dataIdDisplay').style.color = id ? '#00ff88' : '#888';
    if (id) {
        document.getElementById('dataIdBadge').style.display = 'inline';
        document.getElementById('dataIdBadge').textContent = '🔒 ' + id.substring(0, 8) + '...';
    } else {
        document.getElementById('dataIdBadge').style.display = 'none';
    }
}

function startSessionTimer() {
    if (sessionTimerInterval) clearInterval(sessionTimerInterval);
    let remaining = sessionTimeout;
    updateTimerDisplay(remaining);
    sessionTimerInterval = setInterval(() => {
        remaining--;
        updateTimerDisplay(remaining);
        if (remaining <= 0) {
            clearInterval(sessionTimerInterval);
            showStatus('⏰ Phiên đã hết hạn! Tạo phiên mới.', 'warning');
            updateSessionDisplay(null);
        }
    }, 1000);
}

function updateTimerDisplay(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    document.getElementById('sessionTimer').textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    if (seconds < 300) document.getElementById('sessionTimer').style.color = '#ff6b6b';
    else if (seconds < 600) document.getElementById('sessionTimer').style.color = '#f39c12';
    else document.getElementById('sessionTimer').style.color = '#00ff88';
}

function clearSession() {
    if (sessionTimerInterval) clearInterval(sessionTimerInterval);
    browserSessionId = null;
    dataId = null;
    updateSessionDisplay(null);
    updateDataIdDisplay(null);
    document.getElementById('fingerprintDisplay').textContent = 'Chưa đăng ký';
    document.getElementById('sessionTimer').textContent = '--:--';
    showStatus('🗑️ Phiên đã bị xóa', 'info');
    loadSegments();
}

// ============================================================
// TECHNIQUES - DRAG & DROP + TOUCH
// ============================================================
let draggedItem = null;
let touchData = null;

function renderOrder() {
    const container = document.getElementById('techniqueOrder');
    container.innerHTML = '';
    currentOrder.forEach(name => {
        const tag = document.createElement('span');
        tag.className = 'tech-tag';
        tag.innerHTML = `${name} <span class="remove" onclick="removeTechnique('${name}')">×</span>`;
        tag.title = TECH_NAMES[name] || name;
        tag.draggable = true;
        tag.dataset.name = name;
        
        tag.addEventListener('dragstart', handleDragStart);
        tag.addEventListener('dragover', handleDragOver);
        tag.addEventListener('drop', handleDrop);
        tag.addEventListener('dragend', handleDragEnd);
        
        tag.addEventListener('touchstart', handleTouchStart, { passive: true });
        tag.addEventListener('touchmove', handleTouchMove, { passive: false });
        tag.addEventListener('touchend', handleTouchEnd, { passive: true });
        
        container.appendChild(tag);
    });
    document.getElementById('orderDisplay').textContent = currentOrder.join(' → ');
    updateTechCount();
}

function handleDragStart(e) {
    draggedItem = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.name);
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    document.querySelectorAll('.tech-tag').forEach(el => el.classList.remove('drag-over'));
    if (this !== draggedItem) this.classList.add('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    document.querySelectorAll('.tech-tag').forEach(el => el.classList.remove('drag-over'));
    if (draggedItem && this !== draggedItem) {
        const fromIdx = currentOrder.indexOf(draggedItem.dataset.name);
        const toIdx = currentOrder.indexOf(this.dataset.name);
        if (fromIdx > -1 && toIdx > -1) {
            const [removed] = currentOrder.splice(fromIdx, 1);
            currentOrder.splice(toIdx, 0, removed);
            renderOrder();
        }
    }
}

function handleDragEnd(e) {
    document.querySelectorAll('.tech-tag').forEach(el => el.classList.remove('dragging', 'drag-over'));
    draggedItem = null;
}

let touchClone = null;
let touchTarget = null;

function handleTouchStart(e) {
    touchData = {
        element: this,
        name: this.dataset.name,
        startX: e.touches[0].clientX,
        startY: e.touches[0].clientY
    };
    this.classList.add('touch-drag');
    
    touchClone = this.cloneNode(true);
    touchClone.className = 'tech-tag touch-clone';
    touchClone.style.left = (e.touches[0].clientX - 30) + 'px';
    touchClone.style.top = (e.touches[0].clientY - 15) + 'px';
    document.body.appendChild(touchClone);
}

function handleTouchMove(e) {
    e.preventDefault();
    if (!touchClone || !touchData) return;
    
    const touch = e.touches[0];
    touchClone.style.left = (touch.clientX - 30) + 'px';
    touchClone.style.top = (touch.clientY - 15) + 'px';
    
    const elements = document.elementsFromPoint(touch.clientX, touch.clientY);
    const target = elements.find(el => el.classList && el.classList.contains('tech-tag') && el !== touchData.element);
    
    document.querySelectorAll('.tech-tag').forEach(el => el.classList.remove('drag-over'));
    if (target) {
        target.classList.add('drag-over');
        touchTarget = target;
    } else {
        touchTarget = null;
    }
}

function handleTouchEnd(e) {
    if (touchData) {
        touchData.element.classList.remove('touch-drag');
    }
    
    if (touchClone) {
        document.body.removeChild(touchClone);
        touchClone = null;
    }
    
    document.querySelectorAll('.tech-tag').forEach(el => el.classList.remove('drag-over'));
    
    if (touchTarget && touchData) {
        const fromIdx = currentOrder.indexOf(touchData.name);
        const toIdx = currentOrder.indexOf(touchTarget.dataset.name);
        if (fromIdx > -1 && toIdx > -1 && fromIdx !== toIdx) {
            const [removed] = currentOrder.splice(fromIdx, 1);
            currentOrder.splice(toIdx, 0, removed);
            renderOrder();
        }
    }
    
    touchData = null;
    touchTarget = null;
}

function removeTechnique(name) {
    if (currentOrder.length <= 1) {
        showStatus('⚠️ Cần ít nhất 1 kỹ thuật!', 'warning');
        return;
    }
    currentOrder = currentOrder.filter(n => n !== name);
    renderOrder();
}

function resetOrder() { currentOrder = [...ALL_TECH]; renderOrder(); }
function shuffleOrder() {
    for (let i = currentOrder.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [currentOrder[i], currentOrder[j]] = [currentOrder[j], currentOrder[i]];
    }
    renderOrder();
}
function toggleAllTech() {
    if (currentOrder.length === ALL_TECH.length) {
        currentOrder = [currentOrder[0]];
    } else {
        currentOrder = [...ALL_TECH];
    }
    renderOrder();
}
function updateTechCount() {
    document.getElementById('techCount').textContent = `${currentOrder.length}/${ALL_TECH.length}`;
}

// ============================================================
// SEED
// ============================================================
function generateSeed() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    const seed = Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
    document.getElementById('seedInput').value = seed;
    showStatus('✅ Seed đã được tạo!', 'success');
}

// ============================================================
// SAOYUT
// ============================================================
function loadSampleSAOYUT() {
    const sample = {
        "seed_hash": "12e5f286fc804dd4849d7eba90142a9e1b3addb55b659089080f377b45d6c337",
        "techniques": [
            {"metadata": {"header": "48656c6c6f20576f726c642120546869"}, "name": "R"},
            {"metadata": {"cut_point": 17, "first_len": 17, "second_len": 18}, "name": "C"},
            {"metadata": {}, "name": "E"},
            {"metadata": {"fake_header": "5458545f4845414445523a"}, "name": "Z"},
            {"metadata": {"xor_key": "dcb3901dbc6962742cd81a58f0eaa49a"}, "name": "H"}
        ]
    };
    document.getElementById('saoyutInput').value = JSON.stringify(sample, null, 2);
    updateSaoyutStatus('✅ Có dữ liệu', 'success');
    showStatus('📄 Đã load mẫu SAOYUT!', 'success');
}

function clearSAOYUT() {
    document.getElementById('saoyutInput').value = '';
    updateSaoyutStatus('Chưa có', '');
}

function validateSAOYUT() {
    try {
        const text = document.getElementById('saoyutInput').value.trim();
        if (!text) { showStatus('⚠️ Chưa có SAOYUT!', 'warning'); return; }
        const data = JSON.parse(text);
        if (data.techniques && Array.isArray(data.techniques)) {
            updateSaoyutStatus('✅ Hợp lệ', 'success');
            showStatus('✅ SAOYUT hợp lệ!', 'success');
        } else {
            throw new Error('Thiếu techniques');
        }
    } catch (e) {
        updateSaoyutStatus('❌ Không hợp lệ', 'error');
        showStatus('❌ SAOYUT không hợp lệ: ' + e.message, 'error');
    }
}

function updateSaoyutStatus(text, type) {
    const el = document.getElementById('saoyutStatus');
    el.textContent = text;
    el.className = 'badge' + (type ? ' badge-' + type : '');
}

function getSAOYUT() {
    try {
        const text = document.getElementById('saoyutInput').value.trim();
        if (!text) return null;
        return JSON.parse(text);
    } catch (e) { return null; }
}

function copySAOYUTInput() {
    const text = document.getElementById('saoyutInput').value;
    if (text) { navigator.clipboard.writeText(text); showStatus('✅ Đã copy SAOYUT!', 'success'); }
}

function copySAOYUTDisplay() {
    const text = document.getElementById('saoyutDisplay').textContent;
    if (text && text !== 'Chưa có...') {
        navigator.clipboard.writeText(text);
        showStatus('✅ Đã copy SAOYUT!', 'success');
    }
}

function syncSAOYUT() {
    const text = document.getElementById('saoyutDisplay').textContent;
    if (text && text !== 'Chưa có...') {
        document.getElementById('saoyutInput').value = text;
        updateSaoyutStatus('✅ Đã sync', 'success');
        showStatus('🔄 Đã sync SAOYUT sang ô nhập!', 'success');
    } else {
        showStatus('⚠️ Không có SAOYUT để sync!', 'warning');
    }
}

function exportSAOYUTFile() {
    const text = document.getElementById('saoyutInput').value.trim();
    if (!text) { showStatus('⚠️ Chưa có SAOYUT!', 'warning'); return; }
    downloadTextFile(text, 'saoyut.json');
}

function importSAOYUTFile() {
    document.getElementById('fileInput').click();
}

// ============================================================
// FILE HANDLING
// ============================================================
function handleFileUpload() {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) return;
    document.getElementById('uploadedFileName').textContent = '📎 ' + file.name;
    document.getElementById('fileBadge').style.display = 'inline';
    const reader = new FileReader();
    reader.onload = function(e) {
        const content = e.target.result;
        if (file.name.endsWith('.saoyut') || file.name.endsWith('.json')) {
            document.getElementById('saoyutInput').value = content;
            validateSAOYUT();
            showStatus('📄 Đã load file SAOYUT!', 'success');
        } else {
            document.getElementById('inputText').value = content;
            updateCharCount();
            showStatus('📄 Đã load file: ' + file.name, 'success');
        }
    };
    reader.readAsText(file);
}

function downloadTextFile(content, filename) {
    const blob = new Blob([content], {type: 'text/plain;charset=utf-8'});
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
}

function downloadResult() {
    const activeTab = document.querySelector('.tab-content.active');
    const text = activeTab ? activeTab.querySelector('.output-box').textContent : '';
    if (text && text !== 'Chưa có...') {
        let ext = '.txt';
        const tabId = activeTab.id;
        if (tabId === 'tab-b64') ext = '.b64.txt';
        else if (tabId === 'tab-hex') ext = '.hex.txt';
        else if (tabId === 'tab-plain') ext = '.txt';
        downloadTextFile(text, 'spc_result' + ext);
        showStatus('💾 Đã tải xuống!', 'success');
    } else {
        showStatus('⚠️ Chưa có kết quả để tải!', 'warning');
    }
}

function saveInputAsFile() {
    const text = document.getElementById('inputText').value;
    if (text) {
        downloadTextFile(text, 'spc_input.txt');
        showStatus('💾 Đã lưu input!', 'success');
    } else {
        showStatus('⚠️ Không có dữ liệu!', 'warning');
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
}

function copyOutput() {
    const activeTab = document.querySelector('.tab-content.active');
    const text = activeTab ? activeTab.querySelector('.output-box').textContent : '';
    if (text && text !== 'Chưa có...') {
        navigator.clipboard.writeText(text);
        showStatus('✅ Đã copy!', 'success');
    }
}

function copySeed() {
    const text = document.getElementById('seedDisplay').textContent;
    if (text && text !== 'Chưa có seed') {
        navigator.clipboard.writeText(text);
        showStatus('✅ Đã copy Seed!', 'success');
    }
}

function loadSample() {
    if (currentMode === 'encrypt') {
        document.getElementById('inputText').value = 'Hello World! This is SPC Encryption system by Mr.MR';
        showStatus('📄 Đã load mẫu mã hóa!', 'info');
    } else {
        document.getElementById('inputText').value = 'iOvEQvQsIzBpiiB6zKK2l+KVnRHoRkk8AN55R8r48L79+6I5shtPezvnMUDl9w==';
        document.getElementById('seedInput').value = 'MRhat';
        currentOrder = ['H', 'Z', 'E', 'C', 'R'];
        renderOrder();
        loadSampleSAOYUT();
        showStatus('📄 Đã load mẫu giải mã! Hãy bấm "Giải mã"', 'info');
    }
    updateCharCount();
}

function clearInput() {
    document.getElementById('inputText').value = '';
    updateCharCount();
}

function updateCharCount() {
    const count = document.getElementById('inputText').value.length;
    document.getElementById('charCount').textContent = count + ' ký tự';
}

// ============================================================
// MAIN ACTION
// ============================================================
async function executeAction() {
    if (currentMode === 'encrypt') {
        await encrypt();
    } else {
        await decrypt();
    }
}

// ============================================================
// ENCRYPT
// ============================================================
async function encrypt() {
    const text = document.getElementById('inputText').value;
    const seed = document.getElementById('seedInput').value;
    if (!text) { showStatus('⚠️ Vui lòng nhập dữ liệu!', 'error'); return; }
    if (!browserSessionId) await createNewSession();
    showStatus('⏳ Đang mã hóa với ' + currentOrder.length + ' kỹ thuật...', 'info');
    try {
        const response = await fetch('/encrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: text,
                seed: seed,
                order: currentOrder,
                session_id: browserSessionId
            })
        });
        const result = await response.json();
        if (!result.success) { showStatus('❌ ' + result.error, 'error'); return; }
        lastResult = result;
        document.getElementById('outputB64').textContent = result.encrypted_b64;
        document.getElementById('outputHex').textContent = result.encrypted_hex;
        document.getElementById('outputPlain').textContent = text;
        document.getElementById('seedDisplay').textContent = result.seed;
        
        const saoyutDisplay = document.getElementById('saoyutDisplay');
        saoyutDisplay.textContent = JSON.stringify(result.saoyut, null, 2);
        saoyutDisplay.style.color = '#00ff88';
        document.getElementById('saoyutInput').value = JSON.stringify(result.saoyut, null, 2);
        updateSaoyutStatus('✅ Đã sinh', 'success');
        document.getElementById('compareCard').style.display = 'none';
        
        if (result.data_id) {
            dataId = result.data_id;
            updateDataIdDisplay(dataId);
        }
        
        let hasL = false;
        for (const tech of result.saoyut.techniques) {
            if (tech.name === 'L') { hasL = true; break; }
        }
        if (hasL) {
            showStatus('📦 Kỹ thuật L phát hiện! Data ID: ' + dataId, 'info');
            setTimeout(() => loadSegments(), 500);
        }
        showStatus('✅ Mã hóa thành công! ' + currentOrder.length + ' kỹ thuật đã áp dụng.', 'success');
    } catch (e) {
        showStatus('❌ Lỗi: ' + e.message, 'error');
    }
}

// ============================================================
// DECRYPT
// ============================================================
async function decrypt() {
    const input = document.getElementById('inputText').value.trim();
    const seed = document.getElementById('seedInput').value;
    if (!input) { showStatus('⚠️ Vui lòng nhập Base64!', 'error'); return; }
    if (!seed) { showStatus('⚠️ Vui lòng nhập seed!', 'error'); return; }
    const saoyut = getSAOYUT();
    if (!saoyut) { showStatus('⚠️ Vui lòng nhập SAOYUT!', 'error'); return; }
    showStatus('⏳ Đang giải mã với ' + currentOrder.length + ' kỹ thuật...', 'info');
    try {
        const response = await fetch('/decrypt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                encrypted_b64: input,
                seed: seed,
                saoyut: saoyut,
                order: currentOrder,
                session_id: browserSessionId
            })
        });
        const result = await response.json();
        if (!result.success) {
            showStatus('❌ ' + result.error, 'error');
            if (result.hint) showStatus('💡 ' + result.hint, 'warning');
            return;
        }
        document.getElementById('outputPlain').textContent = result.decrypted_text;
        document.getElementById('outputB64').textContent = input;
        document.getElementById('seedDisplay').textContent = seed;
        
        const saoyutDisplay = document.getElementById('saoyutDisplay');
        saoyutDisplay.textContent = JSON.stringify(saoyut, null, 2);
        saoyutDisplay.style.color = '#f39c12';
        
        document.getElementById('originalText').innerHTML = 
            `<span style="color:#888;font-size:11px;">📦 Base64 (input)</span><br>${input.substring(0, 60)}${input.length > 60 ? '...' : ''}`;
        document.getElementById('originalText').style.color = '#f39c12';
        document.getElementById('decryptedText').innerHTML = 
            `<span style="color:#888;font-size:11px;">📝 Plaintext (output)</span><br>${result.decrypted_text}`;
        document.getElementById('decryptedText').style.color = '#00ff88';
        document.getElementById('compareLabel1').textContent = '📦 Base64 (input)';
        document.getElementById('compareLabel2').textContent = '📝 Plaintext (output)';
        
        const compareCard = document.getElementById('compareCard');
        compareCard.style.display = 'block';
        const compareResult = document.getElementById('compareResult');
        compareResult.innerHTML = '✅ GIẢI MÃ THÀNH CÔNG! 🎉';
        compareResult.style.color = '#00ff88';
        compareResult.style.fontSize = '20px';
        showStatus('✅ Giải mã thành công!', 'success');
    } catch (e) {
        showStatus('❌ Lỗi: ' + e.message, 'error');
    }
}

// ============================================================
// SEGMENT MANAGER
// ============================================================
async function loadSegments() {
    if (!dataId) {
        document.getElementById('segmentList').innerHTML = 
            '<div class="text-muted" style="padding:10px; text-align:center;">Chưa có Data ID. Hãy mã hóa hoặc upload segment để có data_id.</div>';
        document.getElementById('segmentCount').textContent = '0 segments';
        return;
    }
    
    try {
        const url = `/segments/list?data_id=${dataId}&session_id=${browserSessionId}`;
        const response = await fetch(url);
        const result = await response.json();
        
        const container = document.getElementById('segmentList');
        const count = document.getElementById('segmentCount');
        
        if (!result.success || !result.segments || result.segments.length === 0) {
            container.innerHTML = '<div class="text-muted" style="padding:10px; text-align:center;">Chưa có segment nào. Upload segments để giải mã.</div>';
            count.textContent = '0 segments';
            return;
        }
        
        let html = '';
        result.segments.forEach((seg) => {
            const sizeKB = (seg.size / 1024).toFixed(2);
            html += `<div class="segment-item"><span>${seg.filename}</span><span class="size">${sizeKB} KB</span></div>`;
        });
        
        container.innerHTML = html;
        count.textContent = `${result.segments.length} segments`;
        
    } catch (e) {
        console.error('Error loading segments:', e);
        document.getElementById('segmentList').innerHTML = 
            '<div class="text-muted" style="padding:10px; text-align:center;">Lỗi: ' + e.message + '</div>';
    }
}

async function downloadAllSegments() {
    if (!dataId) {
        showStatus('⚠️ Không có data_id!', 'warning');
        return;
    }
    
    const saoyutText = document.getElementById('saoyutDisplay').textContent;
    if (!saoyutText || saoyutText === 'Chưa có...') {
        showStatus('⚠️ Không có SAOYUT!', 'warning');
        return;
    }
    
    try {
        const saoyut = JSON.parse(saoyutText);
        let numSegments = 0;
        for (const tech of saoyut.techniques) {
            if (tech.name === 'L') { 
                numSegments = tech.metadata.num_segments; 
                break; 
            }
        }
        
        if (numSegments === 0) {
            showStatus('⚠️ Không tìm thấy kỹ thuật L!', 'warning');
            return;
        }
        
        showStatus('⏳ Đang tạo file zip...', 'info');
        
        const response = await fetch('/segments/download-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                data_id: dataId,
                num_segments: numSegments,
                session_id: browserSessionId
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            showStatus('❌ ' + (error.error || 'Lỗi tải segments'), 'error');
            return;
        }
        
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `segments_${dataId}.zip`;
        link.click();
        URL.revokeObjectURL(link.href);
        showStatus('✅ Đã tải xuống!', 'success');
    } catch (e) {
        showStatus('❌ Lỗi: ' + e.message, 'error');
    }
}

function uploadSegments() {
    if (!browserSessionId) {
        showStatus('⚠️ Cần có phiên trình duyệt!', 'warning');
        createNewSession();
        return;
    }
    document.getElementById('segmentFileInput').click();
}

// ============================================================
// UPLOAD SEGMENTS
// ============================================================
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('segmentFileInput').addEventListener('change', async function(e) {
        const files = e.target.files;
        if (files.length === 0) return;
        
        if (!browserSessionId) {
            await createNewSession();
        }
        
        // Kiểm tra file có phải zip không
        const firstFile = files[0];
        if (firstFile.name.endsWith('.zip')) {
            const formData = new FormData();
            formData.append('session_id', browserSessionId);
            formData.append('zip_file', firstFile);
            
            showStatus('⏳ Đang upload ZIP...', 'info');
            
            try {
                const response = await fetch(`/segments/upload-zip?session_id=${browserSessionId}`, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showStatus(`✅ Đã upload ${result.count} segments từ ZIP!`, 'success');
                    if (result.data_id) {
                        dataId = result.data_id;
                        updateDataIdDisplay(dataId);
                    }
                    loadSegments();
                } else {
                    showStatus('❌ ' + result.error, 'error');
                }
            } catch (err) {
                showStatus('❌ Lỗi: ' + err.message, 'error');
            }
            
            e.target.value = '';
            return;
        }
        
        // Upload .dat files
        const formData = new FormData();
        formData.append('session_id', browserSessionId);
        let validFiles = 0;
        
        for (const file of files) {
            if (file.name.endsWith('.dat')) {
                formData.append('segments', file);
                validFiles++;
            }
        }
        
        if (validFiles === 0) {
            showStatus('⚠️ Không có file .dat hợp lệ!', 'warning');
            e.target.value = '';
            return;
        }
        
        showStatus('⏳ Đang upload segments...', 'info');
        
        try {
            const response = await fetch(`/segments/upload?session_id=${browserSessionId}`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                if (result.data_id) {
                    dataId = result.data_id;
                    updateDataIdDisplay(dataId);
                }
                showStatus(`✅ Đã upload ${result.count} segments!`, 'success');
                loadSegments();
            } else {
                showStatus('❌ ' + result.error, 'error');
            }
        } catch (err) {
            showStatus('❌ Lỗi: ' + err.message, 'error');
        }
        
        e.target.value = '';
    });
});

// ============================================================
// CHECK SEGMENT STATUS
// ============================================================
async function checkSegmentStatus() {
    if (!browserSessionId) {
        showStatus('⚠️ Chưa có phiên trình duyệt!', 'warning');
        return;
    }
    
    try {
        const sessionRes = await fetch('/api/session/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: browserSessionId })
        });
        const sessionData = await sessionRes.json();
        
        const timerText = document.getElementById('sessionTimer').textContent;
        const isValid = sessionData.valid;
        
        let details = `📊 Browser Session: ${isValid ? '✅ Hoạt động' : '❌ Hết hạn'} | Còn: ${timerText}`;
        details += `\n📦 Data ID: ${dataId || 'Chưa có'}`;
        
        if (dataId) {
            const segRes = await fetch(`/segments/list?data_id=${dataId}&session_id=${browserSessionId}`);
            const segData = await segRes.json();
            
            if (segData.success && segData.segments && segData.segments.length > 0) {
                details += `\n📦 Segments: ${segData.segments.length}`;
                segData.segments.forEach(s => {
                    details += `\n   - ${s.filename} (${(s.size/1024).toFixed(2)} KB)`;
                });
            } else {
                details += '\n📦 Không có segment nào.';
            }
        }
        
        showStatus(details, isValid ? 'info' : 'warning');
        console.log('🔍 Session:', sessionData);
        
    } catch (e) {
        showStatus('❌ Lỗi kiểm tra: ' + e.message, 'error');
        console.error('Check error:', e);
    }
}

async function clearSegments() {
    if (!confirm('Xóa tất cả segments đã hết hạn?')) return;
    try {
        const response = await fetch('/segments/clear', { method: 'POST' });
        const result = await response.json();
        if (result.success) {
            showStatus('✅ Đã xóa segments hết hạn!', 'success');
            loadSegments();
        } else {
            showStatus('❌ ' + result.error, 'error');
        }
    } catch (e) { showStatus('❌ Lỗi: ' + e.message, 'error'); }
}

// ============================================================
// SEGMENT SIZE
// ============================================================
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function getSegmentSizeDisplay() {
    const select = document.getElementById('segmentSizeSelect');
    return formatSize(parseInt(select.value));
}

function updateSegmentSizeDisplay() {
    document.getElementById('currentSegmentSizeDisplay').textContent = getSegmentSizeDisplay();
}

async function updateSegmentSize() {
    const select = document.getElementById('segmentSizeSelect');
    const size = parseInt(select.value);
    updateSegmentSizeDisplay();
    try {
        const response = await fetch('/settings/segment-size', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size: size })
        });
        const result = await response.json();
        if (result.success) showStatus('✅ Segment size: ' + formatSize(result.segment_size), 'success');
    } catch (e) { console.error('Error updating segment size:', e); }
}

async function loadSegmentSize() {
    try {
        const response = await fetch('/settings/segment-size');
        const result = await response.json();
        if (result.success) {
            const select = document.getElementById('segmentSizeSelect');
            let bestOption = select.options[0];
            for (const option of select.options) {
                if (Math.abs(parseInt(option.value) - result.segment_size) < Math.abs(parseInt(bestOption.value) - result.segment_size)) {
                    bestOption = option;
                }
            }
            bestOption.selected = true;
            updateSegmentSizeDisplay();
        }
    } catch (e) { console.error('Error loading segment size:', e); }
}

// ============================================================
// CLEAR ALL
// ============================================================
function clearAll() {
    document.getElementById('inputText').value = '';
    document.getElementById('outputB64').textContent = 'Chưa có...';
    document.getElementById('outputHex').textContent = 'Chưa có...';
    document.getElementById('outputPlain').textContent = 'Chưa có...';
    document.getElementById('seedDisplay').textContent = 'Chưa có seed';
    document.getElementById('seedInput').value = '';
    document.getElementById('compareCard').style.display = 'none';
    document.getElementById('status').innerHTML = '';
    clearSAOYUT();
    document.getElementById('saoyutDisplay').textContent = 'Chưa có...';
    document.getElementById('saoyutDisplay').style.color = '#aaa';
    document.getElementById('uploadedFileName').textContent = '';
    document.getElementById('fileBadge').style.display = 'none';
    dataId = null;
    updateDataIdDisplay(null);
    lastResult = null;
    updateCharCount();
    loadSegments();
    showStatus('🗑️ Đã xóa tất cả', 'info');
}

function showStatus(message, type) {
    const status = document.getElementById('status');
    if (type) {
        status.className = 'status ' + type;
    } else {
        status.className = 'status';
    }
    status.textContent = message;
}

// ============================================================
// MODE
// ============================================================
function setMode(mode) {
    currentMode = mode;
    const encryptBtn = document.getElementById('modeEncrypt');
    const decryptBtn = document.getElementById('modeDecrypt');
    const actionBtn = document.getElementById('actionBtn');
    const hint = document.getElementById('inputHint');
    if (mode === 'encrypt') {
        encryptBtn.className = 'btn btn-sm btn-active';
        decryptBtn.className = 'btn btn-sm btn-outline';
        actionBtn.textContent = '🔐 Mã hóa';
        actionBtn.className = 'btn btn-primary';
        document.getElementById('modeLabel').textContent = 'Đang: Mã hóa';
        hint.innerHTML = '💡 Nhập <span class="highlight">văn bản</span> hoặc <span class="highlight">tải file lên</span> để mã hóa';
    } else {
        encryptBtn.className = 'btn btn-sm btn-outline';
        decryptBtn.className = 'btn btn-sm btn-active';
        actionBtn.textContent = '🔓 Giải mã';
        actionBtn.className = 'btn btn-secondary';
        document.getElementById('modeLabel').textContent = 'Đang: Giải mã';
        hint.innerHTML = '💡 Nhập <span class="highlight">Base64</span> hoặc <span class="highlight">tải file .spc</span> để giải mã';
    }
    document.getElementById('compareCard').style.display = 'none';
}

// ============================================================
// INIT
// ============================================================
function init() {
    renderOrder();
    updateCharCount();
    setMode('encrypt');
    updateTechCount();
    loadSegmentSize();
    setTimeout(createNewSession, 500);
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    const dropArea = document.getElementById('fileUploadArea');
    dropArea.addEventListener('dragover', (e) => { e.preventDefault(); dropArea.style.borderColor = '#00ff88'; });
    dropArea.addEventListener('dragleave', () => { dropArea.style.borderColor = 'rgba(255,255,255,0.15)'; });
    dropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        dropArea.style.borderColor = 'rgba(255,255,255,0.15)';
        if (e.dataTransfer.files.length) {
            document.getElementById('fileInput').files = e.dataTransfer.files;
            handleFileUpload();
        }
    });
    loadSegments();
    document.getElementById('inputText').addEventListener('input', updateCharCount);
    document.getElementById('segmentSizeSelect').addEventListener('change', updateSegmentSizeDisplay);
}

// ============================================================
// START
// ============================================================
document.addEventListener('DOMContentLoaded', init);
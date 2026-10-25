/**
 * Attendance Module
 * Handles session management and face recognition for attendance.
 */

let camera = null;
let activeSession = null;
let autoCapture = false;
let autoCaptureInterval = null;
let attendanceList = [];

document.addEventListener('DOMContentLoaded', () => {
    checkActiveSession();
    
    const startSessionBtn = document.getElementById('btnStartSession');
    const endSessionBtn = document.getElementById('btnEndSession');
    const startCameraBtn = document.getElementById('btnStartCamera');
    const markAttendanceBtn = document.getElementById('btnMarkAttendance');
    const autoCaptureToggle = document.getElementById('autoCaptureToggle');
    
    if (startSessionBtn) startSessionBtn.addEventListener('click', startSession);
    if (endSessionBtn) endSessionBtn.addEventListener('click', endSession);
    if (startCameraBtn) startCameraBtn.addEventListener('click', startCamera);
    if (markAttendanceBtn) markAttendanceBtn.addEventListener('click', markAttendance);
    if (autoCaptureToggle) autoCaptureToggle.addEventListener('change', toggleAutoCapture);
});

async function checkActiveSession() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/attendance/sessions/active`);
        if (response.ok) {
            const data = await response.json();
            const session = data.session;
            if (session && session.session_id) {
                activeSession = session;
                updateSessionInfo();
                
                const btnStart = document.getElementById('btnStartSession');
                const btnEnd = document.getElementById('btnEndSession');
                const btnCam = document.getElementById('btnStartCamera');
                if (btnStart) btnStart.disabled = true;
                if (btnEnd) {
                    btnEnd.disabled = false;
                    btnEnd.style.display = 'inline-block';
                }
                if (btnCam) btnCam.disabled = false;
                
                // Fetch existing attendance records for this session
                const recordsResponse = await fetch(`${CONFIG.API_BASE_URL}/attendance?session_id=${session.session_id}`);
                if (recordsResponse.ok) {
                    const recordsData = await recordsResponse.json();
                    attendanceList = recordsData.data || recordsData;
                    attendanceList.forEach((r, i) => updateAttendanceTable(r, i + 1));
                }
            }
        }
    } catch (error) {
        console.error('Failed to check active session:', error);
    }
}

async function startSession() {
    try {
        const course = document.getElementById('courseName').value;
        const dateInput = document.getElementById('sessionDate');
        const date = (dateInput && dateInput.value) ? dateInput.value : new Date().toISOString().split('T')[0];
        
        if (!course) {
            showResult('error', 'Please enter a course name');
            return;
        }
        
        const btnStart = document.getElementById('btnStartSession');
        if (btnStart) btnStart.disabled = true;
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/attendance/sessions/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ course, date })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start session');
        }
        
        const data = await response.json();
        activeSession = data.session || data;
        updateSessionInfo();
        
        const btnEnd = document.getElementById('btnEndSession');
        const btnCam = document.getElementById('btnStartCamera');
        if (btnStart) btnStart.disabled = true;
        if (btnEnd) {
            btnEnd.disabled = false;
            btnEnd.style.display = 'inline-block';
        }
        if (btnCam) btnCam.disabled = false;
        
        showResult('info', `Session started for ${course}`);
        
    } catch (error) {
        showResult('error', error.message);
        const btnStart = document.getElementById('btnStartSession');
        if (btnStart) btnStart.disabled = false;
    }
}

async function endSession() {
    if (!activeSession) return;
    
    try {
        document.getElementById('btnEndSession').disabled = true;
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/attendance/sessions/end`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ session_id: activeSession.session_id })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to end session');
        }
        
        const autoCaptureToggle = document.getElementById('autoCaptureToggle');
        if (autoCaptureToggle) {
            autoCaptureToggle.checked = false;
            toggleAutoCapture({ target: { checked: false } });
        }
        
        if (camera) {
            camera.stop();
        }
        
        activeSession = null;
        attendanceList = [];
        
        const tbody = document.getElementById('attendanceTableBody');
        if (tbody) tbody.innerHTML = '';
        
        const btnStart = document.getElementById('btnStartSession');
        const btnEnd = document.getElementById('btnEndSession');
        const btnCam = document.getElementById('btnStartCamera');
        const btnMark = document.getElementById('btnMarkAttendance');
        
        if (btnStart) btnStart.disabled = false;
        if (btnEnd) {
            btnEnd.disabled = true;
            btnEnd.style.display = 'none';
        }
        if (btnCam) btnCam.disabled = true;
        if (btnMark) btnMark.disabled = true;
        
        const display = document.getElementById('sessionIdDisplay');
        if (display) display.textContent = '';
        const statusBadge = document.getElementById('sessionStatus');
        if (statusBadge) {
            statusBadge.className = 'badge badge-error';
            statusBadge.textContent = 'Inactive';
        }
        
        showResult('info', 'Session ended successfully');
        
    } catch (error) {
        showResult('error', error.message);
        const btnEnd = document.getElementById('btnEndSession');
        if (btnEnd) btnEnd.disabled = false;
    }
}

async function startCamera() {
    try {
        if (!camera) {
            camera = new Camera('webcamVideo', 'captureCanvas');
        }
        const result = await camera.start();
        if (!result.success) throw new Error(result.error);
        
        const btnCam = document.getElementById('btnStartCamera');
        const btnMark = document.getElementById('btnMarkAttendance');
        const autoToggle = document.getElementById('autoCaptureToggle');
        
        if (btnCam) btnCam.disabled = true;
        if (btnMark) btnMark.disabled = false;
        if (autoToggle) autoToggle.disabled = false;
        
    } catch (error) {
        showResult('error', 'Failed to start camera: ' + error.message);
    }
}

async function markAttendance() {
    if (!camera || !camera.isActive || !activeSession) {
        if (!autoCapture) showResult('error', 'Camera and active session required');
        return;
    }
    
    try {
        document.getElementById('btnMarkAttendance').disabled = true;
        const imageData = camera.captureFrame();
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/recognize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ image: imageData, session_id: activeSession.session_id })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Recognition failed');
        }
        
        const result = await response.json();
        
        if (result.matched) {
            const isDuplicate = result.duplicate;
            const studentName = result.name || result.student_id;
            showResult(
                isDuplicate ? 'info' : 'success',
                isDuplicate ? `Already marked for ${studentName}` : `Attendance marked for ${studentName}`,
                { student_id: result.student_id, student_name: studentName, name: studentName, confidence: result.confidence }
            );
            
            if (!isDuplicate) {
                const record = {
                    student_id: result.student_id,
                    student_name: studentName,
                    timestamp: new Date().toISOString(),
                    confidence: result.confidence,
                    status: 'Present'
                };
                attendanceList.push(record);
                updateAttendanceTable(record, attendanceList.length);
                updateSessionInfo();
            }
        } else {
            showResult('warning', result.message || 'Face not recognized');
        }
        
    } catch (error) {
        showResult('error', error.message);
    } finally {
        if (!autoCapture) {
            document.getElementById('btnMarkAttendance').disabled = false;
        }
    }
}

function toggleAutoCapture(e) {
    autoCapture = e.target.checked;
    if (autoCapture) {
        document.getElementById('btnMarkAttendance').disabled = true;
        const interval = (typeof CONFIG !== 'undefined' && CONFIG.AUTO_CAPTURE_INTERVAL) ? CONFIG.AUTO_CAPTURE_INTERVAL : 3000;
        autoCaptureInterval = setInterval(markAttendance, interval);
        showResult('info', 'Auto-capture started');
    } else {
        clearInterval(autoCaptureInterval);
        document.getElementById('btnMarkAttendance').disabled = false;
        showResult('info', 'Auto-capture stopped');
    }
}

function showResult(type, message, data = null) {
    const resultBox = document.getElementById('recognitionResult');
    const resultName = document.getElementById('resultName');
    const resultId = document.getElementById('resultId');
    const resultConfidenceText = document.getElementById('resultConfidenceText');
    const resultConfidenceBar = document.getElementById('resultConfidenceBar');
    const resultStatus = document.getElementById('resultStatus');
    const resultAvatar = document.getElementById('resultAvatar');

    if (type === 'success' || type === 'info') {
        if (resultName && data) resultName.textContent = data.student_name || data.name || data.student_id || 'Recognized';
        if (resultId && data) resultId.textContent = data.student_id || '--';
        if (resultAvatar) resultAvatar.textContent = '✅';
        
        const confPercent = data && data.confidence ? Math.round(data.confidence * 100) : 0;
        if (resultConfidenceText) resultConfidenceText.textContent = `${confPercent}%`;
        if (resultConfidenceBar) {
            resultConfidenceBar.style.width = `${confPercent}%`;
            resultConfidenceBar.style.backgroundColor = 'var(--success, #10b981)';
        }
        
        if (resultStatus) {
            resultStatus.className = 'badge badge-success';
            resultStatus.textContent = type === 'info' ? 'Already Marked' : 'Present';
        }
    } else {
        if (resultName) resultName.textContent = '--';
        if (resultId) resultId.textContent = message;
        if (resultAvatar) resultAvatar.textContent = type === 'warning' ? '⚠️' : '❌';
        if (resultConfidenceText) resultConfidenceText.textContent = '0%';
        if (resultConfidenceBar) {
            resultConfidenceBar.style.width = '0%';
            resultConfidenceBar.style.backgroundColor = 'var(--error, #ef4444)';
        }
        if (resultStatus) {
            resultStatus.className = type === 'warning' ? 'badge badge-warning' : 'badge badge-error';
            resultStatus.textContent = type === 'warning' ? 'Not Recognized' : 'Error';
        }
    }

    if (resultBox) {
        resultBox.className = `alert alert-${type}`;
        let html = `<strong>${message}</strong>`;
        if (data && (type === 'success' || type === 'info')) {
            html += `<br>Student ID: ${data.student_id}`;
            if (data.confidence) {
                html += `<br>Confidence: ${(data.confidence * 100).toFixed(1)}%`;
            }
        }
        resultBox.innerHTML = html;
        resultBox.style.display = 'block';

        if (type === 'error' || type === 'warning' || type === 'info') {
            setTimeout(() => {
                if (!autoCapture && resultBox) resultBox.style.display = 'none';
            }, 5000);
        }
    }
}

function updateAttendanceTable(record, index) {
    const tbody = document.getElementById('attendanceTableBody') || document.querySelector('#attendanceTable tbody');
    if (!tbody) return;
    
    const tr = document.createElement('tr');
    
    const time = new Date(record.timestamp || new Date()).toLocaleTimeString();
    const conf = record.confidence ? (record.confidence * 100).toFixed(1) + '%' : '-';
    
    tr.innerHTML = `
        <td>${index}</td>
        <td>${record.student_id}</td>
        <td>${record.student_name || record.name || '-'}</td>
        <td>${time}</td>
        <td>${conf}</td>
        <td><span class="badge badge-success">Present</span></td>
    `;
    
    tbody.insertBefore(tr, tbody.firstChild);
}

function updateSessionInfo() {
    if (!activeSession) return;
    
    const statusBadge = document.getElementById('sessionStatus');
    if (statusBadge) {
        statusBadge.className = 'badge badge-success';
        statusBadge.textContent = `Active: ${activeSession.course || ''}`;
    }
    
    const display = document.getElementById('sessionIdDisplay');
    if (display) {
        display.textContent = `Session: ${activeSession.session_id || ''} | Present: ${attendanceList.length}`;
    }
}

/**
 * Student Registration Module
 * Handles student info submission and face sample capture.
 */

let camera = null;
let currentStudentId = null;
let sampleCount = 0;
const MAX_SAMPLES = 10;
let isRegistered = false;

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registrationForm');
    const registerBtn = document.getElementById('btnRegister');
    const startCameraBtn = document.getElementById('btnStartCamera');
    const captureBtn = document.getElementById('btnCaptureSample');
    const retakeBtn = document.getElementById('btnRetake');
    const completeBtn = document.getElementById('btnComplete');
    
    if (registerForm) registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await registerStudent();
    });
    if (registerBtn) registerBtn.addEventListener('click', registerStudent);
    
    if (startCameraBtn) startCameraBtn.addEventListener('click', startCamera);
    if (captureBtn) captureBtn.addEventListener('click', captureSample);
    if (retakeBtn) retakeBtn.addEventListener('click', retakeLastSample);
    if (completeBtn) completeBtn.addEventListener('click', completeRegistration);
});

async function registerStudent() {
    try {
        const submitBtn = document.getElementById('btnRegister');
        if (submitBtn) submitBtn.disabled = true;
        
        const studentId = document.getElementById('studentId').value;
        const name = document.getElementById('studentName').value;
        const department = document.getElementById('department').value;
        const semester = document.getElementById('semester').value;
        const section = document.getElementById('section').value;
        const email = document.getElementById('email').value;
        
        const payload = {
            student_id: studentId,
            name: name,
            department: department,
            semester: parseInt(semester),
            section: section,
            email: email
        };
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/students/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            let msg = 'Registration failed';
            if (typeof error.detail === 'string') {
                msg = error.detail;
            } else if (Array.isArray(error.detail)) {
                msg = error.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join('; ');
            } else if (error.detail) {
                msg = JSON.stringify(error.detail);
            }
            throw new Error(msg);
        }
        
        const data = await response.json();
        currentStudentId = studentId;
        isRegistered = true;
        
        showStatus('Student registered successfully. Please proceed to capture face samples.', 'success');
        
        // Enable camera button
        const startCameraBtn = document.getElementById('btnStartCamera');
        if (startCameraBtn) startCameraBtn.disabled = false;
        
    } catch (error) {
        showStatus(error.message, 'error');
    } finally {
        const submitBtn = document.getElementById('btnRegister');
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function startCamera() {
    try {
        if (!camera) {
            // Assuming Camera is globally available from camera.js
            camera = new Camera('webcamVideo', 'captureCanvas');
        }
        const result = await camera.start();
        if (!result.success) throw new Error(result.error);
        
        document.getElementById('btnStartCamera').disabled = true;
        document.getElementById('btnCaptureSample').disabled = false;
        
        showStatus('Camera started. Please capture face samples with different poses.', 'info');
    } catch (error) {
        showStatus('Failed to start camera: ' + error.message, 'error');
    }
}

async function captureSample() {
    if (!camera || !camera.isActive) {
        showStatus('Please start the camera first.', 'warning');
        return;
    }
    
    if (!currentStudentId) {
        const idField = document.getElementById('studentId');
        if (idField && idField.value.trim()) {
            currentStudentId = idField.value.trim();
        } else {
            showStatus('Please enter a Student ID and click "Register Student" first.', 'warning');
            return;
        }
    }
    
    if (sampleCount >= MAX_SAMPLES) {
        showStatus(`Maximum samples (${MAX_SAMPLES}) reached.`, 'warning');
        return;
    }
    
    try {
        const captureBtn = document.getElementById('btnCaptureSample');
        if (captureBtn) captureBtn.disabled = true;
        const imageData = camera.captureFrame();
        if (!imageData) {
            throw new Error('Could not capture frame from camera.');
        }
        
        const payload = {
            student_id: currentStudentId,
            image: imageData,
            pose: 'front', // Could be dynamic based on UI
            sample_index: sampleCount + 1
        };
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/students/capture`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const error = await response.json();
            let msg = 'Failed to capture sample';
            if (typeof error.detail === 'string') {
                msg = error.detail;
            } else if (Array.isArray(error.detail)) {
                msg = error.detail.map(d => `${d.loc ? d.loc.join('.') : ''}: ${d.msg}`).join('; ');
            } else if (error.detail) {
                msg = JSON.stringify(error.detail);
            }
            throw new Error(msg);
        }
        
        addThumbnail(imageData, sampleCount);
        sampleCount++;
        updateSampleCounter();
        
        if (sampleCount > 0) {
            document.getElementById('btnRetake').disabled = false;
        }
        
        if (sampleCount >= 5) {
            document.getElementById('btnComplete').disabled = false;
        }
        
        if (sampleCount >= MAX_SAMPLES) {
            document.getElementById('btnCaptureSample').disabled = true;
            showStatus('10 samples captured successfully. You can now complete registration.', 'success');
        } else {
            document.getElementById('btnCaptureSample').disabled = false;
        }
        
    } catch (error) {
        showStatus(error.message, 'error');
        document.getElementById('btnCaptureSample').disabled = false;
    }
}

async function retakeLastSample() {
    if (sampleCount === 0) return;
    
    sampleCount--;
    const grid = document.getElementById('thumbnailContainer');
    if (grid && grid.lastChild) {
        grid.removeChild(grid.lastChild);
    }
    
    updateSampleCounter();
    
    document.getElementById('btnCaptureSample').disabled = false;
    document.getElementById('btnComplete').disabled = true;
    
    if (sampleCount === 0) {
        document.getElementById('btnRetake').disabled = true;
    }
}

async function completeRegistration() {
    try {
        document.getElementById('btnComplete').disabled = true;
        showStatus('Generating embeddings...', 'info');
        
        const response = await fetch(`${CONFIG.API_BASE_URL}/ml/generate-embeddings`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate embeddings');
        }
        
        showStatus('Registration complete and embeddings generated successfully.', 'success');
        
        if (camera) {
            camera.stop();
        }
        
        setTimeout(() => {
            resetForm();
        }, 3000);
        
    } catch (error) {
        showStatus(error.message, 'error');
            document.getElementById('btnComplete').disabled = false;
    }
}

function showStatus(message, type = 'info') {
    const statusBar = document.getElementById('statusAlert');
    if (statusBar) {
        statusBar.textContent = message;
        statusBar.className = `alert alert-${type}`;
        statusBar.style.display = 'block';
    }
}

function addThumbnail(imageData, index) {
    const grid = document.getElementById('thumbnailContainer');
    if (grid) {
        const img = document.createElement('img');
        img.src = imageData;
        img.className = 'thumbnail';
        img.alt = `Sample ${index + 1}`;
        grid.appendChild(img);
    }
}

function updateSampleCounter() {
    const counter = document.getElementById('sampleCounter');
    if (counter) {
        counter.textContent = `Samples: ${sampleCount}/${MAX_SAMPLES}`;
    }
}

function resetForm() {
    const registerForm = document.getElementById('registrationForm');
    if (registerForm) registerForm.reset();
    
    currentStudentId = null;
    sampleCount = 0;
    isRegistered = false;
    
    const grid = document.getElementById('thumbnailContainer');
    if (grid) grid.innerHTML = '';
    
    updateSampleCounter();
    
    const startCameraBtn = document.getElementById('btnStartCamera');
    const captureBtn = document.getElementById('btnCaptureSample');
    const retakeBtn = document.getElementById('btnRetake');
    const completeBtn = document.getElementById('btnComplete');
    
    if (startCameraBtn) startCameraBtn.disabled = true;
    if (captureBtn) captureBtn.disabled = true;
    if (retakeBtn) retakeBtn.disabled = true;
    if (completeBtn) completeBtn.disabled = true;
    
    const statusBar = document.getElementById('statusAlert');
    if (statusBar) statusBar.style.display = 'none';
}

/**
 * Camera Utility Module
 * Handles webcam access, video streaming, and frame capture.
 */
class Camera {
    constructor(videoElementId, canvasElementId = null) {
        this.video = document.getElementById(videoElementId);
        const existingCanvas = canvasElementId ? document.getElementById(canvasElementId) : null;
        this.canvas = existingCanvas || document.createElement('canvas');
        this.stream = null;
        this.isActive = false;
    }
    
    async start() {
        try {
            if (this.isActive && this.stream && this.stream.active) {
                return { success: true };
            }
            
            // Clean up any old tracks first
            this.stop();
            
            const constraints = {
                video: {
                    width: { ideal: CONFIG.CAMERA.WIDTH },
                    height: { ideal: CONFIG.CAMERA.HEIGHT },
                    facingMode: CONFIG.CAMERA.FACING_MODE
                },
                audio: false
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            await new Promise((resolve) => {
                if (this.video.readyState >= 2) {
                    resolve();
                } else {
                    this.video.onloadedmetadata = () => resolve();
                }
            });
            
            await this.video.play();
            this.isActive = true;
            
            return { success: true };
        } catch (error) {
            console.error('Camera error:', error);
            // If the video is actually displaying frames despite error, consider active
            if (this.video && this.video.srcObject) {
                this.isActive = true;
                return { success: true };
            }
            let message = 'Failed to access camera: ' + (error.message || error.name);
            if (error.name === 'NotAllowedError') {
                message = 'Camera permission denied. Please allow camera access in browser.';
            } else if (error.name === 'NotReadableError') {
                message = 'Camera is in use by another tab or app. Please close other camera tabs.';
            }
            return { success: false, error: message };
        }
    }
    
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
        this.isActive = false;
    }
    
    captureFrame() {
        if (!this.isActive) return null;
        
        if (this.video.videoWidth && this.video.videoHeight) {
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
        } else {
            this.canvas.width = CONFIG.CAMERA.WIDTH;
            this.canvas.height = CONFIG.CAMERA.HEIGHT;
        }
        
        const ctx = this.canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        return this.canvas.toDataURL(
            CONFIG.CAMERA.IMAGE_FORMAT, 
            CONFIG.CAMERA.IMAGE_QUALITY
        );
    }
    
    captureBlob() {
        return new Promise((resolve) => {
            if (!this.isActive) { resolve(null); return; }
            const ctx = this.canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);
            this.canvas.toBlob(resolve, CONFIG.CAMERA.IMAGE_FORMAT, CONFIG.CAMERA.IMAGE_QUALITY);
        });
    }
}

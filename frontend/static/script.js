document.addEventListener('DOMContentLoaded', () => {
    // --- UI Elements ---
    const API_BASE_URL = '';
    const screens = { 
        upload: document.getElementById('screen-upload'), 
        loading: document.getElementById('screen-loading'), 
        results: document.getElementById('screen-results'),
        payment: document.getElementById('screen-payment'),
        download: document.getElementById('screen-download')
    };
    
    // UI Elements for Camera-Only flow
    const previewContainer = document.getElementById('preview-container');
    const searchBtn = document.getElementById('search-btn');
    const uploadPreviewSection = document.getElementById('upload-preview-section');
    const webcamVideo = document.getElementById('webcam');
    const cameraPlaceholder = document.getElementById('camera-placeholder');
    const startCameraBtn = document.getElementById('start-camera-btn');
    const captureBtn = document.getElementById('capture-btn');
    const toastContainer = document.getElementById('toast-container');
    const collectionDropdown = document.getElementById('collection-dropdown');
    const guestLogoutBtn = document.getElementById('guest-logout-btn');
    const emailInput = document.getElementById('email-input');
    const sendEmailBtn = document.getElementById('send-email-btn');

    // NEW: Reference for the "Print All" button on the final screen
    const printAllBtn = document.getElementById('print-all-btn');

    // --- State Variables ---
    let currentFile = null;
    let stream = null;
    let selectedImages = new Set();
    let paymentPollInterval = null;

    // --- Helper Functions ---
    const showToast = (message, type = 'info') => {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        let iconClass = 'fa-solid fa-circle-info';
        if (type === 'success') iconClass = 'fa-solid fa-circle-check';
        if (type === 'error') iconClass = 'fa-solid fa-circle-exclamation';
        toast.innerHTML = `<i class="${iconClass} mr-3"></i> ${message}`;
        toastContainer.appendChild(toast);
        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            toast.addEventListener('transitionend', () => toast.remove());
        }, 5000);
    };

    const showScreen = (screenName) => {
        if (paymentPollInterval) { clearInterval(paymentPollInterval); paymentPollInterval = null; }
        Object.values(screens).forEach(s => s.classList.add('hidden'));
        screens[screenName]?.classList.remove('hidden');
    };
    
    // --- Payment Polling ---
    const pollPaymentStatus = (transactionId) => {
        if (paymentPollInterval) clearInterval(paymentPollInterval);
        paymentPollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/check-payment-status/${transactionId}`);
                if (!response.ok) {
                    clearInterval(paymentPollInterval);
                    showToast('Payment session expired. Please try again.', 'error');
                    showScreen('results');
                    return;
                }
                const data = await response.json();
                if (data.status === 'PAID') {
                    clearInterval(paymentPollInterval);
                    paymentPollInterval = null;
                    showToast('Payment successful!', 'success');
                    showScreen('download');
                }
            } catch (error) {
                console.error("Polling error:", error);
                clearInterval(paymentPollInterval);
            }
        }, 3000);
    };
    
    const handleFile = (file) => {
        if (!file || !file.type.startsWith('image/')) return showToast('Please capture a valid image.', 'error');
        currentFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewContainer.innerHTML = `
                <div class="relative w-24 h-24 rounded-lg overflow-hidden border-2 border-cyan-400" title="${file.name}">
                    <img src="${e.target.result}" class="w-full h-full object-cover">
                    <button id="remove-preview-btn" class="absolute top-0 right-0 bg-red-600 hover:bg-red-700 text-white w-5 h-5 flex items-center justify-center text-xs rounded-bl-md" title="Retake photo">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>`;
            
            document.getElementById('remove-preview-btn').addEventListener('click', () => {
                currentFile = null;
                uploadPreviewSection.classList.add('hidden');
                previewContainer.innerHTML = '';
                startCamera();
            });
            uploadPreviewSection.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    };

    const populateCollections = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/collections`);
            if (!response.ok) throw new Error('Failed to fetch collections.');
            const data = await response.json();
            collectionDropdown.innerHTML = '';
            if (data.collections.length === 0) {
                collectionDropdown.innerHTML = '<option>No collections available</option>';
            } else {
                data.collections.forEach(name => collectionDropdown.innerHTML += `<option value="${name}">${name}</option>`);
            }
        } catch (error) { showToast(error.message, 'error'); }
    };

    const performSearch = async () => {
        const selectedCollection = collectionDropdown.value;
        if (!currentFile || !selectedCollection) return showToast('Please capture a photo and select a collection.', 'error');
        showScreen('loading');
        const formData = new FormData();
        formData.append('file', currentFile);
        try {
            const response = await fetch(`${API_BASE_URL}/api/search/${selectedCollection}`, { method: 'POST', body: formData });
            if (!response.ok) {
                if(response.status === 401 || response.status === 307) window.location.href = '/';
                throw new Error((await response.json()).detail);
            }
            const data = await response.json();
            screens.results.innerHTML = createResultsScreenHtml(data);
            attachResultsScreenListeners(data.results);
            showScreen('results');
        } catch (error) {
            showToast(`Error: ${error.message}`, 'error');
            showScreen('upload');
        }
    };

    // =========================================================================
    // MODIFIED: This function NO LONGER creates the individual print button
    // =========================================================================
    const createResultsScreenHtml = (data) => {
        const hasResults = data.results && data.results.length > 0;
        let resultsContent;
        if (hasResults) {
            resultsContent = `
                <div class="results-grid-container">
                    <div class="thumbnail-sidebar glass-card">
                        <div class="thumbnail-grid">
                            ${data.results.map((r, i) => `
                                <div class="thumbnail-image" data-index="${i}" data-original-path="${r.original_path}" title="Click to select, hover to view">
                                    <img src="${API_BASE_URL}${r.web_path}" loading="lazy">
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="gallery-main">
                        <div class="gallery-container">
                            <div class="main-image-display"><img src="" alt="Selected Memory"></div>
                            <button class="prev-btn gallery-nav-btn left-4"><i class="fa-solid fa-chevron-left"></i></button>
                            <button class="next-btn gallery-nav-btn right-4"><i class="fa-solid fa-chevron-right"></i></button>
                        </div>
                    </div>
                </div>`;
        } else {
            resultsContent = `<div class="no-results-message glass-card"><i class="fa-regular fa-face-frown text-6xl text-gray-400 mb-4"></i><p class="text-2xl text-gray-600">No Similar Images Found</p><p class="text-gray-500 mt-2">Try capturing another photo in a well-lit area.</p></div>`;
        }
        return `<div class="results-header"><button class="back-to-upload secondary-button"><i class="fa-solid fa-arrow-left mr-2"></i>New Search</button><div class="results-summary">${data.status}</div><button id="proceed-to-pay-btn" class="primary-button disabled:opacity-50" disabled><i class="fa-solid fa-credit-card mr-2"></i>Proceed to Pay <span class="selected-count font-normal ml-1"></span></button></div>${resultsContent}`;
    };

    // ====================================================================
    // MODIFIED: This function NO LONGER has a listener for an individual
    // print button.
    // ====================================================================
    const attachResultsScreenListeners = (results) => {
        selectedImages.clear();
        let currentIndex = 0;
        const mainImg = screens.results.querySelector('.main-image-display img');
        const prevBtn = screens.results.querySelector('.prev-btn');
        const nextBtn = screens.results.querySelector('.next-btn');
        const thumbnails = screens.results.querySelectorAll('.thumbnail-image');
        const proceedToPayBtn = screens.results.querySelector('#proceed-to-pay-btn');

        if (!results || results.length === 0) return;

        const updateGalleryView = () => {
            const currentResult = results[currentIndex];
            if (mainImg) mainImg.src = `${API_BASE_URL}${currentResult.web_path}`;
            thumbnails.forEach((thumb, i) => thumb.classList.toggle('active-thumbnail', i === currentIndex));
            if (prevBtn) prevBtn.disabled = currentIndex === 0;
            if (nextBtn) nextBtn.disabled = currentIndex === results.length - 1;
        };
        const updatePaymentButtonState = () => {
            const count = selectedImages.size;
            if (proceedToPayBtn) {
                proceedToPayBtn.disabled = count === 0;
                proceedToPayBtn.querySelector('.selected-count').textContent = count > 0 ? `(${count})` : '';
            }
        };
        thumbnails.forEach(thumb => {
            thumb.addEventListener('mouseover', () => { currentIndex = parseInt(thumb.dataset.index); updateGalleryView(); });
            thumb.addEventListener('click', (e) => {
                const originalPath = e.currentTarget.dataset.originalPath;
                e.currentTarget.classList.toggle('selected-thumbnail');
                if (e.currentTarget.classList.contains('selected-thumbnail')) { selectedImages.add(originalPath); } else { selectedImages.delete(originalPath); }
                updatePaymentButtonState();
            });
        });
        prevBtn?.addEventListener('click', () => { if (currentIndex > 0) { currentIndex--; updateGalleryView(); } });
        nextBtn?.addEventListener('click', () => { if (currentIndex < results.length - 1) { currentIndex++; updateGalleryView(); } });
        proceedToPayBtn?.addEventListener('click', async () => {
            if (selectedImages.size === 0) return;
            showScreen('payment');
            showToast('Please complete payment. We are checking for confirmation...', 'info');
            try {
                const response = await fetch(`${API_BASE_URL}/api/start-payment`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_paths: Array.from(selectedImages) })
                });
                if (!response.ok) throw new Error('Could not initiate payment session.');
                const data = await response.json();
                pollPaymentStatus(data.transaction_id);
            } catch (error) {
                showToast(error.message, 'error');
                showScreen('results');
            }
        });
        updateGalleryView();
        updatePaymentButtonState();
    };
    
    const startCamera = async () => { try { stream = await navigator.mediaDevices.getUserMedia({ video: true }); webcamVideo.srcObject = stream; webcamVideo.play(); webcamVideo.classList.remove('hidden'); cameraPlaceholder.classList.add('hidden'); startCameraBtn.textContent = 'Restart Camera'; captureBtn.disabled = false; } catch (err) { showToast('Could not access webcam. Please allow camera permissions.', 'error'); } };
    const stopCamera = () => { if (stream) { stream.getTracks().forEach(track => track.stop()); } stream = null; webcamVideo.classList.add('hidden'); cameraPlaceholder.classList.remove('hidden'); startCameraBtn.textContent = 'Start Camera'; captureBtn.disabled = true; };
    const capturePhoto = () => {
        if (!stream) return;
        const canvas = document.createElement('canvas');
        canvas.width = webcamVideo.videoWidth; canvas.height = webcamVideo.videoHeight;
        canvas.getContext('2d').drawImage(webcamVideo, 0, 0);
        stopCamera();
        canvas.toBlob((blob) => { handleFile(new File([blob], "webcam.jpg", { type: "image/jpeg" })); }, 'image/jpeg');
    };
    
    // --- Event Listeners ---
    searchBtn.addEventListener('click', performSearch);
    startCameraBtn.addEventListener('click', () => { stream ? stopCamera() : startCamera(); });
    captureBtn.addEventListener('click', capturePhoto);

    document.getElementById('final-download-btn')?.addEventListener('click', async () => {
        if (selectedImages.size === 0) return;
        showToast('Preparing your high-quality photos...', 'info');
        try {
            const response = await fetch(`${API_BASE_URL}/api/download-selected/`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_paths: Array.from(selectedImages) })
            });
            if(response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none'; a.href = url; a.download = 'FaceSearch_Memories.zip';
                document.body.appendChild(a); a.click();
                window.URL.revokeObjectURL(url); a.remove();
            } else { throw new Error('Download failed.'); }
        } catch (error) { showToast(error.message, 'error'); }
    });

    sendEmailBtn?.addEventListener('click', async () => {
        const email = emailInput.value.trim();
        if (!email || !/^\S+@\S+\.\S+$/.test(email)) {
            return showToast('Please enter a valid email address.', 'error');
        }
        if (selectedImages.size === 0) { return showToast('No images were selected.', 'error'); }
        const originalBtnText = sendEmailBtn.innerHTML;
        sendEmailBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Sending...';
        sendEmailBtn.disabled = true;
        try {
            const response = await fetch(`${API_BASE_URL}/api/send-email`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_paths: Array.from(selectedImages), email: email })
            });
            const data = await response.json();
            if (response.ok) {
                showToast(data.message || 'Email sent successfully!', 'success');
                emailInput.value = '';
            } else { throw new Error(data.detail || 'Failed to send email.'); }
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            sendEmailBtn.innerHTML = originalBtnText;
            sendEmailBtn.disabled = false;
        }
    });

    // NEW: EVENT LISTENER FOR THE "PRINT ALL PHOTOS" BUTTON
    printAllBtn?.addEventListener('click', () => {
        if (selectedImages.size === 0) {
            return showToast('No photos were selected to print.', 'error');
        }
        showToast(`Preparing ${selectedImages.size} photos for printing...`, 'info');

        let printHtmlContent = `
            <html><head><title>Print Your Park Memories</title><style>
            body { margin: 20px; }
            img { max-width: 100%; height: auto; display: block; margin-bottom: 20px; page-break-inside: avoid; }
            </style></head><body>`;

        selectedImages.forEach(imagePath => {
            printHtmlContent += `<img src="${imagePath}">`;
        });
        printHtmlContent += '</body></html>';

        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.srcdoc = printHtmlContent;
        iframe.onload = function() {
            try {
                iframe.contentWindow.focus();
                iframe.contentWindow.print();
            } catch (error) {
                console.error("Print failed:", error);
                showToast('Could not open print dialog.', 'error');
            }
            setTimeout(() => document.body.removeChild(iframe), 1000);
        };
        document.body.appendChild(iframe);
    });

    guestLogoutBtn.addEventListener('click', async () => {
        const response = await fetch('/guest/logout', { method: 'POST' });
        if (response.redirected) window.location.href = response.url;
    });

    document.body.addEventListener('click', (e) => {
        if (e.target.closest('.back-to-upload')) {
            e.preventDefault();
            stopCamera();
            currentFile = null;
            selectedImages.clear();
            uploadPreviewSection.classList.add('hidden');
            previewContainer.innerHTML = '';
            showScreen('upload');
            startCamera();
        }
    });

    // --- Initial Load ---
    showScreen('upload');
    populateCollections();
    startCamera();
});
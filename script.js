// Configuration
const PDFJS_WORKER_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_URL;
}

// Dark Mode Logic
const themeToggle = document.getElementById('themeToggle');
const sunIcon = document.querySelector('.sun-icon');
const moonIcon = document.querySelector('.moon-icon');

function updateThemeIcon(isLight) {
    if (sunIcon && moonIcon) {
        if (isLight) {
            sunIcon.classList.remove('hidden');
            moonIcon.classList.add('hidden');
        } else {
            sunIcon.classList.add('hidden');
            moonIcon.classList.remove('hidden');
        }
    }
}

// Load saved theme
const savedTheme = localStorage.getItem('theme');
if (savedTheme === 'light') {
    document.body.classList.add('light-theme');
    updateThemeIcon(true);
} else {
    // Default is dark
    document.body.classList.remove('light-theme');
    updateThemeIcon(false);
}

if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const isLight = document.body.classList.contains('light-theme');
        localStorage.setItem('theme', isLight ? 'light' : 'dark');
        updateThemeIcon(isLight);
    });
}

// Determine current tool mode
const path = window.location.pathname;
let currentTool = 'any-to-png';
if (path.includes('png-to-jpg')) currentTool = 'png-to-jpg';
else if (path.includes('png-to-pdf')) currentTool = 'png-to-pdf';
else if (path.includes('png-to-webp')) currentTool = 'png-to-webp';
else if (path.includes('compress-image')) currentTool = 'compress';
else if (path.includes('resize-image')) currentTool = 'resize';

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const statusContainer = document.getElementById('statusContainer');
const statusTitle = document.getElementById('statusTitle');
const statusMessage = document.getElementById('statusMessage');
const progressBar = document.getElementById('progressBar');
const resultsContainer = document.getElementById('resultsContainer');

// --- Drag & Drop Implementation ---
if (dropZone) {
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFiles(e.dataTransfer.files);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFiles(e.target.files);
        }
    });
}

// --- Core Logic ---
let allResults = [];

async function handleFiles(files) {
    statusContainer.classList.remove('hidden');
    resultsContainer.classList.add('hidden');
    resultsContainer.innerHTML = ''; 
    allResults = [];
    
    for(let i = 0; i < files.length; i++) {
        const file = files[i];
        
        statusTitle.textContent = `Processing: ${file.name} (${i+1}/${files.length})`;
        statusMessage.textContent = 'Analyzing...';
        updateProgress((i / files.length) * 100);

        try {
            const ext = file.name.toLowerCase();
            
            // Depending on currentTool, do different conversions
            if (currentTool === 'png-to-jpg' && ext.endsWith('.png')) {
                await processImageToFormat(file, 'image/jpeg', '.jpg');
            } else if (currentTool === 'png-to-webp' && ext.endsWith('.png')) {
                await processImageToFormat(file, 'image/webp', '.webp');
            } else if (currentTool === 'png-to-pdf' && ext.endsWith('.png')) {
                await processImageToPDF(file);
            } else if (currentTool === 'compress') {
                const qualityInput = document.getElementById('qualitySlider');
                const quality = qualityInput ? qualityInput.value / 100 : 0.6;
                await processCompress(file, quality);
            } else if (currentTool === 'resize') {
                const wInput = document.getElementById('resizeWidth');
                const hInput = document.getElementById('resizeHeight');
                const w = (wInput && wInput.value) ? parseInt(wInput.value) : null;
                const h = (hInput && hInput.value) ? parseInt(hInput.value) : null;
                await processResize(file, w, h);
            } else {
                // Default: To PNG
                if (ext.endsWith('.svg') || ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.webp') || ext.endsWith('.bmp') || ext.endsWith('.png')) {
                    await processNativeImage(file);
                } else if (file.type === 'application/pdf' || ext.endsWith('.pdf')) {
                    await processPDF(file);
                } else {
                    addResultItem(file.name, 'Unsupported format for this tool', null, true);
                }
            }
        } catch (error) {
            console.error(error);
            addResultItem(file.name, `Error: ${error.message}`, null, true);
        }
    }
    
    updateProgress(100);
    
    // If bulk, add Download All ZIP button
    if (allResults.length > 1) {
        addZipDownloadButton(allResults);
    }

    setTimeout(() => {
        statusContainer.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
    }, 500);
}

function updateProgress(percent) {
    if(progressBar) progressBar.style.width = `${percent}%`;
}

// --- Conversions ---

function processNativeImage(file) {
    return new Promise((resolve, reject) => {
        statusMessage.textContent = 'Rendering image...';
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                canvas.width = img.width || 800; 
                canvas.height = img.height || 600;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                const dataUrl = canvas.toDataURL('image/png');
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                const res = { url: dataUrl, filename: `${baseName}.png` };
                allResults.push(res);
                addResultItem(file.name, 'Converted to PNG', res);
                resolve();
            };
            img.onerror = () => reject(new Error("Invalid image"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

function processImageToFormat(file, mimeType, newExt) {
    return new Promise((resolve, reject) => {
        statusMessage.textContent = `Converting to ${newExt}...`;
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                canvas.width = img.width; 
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                // Fill white background for JPGs
                if (mimeType === 'image/jpeg') {
                    ctx.fillStyle = '#FFFFFF';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);
                }
                ctx.drawImage(img, 0, 0);
                const dataUrl = canvas.toDataURL(mimeType, 0.9);
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                const res = { url: dataUrl, filename: `${baseName}${newExt}` };
                allResults.push(res);
                addResultItem(file.name, `Converted to ${newExt}`, res);
                resolve();
            };
            img.onerror = () => reject(new Error("Invalid image"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

async function processImageToPDF(file) {
    statusMessage.textContent = 'Generating PDF...';
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                try {
                    const { jsPDF } = window.jspdf;
                    const orientation = img.width > img.height ? 'l' : 'p';
                    const doc = new jsPDF(orientation, 'px', [img.width, img.height]);
                    doc.addImage(img, 'PNG', 0, 0, img.width, img.height);
                    
                    const blob = doc.output('blob');
                    const url = URL.createObjectURL(blob);
                    const baseName = file.name.replace(/\.[^/.]+$/, "");
                    const res = { url: url, filename: `${baseName}.pdf`, isBlob: true, blob: blob };
                    allResults.push(res);
                    addResultItem(file.name, 'Converted to PDF', res);
                    resolve();
                } catch(err) {
                    reject(err);
                }
            };
            img.onerror = () => reject(new Error("Invalid image"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

function processCompress(file, quality) {
    return new Promise((resolve, reject) => {
        statusMessage.textContent = 'Compressing...';
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                canvas.width = img.width; 
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);
                
                // Determine format
                const ext = file.name.toLowerCase();
                let mime = 'image/jpeg';
                if (ext.endsWith('.webp')) mime = 'image/webp';
                if (ext.endsWith('.png')) mime = 'image/webp'; // Convert PNG to WebP under the hood for size saving
                
                const dataUrl = canvas.toDataURL(mime, quality);
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                const newExt = mime === 'image/webp' ? '.webp' : '.jpg';
                const res = { url: dataUrl, filename: `${baseName}_compressed${newExt}` };
                allResults.push(res);
                addResultItem(file.name, `Compressed (${(quality*100).toFixed(0)}% quality)`, res);
                resolve();
            };
            img.onerror = () => reject(new Error("Invalid image"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

function processResize(file, targetW, targetH) {
    return new Promise((resolve, reject) => {
        statusMessage.textContent = 'Resizing...';
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                
                let finalW = img.width;
                let finalH = img.height;
                
                if (targetW && !targetH) {
                    finalW = targetW;
                    finalH = (targetW / img.width) * img.height;
                } else if (!targetW && targetH) {
                    finalH = targetH;
                    finalW = (targetH / img.height) * img.width;
                } else if (targetW && targetH) {
                    finalW = targetW;
                    finalH = targetH;
                }
                
                canvas.width = finalW; 
                canvas.height = finalH;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, finalW, finalH);
                
                const mime = file.type || 'image/jpeg';
                const dataUrl = canvas.toDataURL(mime, 0.9);
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                const extMatch = file.name.match(/\.[^/.]+$/);
                const ext = extMatch ? extMatch[0] : '.jpg';
                
                const res = { url: dataUrl, filename: `${baseName}_resized${ext}` };
                allResults.push(res);
                addResultItem(file.name, `Resized to ${Math.round(finalW)}x${Math.round(finalH)}`, res);
                resolve();
            };
            img.onerror = () => reject(new Error("Invalid image"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

// Existing PDF logic
async function processPDF(file) {
    statusMessage.textContent = 'Loading PDF...';
    const arrayBuffer = await file.arrayBuffer();
    const loadingTask = pdfjsLib.getDocument(arrayBuffer);
    const pdf = await loadingTask.promise;
    const numPages = pdf.numPages;
    const baseName = file.name.replace(/\.[^/.]+$/, "");

    if (numPages === 1) {
        statusMessage.textContent = 'Rendering PDF Page 1...';
        const page = await pdf.getPage(1);
        const dataUrl = await renderPdfPageToPNG(page);
        const res = { url: dataUrl, filename: `${baseName}.png` };
        allResults.push(res);
        addResultItem(file.name, 'Converted to PNG', res);
    } else {
        statusMessage.textContent = `Preparing ZIP for ${numPages} pages...`;
        const zip = new JSZip();
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            statusMessage.textContent = `Rendering page ${pageNum}/${numPages}...`;
            const page = await pdf.getPage(pageNum);
            const dataUrl = await renderPdfPageToPNG(page);
            const base64Data = dataUrl.split(',')[1];
            zip.file(`${baseName}_page_${pageNum}.png`, base64Data, {base64: true});
        }
        statusMessage.textContent = 'Zipping PNG files...';
        const content = await zip.generateAsync({type:"blob"});
        const objectUrl = URL.createObjectURL(content);
        
        const res = { url: objectUrl, filename: `${baseName}_PNGs.zip` };
        allResults.push(res);
        addResultItem(file.name, `Converted ${numPages} pages to ZIP`, res);
    }
}

async function renderPdfPageToPNG(page) {
    const scale = 2.0; 
    const viewport = page.getViewport({scale: scale});
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    await page.render({canvasContext: ctx, viewport: viewport}).promise;
    return canvas.toDataURL('image/png');
}

// --- UI Helpers ---
function addResultItem(originalName, status, downloadData, isError = false) {
    const div = document.createElement('div');
    div.className = 'result-item';
    let btnHtml = '';
    if (downloadData && !isError) {
        btnHtml = `<a href="${downloadData.url}" download="${downloadData.filename}" class="btn-download">Download</a>`;
    }
    div.innerHTML = `
        <div class="result-info">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="${isError ? '#EF4444' : '#10B981'}" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16c0 1.1.9 2 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/><path d="M14 3v5h5M16 13H8M16 17H8M10 9H8"/></svg>
            <div>
                <strong>${originalName}</strong>
                <p style="color: ${isError ? '#EF4444' : 'var(--text-muted)'}; font-size: 0.875rem;">${status}</p>
            </div>
        </div>
        ${btnHtml}
    `;
    resultsContainer.appendChild(div);
}

async function addZipDownloadButton(results) {
    if (results.length < 2) return;
    const div = document.createElement('div');
    div.className = 'result-item';
    div.style.background = 'var(--primary)';
    div.style.color = '#fff';
    
    div.innerHTML = `
        <div class="result-info">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <div>
                <strong style="color:#fff">Download All (${results.length} files)</strong>
                <p style="color: rgba(255,255,255,0.8); font-size: 0.875rem;">Packed as ZIP</p>
            </div>
        </div>
        <button id="downloadAllBtn" class="btn-download outline" style="color:#fff; border-color: rgba(255,255,255,0.5)">Download ZIP</button>
    `;
    resultsContainer.prepend(div);

    document.getElementById('downloadAllBtn').addEventListener('click', async () => {
        statusContainer.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        statusTitle.textContent = 'Zipping files...';
        statusMessage.textContent = 'Please wait';
        
        const zip = new JSZip();
        for(let res of results) {
            if (res.isBlob) {
                zip.file(res.filename, res.blob);
            } else {
                const base64Data = res.url.split(',')[1];
                if (base64Data) {
                    zip.file(res.filename, base64Data, {base64: true});
                }
            }
        }
        
        const content = await zip.generateAsync({type:"blob"});
        const url = URL.createObjectURL(content);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'all2png_bulk.zip';
        a.click();
        
        statusContainer.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
    });
}

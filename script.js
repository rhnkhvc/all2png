// Configuration
const PDFJS_WORKER_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_URL;

// DOM Elements
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const statusContainer = document.getElementById('statusContainer');
const statusTitle = document.getElementById('statusTitle');
const statusMessage = document.getElementById('statusMessage');
const progressBar = document.getElementById('progressBar');
const resultsContainer = document.getElementById('resultsContainer');

// --- Drag & Drop Implementation ---

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

// --- Core Logic ---

async function handleFiles(files) {
    statusContainer.classList.remove('hidden');
    resultsContainer.classList.add('hidden');
    resultsContainer.innerHTML = ''; // Clear old results
    let progress = 0;
    
    for(let i = 0; i < files.length; i++) {
        const file = files[i];
        
        statusTitle.textContent = `Processing: ${file.name}`;
        statusMessage.textContent = 'Analyzing file format...';
        updateProgress((i / files.length) * 100);

        try {
            const ext = file.name.toLowerCase();
            if (ext.endsWith('.svg') || ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.webp') || ext.endsWith('.bmp')) {
                await processNativeImage(file);
            } else if (file.type === 'application/pdf' || ext.endsWith('.pdf')) {
                await processPDF(file);
            } else {
                addResultItem(file.name, 'Unsupported format', null, true);
            }
        } catch (error) {
            console.error(error);
            addResultItem(file.name, `Error: ${error.message}`, null, true);
        }
    }
    
    updateProgress(100);
    setTimeout(() => {
        statusContainer.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
    }, 500);
}

function updateProgress(percent) {
    progressBar.style.width = `${percent}%`;
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
                canvas.width = img.width || 800; // fallback width
                canvas.height = img.height || 600;

                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0);

                const dataUrl = canvas.toDataURL('image/png');
                const baseName = file.name.replace(/\.[^/.]+$/, "");
                addResultItem(file.name, 'Converted to PNG', {
                    url: dataUrl,
                    filename: `${baseName}.png`
                });
                resolve();
            };
            img.onerror = () => reject(new Error("Invalid or unsupported image format"));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error("Failed to read file"));
        reader.readAsDataURL(file);
    });
}

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
        addResultItem(file.name, 'Converted to PNG', {
            url: dataUrl,
            filename: `${baseName}.png`
        });
    } else {
        statusMessage.textContent = `Preparing ZIP for ${numPages} pages...`;
        const zip = new JSZip();
        
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
            statusMessage.textContent = `Rendering page ${pageNum}/${numPages}...`;
            const page = await pdf.getPage(pageNum);
            const dataUrl = await renderPdfPageToPNG(page);
            
            // Extract base64 part
            const base64Data = dataUrl.split(',')[1];
            zip.file(`${baseName}_page_${pageNum}.png`, base64Data, {base64: true});
        }
        
        statusMessage.textContent = 'Zipping PNG files...';
        const content = await zip.generateAsync({type:"blob"});
        const objectUrl = URL.createObjectURL(content);
        
        addResultItem(file.name, `Converted ${numPages} pages to ZIP`, {
            url: objectUrl,
            filename: `${baseName}_PNGs.zip`
        });
    }
}

async function renderPdfPageToPNG(page) {
    const scale = 2.0; // High quality scale
    const viewport = page.getViewport({scale: scale});
    
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const renderContext = {
        canvasContext: ctx,
        viewport: viewport
    };

    await page.render(renderContext).promise;
    return canvas.toDataURL('image/png');
}

// --- UI Helpers ---

function addResultItem(originalName, status, downloadData, isError = false) {
    const div = document.createElement('div');
    div.className = 'result-item';
    
    let btnHtml = '';
    if (downloadData && !isError) {
        btnHtml = `<a href="${downloadData.url}" download="${downloadData.filename}" class="btn-download">
                       Download
                   </a>`;
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

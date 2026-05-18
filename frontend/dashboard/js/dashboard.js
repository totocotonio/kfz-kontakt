const API_BASE = '/api';
let currentMessageId = null;
let confirmCallback = null;
let loginResolve = null;

// Globale Variable für Passwort - Versuche aus sessionStorage zu laden
let dashboardPassword = sessionStorage.getItem('dashboardPassword') || null;

// Login Modal Handler
function showLoginModal() {
    return new Promise((resolve) => {
        loginResolve = resolve;
        document.getElementById('loginModal').style.display = 'flex';
        document.getElementById('loginPassword').focus();
    });
}

document.getElementById('loginBtn')?.addEventListener('click', async () => {
    const password = document.getElementById('loginPassword').value;
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginPassword').value = '';

    // Speichere Passwort in sessionStorage für diese Session
    if (password) {
        sessionStorage.setItem('dashboardPassword', password);
    }

    if (loginResolve) {
        loginResolve(password);
        loginResolve = null;
    }
});

document.getElementById('loginPassword')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        document.getElementById('loginBtn').click();
    }
});

// Helper für API-Calls mit Basic Auth
async function apiFetch(url, options = {}) {
    // Wenn Passwort nicht gespeichert, fragen
    if (!dashboardPassword) {
        dashboardPassword = await showLoginModal();
        if (!dashboardPassword) {
            alert('Passwort erforderlich!');
            return { status: 401, ok: false, json: async () => ({ detail: 'Passwort erforderlich' }) };
        }
    }

    const headers = { ...options.headers };
    headers['Authorization'] = 'Basic ' + btoa(':' + dashboardPassword);

    const fetchOptions = {
        ...options,
        headers,
        credentials: 'include'
    };

    const response = await fetch(url, fetchOptions);

    if (response.status === 401) {
        dashboardPassword = null; // Reset für neuen Versuch
        alert('Passwort falsch. Bitte erneut eingeben.');
        return apiFetch(url, options); // Retry
    }

    return response;
}

function showConfirm(title, message, onConfirm) {
    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmModal').style.display = 'flex';
    confirmCallback = onConfirm;
}

function showError(message) {
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('errorModal').style.display = 'flex';
}

document.getElementById('confirmCancel')?.addEventListener('click', () => {
    document.getElementById('confirmModal').style.display = 'none';
    confirmCallback = null;
});

document.getElementById('confirmOk')?.addEventListener('click', () => {
    document.getElementById('confirmModal').style.display = 'none';
    if (confirmCallback) confirmCallback();
    confirmCallback = null;
});

document.getElementById('errorOk')?.addEventListener('click', () => {
    document.getElementById('errorModal').style.display = 'none';
});

function showDownloadModal(qrId, filename, label) {
    // Cache-busting mit Timestamp um neueste QR-Code Version zu laden
    document.getElementById('downloadPreview').src = `${API_BASE}/qrcode/${qrId}/image?t=${Date.now()}`;
    document.getElementById('downloadLabel').textContent = label;
    document.getElementById('downloadModal').dataset.qrId = qrId;
    document.getElementById('downloadModal').dataset.filename = filename;
    document.getElementById('downloadModal').style.display = 'flex';
}

async function downloadQRCode() {
    const qrId = document.getElementById('downloadModal').dataset.qrId;
    const filename = document.getElementById('downloadModal').dataset.filename;

    try {
        const res = await apiFetch(`${API_BASE}/qrcode/${qrId}/image`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        document.getElementById('downloadModal').style.display = 'none';
    } catch (e) {
        showError('Fehler beim Download: ' + e.message);
    }
}

document.getElementById('closeDownloadBtn')?.addEventListener('click', () => {
    document.getElementById('downloadModal').style.display = 'none';
});

document.getElementById('closeDownloadBtnBottom')?.addEventListener('click', () => {
    document.getElementById('downloadModal').style.display = 'none';
});

document.getElementById('confirmDownloadBtn')?.addEventListener('click', downloadQRCode);

function setupContactSettings() {
    loadContactSettings();

    document.getElementById('saveContactBtn')?.addEventListener('click', async () => {
        const number = document.getElementById('phoneNumber').value;
        if (!number) {
            showError('Bitte gebe eine Telefonnummer ein');
            return;
        }

        try {
            const res = await apiFetch(`${API_BASE}/dashboard/contact`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_number: number })
            });

            if (res.ok) {
                showConfirm('Erfolg', 'Telefonnummer gespeichert!', () => {});
            } else {
                showError('Fehler beim Speichern');
            }
        } catch (e) {
            showError('Fehler: ' + e.message);
        }
    });

    document.getElementById('saveMethodsBtn')?.addEventListener('click', async () => {
        const methods = {
            enable_telegram: document.getElementById('enableTelegram').checked,
            enable_sms: document.getElementById('enableSMS').checked,
            enable_whatsapp: document.getElementById('enableWhatsApp').checked
        };

        try {
            const res = await apiFetch(`${API_BASE}/dashboard/contact-methods`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(methods)
            });

            if (res.ok) {
                showConfirm('Erfolg', 'Kontaktmethoden gespeichert!', () => {});
            } else {
                showError('Fehler beim Speichern');
            }
        } catch (e) {
            showError('Fehler: ' + e.message);
        }
    });
}

async function loadContactSettings() {
    try {
        const res = await apiFetch(`${API_BASE}/dashboard/contact`);
        const data = await res.json();

        if (data.phone_number) {
            document.getElementById('phoneNumber').value = data.phone_number;
        }

        if (document.getElementById('enableTelegram')) {
            document.getElementById('enableTelegram').checked = data.enable_telegram || false;
            document.getElementById('enableSMS').checked = data.enable_sms || false;
            document.getElementById('enableWhatsApp').checked = data.enable_whatsapp || false;
        }
    } catch (e) {
        console.error('Fehler beim Laden der Kontakteinstellungen:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Passwort wird erst in apiFetch() abgefragt, wenn nötig
    setupNavigation();
    // Initialize with messages tab active
    switchTab('messages');
    setupQRCodeGenerator();
    setupContactSettings();
});

// Version wird SERVER-SIDE injiziert in das HTML - nicht hier laden!

function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

    document.querySelector('[data-tab="' + tabName + '"]')?.classList.add('active');
    document.getElementById(tabName).classList.add('active');

    const titles = {
        messages: 'Nachrichten',
        settings: 'Einstellungen',
        qrcodes: 'QR-Codes',
        stats: 'Statistiken',
        analytics: 'Analytics'
    };
    document.getElementById('pageTitle').textContent = titles[tabName];

    if (tabName === 'messages') loadMessages();
    if (tabName === 'qrcodes') loadQRCodes();
    if (tabName === 'stats') loadStats();
    if (tabName === 'analytics') loadAnalytics();
}

async function loadMessages() {
    try {
        const res = await apiFetch(`${API_BASE}/dashboard/messages`);
        const data = await res.json();
        const list = document.getElementById('messagesList');

        if (!data.messages || data.messages.length === 0) {
            list.innerHTML = '<div class="loading">Keine Nachrichten vorhanden</div>';
            return;
        }

        list.innerHTML = data.messages.map(msg => `
            <div class="message-card ${!msg.read ? 'unread' : ''}" onclick="openMessage(${msg.id})">
                <div class="message-header">
                    <span class="message-sender">${msg.sender_name}</span>
                    <span class="message-time">${new Date(msg.created_at).toLocaleDateString('de-DE')}</span>
                </div>
                ${msg.category ? `<span class="message-category">${msg.category}</span>` : ''}
                <div class="message-preview">${msg.message}</div>
                <div class="message-qr">📌 ${msg.qr_label}</div>
            </div>
        `).join('');

        const unreadCount = data.messages.filter(m => !m.read).length;
        document.getElementById('unreadCount').textContent = unreadCount;
    } catch (e) {
        console.error('Fehler beim Laden der Nachrichten:', e);
    }
}

async function openMessage(msgId) {
    try {
        const res = await apiFetch(`${API_BASE}/dashboard/messages/${msgId}`);
        const msg = await res.json();
        currentMessageId = msgId;

        const detail = document.getElementById('messageDetail');
        detail.innerHTML = `
            <div class="message-detail-header">
                <div>
                    <h2>${msg.sender_name}</h2>
                    <div class="message-detail-meta">
                        <span>📌 ${msg.qr_label}</span>
                        <span>📅 ${new Date(msg.created_at).toLocaleDateString('de-DE')}</span>
                        ${msg.category ? `<span>🏷️ ${msg.category}</span>` : ''}
                    </div>
                </div>
                <button onclick="deleteMessage(${msgId}, true)" class="btn btn-danger" title="Nachricht löschen">🗑️ Löschen</button>
            </div>
            ${msg.sender_contact ? `<div><strong>Kontakt:</strong> ${msg.sender_contact}</div>` : ''}
            <div class="message-detail-body">${msg.message}</div>
        `;

        document.getElementById('messageModal').style.display = 'flex';
    } catch (e) {
        console.error('Fehler beim Öffnen der Nachricht:', e);
    }
}

document.getElementById('closeMessageBtn')?.addEventListener('click', () => {
    document.getElementById('messageModal').style.display = 'none';
});

document.getElementById('markUnreadBtn')?.addEventListener('click', async () => {
    await updateMessage(currentMessageId, { read: false });
    document.getElementById('messageModal').style.display = 'none';
    loadMessages();
});

document.getElementById('markRespondedBtn')?.addEventListener('click', async () => {
    await updateMessage(currentMessageId, { responded: true });
    document.getElementById('messageModal').style.display = 'none';
    loadMessages();
});

async function updateMessage(msgId, data) {
    try {
        await fetch(`${API_BASE}/dashboard/messages/${msgId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    } catch (e) {
        console.error('Fehler beim Aktualisieren:', e);
    }
}

async function deleteMessage(msgId, closeModal = false) {
    if (!confirm('Nachricht wirklich löschen?')) return;

    try {
        const res = await apiFetch(`${API_BASE}/message/${msgId}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            if (closeModal) {
                document.getElementById('messageModal').style.display = 'none';
            }
            loadMessages();
        } else {
            showError('Fehler beim Löschen der Nachricht');
        }
    } catch (e) {
        console.error('Fehler beim Löschen:', e);
        showError('Fehler: ' + e.message);
    }
}

async function loadStats() {
    try {
        const res = await apiFetch(`${API_BASE}/dashboard/stats`);
        const data = await res.json();

        document.getElementById('totalMessages').textContent = data.total_messages;
        document.getElementById('statsUnread').textContent = data.unread_messages;
        document.getElementById('statsResponded').textContent = data.responded_messages;
    } catch (e) {
        console.error('Fehler beim Laden der Statistiken:', e);
    }
}

async function loadQRCodes() {
    try {
        const res = await apiFetch(`${API_BASE}/qrcodes/list`);
        const data = await res.json();
        const grid = document.getElementById('qrcodesGrid');

        if (!data.qrcodes || data.qrcodes.length === 0) {
            grid.innerHTML = '<div class="loading">Keine QR-Codes erstellt</div>';
            return;
        }

        const timestamp = new Date().getTime();
        grid.innerHTML = data.qrcodes.map(qr => `
            <div class="qrcode-card" data-qr-id="${qr.id}">
                <div class="qrcode-preview">
                    <img src="${API_BASE}/qrcode/${qr.id}/image?t=${timestamp}" alt="${qr.label}">
                </div>
                <div class="qrcode-label qr-label">${qr.label}</div>
                <div style="font-size: 12px; color: #999; margin-top: 5px; word-break: break-all;">ID: ${qr.unique_id}</div>
                <div style="font-size: 12px; color: #999;">Design: ${qr.design}</div>
                <div style="font-size: 12px; color: #999; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">
                    Farbe: <div style="width: 20px; height: 20px; border: 1px solid #ccc; border-radius: 3px; background-color: ${qr.background_color || '#f5f5f5'}; cursor: help;" title="${qr.background_color || '#f5f5f5'}"></div>
                </div>
                <div class="qrcode-actions">
                    <button onclick="showDownloadModal(${qr.id}, 'qr_${qr.id}.png', '${qr.label}')" class="btn btn-primary">Runterladen</button>
                    <button class="btn btn-secondary" data-qrid="${qr.id}" data-label="${qr.label}" data-title="${qr.title}" data-design="${qr.design}" data-background-color="${qr.background_color || '#f5f5f5'}" data-icon-type="${qr.icon_type || 'phone'}" data-icon-position="${qr.icon_position || 'bottom'}" data-license-plate="${qr.license_plate || ''}" data-vehicle-image-path="${qr.vehicle_image_path || ''}" onclick="editQRCodeClick(this)">Bearbeiten</button>
                    <button onclick="deleteQRCode(${qr.id})" class="btn btn-secondary" style="background: #ff6b6b;">Löschen</button>
                </div>
            </div>
        `).join('');

        // Populate QR Code Select für Analytics
        populateQRCodeSelect();
    } catch (e) {
        console.error('Fehler beim Laden der QR-Codes:', e);
    }
}

function setupQRCodeGenerator() {
    const designSelect = document.getElementById('qrDesign');
    const designInfo = document.getElementById('designInfo');

    const designDescriptions = {
        default: 'Standard: 400×500px, hellgrau mit blauem Rahmen und Text "Kontakt via QR"',
        minimal: 'Minimal: 340×340px, kompakt mit dünnem grauem Rahmen – perfekt für kleine Plätze',
        professional: 'Professionell: 450×550px, schwarzer doppelter Rahmen mit rotem Akzent und großem Text "FAHRZEUG-KONTAKT"'
    };

    designSelect?.addEventListener('change', () => {
        designInfo.textContent = designDescriptions[designSelect.value];
    });

    document.getElementById('generateBtn')?.addEventListener('click', () => {
        document.getElementById('generatorModal').style.display = 'flex';
    });

    document.getElementById('closeModalBtn')?.addEventListener('click', () => {
        document.getElementById('generatorModal').style.display = 'none';
    });

    // Select to Input Handler
    document.getElementById('qrTitleSelect')?.addEventListener('change', function() {
        if (this.value) {
            document.getElementById('qrTitle').value = this.value;
        }
    });

    document.getElementById('editQRTitleSelect')?.addEventListener('change', function() {
        if (this.value) {
            document.getElementById('editQRTitle').value = this.value;
        }
    });

    document.getElementById('createQrBtn')?.addEventListener('click', async () => {
        const label = document.getElementById('qrLabel').value;
        const title = document.getElementById('qrTitle').value;
        const design = document.getElementById('qrDesign').value;
        const backgroundColor = document.getElementById('qrBackgroundColor').value;
        const iconType = document.getElementById('qrIconType').value;
        const iconPosition = document.getElementById('qrIconPosition').value;
        const licensePlate = document.getElementById('qrLicensePlate').value || null;
        const vehicleImageFile = document.getElementById('qrVehicleImage').files[0];

        console.log('[QR Create] Daten:', { label, title, design, background_color: backgroundColor, icon_type: iconType, icon_position: iconPosition, license_plate: licensePlate });

        try {
            const res = await apiFetch(`${API_BASE}/qrcode/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label, title, design, background_color: backgroundColor, icon_type: iconType, icon_position: iconPosition, license_plate: licensePlate })
            });

            console.log('[QR Create] Response Status:', res.status, res.ok);

            if (res.ok) {
                const qrData = await res.json();
                console.log('[QR Create] Success, ID:', qrData.id);

                // Upload Fahrzeugbild falls vorhanden
                if (vehicleImageFile) {
                    const formData = new FormData();
                    formData.append('file', vehicleImageFile);
                    await apiFetch(`${API_BASE}/qrcode/${qrData.id}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });
                }

                document.getElementById('generatorModal').style.display = 'none';
                document.getElementById('qrLabel').value = 'Mein Auto';
                document.getElementById('qrTitle').value = 'KONTAKT FAHRZEUGHALTER';
                document.getElementById('qrDesign').value = 'default';
                document.getElementById('qrIconType').value = 'phone';
                document.getElementById('qrIconPosition').value = 'bottom';
                document.getElementById('qrLicensePlate').value = '';
                document.getElementById('qrVehicleImage').value = '';
                loadQRCodes();
            } else {
                console.error('[QR Create] Response NOT ok:', res.status);
                const errorData = await res.json().catch(() => ({}));
                console.error('[QR Create] Error data:', errorData);
            }
        } catch (e) {
            console.error('[QR Create] Fehler:', e);
        }
    });
}

function editQRCodeClick(btn) {
    const qrId = btn.dataset.qrid;
    const label = btn.dataset.label;
    const title = btn.dataset.title;
    const design = btn.dataset.design;
    const backgroundColor = btn.dataset.backgroundColor;
    const iconType = btn.dataset.iconType;
    const iconPosition = btn.dataset.iconPosition;
    const licensePlate = btn.dataset.licensePlate;
    const vehicleImagePath = btn.dataset.vehicleImagePath;

    // Speichere original title für später
    document.getElementById('editQRModal').dataset.originalTitle = title;
    document.getElementById('editQRModal').dataset.qrId = qrId;

    editQRCode(qrId, label, title, design, licensePlate, vehicleImagePath, backgroundColor, iconType, iconPosition);
}

function editQRCode(qrId, label, title, design, licensePlate, vehicleImagePath, backgroundColor, iconType, iconPosition) {
    document.getElementById('editQRLabel').value = label || '';
    document.getElementById('editQRTitle').value = title || '';
    document.getElementById('editQRDesign').value = design || '';
    document.getElementById('editQRBackgroundColor').value = backgroundColor || '#f5f5f5';
    document.getElementById('editQRIconType').value = iconType || 'phone';
    document.getElementById('editQRIconPosition').value = iconPosition || 'bottom';
    document.getElementById('editLicensePlate').value = licensePlate || '';
    document.getElementById('editVehicleImage').value = '';
    document.getElementById('editQRModal').style.display = 'flex';
    document.getElementById('editQRModal').dataset.qrId = qrId;
    updateEditDesignInfo(design);

    // Zeige Fahrzeugbild Vorschau, falls vorhanden
    const previewDiv = document.getElementById('vehicleImagePreview');
    if (vehicleImagePath) {
        previewDiv.innerHTML = `
            <div style="position: relative;">
                <img src="${vehicleImagePath}" alt="Fahrzeugbild" style="max-width: 300px; border-radius: 8px;">
                <button type="button" class="btn btn-secondary" id="removeImageBtn" style="margin-top: 10px; width: 100%;">Bild entfernen</button>
            </div>
        `;
        document.getElementById('removeImageBtn').addEventListener('click', () => {
            previewDiv.innerHTML = '';
        });
    } else {
        previewDiv.innerHTML = '';
    }
}

function updateEditDesignInfo(design) {
    const designDescriptions = {
        default: 'Standard: 400×500px, hellgrau mit blauem Rahmen und Text "Kontakt via QR"',
        minimal: 'Minimal: 340×340px, kompakt mit dünnem grauem Rahmen – perfekt für kleine Plätze',
        professional: 'Professionell: 450×550px, schwarzer doppelter Rahmen mit rotem Akzent und großem Text "FAHRZEUG-KONTAKT"'
    };
    document.getElementById('editDesignInfo').textContent = designDescriptions[design] || '';
}

document.getElementById('closeEditBtn')?.addEventListener('click', () => {
    document.getElementById('editQRModal').style.display = 'none';
});

document.getElementById('cancelEditBtn')?.addEventListener('click', () => {
    document.getElementById('editQRModal').style.display = 'none';
});

document.getElementById('editQRDesign')?.addEventListener('change', (e) => {
    updateEditDesignInfo(e.target.value);
});

document.getElementById('saveEditBtn')?.addEventListener('click', async () => {
    const editModal = document.getElementById('editQRModal');
    const qrId = editModal.dataset.qrId;
    const newLabel = document.getElementById('editQRLabel').value || '';
    const newTitle = document.getElementById('editQRTitle').value || editModal.dataset.originalTitle || '';
    const newDesign = document.getElementById('editQRDesign').value || '';
    const newBackgroundColor = document.getElementById('editQRBackgroundColor').value;
    const newIconType = document.getElementById('editQRIconType').value || 'phone';
    const newIconPosition = document.getElementById('editQRIconPosition').value || 'bottom';
    const newLicensePlate = document.getElementById('editLicensePlate').value || '';
    const vehicleImageFile = document.getElementById('editVehicleImage').files[0];

    console.log('Saving:', {qrId, newLabel, newTitle, newDesign, newBackgroundColor, newIconType, newIconPosition, newLicensePlate});

    try {
        // Speichere QR-Code Metadaten
        const res = await apiFetch(`${API_BASE}/qrcode/${qrId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label: newLabel, title: newTitle, design: newDesign, background_color: newBackgroundColor, icon_type: newIconType, icon_position: newIconPosition, license_plate: newLicensePlate })
        });

        if (res.ok) {
            // Wenn ein neues Bild ausgewählt wurde, lade es hoch
            if (vehicleImageFile) {
                await uploadVehicleImage(qrId, vehicleImageFile);
            }

            document.getElementById('editQRModal').style.display = 'none';
            // Cache-Buster für Bilder
            const timestamp = new Date().getTime();
            document.querySelectorAll(`img[src*="/qrcode/${qrId}/image"]`).forEach(img => {
                img.src = `${API_BASE}/qrcode/${qrId}/image?t=${timestamp}`;
            });
            loadQRCodes();
        } else {
            showError('Fehler beim Aktualisieren');
        }
    } catch (e) {
        showError('Fehler: ' + e.message);
    }
});

async function uploadVehicleImage(qrId, file) {
    // Stelle sicher, dass Passwort gespeichert ist
    if (!dashboardPassword) {
        dashboardPassword = prompt('Dashboard Passwort:');
        if (!dashboardPassword) {
            throw new Error('Passwort erforderlich');
        }
    }

    try {
        const formData = new FormData();
        formData.append('file', file);

        const headers = {
            'Authorization': 'Basic ' + btoa(':' + dashboardPassword)
        };

        const res = await fetch(`${API_BASE}/qrcode/${qrId}/upload-image`, {
            method: 'POST',
            headers,
            body: formData,
            credentials: 'include'
        });

        if (res.status === 401) {
            dashboardPassword = null;
            throw new Error('Passwort falsch, bitte erneut versuchen');
        }

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || 'Fehler beim Upload');
        }

        return await res.json();
    } catch (e) {
        showError('Fehler beim Bild-Upload: ' + e.message);
        throw e;
    }
}

document.getElementById('uploadVehicleImageBtn')?.addEventListener('click', async () => {
    const file = document.getElementById('editVehicleImage').files[0];
    if (!file) {
        showError('Bitte wähle ein Bild aus');
        return;
    }

    const qrId = document.getElementById('editQRModal').dataset.qrId;
    if (!qrId) {
        showError('QR-Code ID nicht gefunden');
        return;
    }

    try {
        await uploadVehicleImage(qrId, file);
        const data = await (await apiFetch(`${API_BASE}/qrcode/${qrId}`)).json();

        // Aktualisiere die Vorschau
        const previewDiv = document.getElementById('vehicleImagePreview');
        if (data.vehicle_image_path) {
            previewDiv.innerHTML = `
                <div style="position: relative;">
                    <img src="${data.vehicle_image_path}?t=${new Date().getTime()}" alt="Fahrzeugbild" style="max-width: 300px; border-radius: 8px;">
                    <button type="button" class="btn btn-secondary" id="removeImageBtn" style="margin-top: 10px; width: 100%;">Bild entfernen</button>
                </div>
            `;
        }
    } catch (e) {
        console.error('Upload-Fehler:', e);
    }
});

function deleteQRCode(qrId) {
    showConfirm('QR-Code löschen', 'QR-Code wirklich löschen?', async () => {
        try {
            const res = await apiFetch(`${API_BASE}/qrcode/${qrId}`, { method: 'DELETE' });
            if (res.ok) {
                loadQRCodes();
            } else {
                showError('Fehler beim Löschen');
            }
        } catch (e) {
            showError('Fehler: ' + e.message);
        }
    });
}

window.addEventListener('click', (e) => {
    const modal = document.getElementById('generatorModal');
    if (e.target === modal) {
        modal.style.display = 'none';
    }
    const msgModal = document.getElementById('messageModal');
    if (e.target === msgModal) {
        msgModal.style.display = 'none';
    }
    const editModal = document.getElementById('editQRModal');
    if (e.target === editModal) {
        editModal.style.display = 'none';
    }
});

// ===== ANALYTICS TAB =====
async function loadAnalytics() {
    try {
        const res = await apiFetch(`${API_BASE}/dashboard/stats`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('totalScans').textContent = data.total_scans || 0;
            document.getElementById('conversionRate').textContent = (data.conversion_rate || 0) + '%';
        }
    } catch (e) {
        console.error('Error loading analytics:', e);
    }
}

// QR-Code Selection für Analytics
document.getElementById('qrCodeSelect')?.addEventListener('change', async (e) => {
    const qrId = e.target.value;
    const content = document.getElementById('analyticsContent');
    const noQR = document.getElementById('noQRSelected');

    if (!qrId) {
        content.style.display = 'none';
        noQR.style.display = 'block';
        return;
    }

    content.style.display = 'block';
    noQR.style.display = 'none';

    try {
        const res = await apiFetch(`${API_BASE}/dashboard/qr-stats/${qrId}`);
        if (res.ok) {
            const stats = await res.json();

            // Update stat cards
            document.getElementById('qrTotalScans').textContent = stats.total_scans || 0;
            document.getElementById('qrMessages').textContent = stats.messages_count || 0;
            document.getElementById('qrConversion').textContent = (stats.conversion_rate || 0) + '%';

            // Device Breakdown
            const deviceDiv = document.getElementById('deviceBreakdown');
            deviceDiv.innerHTML = '';
            Object.entries(stats.scans_by_device || {}).forEach(([device, count]) => {
                const bar = document.createElement('div');
                bar.className = 'breakdown-item';
                const percentage = ((count / stats.total_scans) * 100).toFixed(1);
                bar.innerHTML = `
                    <div class="breakdown-label">${device} <span class="breakdown-count">${count}</span></div>
                    <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div class="breakdown-percent">${percentage}%</div>
                `;
                deviceDiv.appendChild(bar);
            });

            // Browser Breakdown
            const browserDiv = document.getElementById('browserBreakdown');
            browserDiv.innerHTML = '';
            Object.entries(stats.scans_by_browser || {}).forEach(([browser, count]) => {
                const bar = document.createElement('div');
                bar.className = 'breakdown-item';
                const percentage = ((count / stats.total_scans) * 100).toFixed(1);
                bar.innerHTML = `
                    <div class="breakdown-label">${browser} <span class="breakdown-count">${count}</span></div>
                    <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div class="breakdown-percent">${percentage}%</div>
                `;
                browserDiv.appendChild(bar);
            });

            // Country Breakdown
            const countryDiv = document.getElementById('countryBreakdown');
            countryDiv.innerHTML = '';
            Object.entries(stats.scans_by_country || {}).forEach(([country, count]) => {
                const bar = document.createElement('div');
                bar.className = 'breakdown-item';
                const percentage = ((count / stats.total_scans) * 100).toFixed(1);
                bar.innerHTML = `
                    <div class="breakdown-label">${country || 'Unknown'} <span class="breakdown-count">${count}</span></div>
                    <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div class="breakdown-percent">${percentage}%</div>
                `;
                countryDiv.appendChild(bar);
            });

            // Latest Scans
            const scansDiv = document.getElementById('latestScans');
            scansDiv.innerHTML = '';
            (stats.latest_scans || []).forEach(scan => {
                const scanEl = document.createElement('div');
                scanEl.className = 'scan-item';
                const date = new Date(scan.created_at).toLocaleString('de-DE');
                const geo = scan.latitude && scan.longitude ?
                    `📍 ${scan.latitude.toFixed(4)}, ${scan.longitude.toFixed(4)}` :
                    '📍 IP-based';
                scanEl.innerHTML = `
                    <div class="scan-info">
                        <div class="scan-device">${scan.device_type} • ${scan.browser_name}</div>
                        <div class="scan-country">${scan.country || 'Unknown'}</div>
                        <div class="scan-geo">${geo}</div>
                        <div class="scan-time">${date}</div>
                    </div>
                `;
                scansDiv.appendChild(scanEl);
            });
        }
    } catch (e) {
        showError('Fehler beim Laden von Analytics: ' + e.message);
    }
}

// Populate QR Code Select on QR Codes load
function populateQRCodeSelect() {
    const select = document.getElementById('qrCodeSelect');
    const qrGrid = document.getElementById('qrcodesGrid');

    const qrCards = qrGrid.querySelectorAll('[data-qr-id]');
    select.innerHTML = '<option value="">-- QR-Code wählen --</option>';

    qrCards.forEach(card => {
        const qrId = card.dataset.qrId;
        const label = card.querySelector('.qr-label')?.textContent || `QR ${qrId}`;
        const option = document.createElement('option');
        option.value = qrId;
        option.textContent = label;
        select.appendChild(option);
    });
}

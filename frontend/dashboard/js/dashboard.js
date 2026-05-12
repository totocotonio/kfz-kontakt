const API_BASE = '/api';
let currentMessageId = null;

document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    loadMessages();
    loadStats();
    loadQRCodes();
    setupQRCodeGenerator();
});

function setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tabName) {
    document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));

    event.target.closest('.nav-item').classList.add('active');
    document.getElementById(tabName).classList.add('active');

    const titles = {
        messages: 'Nachrichten',
        qrcodes: 'QR-Codes',
        stats: 'Statistiken'
    };
    document.getElementById('pageTitle').textContent = titles[tabName];

    if (tabName === 'messages') loadMessages();
    if (tabName === 'qrcodes') loadQRCodes();
    if (tabName === 'stats') loadStats();
}

async function loadMessages() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/messages`);
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
        const res = await fetch(`${API_BASE}/dashboard/messages/${msgId}`);
        const msg = await res.json();
        currentMessageId = msgId;

        const detail = document.getElementById('messageDetail');
        detail.innerHTML = `
            <div class="message-detail-header">
                <h2>${msg.sender_name}</h2>
                <div class="message-detail-meta">
                    <span>📌 ${msg.qr_label}</span>
                    <span>📅 ${new Date(msg.created_at).toLocaleDateString('de-DE')}</span>
                    ${msg.category ? `<span>🏷️ ${msg.category}</span>` : ''}
                </div>
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

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/dashboard/stats`);
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
        const res = await fetch(`${API_BASE}/qrcodes/list`);
        const data = await res.json();
        const grid = document.getElementById('qrcodesGrid');

        if (!data.qrcodes || data.qrcodes.length === 0) {
            grid.innerHTML = '<div class="loading">Keine QR-Codes erstellt</div>';
            return;
        }

        grid.innerHTML = data.qrcodes.map(qr => `
            <div class="qrcode-card">
                <div class="qrcode-preview">
                    <img src="${API_BASE}/qrcode/${qr.id}/image" alt="${qr.label}">
                </div>
                <div class="qrcode-label">${qr.label}</div>
                <div style="font-size: 12px; color: #999; margin-bottom: 10px;">Design: ${qr.design}</div>
                <div class="qrcode-actions">
                    <a href="${API_BASE}/qrcode/${qr.id}/image" download="qr_${qr.id}.png" class="btn btn-primary">Runterladen</a>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Fehler beim Laden der QR-Codes:', e);
    }
}

function setupQRCodeGenerator() {
    document.getElementById('generateBtn')?.addEventListener('click', () => {
        document.getElementById('generatorModal').style.display = 'flex';
    });

    document.getElementById('closeModalBtn')?.addEventListener('click', () => {
        document.getElementById('generatorModal').style.display = 'none';
    });

    document.getElementById('createQrBtn')?.addEventListener('click', async () => {
        const label = document.getElementById('qrLabel').value;
        const design = document.getElementById('qrDesign').value;

        try {
            const res = await fetch(`${API_BASE}/qrcode/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label, design })
            });

            if (res.ok) {
                document.getElementById('generatorModal').style.display = 'none';
                loadQRCodes();
            }
        } catch (e) {
            console.error('Fehler beim Erstellen des QR-Codes:', e);
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
});

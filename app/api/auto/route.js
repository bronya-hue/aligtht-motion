const express = require('express');
const crypto = require('crypto');
const fetch = require('node-fetch');
const mailAccounts = require('../../../lib/mail-store'); // Import gudang password

const router = express.Router();

// Konfigurasi API
const MAILTM_BASE = 'https://api.mail.tm';
const ALIGHT_API = 'https://api.alightmotion.com'; // Sesuaikan jika ada perubahan

router.post('/', async (req, res) => {
    try {
        // 1. Buat email & password acak baru
        const domainsRes = await fetch(`${MAILTM_BASE}/domains`);
        const domainsData = await domainsRes.json();
        const domain = domainsData['hydra:member'][0].domain;
        
        const address = `neo${crypto.randomBytes(6).toString('hex')}@${domain}`;
        const password = crypto.randomBytes(12).toString('base64url') + 'X1!';

        // 2. Daftarkan email ke mail.tm
        const regRes = await fetch(`${MAILTM_BASE}/accounts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address, password })
        });
        if (!regRes.ok) throw new Error('Gagal mendaftarkan email ke mail.tm');

        // 3. Login untuk mendapatkan token inbox
        const tokenRes = await fetch(`${MAILTM_BASE}/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address, password })
        });
        const tokenData = await tokenRes.json();
        if (!tokenData.token) throw new Error('Gagal login ke mail.tm');

        // ==========================================
        // 💾 SIMPAN PASSWORD KE GUDANG (PENTING!)
        // ==========================================
        mailAccounts.set(address, { password, token: tokenData.token });

        // 4. Kirim request Magic Link ke Alight Motion
        await fetch(`${ALIGHT_API}/api/auth/magic-link`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'okhttp/4.9.2',
                'x-android-package': 'com.alightcreative.motion',
                'x-android-cert': '...' // Jika kode asli Anda punya cert fingerprint, tambahkan di sini
            },
            body: JSON.stringify({ email: address })
        });

        // 5. Polling inbox menunggu email masuk
        let magicLink = null;
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 3000)); // Tunggu 3 detik
            
            const msgRes = await fetch(`${MAILTM_BASE}/messages`, {
                headers: { 'Authorization': `Bearer ${tokenData.token}` }
            });
            const msgData = await msgRes.json();
            const messages = msgData['hydra:member'] || [];

            if (messages.length > 0) {
                const msgId = messages[0].id;
                const detailRes = await fetch(`${MAILTM_BASE}/messages/${msgId}`, {
                    headers: { 'Authorization': `Bearer ${tokenData.token}` }
                });
                const detail = await detailRes.json();
                const text = detail.text || '';
                const urls = text.match(/https?:\/\/[^\s]+/g);
                if (urls) {
                    magicLink = urls.find(u => u.includes('oobCode') || u.includes('alight'));
                    if (magicLink) break;
                }
            }
        }

        if (!magicLink) throw new Error('link verifikasi tidak ditemukan di email');

        // 6. Verifikasi link & dapatkan idToken
        // (Sesuaikan endpoint verify ini dengan kode asli repo Anda)
        const verifyRes = await fetch(`${ALIGHT_API}/api/auth/verify-link`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: address, magicLink })
        });
        const verifyData = await verifyRes.json();
        const idToken = verifyData.idToken;
        if (!idToken) throw new Error('Gagal mendapatkan token verifikasi');

        // 7. Aktifkan Premium (verifyPurchase)
        // (Sesuaikan endpoint ini dengan kode asli repo Anda)
        const purchaseRes = await fetch(`${ALIGHT_API}/api/verifyPurchase`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${idToken}`
            },
            body: JSON.stringify({ idToken })
        });
        const purchaseData = await purchaseRes.json();

        // 8. Sukses! Kembalikan data ke bot
        return res.json({
            success: true,
            data: {
                email: address,
                uid: purchaseData.uid || verifyData.uid || 'Unknown',
                orderId: purchaseData.orderId || `neo-${crypto.randomBytes(4).toString('hex')}`,
                validUntil: '7 November 2027', // Atau ambil dari respons purchaseData
                idToken: idToken
            }
        });

    } catch (error) {
        console.error('Auto Error:', error);
        return res.status(500).json({ success: false, message: error.message });
    }
});

module.exports = router;

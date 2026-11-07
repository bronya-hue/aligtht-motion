const express = require('express');
const statusRoute = require('./status/route');
const sendLinkRoute = require('./send-link/route');
const verifyLinkRoute = require('./verify-link/route');
const statsRoute = require('./stats/route');
const emailRoute = require('./email/route');
const autoRoute = require('./auto/route');
const mailAccounts = require('../../lib/mail-store');
const fetch = require('node-fetch');

const router = express.Router();

router.use('/status', statusRoute);
router.use('/send-link', sendLinkRoute);
router.use('/verify-link', verifyLinkRoute);
router.use('/stats', statsRoute);
router.use('/email', emailRoute);
router.use('/auto', autoRoute);

// ==========================================
// ENDPOINT BARU: Cek Inbox untuk Fitur /login
// ==========================================
router.post('/inbox', async (req, res) => {
    const { email } = req.body;
    if (!email) return res.status(400).json({ success: false, message: 'Email required' });

    const account = mailAccounts.get(email);
    if (!account) {
        return res.json({ 
            success: false, 
            message: 'Akun email tidak ditemukan. Pastikan email ini dibuat melalui bot (fitur Auto Premium), atau server bot baru saja restart.' 
        });
    }

    try {
        // 1. Dapatkan token baru dari mail.tm menggunakan password yang tersimpan
        const tokenRes = await fetch('https://api.mail.tm/token', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ address: email, password: account.password })
        });
        const tokenData = await tokenRes.json();
        
        if (!tokenData.token) {
            return res.json({ success: false, message: 'Gagal login ke mail.tm. Sesi mungkin sudah expired, silakan buat akun baru.' });
        }

        // 2. Ambil daftar pesan
        const msgRes = await fetch('https://api.mail.tm/messages', {
            headers: { 'Authorization': `Bearer ${tokenData.token}` }
        });
        const msgData = await msgRes.json();
        const messages = msgData['hydra:member'] || [];

        if (messages.length === 0) {
            return res.json({ 
                success: false, 
                message: 'Inbox kosong. Buka aplikasi Alight Motion, masukkan email ini, klik "Kirim Magic Link", lalu tunggu 10 detik dan coba /login lagi.' 
            });
        }

        // 3. Ambil pesan terbaru dan download raw email untuk ekstrak link
        const latestMsg = messages[0];
        const downloadRes = await fetch(`https://api.mail.tm/messages/${latestMsg.id}/download`, {
            headers: { 'Authorization': `Bearer ${tokenData.token}` }
        });
        const raw = await downloadRes.text();
        
        // Decode format email (quoted-printable)
        let joined = raw.replace(/=\r?\n/g, '').replace(/=3D/g, '=');
        
        // Cari URL lengkap yang mengandung oobCode
        const urlMatch = joined.match(/https?:\/\/[^\s"'<>]+oobCode[^\s"'<>]+/i);
        
        if (urlMatch) {
            return res.json({ success: true, link: urlMatch[0] });
        } else {
            return res.json({ success: false, message: 'Email masuk, tapi link verifikasi tidak ditemukan di dalamnya.' });
        }

    } catch (error) {
        return res.status(500).json({ success: false, message: error.message });
    }
});

module.exports = router;

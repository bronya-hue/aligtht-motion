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

router.post('/inbox', async (req, res) => {
    const { email } = req.body;
    if (!email) return res.status(400).json({ success: false, message: 'Email required' });

    const account = mailAccounts.get(email);
    if (!account) {
        return res.json({ success: false, message: 'Akun email tidak ditemukan. Pastikan dibuat dari bot ini.' });
    }

    try {
        const tokenRes = await fetch('https://api.mail.tm/token', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ address: email, password: account.password })
        });
        const tokenData = await tokenRes.json();
        
        if (!tokenData.token) return res.json({ success: false, message: 'Gagal login ke mail.tm.' });

        const msgRes = await fetch('https://api.mail.tm/messages', {
            headers: { 'Authorization': `Bearer ${tokenData.token}` }
        });
        const msgData = await msgRes.json();
        const messages = msgData['hydra:member'] || [];

        if (messages.length === 0) {
            return res.json({ success: false, message: 'Inbox kosong. Klik "Kirim Magic Link" di aplikasi dulu.' });
        }

        const latestMsg = messages[0];
        const downloadRes = await fetch(`https://api.mail.tm/messages/${latestMsg.id}/download`, {
            headers: { 'Authorization': `Bearer ${tokenData.token}` }
        });
        const raw = await downloadRes.text();
        
        let joined = raw.replace(/=\r?\n/g, '').replace(/=3D/g, '=');
        const urlMatch = joined.match(/https?:\/\/[^\s"'<>]+oobCode[^\s"'<>]+/i);
        
        if (urlMatch) {
            let link = urlMatch[0].replace(/&amp;/g, '&');
            
            // =========================================================
            // PERBAIKAN: Ambil link asli Alight Motion & Kode OOB
            // =========================================================
            const redirectMatch = link.match(/[?&]link=([^&]+)/);
            if (redirectMatch) {
                // Jika link adalah redirector Firebase, ambil link aslinya (alightcreative.com)
                link = decodeURIComponent(redirectMatch[1]);
            }
            
            // Ambil kode oobCode (misal: sFoK26Ssgv7lX5E...)
            const oobMatch = link.match(/oobCode(?:%3D|=)([a-zA-Z0-9_-]+)/i);
            const oobCode = oobMatch ? oobMatch[1] : 'Tidak ditemukan';

            return res.json({ 
                success: true, 
                link: link.replace(/\/\//g, '/'), // Bersihkan double slash
                oobCode: oobCode
            });
        } else {
            return res.json({ success: false, message: 'Email masuk, tapi link tidak ditemukan.' });
        }

    } catch (error) {
        return res.status(500).json({ success: false, message: error.message });
    }
});

module.exports = router;

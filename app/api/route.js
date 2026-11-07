const express = require('express');
const statusRoute = require('./status/route');
const sendLinkRoute = require('./send-link/route');
const verifyLinkRoute = require('./verify-link/route');
const statsRoute = require('./stats/route');
const emailRoute = require('./email/route');
const autoRoute = require('./auto/route');

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

    try {
        // ⚠️ CATATAN PENTING:
        // Di bawah ini adalah contoh menggunakan API mail.tm.
        // Karena bot Anda berhasil membuat email @fldubai.com, Anda HARUS menyesuaikan
        // logika fetch di bawah ini dengan API temp mail yang Anda gunakan di endpoint /auto.
        
        // CONTOH (Silakan ganti dengan logika API temp mail Anda):
        /*
        const tokenRes = await fetch('https://api.mail.tm/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address: email, password: 'password_anda' })
        });
        const tokenData = await tokenRes.json();
        
        const msgRes = await fetch('https://api.mail.tm/messages', {
            headers: { Authorization: `Bearer ${tokenData.token}` }
        });
        const messages = await msgRes.json();
        
        let magicLink = null;
        for (const msg of messages['hydra:member'] || []) {
            const detailRes = await fetch(`https://api.mail.tm/messages/${msg.id}`, {
                headers: { Authorization: `Bearer ${tokenData.token}` }
            });
            const detail = await detailRes.json();
            const text = detail.text || '';
            
            const urls = text.match(/https?:\/\/[^\s]+/g);
            if (urls) {
                magicLink = urls.find(u => u.includes('oobCode') || u.includes('alight'));
                if (magicLink) break;
            }
        }

        if (magicLink) {
            return res.json({ success: true, link: magicLink });
        } else {
            return res.json({ success: false, message: 'Link belum masuk ke inbox.' });
        }
        */

        // SEMENTARA: Kirim respons palsu jika API belum disesuaikan
        return res.json({ success: false, message: 'Endpoint siap, tapi logika API temp mail belum disesuaikan.' });

    } catch (error) {
        return res.status(500).json({ success: false, message: error.message });
    }
});

module.exports = router;

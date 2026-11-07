const express = require('express');
const crypto = require('crypto');
const fetch = require('node-fetch');
const mailAccounts = require('../../../lib/mail-store');
const { getProxyAgent } = require('../../../lib/proxy-manager');
const auth = require('../../../lib/auth'); // Kode rahasia Alight Motion

const router = express.Router();
const MAILTM_BASE = 'https://api.mail.tm';
const delay = (ms) => new Promise(res => setTimeout(res, ms));

router.post('/', async (req, res) => {
    const log = [];
    const push = (step, msg) => log.push({ step, message: msg, at: new Date().toISOString() });
    
    try {
        const agent = getProxyAgent();
        push('init', agent ? 'Menggunakan Proxy...' : 'Tanpa Proxy...');
        
        // 1. Ambil Domain mail.tm (Rotasi Domain)
        const domainRes = await fetch(`${MAILTM_BASE}/domains`, { agent });
        const domainData = await domainRes.json();
        const domains = domainData['hydra:member'] || [];
        if (!domains.length) throw new Error('mail.tm: no domains available');
        
        const randomDomain = domains[Math.floor(Math.random() * domains.length)].domain;
        const address = `neo${crypto.randomBytes(5).toString('hex')}@${randomDomain}`;
        const password = crypto.randomBytes(12).toString('base64url') + 'X1!';
        
        // 2. Daftar Email
        push('email', `Mendaftarkan ${address}...`);
        const createRes = await fetch(`${MAILTM_BASE}/accounts`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ address, password }),
            agent
        });
        if (!createRes.ok) throw new Error(`mail.tm create failed (Proxy mati/IP blokir)`);
        
        // 3. Ambil Token Inbox
        const tokenRes = await fetch(`${MAILTM_BASE}/token`, {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ address, password }),
            agent
        });
        const tokenData = await tokenRes.json();
        if (!tokenData.token) throw new Error('mail.tm: failed to get token');
        
        // Simpan ke gudang
        mailAccounts.set(address, { password, token: tokenData.token });
        
        // 4. Tembak Alight Motion
        push('link', 'Mengirim magic link...');
        await delay(Math.floor(Math.random() * 3000) + 2000); 
        const lr = await auth.link(address); 
        if (!lr.ok) throw new Error(`link gagal: ${lr.why}`);
        
        // 5. Polling Inbox
        push('poll', 'Menunggu email masuk...');
        let magicLink = null;
        for (let i = 0; i < 20; i++) {
            await delay(3000);
            const msgRes = await fetch(`${MAILTM_BASE}/messages`, { headers: { 'Authorization': `Bearer ${tokenData.token}` }, agent });
            const msgData = await msgRes.json();
            const messages = msgData['hydra:member'] || [];
            
            if (messages.length > 0) {
                const downloadRes = await fetch(`${MAILTM_BASE}/messages/${messages[0].id}/download`, { headers: { 'Authorization': `Bearer ${tokenData.token}` }, agent });
                const raw = await downloadRes.text();
                let joined = raw.replace(/=\r?\n/g, '').replace(/=3D/g, '=');
                const urlMatch = joined.match(/https?:\/\/[^\s"'<>]+oobCode[^\s"'<>]+/i);
                if (urlMatch) {
                    magicLink = urlMatch[0].replace(/&amp;/g, '&');
                    break;
                }
            }
        }
        
        if (!magicLink) throw new Error('link verifikasi tidak ditemukan di email');
        
        // 6. Verifikasi & Aktivasi
        push('verify', 'Memverifikasi link...');
        const v = await auth.auth(address, magicLink);
        if (!v.ok) throw new Error(`verifikasi gagal: ${v.why}`);
        
        push('premium', 'Mengaktifkan premium...');
        const premium = await auth.pro(v.id);
        
        return res.json({
            success: premium.ok,
            message: premium.ok ? `Premium aktif` : `Gagal aktivasi`,
            data: {
                email: address,
                uid: v.uid,
                orderId: premium.order || null,
                validUntil: new Date(new Date().setFullYear(new Date().getFullYear() + 1)).toLocaleDateString('id-ID'),
                idToken: v.id
            },
            log
        });
        
    } catch (e) {
        console.error('Auto Error:', e);
        return res.status(500).json({ success: false, message: e.message, log });
    }
});

module.exports = router;

const axios = require('axios');
const HttpsProxyAgent = require('https-proxy-agent');
const fs = require('fs');
const path = require('path');

let aliveProxies = [];
let allProxies = [];
let isScraping = false;

// Baca file proxies.txt
try {
    const proxyFile = path.join(__dirname, '../../proxies.txt');
    if (fs.existsSync(proxyFile)) {
        allProxies = fs.readFileSync(proxyFile, 'utf8')
            .split('\n')
            .map(p => p.trim())
            .filter(p => p.length > 0);
        console.log(`[PROXY] Berhasil memuat ${allProxies.length} proxy dari proxies.txt`);
    }
} catch (e) {
    console.log(`[PROXY] Error membaca proxies.txt: ${e.message}`);
}

// ==========================================
// FUNGSI AUTO-FORMAT PROXY
// ==========================================
function formatProxy(p) {
    // Jika sudah ada http:// atau socks5://, biarkan
    if (p.includes('://')) return p; 
    
    const parts = p.split(':');
    if (parts.length === 4) {
        // Format: host:port:user:pass
        const [host, port, user, pass] = parts;
        return `http://${user}:${pass}@${host}:${port}`;
    } else if (parts.length === 2) {
        // Format: host:port
        const [host, port] = parts;
        return `http://${host}:${port}`;
    }
    // Fallback
    return `http://${p}`;
}

async function testProxy(rawProxy) {
    try {
        const proxyUrl = formatProxy(rawProxy);
        const agent = new HttpsProxyAgent(proxyUrl);
        await axios.get('http://httpbin.org/ip', { 
            httpsAgent: agent, 
            proxy: false, 
            timeout: 5000 
        });
        return proxyUrl; // Kembalikan format yang sudah benar
    } catch (e) {
        return null;
    }
}

async function pickAndTestProxies() {
    if (isScraping || allProxies.length === 0) return;
    isScraping = true;
    
    const sampleSize = 150;
    const shuffled = [...allProxies].sort(() => 0.5 - Math.random());
    const sample = shuffled.slice(0, sampleSize);

    console.log(`[PROXY] Mengetes ${sampleSize} proxy acak dari total ${allProxies.length}...`);

    let alive = [];
    const batchSize = 30;

    for (let i = 0; i < sample.length; i += batchSize) {
        const batch = sample.slice(i, i + batchSize);
        const promises = batch.map(async (p) => {
            const validProxyUrl = await testProxy(p);
            if (validProxyUrl) alive.push(validProxyUrl);
        });
        
        await Promise.all(promises);
        if (alive.length >= 50) break; 
    }

    // Simpan maksimal 200 proxy hidup di RAM
    aliveProxies = [...new Set([...aliveProxies, ...alive])].slice(-200);
    
    console.log(`[PROXY] Selesai! Total proxy hidup siap pakai: ${aliveProxies.length}`);
    isScraping = false;
}

setTimeout(pickAndTestProxies, 5000);
setInterval(pickAndTestProxies, 5 * 60 * 1000);

function getProxyAgent() {
    if (aliveProxies.length === 0) return null; 
    const randomProxy = aliveProxies[Math.floor(Math.random() * aliveProxies.length)];
    return new HttpsProxyAgent(randomProxy);
}

module.exports = { getProxyAgent, aliveProxies };

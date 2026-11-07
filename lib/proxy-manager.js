const axios = require('axios');
const HttpsProxyAgent = require('https-proxy-agent');
const fs = require('fs');
const path = require('path');

let aliveProxies = [];
let allProxies = [];
let isScraping = false;

try {
    const proxyFile = path.join(__dirname, '../../proxies.txt');
    if (fs.existsSync(proxyFile)) {
        allProxies = fs.readFileSync(proxyFile, 'utf8').split('\n').map(p => p.trim()).filter(p => p.length > 0);
        console.log(`[PROXY] Memuat ${allProxies.length} proxy dari proxies.txt`);
    }
} catch (e) {
    console.log(`[PROXY] Error membaca proxies.txt: ${e.message}`);
}

function formatProxy(p) {
    if (p.includes('://')) return p; 
    const parts = p.split(':');
    if (parts.length === 4) {
        const [host, port, user, pass] = parts;
        return `http://${user}:${pass}@${host}:${port}`;
    } else if (parts.length === 2) {
        const [host, port] = parts;
        return `http://${host}:${port}`;
    }
    return `http://${p}`;
}

async function testProxy(rawProxy) {
    try {
        const proxyUrl = formatProxy(rawProxy);
        const agent = new HttpsProxyAgent(proxyUrl);
        await axios.get('http://httpbin.org/ip', { httpsAgent: agent, proxy: false, timeout: 5000 });
        return proxyUrl;
    } catch (e) {
        return null;
    }
}

async function pickAndTestProxies() {
    if (isScraping || allProxies.length === 0) return;
    isScraping = true;
    
    const sample = [...allProxies].sort(() => 0.5 - Math.random()).slice(0, 150);
    console.log(`[PROXY] Mengetes ${sample.length} proxy acak...`);

    let alive = [];
    for (let i = 0; i < sample.length; i += 30) {
        const batch = sample.slice(i, i + 30);
        const promises = batch.map(async (p) => {
            const validProxyUrl = await testProxy(p);
            if (validProxyUrl) alive.push(validProxyUrl);
        });
        await Promise.all(promises);
        if (alive.length >= 50) break; 
    }

    aliveProxies = [...new Set([...aliveProxies, ...alive])].slice(-200);
    console.log(`[PROXY] Selesai! Total proxy hidup: ${aliveProxies.length}`);
    isScraping = false;
}

setTimeout(pickAndTestProxies, 5000);
setInterval(pickAndTestProxies, 5 * 60 * 1000);

function getProxyAgent() {
    if (aliveProxies.length === 0) return null; 
    return new HttpsProxyAgent(aliveProxies[Math.floor(Math.random() * aliveProxies.length)]);
}

module.exports = { getProxyAgent, aliveProxies };

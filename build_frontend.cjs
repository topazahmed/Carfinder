const fs = require('node:fs');
const path = require('node:path');

const output = path.join(__dirname, 'public');
let html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const apiBase = process.env.API_BASE_URL;

if (apiBase) {
    const parsed = new URL(apiBase);
    if (!['https:', 'http:'].includes(parsed.protocol) || parsed.username || parsed.password || parsed.search || parsed.hash) {
        throw new Error('API_BASE_URL must be an HTTP(S) base URL without credentials, query, or fragment.');
    }
    const anchor = 'const API_BASE_URL =';
    if (!html.includes(anchor)) {
        throw new Error('Frontend API configuration anchor was not found.');
    }
    html = html.replace(anchor, `${anchor} ${JSON.stringify(apiBase.replace(/\/$/, ''))} ||`);
} else {
    console.warn('API_BASE_URL is not set; the frontend will use its existing hosted API default.');
}

fs.mkdirSync(output, { recursive: true });
fs.writeFileSync(path.join(output, 'index.html'), html);
fs.cpSync(path.join(__dirname, 'assets'), path.join(output, 'assets'), { recursive: true });
console.log('Built static frontend in public/; no backend files or credentials are published.');
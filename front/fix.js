
const fs = require('fs');

let content = fs.readFileSync('index.html', 'utf8');

const svgIcon = '<i class=\"van-icon text-lg\" style=\"display: flex; align-items: center; justify-content: center;\"><svg viewBox=\"0 0 24 24\" width=\"1em\" height=\"1em\" stroke=\"currentColor\" fill=\"none\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M20.38 3.46L16 2a8.96 8.96 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.25 1.15l-1.3 3.08a2 2 0 0 0 1.34 2.65l1.64.48V20a2 2 0 0 0 2 2h7.9a2 2 0 0 0 2-2v-9.18l1.64-.48a2 2 0 0 0 1.34-2.65l-1.3-3.08a2 2 0 0 0-1.25-1.15z\"></path></svg></i>';

// Replace all van-icon-clothes
content = content.replace(/<i class=\"van-icon van-icon-clothes text-lg\"><\/i>/g, svgIcon);

// Replace van-icon-box-o only in tabbar for wardrobePage
content = content.replace(
  /<div class=\"tabbar-item\" @click=\"showPage\('wardrobePage'\)\">\s*<i class=\"van-icon van-icon-box-o text-lg\"><\/i>/g,
  '<div class=\"tabbar-item\" @click=\"showPage(\'wardrobePage\')\">\\n          ' + svgIcon
);

fs.writeFileSync('index.html', content, 'utf8');
console.log('Replaced icons successfully.');


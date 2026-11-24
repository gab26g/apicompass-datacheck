/* Build a reversible static overlay from the exact pinned upstream image. */
const fs = require('node:fs');
const zlib = require('node:zlib');

const original = fs.readFileSync('/app/client/dist/index.html', 'utf8');
if (!original.includes('</head>')) throw new Error('Pinned upstream HTML has no closing head');
const html = original
  .replace(/<title>[^<]*<\/title>/, '<title>APICompass</title>')
  .replace(/content="LibreChat - [^"]*"/, 'content="Inspect synthetic inventory, shipments and equipment with DataCheck."')
  .replace('</head>', '<link rel="stylesheet" href="/assets/apicompass.css?v=1" /><link rel="icon" type="image/svg+xml" href="/assets/apicompass.svg" /></head>');
fs.writeFileSync('/brand-output/index.html', html);
fs.writeFileSync('/brand-output/index.html.gz', zlib.gzipSync(html));
fs.writeFileSync('/brand-output/index.html.br', zlib.brotliCompressSync(Buffer.from(html)));
console.log('Prepared APICompass HTML overlay and matching gzip/Brotli variants.');

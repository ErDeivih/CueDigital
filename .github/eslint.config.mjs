// Comprobaciones de fallos de ejecución; no introduce una compilación del frontend.
const browserGlobals = `
  window document navigator location history localStorage sessionStorage fetch
  Request Response Headers URL URLSearchParams Blob File FileReader FormData
  AbortController Event CustomEvent MouseEvent KeyboardEvent HTMLElement HTMLInputElement
  Node Element MutationObserver IntersectionObserver ResizeObserver DOMParser DOMException
  Image Audio Worker self caches clients indexedDB React ReactDOM ReactDOMServer htm
  console setTimeout clearTimeout setInterval clearInterval requestAnimationFrame
  cancelAnimationFrame queueMicrotask structuredClone crypto atob btoa performance
  matchMedia getComputedStyle SpeechRecognition webkitSpeechRecognition
`.trim().split(/\s+/);

export default [{
  files: ['**/*.js'],
  languageOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    globals: Object.fromEntries(browserGlobals.map((name) => [name, 'readonly'])),
  },
  rules: {
    'no-undef': 'error',
    'no-dupe-keys': 'error',
    'no-unreachable': 'error',
  },
}];

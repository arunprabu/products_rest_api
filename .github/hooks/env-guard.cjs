#!/usr/bin/env node
'use strict';

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  input += chunk;
});
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(input);
  } catch {
    process.stdout.write(JSON.stringify({ permissionDecision: 'allow' }));
    return;
  }

  const sensitivePath = /(?:^|[\\/])\.env(?:[^/\\]*)?(?=$|[\\/])/i;
  const allowedPath = /(?:^|[\\/])\.env\.example(?=$|[\\/])/i;
  const searchKeys = new Set(['query', 'pattern', 'regex', 'search']);
  const violations = [];

  function inspect(value, key = '') {
    if (typeof value === 'string') {
      if (searchKeys.has(key) && !/[\\/]/.test(value)) return;
      const paths = value.match(/(?:^|[\s"'=:])[^\s"'=:]*\.env[^\s"'=:]*/gi) ?? [];
      for (const candidate of paths) {
        const path = candidate.trim().replace(/^[\s"'=:]+/, '');
        if (sensitivePath.test(path) && !allowedPath.test(path)) violations.push(path);
      }
    } else if (Array.isArray(value)) {
      for (const item of value) inspect(item, key);
    } else if (value && typeof value === 'object') {
      for (const [childKey, childValue] of Object.entries(value)) inspect(childValue, childKey);
    }
  }

  inspect(payload.tool_input ?? {});
  if (violations.length > 0) {
    process.stdout.write(JSON.stringify({
      permissionDecision: 'deny',
      userMessage: 'Access to environment files is blocked; only .env.example is allowed.',
    }));
    return;
  }
  process.stdout.write(JSON.stringify({ permissionDecision: 'allow' }));
});

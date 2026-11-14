import { readFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const root = dirname(fileURLToPath(import.meta.url))
const cache = new Map()
export function loadTs(relative) {
  const path = resolve(root, relative)
  if (cache.has(path)) return cache.get(path).exports
  const module = { exports: {} }
  cache.set(path, module)
  const js = ts.transpileModule(readFileSync(path, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('require', 'module', 'exports', js)(specifier => {
    if (!specifier.startsWith('.')) throw new Error('Unit helper loader only allows local modules')
    return loadTs(resolve(dirname(path), specifier + '.ts'))
  }, module, module.exports)
  return module.exports
}

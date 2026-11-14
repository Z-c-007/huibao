import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import ts from 'typescript'

// Test the actual TypeScript consumer without a browser or an extra test runner.
const source = readFileSync(new URL('./src/lib/chatStream.ts', import.meta.url), 'utf8')
const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
const { readChatStream } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`)
function stream(text, chunkSize = 1) {
  const bytes = new TextEncoder().encode(text)
  return new ReadableStream({ start(controller) {
    for (let index = 0; index < bytes.length; index += chunkSize) controller.enqueue(bytes.slice(index, index + chunkSize))
    controller.close()
  } })
}
const events = []
await readChatStream(stream(': heartbeat\r\n\r\ndata: {"type":"reasoning_delta","text":"中文思考"}\r\n\r\ndata: {"type":"content_delta","text":"回答"}\n\ndata: {"type":"done","history":[]}\n\n'), event => events.push(event))
assert.deepEqual(events.map(event => event.text).filter(Boolean), ['中文思考', '回答'])
assert.equal(events.at(-1).type, 'done')
await assert.rejects(readChatStream(stream('data: {"type":"content_delta","text":"部分回答"}\n\n'), () => {}), /回答未完成/)
await assert.rejects(readChatStream(stream('data: {"type":"error","message":"服务错误"}\n\n'), () => {}), /服务错误/)
const multiline = []
await readChatStream(stream('data: {"type":"done",\ndata: "history":[]}\n\n', 3), event => multiline.push(event))
assert.equal(multiline[0].type, 'done')
console.log('Passed: split UTF-8 / CRLF frames, heartbeat, completion, interruption, server errors and multiline SSE.')

export interface ToolResult {
  tool: string
  args: Record<string, unknown>
  result: Record<string, unknown>
}
export type WireMessage = Record<string, unknown>
export type ChatStreamEvent =
  | { type: 'round_start'; round: number }
  | { type: 'reasoning_delta' | 'content_delta'; text: string }
  | { type: 'tool_start'; id: string; tool: string }
  | ({ type: 'tool_result'; id: string } & ToolResult)
  | { type: 'done'; history: WireMessage[] }
  | { type: 'error'; message: string }

// Buffer complete SSE frames: chunks can split Chinese UTF-8, CRLFs and JSON.
export async function readChatStream(body: ReadableStream<Uint8Array>, onEvent: (event: ChatStreamEvent) => void) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false
  function frame(text: string) {
    const data = text.split(/\r?\n/).filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).replace(/^ /, '')).join('\n')
    if (!data) return
    const event = JSON.parse(data) as ChatStreamEvent
    if (event.type === 'error') throw new Error(event.message)
    if (event.type === 'done') completed = true
    onEvent(event)
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let boundary: RegExpMatchArray | null
      while ((boundary = buffer.match(/\r?\n\r?\n/))) {
        const index = boundary.index!
        frame(buffer.slice(0, index))
        buffer = buffer.slice(index + boundary[0].length)
      }
      if (done) break
    }
    if (buffer.trim()) frame(buffer)
    if (!completed) throw new Error('连接已中断，回答未完成，请重试。')
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

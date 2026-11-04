import { ref } from 'vue'
import { errorText } from '../api/http'
export function useAction() {
  const busy = ref(false),
    message = ref('')
  async function run(action) {
    if (busy.value) return false
    busy.value = true
    message.value = ''
    try {
      await action()
      return true
    } catch (error) {
      message.value = errorText(error)
      return false
    } finally {
      busy.value = false
    }
  }
  return { busy, message, run }
}

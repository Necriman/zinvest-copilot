// The thin bar along the top of the window while something loads: a route's
// code chunk, or a request to the API. Fast work never shows it (the delay),
// and it stays up for a moment after the last job so it does not flicker
// between two requests that follow each other.
import { computed, ref } from 'vue'

const SHOW_AFTER_MS = 250

const routing = ref(false)
const requests = ref(0)
const visible = ref(false)
let showTimer = null

const busy = computed(() => routing.value || requests.value > 0)

function sync() {
  if (busy.value) {
    if (!visible.value && !showTimer) {
      showTimer = setTimeout(() => {
        showTimer = null
        if (busy.value) visible.value = true
      }, SHOW_AFTER_MS)
    }
  } else {
    clearTimeout(showTimer)
    showTimer = null
    visible.value = false
  }
}

export const loadingBar = {
  visible,
  routeStart() {
    routing.value = true
    sync()
  },
  routeDone() {
    routing.value = false
    sync()
  },
  requestStart() {
    requests.value++
    sync()
  },
  requestDone() {
    requests.value = Math.max(0, requests.value - 1)
    sync()
  },
}

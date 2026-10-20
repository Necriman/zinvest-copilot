<script setup>
/**
 * A unit's scenery on the study map: a soft wash of the unit's colour and
 * three objects from its lessons standing in the margins beside the path.
 *
 * Purely decorative and behind everything — the path, the stops and the bear
 * stay the only things you can press. The objects appear only when the column
 * is wide enough to have margins; on a phone the unit keeps its emblem in the
 * header instead, and the path keeps the full width.
 */
import { computed } from 'vue'

import { sceneryFor } from './scenery'

const props = defineProps({
  slug: { type: String, default: '' },
  accent: { type: String, default: 'brand' },
  locked: { type: Boolean, default: false },
})

const scene = computed(() => sceneryFor(props.slug))
</script>

<template>
  <div class="us" :data-accent="accent" :class="locked ? 'us--locked' : ''" aria-hidden="true">
    <div class="us__wash" />
    <template v-if="scene">
      <img
        v-for="(obj, i) in scene.objects"
        :key="obj.name"
        :src="obj.src"
        alt=""
        loading="lazy"
        decoding="async"
        draggable="false"
        class="us__obj"
        :class="`us__obj--${obj.side}`"
        :style="{
          top: obj.top + '%',
          width: obj.size + 'px',
          '--tilt': obj.tilt + 'deg',
          animationDelay: `${-i * 2.1}s`,
        }"
      />
    </template>
  </div>
</template>

<style scoped>
.us {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  container-type: inline-size;
  --tint: var(--brand-500);
}
.us[data-accent='invest'] {
  --tint: #0ea5e9;
}
.us[data-accent='risk'] {
  --tint: #8b5cf6;
}
.us[data-accent='budget'] {
  --tint: #f59e0b;
}

/* The unit's floor: its colour, pooled at the edges where the objects stand
   and fading out before the path, so the stops keep a clean ground. */
.us__wash {
  --k: 11%;
  position: absolute;
  inset: 0;
  background:
    radial-gradient(40% 32% at 6% 22%, color-mix(in oklab, var(--tint) var(--k), transparent), transparent 72%),
    radial-gradient(40% 32% at 94% 52%, color-mix(in oklab, var(--tint) var(--k), transparent), transparent 72%),
    radial-gradient(40% 30% at 8% 82%, color-mix(in oklab, var(--tint) calc(var(--k) - 2%), transparent), transparent 72%);
}
/* A dark floor needs a touch more colour to read as lit at all. */
.dark .us__wash {
  --k: 16%;
}

.us__obj {
  position: absolute;
  display: none;
  height: auto;
  user-select: none;
  filter: drop-shadow(0 14px 16px rgb(15 23 42 / 0.14));
  transform: rotate(var(--tilt, 0deg));
  animation: us-float 6.3s ease-in-out infinite;
}
.us__obj--left {
  left: 2.5%;
}
.us__obj--right {
  right: 2.5%;
}
/* Margins exist only once the column is wider than the path's own 28rem. */
@container (min-width: 44rem) {
  .us__obj {
    display: block;
  }
}

.us--locked .us__obj {
  filter: grayscale(0.7) drop-shadow(0 10px 12px rgb(15 23 42 / 0.1));
  opacity: 0.5;
}
.us--locked .us__wash {
  opacity: 0.45;
  filter: grayscale(0.6);
}

@keyframes us-float {
  0%,
  100% {
    transform: translateY(0) rotate(var(--tilt, 0deg));
  }
  50% {
    transform: translateY(-9px) rotate(calc(var(--tilt, 0deg) * 0.4));
  }
}
@media (prefers-reduced-motion: reduce) {
  .us__obj {
    animation: none;
  }
}
</style>

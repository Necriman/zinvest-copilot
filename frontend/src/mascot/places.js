/**
 * One gesture per place on the site, so no two screens greet you the same way
 * (they all used to wave). Same contract as the moods in ./engine.js: a
 * function of time that writes into a neutral pose; each one is a loop of the
 * gesture, a hold, the return and a few seconds of rest.
 *
 *   present    landing hero         shows off the headline beside it
 *   weigh      the $10,000 demo     weighs the two answers like scales
 *   introduce  "Your guide"         paw on the chest, a small bow
 *   invite     closing CTA          beckons "come on"
 *   welcome    sign-up              arms open wide
 *   ready      sign-in              "let's go!", a pumped paw
 *   handshake  startup onboarding   offers a paw on the deal
 *   warmup     before a unit test   stretches, leans, shakes it out
 *   point      the study map        points ahead along the route
 *   proud      the Today card       paws on the hips, ready for today
 *   eager      a lesson opening     rubs his paws together
 *   reading    sign-in, typing      leans in and reads along as you type
 *   shy        sign-in, password    turns his back, face in his paws (Telegram's monkey)
 *   peek       password shown       side-on, peeking with one eye
 *
 * `wave` itself stays for the one real hello: the Today greeting.
 *
 * Angles follow engine.js: armR is the arm on the viewer's right, z raises an
 * arm out to its side, x swings it forward (negative), and mirror() turns a
 * right-arm angle into the left one.
 */
const deg = Math.PI / 180

const D = (x, y, z) => [x * deg, y * deg, z * deg]
const add3 = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
const lerp1 = (a, b, k) => a + (b - a) * k
const lerp3 = (a, b, k) => [lerp1(a[0], b[0], k), lerp1(a[1], b[1], k), lerp1(a[2], b[2], k)]
const clamp01 = (x) => Math.max(0, Math.min(1, x))
const ease = (x) => x * x * (3 - 2 * x)
// 0 → 1 → 0: rises over a..b, holds until c, falls back by d.
function envelope(u, a, b, c, d) {
  if (u <= a || u >= d) return 0
  if (u < b) return ease((u - a) / (b - a))
  if (u <= c) return 1
  return 1 - ease((u - c) / (d - c))
}

// The ones that keep the eyes open get the engine's natural blinks.
export const PLACE_BLINKS = ['present', 'weigh', 'introduce', 'invite', 'ready', 'handshake', 'point', 'proud', 'reading']

// Both paws up at the face, the way you hide it. `k` raises them (0 at rest).
// These arms are too short to reach the glasses from the front, so the
// password poses turn him away instead of covering his eyes head-on.
function pawsToFace(p, k, mirror) {
  p.armR = lerp3(p.armR, D(-95, -50, -10), k)
  p.foreR = lerp3(p.foreR, D(-70, -20, 0), k)
  p.armL = lerp3(p.armL, mirror(D(-95, -50, -10)), k)
  p.foreL = lerp3(p.foreL, mirror(D(-70, -20, 0)), k)
  p.handTwistR = lerp1(p.handTwistR, 0, k)
  p.handTwistL = lerp1(p.handTwistL, 0, k)
}

export function placeMoods({ breathe, mirror }) {
  return {
    present(t, p) {
      breathe(t, p, 0.7)
      const u = t % 6.5
      const e = envelope(u, 0.3, 1.1, 3.9, 4.7)
      const beat = Math.sin(t * 3) * e
      p.armL = lerp3(p.armL, D(-38, 8, -14), e)
      p.foreL = lerp3(p.foreL, D(-24, 0, -16 - 5 * beat), e)
      p.handTwistL += 70 * deg * e // palm up, the paw of someone presenting
      p.head = add3(p.head, D(-2, -14 * e, 6 * e))
      p.turn = -0.18 * e // turns a little toward what he shows
      p.lean -= 1.5 * deg * e
      p.mouth = 0.3 * e
      p.brow = 0.45 * e
      // the growth arrow hops up as the paw arrives. It used to turn a full
      // circle, and halfway round a growth arrow points backwards.
      const hop = Math.sin(Math.PI * ease(clamp01((u - 0.5) / 0.9)))
      p.arrowBob += 0.045 * hop
      p.arrowScale *= 1 + 0.1 * hop
    },

    weigh(t, p) {
      breathe(t, p, 0.5)
      const s = Math.sin(t * 1.5)
      // paws held out at the waist, palms up; they rise and fall in turn
      const hold = D(-34, -6, -6)
      p.armR = add3(hold, D(-5 * s, 0, 0))
      p.armL = add3(mirror(hold), D(5 * s, 0, 0))
      p.foreR = D(-46 - 12 * s, 0, 8)
      p.foreL = mirror(D(-46 + 12 * s, 0, 8))
      p.handTwistR = p.handTwistL = 0
      // the head leans toward whichever paw is up
      p.head[2] += 6 * deg * s
      p.head[0] += 3 * deg
      p.brow = 0.45 + 0.2 * Math.abs(s)
      p.mouth = 0.08
      p.arrowSpin += 0.6 * s
    },

    introduce(t, p) {
      breathe(t, p, 0.6)
      p.armR = D(-58, -34, -26)
      p.foreR = D(-78, -22, 0)
      p.handTwistR = 10 * deg
      p.armL[0] += 6 * deg
      const u = t % 5
      const bow = envelope(u, 1.2, 1.8, 2.2, 3.0)
      p.body = add3(p.body, D(11 * bow, 0, 0))
      p.head = add3(p.head, D(9 * bow, 0, 3 * (1 - bow)))
      p.eyeHappy = bow
      p.mouth = 0.25 + 0.2 * bow
      p.brow = 0.3
    },

    invite(t, p) {
      breathe(t, p, 0.5)
      const u = t % 3.2
      const on = envelope(u, 0, 0.3, 1.8, 2.2)
      // three quick curls of the paw, then a pause to see if you follow
      const curl = on * (0.5 + 0.5 * Math.sin(u * 11 - Math.PI / 2))
      p.armR = lerp3(p.armR, D(-58, -10, -6), on)
      p.foreR = lerp3(p.foreR, D(-15 - 75 * curl, 0, 10), on)
      p.handTwistR = lerp1(p.handTwistR, -60 * deg, on) // palm up
      p.turn = 0.15 * on
      p.body[0] += 4 * deg * on
      p.head = add3(p.head, D(-3, 0, -5 * on))
      p.mouth = 0.45
      p.brow = 0.6
      p.eyeHappy = envelope(u, 2.2, 2.45, 2.9, 3.2)
    },

    welcome(t, p) {
      const s = Math.sin(t * 2)
      p.armR = D(-22, 0, 40 + 5 * s)
      p.armL = mirror(D(-22, 0, 40 - 5 * s))
      p.foreR = D(-15, 0, 22)
      p.foreL = mirror(p.foreR)
      p.handTwistR = p.handTwistL = 0
      p.body = add3(p.body, D(0, 0, 3 * s))
      p.head = add3(p.head, D(-3, 0, -4 * s))
      p.hop = 0.025 * Math.max(0, Math.sin(t * 4))
      p.squash = 1 + 0.01 * Math.sin(t * 4)
      p.eyeHappy = 0.5 + 0.5 * Math.max(0, Math.sin(t * 0.9))
      p.mouth = 0.6
      p.brow = 0.55
    },

    ready(t, p) {
      breathe(t, p, 0.6)
      const u = t % 3.4
      const up = envelope(u, 0.2, 0.55, 1.9, 2.4)
      const pump = up * Math.max(0, Math.sin((u - 0.55) * 8.5)) * (u < 1.8 ? 1 : 0)
      p.armR = lerp3(p.armR, D(-40, -14, -6 + 10 * pump), up)
      p.foreR = lerp3(p.foreR, D(-100 + 12 * pump, 0, 0), up)
      p.handTwistR = lerp1(p.handTwistR, 70 * deg, up)
      p.hop = 0.02 * pump
      p.head = add3(p.head, D(-4 * up, 0, -3 * up))
      p.mouth = 0.2 + 0.35 * up
      p.brow = 0.6 * up
      p.eyeHappy = pump > 0.5 ? 1 : 0
    },

    handshake(t, p) {
      breathe(t, p, 0.5)
      const u = t % 4
      const out = envelope(u, 0.2, 0.7, 2.6, 3.2)
      const shake = out * Math.sin((u - 0.7) * 11) * (u > 0.7 && u < 2.4 ? 1 : 0)
      p.armR = lerp3(p.armR, D(-72 + 6 * shake, -4, 2), out)
      p.foreR = lerp3(p.foreR, D(-4 + 4 * shake, 0, 0), out)
      p.handTwistR = lerp1(p.handTwistR, 0, out)
      p.body[0] += 3 * deg * out
      p.turn = 0.32 * out // a quarter turn, so the paw is seen, not foreshortened
      p.head = add3(p.head, D(0, -16 * out, 4 * out))
      p.mouth = 0.45 * out
      p.brow = 0.4
      p.eyeHappy = Math.abs(shake) > 0.6 ? 1 : 0
    },

    warmup(t, p) {
      const u = t % 7
      const up = envelope(u, 0.2, 0.9, 3.6, 4.3)
      const side = up * Math.sin(Math.max(0, u - 1.1) * 2.3) * (u > 1.1 && u < 3.8 ? 1 : 0)
      breathe(t, p, 1 - up)
      p.armR = lerp3(p.armR, D(-6, 0, 118), up)
      p.armL = lerp3(p.armL, mirror(D(-6, 0, 118)), up)
      p.foreR = lerp3(p.foreR, D(0, 0, 28), up)
      p.foreL = lerp3(p.foreL, mirror(D(0, 0, 28)), up)
      p.body = add3(p.body, D(-3 * up, 0, 10 * side))
      p.head = add3(p.head, D(-8 * up, 0, 6 * side))
      p.squash = 1 + 0.03 * up
      p.eyeClose = 0.8 * up
      p.mouth = 0.35 * up
      // then shake the arms out
      const loose = u > 4.3 && u < 5.6 ? Math.sin(u * 30) * (1 - (u - 4.3) / 1.3) : 0
      p.armR[2] += 6 * deg * loose
      p.armL[2] -= 6 * deg * loose
      p.foreR[2] += 8 * deg * loose
      p.foreL[2] -= 8 * deg * loose
    },

    point(t, p) {
      breathe(t, p, 0.6)
      const nudge = Math.max(0, Math.sin(t * 2.4)) ** 3
      p.armR = D(-30, 0, 52 + 3 * nudge)
      p.foreR = D(-6 - 6 * nudge, 0, 4)
      p.handTwistR = 20 * deg
      p.head = add3(p.head, D(-2, 14, -4))
      p.lean += 1.5 * deg
      p.brow = 0.5
      p.mouth = 0.3
    },

    // The Today card: paws on his hips, a confident nod now and then —
    // ready for today. (Pushing the glasses up was the first idea, but these
    // arms are too short to reach them.)
    proud(t, p) {
      breathe(t, p, 0.7)
      p.armR = D(15, 10, 25)
      p.foreR = D(-20, -20, -90)
      p.armL = mirror(p.armR)
      p.foreL = mirror(p.foreR)
      const u = t % 4.5
      const nod = envelope(u, 1.4, 1.65, 1.75, 2.1)
      p.body = add3(p.body, D(-3, 0, 0))
      p.head = add3(p.head, D(8 * nod - 3, 0, 2.5 * Math.sin(t * 0.8)))
      p.squash *= 1 + 0.01 * nod
      p.mouth = 0.3 + 0.2 * nod
      p.brow = 0.35 + 0.3 * nod
    },

    // The start of a lesson: rubs his paws together, "right, let's begin".
    eager(t, p) {
      breathe(t, p, 0.4)
      const rub = Math.sin(t * 14)
      p.armR = D(-66, -33 + 4 * rub, -30)
      p.armL = mirror(D(-66, -33 - 4 * rub, -30))
      p.foreR = D(-8, -24, 0)
      p.foreL = mirror(p.foreR)
      p.handTwistR = p.handTwistL = 0 // palms together
      p.hop = 0.012 * Math.abs(Math.sin(t * 3.5))
      p.eyeHappy = 1
      p.mouth = 0.55
      p.brow = 0.55
    },

    // Sign-in and sign-up, the Telegram monkey's trick. While an address is
    // typed he leans in and reads along (the page steers his head with the
    // engine's pointer look); on the password he turns away; when the
    // password is shown, he peeks.
    reading(t, p) {
      breathe(t, p, 0.6)
      p.body[0] += 4 * deg
      p.head = add3(p.head, D(7, 0, 3 * Math.sin(t * 0.8)))
      p.brow = 0.35
      p.mouth = 0.12
    },

    // "I'm not looking!": he turns his back and hides his face in his paws.
    shy(t, p) {
      breathe(t, p, 0.35)
      const k = ease(clamp01(t / 0.55))
      pawsToFace(p, k, mirror)
      p.turn = Math.PI * k
      p.head = add3(p.head, D(10 * k, 0, 0))
      p.eyeClose = k
    },

    // "Just one peek": side-on, paws still up, one eye on the password.
    peek(t, p) {
      breathe(t, p, 0.35)
      pawsToFace(p, 1, mirror)
      p.turn = 90 * deg
      p.head = add3(p.head, D(6, -50, -6))
      p.winkR = 1
      p.mouth = 0.25
      p.brow = 0.6
    },
  }
}

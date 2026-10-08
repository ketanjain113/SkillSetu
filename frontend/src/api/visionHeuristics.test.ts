import { describe, expect, it } from 'vitest'
import { evaluateFrameQuality, evaluateStepHeuristic } from './visionHeuristics'

describe('evidence step heuristics', () => {
  it('proposes a sustained electrician step when hands are in the work region and posture is upright', () => {
    const pose = Array.from({ length: 25 }, () => ({ x: 0.5, y: 0.5, visibility: 1 }))
    pose[11] = { x: 0.4, y: 0.3, visibility: 1 }
    pose[12] = { x: 0.6, y: 0.3, visibility: 1 }
    pose[23] = { x: 0.42, y: 0.65, visibility: 1 }
    pose[24] = { x: 0.58, y: 0.65, visibility: 1 }

    const proposal = evaluateStepHeuristic('Domestic Electrician', [{ x: 0.5, y: 0.6 }], pose, 1500)
    expect(proposal.active).toBe(true)
    expect(proposal.confidence).toBeGreaterThanOrEqual(0.58)
    expect(proposal.handNearRegion).toBe(true)
    expect(proposal.uprightPosture).toBe(true)
  })

  it('does not propose a step before dwell threshold or outside trade work region', () => {
    const briefContact = evaluateStepHeuristic('Plumber', [{ x: 0.5, y: 0.7 }], [], 500)
    const outsideRegion = evaluateStepHeuristic('Plumber', [{ x: 0.98, y: 0.7 }], [], 4000)
    expect(briefContact.active).toBe(false)
    expect(outsideRegion.active).toBe(false)
  })
})

describe('camera frame quality checks', () => {
  it('flags a uniform image as blurred and retains measured face presence', () => {
    const pixels = new Uint8ClampedArray(8 * 8 * 4)
    for (let index = 0; index < pixels.length; index += 4) {
      pixels[index] = 120
      pixels[index + 1] = 120
      pixels[index + 2] = 120
      pixels[index + 3] = 255
    }
    const quality = evaluateFrameQuality(pixels, 8, 8, true)
    expect(quality.blurry).toBe(true)
    expect(quality.brightnessOk).toBe(true)
    expect(quality.faceInFrame).toBe(true)
  })
})

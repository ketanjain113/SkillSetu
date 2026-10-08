export type VisionPoint = { x: number; y: number; visibility?: number }

export type StepHeuristic = {
  active: boolean
  confidence: number
  handNearRegion: boolean
  uprightPosture: boolean
  postureAvailable: boolean
  dwellMs: number
}

const tradeRegions: Record<string, { left: number; right: number; top: number; bottom: number }> = {
  electrician: { left: 0.2, right: 0.88, top: 0.3, bottom: 0.94 },
  plumber: { left: 0.12, right: 0.88, top: 0.38, bottom: 0.96 },
  tailor: { left: 0.12, right: 0.88, top: 0.24, bottom: 0.84 },
  mason: { left: 0.18, right: 0.92, top: 0.34, bottom: 0.96 },
  default: { left: 0.12, right: 0.9, top: 0.28, bottom: 0.96 },
}

function tradeKey(trade: string): string {
  const normalized = trade.toLowerCase()
  if (normalized.includes('electric')) return 'electrician'
  if (normalized.includes('plumb')) return 'plumber'
  if (normalized.includes('tailor') || normalized.includes('sewing')) return 'tailor'
  if (normalized.includes('mason') || normalized.includes('brick')) return 'mason'
  return 'default'
}

export function evaluateStepHeuristic(
  trade: string,
  handPoints: VisionPoint[],
  posePoints: VisionPoint[],
  dwellMs: number,
): StepHeuristic {
  const region = tradeRegions[tradeKey(trade)]
  const handNearRegion = handPoints.some((point) =>
    point.x >= region.left && point.x <= region.right && point.y >= region.top && point.y <= region.bottom,
  )
  const leftShoulder = posePoints[11]
  const rightShoulder = posePoints[12]
  const leftHip = posePoints[23]
  const rightHip = posePoints[24]
  const poseVisible = [leftShoulder, rightShoulder, leftHip, rightHip].every(
    (point) => point && (point.visibility ?? 1) >= 0.35,
  )
  const uprightPosture = poseVisible
    && (leftShoulder.y + rightShoulder.y) / 2 < (leftHip.y + rightHip.y) / 2
    && Math.abs((leftShoulder.x + rightShoulder.x) / 2 - (leftHip.x + rightHip.x) / 2) < 0.35
  const confidence = Math.min(
    0.99,
    (handNearRegion ? 0.62 : 0.08)
      + (uprightPosture ? 0.2 : 0.04)
      + Math.min(dwellMs / 3000, 1) * 0.16,
  )

  return {
    active: handNearRegion && dwellMs >= 1200 && (uprightPosture || !poseVisible) && confidence >= 0.58,
    confidence: Number(confidence.toFixed(2)),
    handNearRegion,
    uprightPosture,
    postureAvailable: poseVisible,
    dwellMs,
  }
}

export type FrameQuality = {
  brightness: number
  laplacianVariance: number
  blurry: boolean
  brightnessOk: boolean
  faceInFrame: boolean
  retakePrompts: string[]
}

export function evaluateFrameQuality(
  pixels: Uint8ClampedArray,
  width: number,
  height: number,
  faceInFrame: boolean,
): FrameQuality {
  const gray = new Float32Array(width * height)
  let brightness = 0
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    const offset = pixel * 4
    const value = 0.299 * pixels[offset] + 0.587 * pixels[offset + 1] + 0.114 * pixels[offset + 2]
    gray[pixel] = value
    brightness += value
  }
  brightness /= Math.max(width * height, 1)

  let laplacianSum = 0
  let laplacianSquaredSum = 0
  let samples = 0
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const index = y * width + x
      const laplacian = gray[index - width] + gray[index + width] + gray[index - 1] + gray[index + 1] - 4 * gray[index]
      laplacianSum += laplacian
      laplacianSquaredSum += laplacian * laplacian
      samples += 1
    }
  }
  const mean = laplacianSum / Math.max(samples, 1)
  const laplacianVariance = Math.max(0, laplacianSquaredSum / Math.max(samples, 1) - mean * mean)
  const brightnessOk = brightness >= 45 && brightness <= 215
  const blurry = laplacianVariance < 45
  const retakePrompts = [
    ...(!brightnessOk ? [brightness < 45 ? 'Image is too dark; move to a brighter area.' : 'Image is too bright; reduce glare or face the light.'] : []),
    ...(blurry ? ['Image looks blurry; hold the device steady and refocus.'] : []),
    ...(!faceInFrame ? ['No face detected; position your face inside the camera frame.'] : []),
  ]
  return {
    brightness: Number(brightness.toFixed(1)),
    laplacianVariance: Number(laplacianVariance.toFixed(1)),
    blurry,
    brightnessOk,
    faceInFrame,
    retakePrompts,
  }
}

import { useEffect, useRef, useState } from 'react'
import type { FaceLandmarkerResult, HandLandmarkerResult, NormalizedLandmark, PoseLandmarkerResult } from '@mediapipe/tasks-vision'
import { apiRequest, persistQueue } from '../api/client'
import { loadEvidenceVision } from '../api/evidenceVision'
import { evaluateFrameQuality, evaluateStepHeuristic } from '../api/visionHeuristics'
import type { FrameQuality, VisionPoint } from '../api/visionHeuristics'
import type { Locale } from '../i18n/translations'
import { translations } from '../i18n/translations'

type EvidenceStep = {
  start: number | null
  end: number | null
  status: 'pending' | 'started' | 'done'
  confidence: number | null
  suggested: boolean
  simulated: boolean
  review?: 'unreviewed' | 'accepted' | 'edited' | 'rejected'
}

type Liveness = {
  challenge: 'blink' | 'turn' | null
  lastChallenge: 'blink' | 'turn' | null
  status: 'not-started' | 'pending' | 'passed' | 'failed' | 'mock'
  confidence: number
  prompt: string
  mockOutcome: 'pass' | 'fail' | 'not-run' | null
}

type CameraState = 'idle' | 'loading' | 'ready' | 'mock' | 'error'

const mockFallback = import.meta.env.VITE_EVIDENCE_MOCK_FALLBACK === 'true'
const defaultSteps = [
  'Verify site isolation and risk assessment',
  'Wear required PPE and check tools',
  'Inspect cables, points and environment for hazards',
  'Confirm lockout/tagout or safe switching',
  'Document hazards and remedial actions',
]

function landmarkPoints(groups: NormalizedLandmark[][]): VisionPoint[] {
  return groups.flat().map(({ x, y, visibility }) => ({ x, y, visibility }))
}

function drawConnections(
  context: CanvasRenderingContext2D,
  points: NormalizedLandmark[],
  connections: Array<{ start: number; end: number }>,
  width: number,
  height: number,
  color: string,
) {
  context.strokeStyle = color
  context.lineWidth = Math.max(2, width / 360)
  context.beginPath()
  connections.forEach(({ start, end }) => {
    const first = points[start]
    const second = points[end]
    if (!first || !second) return
    context.moveTo(first.x * width, first.y * height)
    context.lineTo(second.x * width, second.y * height)
  })
  context.stroke()
}

function drawLandmarks(
  context: CanvasRenderingContext2D,
  points: NormalizedLandmark[],
  width: number,
  height: number,
  color: string,
) {
  context.fillStyle = color
  points.forEach((point) => {
    context.beginPath()
    context.arc(point.x * width, point.y * height, Math.max(2.2, width / 190), 0, Math.PI * 2)
    context.fill()
  })
}

function drawVisionOverlay(
  canvas: HTMLCanvasElement,
  video: HTMLVideoElement,
  face: FaceLandmarkerResult,
  hands: HandLandmarkerResult,
  pose: PoseLandmarkerResult,
) {
  const width = video.videoWidth
  const height = video.videoHeight
  if (!width || !height) return
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) return
  context.clearRect(0, 0, width, height)
  context.save()
  context.translate(width, 0)
  context.scale(-1, 1)

  face.faceLandmarks.forEach((points) => {
    const xs = points.map((point) => point.x * width)
    const ys = points.map((point) => point.y * height)
    if (xs.length) {
      const left = Math.min(...xs)
      const top = Math.min(...ys)
      context.strokeStyle = '#ff9933'
      context.lineWidth = Math.max(3, width / 240)
      context.strokeRect(left, top, Math.max(...xs) - left, Math.max(...ys) - top)
    }
  })
  hands.landmarks.forEach((points) => {
    drawConnections(context, points, [{ start: 0, end: 1 }, { start: 1, end: 2 }, { start: 2, end: 3 }, { start: 3, end: 4 }, { start: 0, end: 5 }, { start: 5, end: 6 }, { start: 6, end: 7 }, { start: 7, end: 8 }, { start: 5, end: 9 }, { start: 9, end: 10 }, { start: 10, end: 11 }, { start: 11, end: 12 }, { start: 9, end: 13 }, { start: 13, end: 14 }, { start: 14, end: 15 }, { start: 15, end: 16 }, { start: 13, end: 17 }, { start: 17, end: 18 }, { start: 18, end: 19 }, { start: 19, end: 20 }, { start: 0, end: 17 }], width, height, '#44d7a8')
    drawLandmarks(context, points, width, height, '#44d7a8')
  })
  pose.landmarks.forEach((points) => {
    drawConnections(context, points, [
      { start: 11, end: 12 }, { start: 11, end: 13 }, { start: 13, end: 15 },
      { start: 12, end: 14 }, { start: 14, end: 16 }, { start: 11, end: 23 },
      { start: 12, end: 24 }, { start: 23, end: 24 }, { start: 23, end: 25 },
      { start: 25, end: 27 }, { start: 24, end: 26 }, { start: 26, end: 28 },
    ], width, height, '#66a3ff')
    drawLandmarks(context, points.filter((point) => (point.visibility ?? 1) > 0.35), width, height, '#66a3ff')
  })
  context.restore()
}

function readLivenessScore(result: FaceLandmarkerResult, challenge: 'blink' | 'turn'): number | null {
  const categories = result.faceBlendshapes[0]?.categories
  if (challenge === 'blink' && categories) {
    const left = categories.find((item) => item.categoryName === 'eyeBlinkLeft')?.score ?? 0
    const right = categories.find((item) => item.categoryName === 'eyeBlinkRight')?.score ?? 0
    return Math.max(left, right)
  }
  const face = result.faceLandmarks[0]
  if (face && face[1] && face[33] && face[263]) {
    const eyeCenter = (face[33].x + face[263].x) / 2
    const eyeWidth = Math.max(Math.abs(face[263].x - face[33].x), 0.01)
    return (face[1].x - eyeCenter) / eyeWidth
  }
  return null
}

function getGeolocation(): Promise<{ latitude: number; longitude: number; accuracy_m: number } | { unavailable: string }> {
  if (!navigator.geolocation) return Promise.resolve({ unavailable: 'unsupported' })
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => resolve({ latitude: coords.latitude, longitude: coords.longitude, accuracy_m: coords.accuracy }),
      (error) => resolve({ unavailable: error.code === error.PERMISSION_DENIED ? 'permission-denied' : error.message }),
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 30_000 },
    )
  })
}

function requestCameraStream(): Promise<MediaStream> {
  return new Promise((resolve, reject) => {
    let settled = false
    const timeout = window.setTimeout(() => {
      settled = true
      reject(new Error('Camera permission prompt timed out. Check browser permissions and retry.'))
    }, 15_000)
    navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    }).then((stream) => {
      if (settled) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      window.clearTimeout(timeout)
      resolve(stream)
    }, (reason: unknown) => {
      if (settled) return
      window.clearTimeout(timeout)
      reject(reason)
    })
  })
}

async function hashBlob(blob: Blob): Promise<string> {
  if (!crypto.subtle) throw new Error('SHA-256 video hashing requires a secure browser context (HTTPS or localhost).')
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return Array.from(new Uint8Array(digest), (value) => value.toString(16).padStart(2, '0')).join('')
}

export function DemonstratePage({ token, locale, lowLiteracyMode }: { token: string; locale: Locale; lowLiteracyMode: boolean }) {
  const t = translations[locale]
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const playbackRef = useRef<HTMLVideoElement | null>(null)
  const overlayRef = useRef<HTMLCanvasElement | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const visionRef = useRef<Awaited<ReturnType<typeof loadEvidenceVision>> | null>(null)
  const analysisTimerRef = useRef<number | null>(null)
  const analysisBusyRef = useRef(false)
  const recordingRef = useRef(false)
  const recordingStartedAtRef = useRef<number | null>(null)
  const livenessStartedAtRef = useRef<number | null>(null)
  const dwellStartRef = useRef<number | null>(null)
  const stepStartRef = useRef<number | null>(null)
  const lastLivenessRef = useRef<{ sawOpen: boolean; baseline: number | null; best: number } | null>(null)
  const [consent, setConsent] = useState(false)
  const [cameraState, setCameraState] = useState<CameraState>('idle')
  const [cameraHasStream, setCameraHasStream] = useState(false)
  const [cameraMessage, setCameraMessage] = useState('')
  const [recording, setRecording] = useState(false)
  const [videoUrl, setVideoUrl] = useState('')
  const [videoHash, setVideoHash] = useState('')
  const [playbackDuration, setPlaybackDuration] = useState(0)
  const [playbackTime, setPlaybackTime] = useState(0)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [quality, setQuality] = useState<FrameQuality | null>(null)
  const [faceDetected, setFaceDetected] = useState(false)
  const [handCount, setHandCount] = useState(0)
  const [poseDetected, setPoseDetected] = useState(false)
  const [postureReadout, setPostureReadout] = useState('unavailable')
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [trade, setTrade] = useState(() => sessionStorage.getItem('skillsetu-trade') ?? 'Domestic Electrician')
  const steps = defaultSteps
  const [stepRecords, setStepRecords] = useState<EvidenceStep[]>(
    defaultSteps.map(() => ({ start: null, end: null, status: 'pending', confidence: null, suggested: false, simulated: false, review: 'unreviewed' })),
  )
  const [liveness, setLiveness] = useState<Liveness>({
    challenge: null, lastChallenge: null, status: 'not-started', confidence: 0, prompt: 'Choose a blink or head-turn check to begin.', mockOutcome: null,
  })
  const livenessRef = useRef(liveness)
  const tradeRef = useRef(trade)
  const currentStepIndexRef = useRef(currentStepIndex)

  useEffect(() => { livenessRef.current = liveness }, [liveness])
  useEffect(() => { tradeRef.current = trade }, [trade])
  useEffect(() => { currentStepIndexRef.current = currentStepIndex }, [currentStepIndex])
  useEffect(() => { recordingRef.current = recording }, [recording])
  const cameraAvailable = cameraState === 'ready' || (cameraState === 'mock' && cameraHasStream)

  useEffect(() => () => {
    if (analysisTimerRef.current !== null) window.clearInterval(analysisTimerRef.current)
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
    streamRef.current?.getTracks().forEach((track) => track.stop())
    visionRef.current?.close()
  }, [])

  useEffect(() => () => {
    if (videoUrl) URL.revokeObjectURL(videoUrl)
  }, [videoUrl])

  const elapsedSeconds = () => recordingStartedAtRef.current === null ? 0 : (performance.now() - recordingStartedAtRef.current) / 1000

  const setStepValue = (index: number, key: 'start' | 'end', value: number | null, manual: boolean) => {
    setStepRecords((current) => current.map((item, itemIndex) => {
      if (itemIndex !== index) return item
      const updated = {
        ...item,
        [key]: value,
        suggested: item.suggested,
        simulated: item.simulated,
        review: manual && item.suggested ? 'edited' as const : item.review,
      }
      if (key === 'start' && value !== null) updated.status = 'started'
      if (key === 'end' && value !== null) updated.status = 'done'
      return updated
    }))
  }

  const finishLiveness = (status: 'passed' | 'failed', confidence: number, prompt: string) => {
    setLiveness((current) => ({ ...current, challenge: null, status, confidence: Number(confidence.toFixed(2)), prompt }))
    lastLivenessRef.current = null
  }

  const analyzeFrame = () => {
    const video = videoRef.current
    const vision = visionRef.current
    if (!video || !vision || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || analysisBusyRef.current) return
    analysisBusyRef.current = true
    try {
      const timestamp = performance.now()
      const face = vision.face.detectForVideo(video, timestamp)
      const hands = vision.hands.detectForVideo(video, timestamp)
      const pose = vision.pose.detectForVideo(video, timestamp)
      const facePoints = face.faceLandmarks[0] ?? []
      const handPoints = landmarkPoints(hands.landmarks)
      const posePoints = landmarkPoints(pose.landmarks)
      const hasFace = facePoints.length > 0
      setFaceDetected(hasFace)
      setHandCount(hands.landmarks.length)
      setPoseDetected(posePoints.length > 0)
      if (overlayRef.current) drawVisionOverlay(overlayRef.current, video, face, hands, pose)

      const currentLiveness = livenessRef.current
      const challenge = currentLiveness.status === 'pending' ? currentLiveness.challenge : null
      const score = challenge ? readLivenessScore(face, challenge) : null
      if (challenge && score !== null && hasFace) {
        const liveState = lastLivenessRef.current ?? { sawOpen: false, baseline: null, best: 0 }
        if (challenge === 'blink') {
          liveState.best = Math.max(liveState.best, score)
          if (score < 0.3) liveState.sawOpen = true
          if (liveState.sawOpen && score >= 0.55) {
            finishLiveness('passed', Math.min(0.99, 0.7 + score * 0.29), 'Blink detected. Liveness check passed.')
          } else if (timestamp - (livenessStartedAtRef.current ?? timestamp) > 12_000) {
            finishLiveness('failed', liveState.best, 'No blink was detected. Try again with your face in frame.')
          }
        } else {
          liveState.baseline ??= score
          const movement = Math.abs(score - liveState.baseline)
          liveState.best = Math.max(liveState.best, movement)
          if (movement >= 0.16) {
            finishLiveness('passed', Math.min(0.99, 0.55 + movement), 'Head turn detected. Liveness check passed.')
          } else if (timestamp - (livenessStartedAtRef.current ?? timestamp) > 12_000) {
            finishLiveness('failed', Math.min(0.5, liveState.best), 'No head turn was detected. Try again with your face in frame.')
          }
        }
        lastLivenessRef.current = liveState
      } else if (challenge && timestamp - (livenessStartedAtRef.current ?? timestamp) > 12_000) {
        finishLiveness('failed', 0, 'No face was available for the liveness check. Reposition and try again.')
      }

      if (!recordingRef.current) {
        dwellStartRef.current = null
        stepStartRef.current = null
        const preview = evaluateStepHeuristic(tradeRef.current, handPoints, posePoints, 0)
        setPostureReadout(preview.postureAvailable ? preview.uprightPosture ? 'upright' : 'adjust position' : 'not available')
      } else {
        const now = performance.now()
        if (handPoints.length) {
          dwellStartRef.current ??= now
        } else {
          dwellStartRef.current = null
        }
        const dwell = dwellStartRef.current === null ? 0 : now - dwellStartRef.current
        const heuristic = evaluateStepHeuristic(tradeRef.current, handPoints, posePoints, dwell)
        setPostureReadout(heuristic.postureAvailable ? heuristic.uprightPosture ? 'upright' : 'adjust position' : 'not available')
        const activeStep = currentStepIndexRef.current
        if (heuristic.active && stepStartRef.current === null) {
          const start = Math.max(0, elapsedSeconds() - dwell / 1000)
          stepStartRef.current = start
          setStepRecords((current) => current.map((item, itemIndex) =>
            itemIndex === activeStep
              ? { ...item, start: Number(start.toFixed(2)), status: 'started', confidence: heuristic.confidence, suggested: true, simulated: false }
              : item,
          ))
        } else if (heuristic.active && stepStartRef.current !== null) {
          setStepRecords((current) => current.map((item, itemIndex) =>
            itemIndex === activeStep && item.suggested
              ? { ...item, confidence: Math.max(item.confidence ?? 0, heuristic.confidence) }
              : item,
          ))
        } else if (!heuristic.handNearRegion && stepStartRef.current !== null) {
          const end = Number(elapsedSeconds().toFixed(2))
          setStepRecords((current) => current.map((item, itemIndex) =>
            itemIndex === activeStep
              ? { ...item, end, status: 'done', confidence: item.confidence ?? heuristic.confidence, suggested: true, simulated: false }
              : item,
          ))
          stepStartRef.current = null
          currentStepIndexRef.current = Math.min(currentStepIndexRef.current + 1, steps.length - 1)
          setCurrentStepIndex(currentStepIndexRef.current)
        }
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Vision inference failed.'
      setCameraMessage(`Vision processing stopped: ${message}`)
      if (analysisTimerRef.current !== null) window.clearInterval(analysisTimerRef.current)
      analysisTimerRef.current = null
    } finally {
      analysisBusyRef.current = false
    }
  }

  const startCamera = async () => {
    setError('')
    setCameraMessage('')
    setCameraState('loading')
    let stream: MediaStream | null = null
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error('Camera access is not available in this browser context.')
      stream = await requestCameraStream()
      streamRef.current = stream
      setCameraHasStream(true)
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      try {
        visionRef.current = await loadEvidenceVision()
        setCameraState('ready')
        setCameraMessage('On-device face, hand, and pose models are ready. Frames and landmarks stay in this browser.')
        analysisTimerRef.current = window.setInterval(analyzeFrame, 450)
      } catch (reason) {
        const message = reason instanceof Error ? reason.message : 'Could not load MediaPipe models.'
        if (!mockFallback) throw new Error(`On-device vision could not load: ${message}`)
        setCameraState('mock')
        setCameraMessage(`Mock fallback active (VITE_EVIDENCE_MOCK_FALLBACK=true). MediaPipe unavailable: ${message}`)
      }
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Could not start the camera.'
      if (mockFallback) {
        setCameraHasStream(Boolean(streamRef.current))
        setCameraState('mock')
        setCameraMessage(`Mock fallback active (VITE_EVIDENCE_MOCK_FALLBACK=true). Camera/vision unavailable: ${message}`)
      } else {
        stream?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        setCameraHasStream(false)
        if (videoRef.current) videoRef.current.srcObject = null
        setCameraState('error')
        setError(message)
      }
    }
  }

  const stopCamera = () => {
    if (analysisTimerRef.current !== null) window.clearInterval(analysisTimerRef.current)
    analysisTimerRef.current = null
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
    mediaRecorderRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    setCameraHasStream(false)
    visionRef.current?.close()
    visionRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraState('idle')
    setRecording(false)
    recordingRef.current = false
    setFaceDetected(false)
    setHandCount(0)
    setPoseDetected(false)
    setPostureReadout('unavailable')
    if (overlayRef.current) overlayRef.current.getContext('2d')?.clearRect(0, 0, overlayRef.current.width, overlayRef.current.height)
  }

  const startRecording = () => {
    const stream = streamRef.current
    if (!stream) {
      setError('Start the camera before recording evidence.')
      return
    }
    if (typeof MediaRecorder === 'undefined') {
      setError('Video recording is not supported in this browser.')
      return
    }
    const chunks: BlobPart[] = []
    const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
      .find((candidate) => MediaRecorder.isTypeSupported(candidate))
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream)
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: recorder.mimeType || 'video/webm' })
      if (!blob.size) {
        setError('The browser did not produce a video recording. Record again before saving evidence.')
        return
      }
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      setVideoUrl(URL.createObjectURL(blob))
      void hashBlob(blob).then(setVideoHash).catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Could not calculate the video SHA-256 hash.')
      })
    }
    recordingStartedAtRef.current = performance.now()
    recorder.start(250)
    mediaRecorderRef.current = recorder
    setVideoHash('')
    setNotice('')
    setError('')
    setRecording(true)
    recordingRef.current = true
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') mediaRecorderRef.current.stop()
    setRecording(false)
    recordingRef.current = false
    if (stepStartRef.current !== null) {
      const end = Number(elapsedSeconds().toFixed(2))
      const activeStep = currentStepIndexRef.current
      setStepRecords((current) => current.map((item, index) => index === activeStep
        ? { ...item, end, status: 'done' }
        : item))
      stepStartRef.current = null
    }
    dwellStartRef.current = null
  }

  const runQualityCheck = () => {
    const video = videoRef.current
    if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      setError('Start the camera before running an image-quality check.')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = 160
    canvas.height = Math.max(1, Math.round(160 * video.videoHeight / video.videoWidth))
    const context = canvas.getContext('2d', { willReadFrequently: true })
    if (!context) {
      setError('This browser could not read a camera frame for the quality check.')
      return
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    setQuality(evaluateFrameQuality(
      context.getImageData(0, 0, canvas.width, canvas.height).data,
      canvas.width,
      canvas.height,
      cameraState === 'ready' && faceDetected,
    ))
    setError('')
  }

  const startLiveness = (challenge: 'blink' | 'turn') => {
    if (cameraState === 'ready') {
      livenessStartedAtRef.current = performance.now()
      lastLivenessRef.current = { sawOpen: false, baseline: null, best: 0 }
      setLiveness({
        challenge,
        lastChallenge: challenge,
        status: 'pending',
        confidence: 0,
        prompt: challenge === 'blink' ? 'Look at the camera and blink once.' : 'Look at the camera, then turn your head slightly left or right.',
        mockOutcome: null,
      })
      return
    }
    if (cameraState === 'mock' && mockFallback) {
      setLiveness({
        challenge: null,
        lastChallenge: challenge,
        status: 'mock',
        confidence: 0,
        prompt: `Mock fallback: ${challenge === 'blink' ? 'blink' : 'head-turn'} check is simulated, not a real liveness result.`,
        mockOutcome: 'not-run',
      })
      return
    }
    setError('Start the camera and wait for on-device vision before running a liveness check.')
  }

  const markStep = () => {
    const elapsed = Number(elapsedSeconds().toFixed(2))
    const stepIndex = currentStepIndex
    setStepRecords((current) => current.map((item, itemIndex) => {
      if (itemIndex !== stepIndex) return item
      if (item.start === null || item.status === 'pending') {
        return { ...item, start: elapsed, end: null, status: 'started', confidence: null, suggested: false, simulated: false }
      }
      return { ...item, end: elapsed, status: 'done', confidence: null, suggested: false, simulated: false }
    }))
  }

  const simulateStepSuggestion = () => {
    const elapsed = Number(elapsedSeconds().toFixed(2))
    setStepRecords((current) => current.map((item, index) => index === currentStepIndex
      ? { ...item, start: elapsed, end: Number((elapsed + 1.5).toFixed(2)), status: 'done', confidence: 0.65, suggested: true, simulated: true }
      : item))
  }

  const saveEvidence = async () => {
    if (!videoHash) {
      setError('Record a video clip and wait for its SHA-256 hash before saving.')
      return
    }
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const geo = await getGeolocation()
      const timestamp = new Date().toISOString()
      const payload = {
        title: `Evidence capture ${timestamp}`,
        sha256: videoHash,
        geo: { ...geo, captured_at: timestamp },
        timestamp,
        required_steps: steps,
        live_status: liveness.status === 'passed' ? 'passed' : liveness.status === 'failed' ? 'failed' : liveness.status === 'mock' ? 'mock' : liveness.status === 'pending' ? 'pending' : 'not-checked',
        liveness: {
          challenge: liveness.lastChallenge ?? 'not-run',
          result: liveness.status === 'mock' ? `mock-${liveness.mockOutcome ?? 'not-run'}` : liveness.status,
          confidence: liveness.confidence,
        },
        quality: quality ? {
          brightness: quality.brightness,
          blur: quality.blurry ? 1 : 0,
          laplacian_variance: quality.laplacianVariance,
          is_blurry: quality.blurry,
          brightness_ok: quality.brightnessOk,
          face_in_frame: quality.faceInFrame,
          retake_prompts: quality.retakePrompts,
        } : {},
        vision_mode: cameraState === 'ready' ? 'mediapipe-on-device' : cameraState === 'mock' ? 'mock-fallback' : 'unavailable',
        steps: steps.map((name, index) => ({
          step_id: `step-${index + 1}`,
          name,
          status: stepRecords[index].status,
          start_time: stepRecords[index].start ?? 0,
          end_time: stepRecords[index].end ?? 0,
          suggested_by_ai: stepRecords[index].suggested,
          confidence: stepRecords[index].confidence,
          suggestion_source: stepRecords[index].simulated ? 'mock-fallback' : stepRecords[index].suggested ? 'mediapipe-heuristic' : 'worker',
          tag_review: stepRecords[index].review ?? 'unreviewed',
        })),
      }

      if (navigator.onLine) {
        const result = await apiRequest<{
          hash_chain: string
          id: number
          evidence_sufficiency: { sufficient: boolean; flags: string[]; missing_steps: string[] }
        }>('/api/evidence', {
          method: 'POST',
          body: JSON.stringify(payload),
        }, token)
        const qualitySummary = result.evidence_sufficiency.sufficient
          ? 'Evidence-quality checks passed for assessor review.'
          : `Retake/review prompts: ${result.evidence_sufficiency.flags.join(' ')}`
        setNotice(`Evidence #${result.id} saved. Server hash-chain entry: ${result.hash_chain}. ${qualitySummary} Location: ${'unavailable' in geo ? geo.unavailable : 'captured with permission'}.`)
      } else {
        await persistQueue('evidence', payload)
        setNotice(`Evidence queued offline with its video hash. Location: ${'unavailable' in geo ? geo.unavailable : 'captured with permission'}. The server will chain it after synchronization.`)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save evidence.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="page-shell" data-tour="evidence-capture">
      {!consent ? (
        <div className="card consent-card">
          <h2>Consent before capture</h2>
          <p>
            Camera frames are processed on this device for face, hand, and pose landmarks. Raw frames and landmarks are not sent to the API. A local video clip is hashed with SHA-256; the API stores the hash, step metadata, timestamp, optional location, and a verifiable hash-chain record. Location is requested only when you save.
          </p>
          <button type="button" className={lowLiteracyMode ? 'large-button' : ''} onClick={() => setConsent(true)}>I consent and continue</button>
        </div>
      ) : (
        <>
          <section className="card padded-card">
            <div className="card-header-row">
              <h2>{t.qualityCheck}: live on-device checks</h2>
              <span className={`status-pill ${cameraState === 'ready' ? '' : cameraState === 'mock' ? 'vision-mock-pill' : ''}`}>
                {cameraState === 'ready' ? 'MediaPipe live' : cameraState === 'mock' ? 'Mock fallback active' : cameraState === 'loading' ? 'Loading vision models' : cameraState === 'error' ? 'Camera unavailable' : 'Camera stopped'}
              </span>
            </div>
            <div className="video-box vision-video-box">
              <video ref={videoRef} playsInline muted autoPlay aria-label="Live evidence camera" />
              <canvas ref={overlayRef} className="vision-overlay" aria-hidden="true" />
              {!cameraAvailable ? <span className="camera-placeholder">Start the camera to run local vision checks.</span> : null}
            </div>
            <div className="vision-readout" aria-live="polite">
              <span>Face: {cameraState === 'ready' ? faceDetected ? 'in frame' : 'not detected' : cameraState === 'mock' ? 'simulated / unavailable' : 'waiting'}</span>
              <span>Hands: {cameraState === 'ready' ? handCount : cameraState === 'mock' ? 'simulated' : 'waiting'}</span>
              <span>Pose: {cameraState === 'ready' ? poseDetected ? 'detected' : 'not detected' : cameraState === 'mock' ? 'simulated' : 'waiting'}</span>
              <span>Posture: {cameraState === 'ready' ? postureReadout : cameraState === 'mock' ? 'simulated / unavailable' : 'waiting'}</span>
            </div>
            <p className={cameraState === 'mock' ? 'warning-message' : 'micro-copy'} role={cameraMessage ? 'status' : undefined}>
              {cameraMessage || 'MediaPipe model weights and WebAssembly load from the configured CDN when the camera starts. Camera permission is required.'}
            </p>
            {mockFallback ? <p className="warning-message">Mock fallback is enabled by VITE_EVIDENCE_MOCK_FALLBACK. Simulated results are labeled and never presented as measured landmarks.</p> : null}
            <div className="inline-actions">
              {cameraState === 'idle' || cameraState === 'error' || (cameraState === 'mock' && !cameraHasStream) ? <button type="button" onClick={() => void startCamera()}>{cameraState === 'mock' ? 'Retry camera and vision' : 'Start camera and vision'}</button> : null}
              {cameraAvailable ? <button type="button" className="button-secondary" onClick={stopCamera}>Stop camera</button> : null}
              {!recording ? <button type="button" onClick={startRecording} disabled={!cameraAvailable}>Start recording</button> : <button type="button" className="button-secondary" onClick={stopRecording}>Stop recording</button>}
              <button type="button" className="ghost-button" onClick={runQualityCheck} disabled={!cameraAvailable}>{t.qualityCheck}</button>
              <button type="button" className="ghost-button" onClick={() => void saveEvidence()} disabled={saving || !videoHash}>{saving ? 'Saving…' : t.saveEvidence}</button>
            </div>
            {recording ? <p className="recording-indicator" role="status">Recording on this device. Stop the recording to calculate its SHA-256 hash.</p> : null}
            {quality ? (
              <div className={`quality-panel ${quality.retakePrompts.length ? 'quality-retake' : ''}`} aria-live="polite">
                <strong>Measured frame quality</strong>
                <p>Brightness: {quality.brightness}/255 · Laplacian variance: {quality.laplacianVariance}</p>
                <p>Face in frame: {quality.faceInFrame ? 'yes, detected by MediaPipe' : cameraState === 'ready' ? 'no' : 'not available without MediaPipe'}</p>
                {quality.retakePrompts.length ? <ul>{quality.retakePrompts.map((prompt) => <li key={prompt}>{prompt}</li>)}</ul> : <p>Frame quality checks passed. This is a capture-quality check, not identity verification.</p>}
              </div>
            ) : null}
            <div className="card liveness-panel">
              <h3>Liveness check</h3>
              <p>{liveness.prompt}</p>
              <div className="inline-actions">
                <button type="button" className="button-secondary" onClick={() => startLiveness('blink')} disabled={cameraState === 'loading' || recording}>Ask worker to blink</button>
                <button type="button" className="button-secondary" onClick={() => startLiveness('turn')} disabled={cameraState === 'loading' || recording}>Ask worker to turn head</button>
              </div>
              {liveness.status !== 'not-started' ? <p className={liveness.status === 'passed' ? 'success-message' : liveness.status === 'failed' ? 'error-text' : 'micro-copy'}>
                Result: {liveness.status === 'mock' ? `mock ${liveness.mockOutcome ?? 'not marked'}` : liveness.status} · confidence {(liveness.confidence * 100).toFixed(0)}%{liveness.status === 'mock' ? ' (simulated; not a liveness measurement)' : ''}
              </p> : null}
              {cameraState === 'mock' && liveness.status === 'mock' ? (
                <div className="inline-actions">
                  <button type="button" className="button-secondary" onClick={() => setLiveness((current) => ({ ...current, mockOutcome: 'pass', prompt: 'Mock liveness pass selected. This is not measured evidence.' }))}>Simulate pass</button>
                  <button type="button" className="button-secondary" onClick={() => setLiveness((current) => ({ ...current, mockOutcome: 'fail', prompt: 'Mock liveness failure selected. This is not measured evidence.' }))}>Simulate fail</button>
                </div>
              ) : null}
            </div>
            {videoHash ? <p className="micro-copy">Video SHA-256 (local clip): <code>{videoHash}</code></p> : null}
            {videoUrl ? (
              <div className="evidence-playback">
                <p className="calibration-caption">Local video preview. The video itself is not uploaded; only its hash and reviewed step metadata are stored.</p>
                <video
                  ref={playbackRef}
                  controls
                  src={videoUrl}
                  className="preview-video"
                  aria-label="Recorded evidence video"
                  onLoadedMetadata={(event) => setPlaybackDuration(event.currentTarget.duration || 0)}
                  onTimeUpdate={(event) => setPlaybackTime(event.currentTarget.currentTime)}
                />
                <label className="timeline-scrubber">
                  <span>Playback position: {playbackTime.toFixed(1)}s</span>
                  <input
                    type="range"
                    aria-label="Scrub evidence video"
                    min="0"
                    max={playbackDuration || 0}
                    step="0.1"
                    value={Math.min(playbackTime, playbackDuration || 0)}
                    onChange={(event) => {
                      const time = Number(event.target.value)
                      if (playbackRef.current) playbackRef.current.currentTime = time
                      setPlaybackTime(time)
                    }}
                    disabled={!playbackDuration}
                  />
                </label>
                <div className="evidence-segment-track" role="group" aria-label="Evidence step segments">
                  {steps.map((step, index) => {
                    const item = stepRecords[index]
                    if (item.start === null || item.end === null || playbackDuration <= 0) return null
                    const left = Math.max(0, Math.min(100, item.start / playbackDuration * 100))
                    const width = Math.max(1, Math.min(100 - left, (item.end - item.start) / playbackDuration * 100))
                    const confidence = item.confidence ?? 0
                    const confidenceClass = !item.suggested ? 'segment-manual' : confidence >= 0.8 ? 'segment-high' : confidence >= 0.55 ? 'segment-medium' : 'segment-low'
                    return (
                      <button
                        type="button"
                        key={step}
                        className={`evidence-segment ${confidenceClass}`}
                        style={{ left: `${left}%`, width: `${width}%` }}
                        aria-label={`Jump to step ${index + 1}: ${step}`}
                        title={`${step} · ${item.suggested ? `AI confidence ${Math.round(confidence * 100)}%` : 'Worker tag'}`}
                        onClick={() => {
                          if (playbackRef.current) playbackRef.current.currentTime = item.start ?? 0
                          setPlaybackTime(item.start ?? 0)
                          setCurrentStepIndex(index)
                        }}
                      />
                    )
                  })}
                </div>
                <div className="evidence-segment-legend" aria-label="Segment confidence legend">
                  <span><i className="segment-high" /> High confidence (80%+)</span>
                  <span><i className="segment-medium" /> Medium confidence (55–79%)</span>
                  <span><i className="segment-low" /> Low confidence (&lt;55%)</span>
                  <span><i className="segment-manual" /> Worker-tagged</span>
                </div>
              </div>
            ) : null}
            {notice ? <p className="success-message" role="status">{notice}</p> : null}
            {error ? <p className="error-text" role="alert">{error}</p> : null}
          </section>

          <section className="card padded-card">
            <div className="card-header-row">
              <div>
                <h3>Work-step suggestions</h3>
                <p className="micro-copy">Trade-aware hand-region, posture, and dwell heuristics propose timestamps. They are not certification decisions.</p>
              </div>
              <label htmlFor="evidence-trade">Trade heuristic</label>
              <select id="evidence-trade" value={trade} onChange={(event) => setTrade(event.target.value)}>
                <option>Domestic Electrician</option>
                <option>Plumber (General)</option>
                <option>Tailor / Sewing Machine Operator</option>
                <option>Mason</option>
              </select>
            </div>
            <h4>Current step: {steps[currentStepIndex] || 'All steps complete'}</h4>
            <div className="chip-list">
              {steps.map((step, index) => (
                <button key={step} type="button" className={`tag-button ${index === currentStepIndex ? 'active' : ''}`} onClick={() => { currentStepIndexRef.current = index; setCurrentStepIndex(index); stepStartRef.current = null; dwellStartRef.current = null }}>
                  {step}                  {stepRecords[index].suggested ? ` • ${stepRecords[index].simulated ? 'Mock suggested' : 'AI suggested'} (${Math.round((stepRecords[index].confidence ?? 0) * 100)}%)` : ''}
                </button>
              ))}
            </div>
            <div className="inline-actions">
              <button type="button" className="button-secondary" onClick={markStep} disabled={!recording}>{stepRecords[currentStepIndex]?.start === null ? 'Manually mark step start' : 'Manually mark step end'}</button>
              {cameraState === 'mock' && cameraHasStream && mockFallback ? <button type="button" className="button-secondary" onClick={simulateStepSuggestion} disabled={!recording}>Create simulated step suggestion (mock)</button> : null}
              <span className="micro-copy">Manual corrections replace AI suggestions for the selected timestamps.</span>
            </div>
            <div className="step-state-list">
              {steps.map((step, index) => (
                <div key={`${step}-${index}`} className="step-row evidence-step-row">
                  <div>
                    <strong>{index + 1}. {step}</strong>
                    <span className="micro-copy">{stepRecords[index].suggested
                      ? `${stepRecords[index].simulated ? 'Mock simulated' : 'AI suggested'} · confidence ${Math.round((stepRecords[index].confidence ?? 0) * 100)}%${stepRecords[index].review !== 'unreviewed' ? ` · ${stepRecords[index].review}` : ''}`
                      : stepRecords[index].status === 'done' ? 'Worker-corrected' : stepRecords[index].status === 'started' ? 'In progress' : 'Pending'}</span>
                  </div>
                  <label>Start (s)<input aria-label={`${step} start timestamp`} type="number" min="0" step="0.1" value={stepRecords[index].start ?? ''} onChange={(event) => setStepValue(index, 'start', event.target.value === '' ? null : Number(event.target.value), true)} /></label>
                  <label>End (s)<input aria-label={`${step} end timestamp`} type="number" min="0" step="0.1" value={stepRecords[index].end ?? ''} onChange={(event) => setStepValue(index, 'end', event.target.value === '' ? null : Number(event.target.value), true)} /></label>
                  {stepRecords[index].suggested ? (
                    <div className="inline-actions evidence-tag-actions" aria-label={`Review AI tag ${step}`}>
                      <button type="button" className="button-secondary" onClick={() => setStepRecords((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, status: 'done', review: 'accepted' } : item))}>Accept tag</button>
                      <button type="button" className="button-secondary" onClick={() => setStepRecords((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, review: 'edited' } : item))}>Edit tag</button>
                      <button type="button" className="button-secondary" onClick={() => setStepRecords((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, start: null, end: null, status: 'pending', review: 'rejected' } : item))}>Reject tag</button>
                    </div>
                  ) : stepRecords[index].review && stepRecords[index].review !== 'unreviewed'
                    ? <span className="micro-copy">AI tag {stepRecords[index].review} by worker</span>
                    : null}
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </main>
  )
}

export default DemonstratePage

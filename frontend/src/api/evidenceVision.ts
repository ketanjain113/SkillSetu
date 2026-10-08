import type { FaceLandmarker, HandLandmarker, PoseLandmarker } from '@mediapipe/tasks-vision'

export type EvidenceVision = {
  face: FaceLandmarker
  hands: HandLandmarker
  pose: PoseLandmarker
  close: () => void
}

const visionVersion = '1.1.0'
const wasmPath = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${visionVersion}/wasm`
const models = {
  face: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
  hands: 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
  pose: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
}

export async function loadEvidenceVision(): Promise<EvidenceVision> {
  const { FaceLandmarker, FilesetResolver, HandLandmarker, PoseLandmarker } = await import('@mediapipe/tasks-vision')
  const fileset = await FilesetResolver.forVisionTasks(wasmPath)
  const loaded = await Promise.allSettled([
    FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: models.face, delegate: 'CPU' },
      runningMode: 'VIDEO',
      outputFaceBlendshapes: true,
      numFaces: 1,
    }),
    HandLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: models.hands, delegate: 'CPU' },
      runningMode: 'VIDEO',
      numHands: 2,
    }),
    PoseLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath: models.pose, delegate: 'CPU' },
      runningMode: 'VIDEO',
      numPoses: 1,
    }),
  ])
  const failures = loaded.filter((result) => result.status === 'rejected')
  if (failures.length) {
    loaded.forEach((result) => {
      if (result.status === 'fulfilled') result.value.close()
    })
    const failed = failures[0]
    throw failed.status === 'rejected' ? failed.reason : new Error('Could not initialize vision models.')
  }
  const faceResult = loaded[0]
  const handResult = loaded[1]
  const poseResult = loaded[2]
  if (faceResult.status !== 'fulfilled' || handResult.status !== 'fulfilled' || poseResult.status !== 'fulfilled') {
    throw new Error('Could not initialize all requested vision models.')
  }
  return {
    face: faceResult.value,
    hands: handResult.value,
    pose: poseResult.value,
    close: () => {
      faceResult.value.close()
      handResult.value.close()
      poseResult.value.close()
    },
  }
}

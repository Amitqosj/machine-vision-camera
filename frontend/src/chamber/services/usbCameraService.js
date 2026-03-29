/**
 * USB camera facade — mock only.
 * Real: OpenCV VideoCapture indices or directshow/MediaFoundation via backend.
 */
export { connectCamera, disconnectCamera, togglePreview, captureImage, setRecording } from "./cameraService";

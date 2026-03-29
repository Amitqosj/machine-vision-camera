/**
 * Machine vision camera facade — mock only.
 * Real: backend binding to GenICam/GigE/USB3 SDK or OpenCV capture index.
 */
export { connectCamera, disconnectCamera, togglePreview, captureImage, setRecording } from "./cameraService";

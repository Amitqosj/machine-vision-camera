import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import * as arduinoService from "../chamber/services/arduinoService";
import { CommandLog } from "../chamber/components/CommandLog";
import { StatusBadge } from "../chamber/components/StatusBadge";

const COM_OPTIONS = ["COM1", "COM3", "COM4", "COM12", "/dev/ttyUSB0"];

export default function HardwareArduinoPage() {
  const { state, dispatch } = useChamber();
  const { arduino } = state;
  const log = useCallback(
    (line) => dispatch({ type: "LOG", payload: line }),
    [dispatch]
  );

  const [baudDraft, setBaudDraft] = useState(String(arduino.baudRate));

  useEffect(() => {
    setBaudDraft(String(arduino.baudRate));
  }, [arduino.baudRate]);

  const comValue = arduino.comPort;
  const lines = useMemo(() => state.commandLog, [state.commandLog]);

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>Hardware</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>Hardware / Arduino</h1>
          <p className="ch-muted">
            Commands call <code>/api/chamber/arduino/*</code> (simulated device state on server).
          </p>
        </div>
        <StatusBadge tone={arduino.connected ? "ok" : "bad"} pulse={arduino.busy}>
          {arduino.connected ? "Connected" : "Disconnected"}
        </StatusBadge>
      </header>

      <div className="ch-panel ch-io-grid">
        <div>
          <h2>Connection</h2>
          <label className="ch-field">
            Serial port
            <select
              value={comValue}
              disabled={arduino.busy}
              onChange={(e) => {
                const v = e.target.value;
                dispatch({ type: "ARDUINO_PATCH", payload: { comPort: v } });
                void arduinoService.patchSerial(dispatch, log, v, Number(baudDraft) || 9600);
              }}
            >
              {COM_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
          <label className="ch-field">
            Baud rate
            <input
              type="number"
              value={baudDraft}
              disabled={arduino.busy}
              onChange={(e) => setBaudDraft(e.target.value)}
              onBlur={() => {
                const br = Number(baudDraft) || 9600;
                dispatch({ type: "ARDUINO_PATCH", payload: { baudRate: br } });
                void arduinoService.patchSerial(dispatch, log, comValue, br);
              }}
            />
          </label>
          <div className="ch-toolbar ch-toolbar-tight">
            <button
              type="button"
              disabled={arduino.busy || arduino.connected}
              onClick={() => void arduinoService.connectArduino(dispatch, log)}
            >
              Connect
            </button>
            <button
              type="button"
              disabled={arduino.busy || !arduino.connected}
              onClick={() => void arduinoService.disconnectArduino(dispatch, log)}
            >
              Disconnect
            </button>
          </div>
        </div>

        <div>
          <h2>Lights & triggers</h2>
          <div className="ch-toolbar ch-toolbar-tight">
            <button
              type="button"
              disabled={arduino.busy || !arduino.connected || arduino.lightOn}
              onClick={() => void arduinoService.setLight(dispatch, log, true)}
            >
              Light ON
            </button>
            <button
              type="button"
              disabled={arduino.busy || !arduino.connected || !arduino.lightOn}
              onClick={() => void arduinoService.setLight(dispatch, log, false)}
            >
              Light OFF
            </button>
            <button
              type="button"
              disabled={arduino.busy || !arduino.connected}
              onClick={() =>
                void arduinoService.setAutoLight(dispatch, log, !arduino.autoLight)
              }
            >
              Auto light: {arduino.autoLight ? "on" : "off"}
            </button>
            <button
              type="button"
              disabled={arduino.busy || !arduino.connected}
              onClick={() => void arduinoService.triggerCapture(dispatch, log)}
            >
              Trigger capture
            </button>
          </div>
          <h3 className="ch-subhead">Relay / outputs (placeholder)</h3>
          <div className="ch-toolbar ch-toolbar-tight">
            <button
              type="button"
              disabled={!arduino.connected}
              onClick={() => void arduinoService.setRelayPlaceholder(dispatch, log, 1, true)}
            >
              R1 ON
            </button>
            <button
              type="button"
              disabled={!arduino.connected}
              onClick={() => void arduinoService.setRelayPlaceholder(dispatch, log, 1, false)}
            >
              R1 OFF
            </button>
            <button
              type="button"
              disabled={!arduino.connected}
              onClick={() => void arduinoService.setRelayPlaceholder(dispatch, log, 2, true)}
            >
              R2 ON
            </button>
            <button
              type="button"
              disabled={!arduino.connected}
              onClick={() => void arduinoService.setRelayPlaceholder(dispatch, log, 2, false)}
            >
              R2 OFF
            </button>
          </div>
        </div>
      </div>

      <CommandLog lines={lines} />
    </div>
  );
}

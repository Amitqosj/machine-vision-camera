import { useState } from "react";
import { Link } from "react-router-dom";
import { useChamber } from "../chamber/state/ChamberContext";
import * as sessionService from "../chamber/services/sessionService";

export default function SettingsPage() {
  const { state, dispatch } = useChamber();
  const { settings } = state;
  const [local, setLocal] = useState(settings);
  const [savedFlash, setSavedFlash] = useState(false);

  const apply = (patch) => setLocal((prev) => ({ ...prev, ...patch }));

  const persist = () => {
    dispatch({ type: "SETTINGS_PATCH", payload: local });
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 1600);
  };

  const previewName = sessionService.generateSessionName(
    local.sessionNameFormat,
    state.session.batchId
  );

  return (
    <div className="ch-page">
      <div className="ch-breadcrumb">
        <Link to="/">Dashboard</Link>
        <span>/</span>
        <span>Settings</span>
      </div>
      <header className="ch-page-head">
        <div>
          <h1>Settings</h1>
          <p className="ch-muted">Client placeholders — wire to persisted config API later.</p>
        </div>
        {savedFlash && <span className="ch-flash">Saved locally (mock)</span>}
      </header>

      <div className="ch-settings-grid">
        <section className="ch-panel">
          <h2>Capture & cameras</h2>
          <p className="ch-muted ch-small">
            Placeholder fields for exposure, gain, binning, trigger mode — bind to SDK when
            available.
          </p>
          <label className="ch-field">
            Capture mode
            <select
              value={local.captureMode}
              onChange={(e) => apply({ captureMode: e.target.value })}
            >
              <option value="still">Still</option>
              <option value="burst">Burst</option>
              <option value="stream">Stream to disk</option>
            </select>
          </label>
          <label className="ch-field ch-check">
            <input
              type="checkbox"
              checked={local.autoRecordOnTrigger}
              onChange={(e) => apply({ autoRecordOnTrigger: e.target.checked })}
            />
            Auto-record on hardware trigger
          </label>
        </section>

        <section className="ch-panel">
          <h2>Storage & session naming</h2>
          <label className="ch-field">
            Save path
            <input
              type="text"
              value={local.savePath}
              onChange={(e) => apply({ savePath: e.target.value })}
            />
          </label>
          <label className="ch-field">
            Session name format
            <input
              type="text"
              value={local.sessionNameFormat}
              onChange={(e) => apply({ sessionNameFormat: e.target.value })}
              placeholder="{date}_{batch}_{session}"
            />
          </label>
          <p className="ch-muted ch-small">Preview: {previewName}</p>
        </section>

        <section className="ch-panel">
          <h2>Serial / Arduino</h2>
          <p className="ch-muted ch-small">
            Defaults mirror hardware panel; production should load from secure config store.
          </p>
          <label className="ch-field">
            Default baud
            <input
              type="number"
              value={state.arduino.baudRate}
              readOnly
              className="ch-input-readonly"
            />
          </label>
        </section>

        <section className="ch-panel ch-panel-span">
          <h2>Future SDK integration</h2>
          <label className="ch-field">
            Notes for implementers
            <textarea
              rows={5}
              value={local.futureSdkNotes}
              onChange={(e) => apply({ futureSdkNotes: e.target.value })}
            />
          </label>
        </section>
      </div>

      <div className="ch-toolbar">
        <button type="button" onClick={persist}>
          Save settings (in-memory)
        </button>
      </div>
    </div>
  );
}

# Operating Instructions

## Calibration

1. Load film into the gate and transport path.
2. Use manual forward and reverse controls to confirm smooth film motion.
3. Adjust `steps_per_frame` until coarse movement lands near the next frame.
4. Adjust `pixels_per_motor_step` until alignment corrections converge quickly.
5. Set exposure, illumination, and white balance before a production scan.

## Scanning

Launch the UI from a graphical session on the Raspberry Pi desktop, through VNC, or through SSH with X forwarding enabled.

1. Choose an empty output directory.
2. Confirm image format and naming pattern.
3. Press Start.
4. Watch the live preview, frame number, motor status, camera status, and alignment status.
5. Use Pause before touching the transport path.
6. Use Stop for normal cancellation.

## Safety Notes

- Keep tension low and avoid aggressive acceleration while testing old film.
- Verify manual movement before enabling long automated scans.
- Leave overwrite protection enabled for production work.
- Review `logs/film-scanner.log` after any alignment or capture failure.

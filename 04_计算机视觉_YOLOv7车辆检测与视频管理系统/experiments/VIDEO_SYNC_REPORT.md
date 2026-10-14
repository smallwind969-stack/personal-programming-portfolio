# Vehicle detection video synchronization experiment

## Problem and design

The original playback loop read a new video frame every timer tick but painted the
most recent detection boxes onto that new frame. A moving target could therefore
appear outside its box even when the model itself was accurate. It also created a
new QThread for each detection and forced the vehicle model onto the CPU.

The revised loop uses the available CUDA device, the measured untraced model
configuration, and one persistent detection
thread. Each request contains a copied frame, playback session ID and frame ID.
The worker returns boxes with that same frame. The UI never paints boxes from a
different frame, and ignores results from older playback sessions. While a frame
is in flight, later input frames are skipped instead of building an old-frame
queue. Thread and video resources are stopped on window close.

This is **frame synchronization**, not object tracking or motion prediction. It
removes visible *box displacement* caused by cross-frame drawing; it does not
guarantee zero capture-to-display latency or a fixed frame rate on every machine.

## Reproduction

Run from the `yolov7-main` directory with the local CUDA-enabled Python:

```powershell
D:\Python310\python.exe -m unittest discover -s tests -v
D:\Python310\python.exe experiments\vehicle_sync_benchmark.py
D:\Python310\python.exe experiments\qt_vehicle_timing.py
```

The synthetic input horizontally pans the repository's `inference/images/bus.jpg`.
It exercises a moving vehicle without using private road footage. The frame-pair
illustration is at `experiments/output/vehicle_sync_comparison.png`; raw metrics
are in the adjacent JSON reports.

| Measurement | Before | After |
| --- | ---: | ---: |
| 30 FPS Qt test frames shown (of 60) | 30 | 57 |
| Frame-to-result median | about 70-77 ms | 18.42-20.44 ms |
| Frame-to-result p95 | not recorded | 20.97-22.80 ms |
| Detection boxes painted on a different frame | yes | no |

In a separate 45-frame fast-pan test (12 px/frame), every frame detected the
bus. Drawing boxes from eight frames earlier yielded a median IoU of 0.668 with
the current-frame boxes. The paired-frame implementation does not perform that
cross-frame overlay.

## Limitations and acceptance

The repository does not contain `drive_video/drive.mp4`. Also, the current
`D:\Python310\python.exe` lacks `mysql.connector`, which prevents a complete
HomePage launch. Thus these results verify the real detector, Qt event loop and
worker, but not the complete UI on the intended road video. The 57/60 result
also means the synthetic test did not achieve perfect 30 FPS. A human-visible
"no lag" claim needs a full-window playback test with representative footage,
including fast turns, multiple vehicles and the target display hardware.

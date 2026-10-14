"""CT image loading with geometry-preserving DICOM series selection."""

from __future__ import annotations

from pathlib import Path

import SimpleITK as sitk


def load_ct_image(path: str | Path, series_id: str | None = None):
    path = Path(path)
    if path.is_file() and path.suffix.lower() == ".mhd":
        return sitk.ReadImage(str(path))
    if not path.is_dir():
        raise FileNotFoundError(f"CT path is not a DICOM directory or MHD file: {path}")

    reader = sitk.ImageSeriesReader()
    series_ids = list(reader.GetGDCMSeriesIDs(str(path)) or [])
    if not series_ids:
        raise FileNotFoundError(f"No DICOM series found in {path}")
    if series_id is None:
        if len(series_ids) != 1:
            raise ValueError(f"Multiple DICOM series found in {path}; select one series explicitly")
        series_id = series_ids[0]
    elif series_id not in series_ids:
        raise ValueError(f"DICOM series {series_id!r} not found in {path}")

    # GDCM sorts by Image Orientation/Position along the slice normal. Reversing
    # this list would change volume direction and invalidate voxel/world mapping.
    filenames = list(reader.GetGDCMSeriesFileNames(str(path), series_id))
    if not filenames:
        raise FileNotFoundError(f"DICOM series {series_id!r} has no readable images in {path}")
    reader.SetFileNames(filenames)
    return reader.Execute()

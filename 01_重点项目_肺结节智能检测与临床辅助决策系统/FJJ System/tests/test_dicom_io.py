import pytest
import numpy as np
import pydicom
import SimpleITK as sitk
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from dicom_io import load_ct_image


class FakeSeriesReader:
    def __init__(self, series_ids):
        self.series_ids = series_ids
        self.selected = None

    def GetGDCMSeriesIDs(self, path):
        return self.series_ids

    def GetGDCMSeriesFileNames(self, path, series_id):
        assert series_id == self.series_ids[0]
        return ["slice_z_minus.dcm", "slice_z_plus.dcm"]

    def SetFileNames(self, names):
        self.selected = list(names)

    def Execute(self):
        return object()


def test_dicom_order_from_gdcm_is_not_reversed(tmp_path, monkeypatch):
    reader = FakeSeriesReader(["series-A"])
    monkeypatch.setattr("dicom_io.sitk.ImageSeriesReader", lambda: reader)
    load_ct_image(tmp_path)
    assert reader.selected == ["slice_z_minus.dcm", "slice_z_plus.dcm"]


def test_multiple_dicom_series_require_explicit_selection(tmp_path, monkeypatch):
    reader = FakeSeriesReader(["series-A", "series-B"])
    monkeypatch.setattr("dicom_io.sitk.ImageSeriesReader", lambda: reader)
    with pytest.raises(ValueError, match="Multiple DICOM series"):
        load_ct_image(tmp_path)


def test_missing_dicom_series_is_rejected(tmp_path, monkeypatch):
    reader = FakeSeriesReader([])
    monkeypatch.setattr("dicom_io.sitk.ImageSeriesReader", lambda: reader)
    with pytest.raises(FileNotFoundError, match="No DICOM series"):
        load_ct_image(tmp_path)


def test_real_dicom_series_uses_geometry_order_not_filename_order(tmp_path):
    study_uid, series_uid, frame_uid = generate_uid(), generate_uid(), generate_uid()
    # Reverse the alphabetical file order relative to physical z-position.
    for filename, z, value, instance in (("z.dcm", 0, 10, 1), ("m.dcm", 2, 20, 2), ("a.dcm", 4, 30, 3)):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = FileDataset(str(tmp_path / filename), {}, file_meta=meta, preamble=b"\0" * 128)
        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.FrameOfReferenceUID = frame_uid
        ds.PatientName = "Synthetic^Test"
        ds.PatientID = "SYNTHETIC"
        ds.Modality = "CT"
        ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]
        ds.ImagePositionPatient = [0, 0, z]
        ds.PixelSpacing = [1, 1]
        ds.SliceThickness = 2
        ds.InstanceNumber = instance
        ds.Rows = ds.Columns = 2
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.BitsAllocated = ds.BitsStored = 16
        ds.HighBit = 15
        ds.PixelRepresentation = 1
        ds.RescaleIntercept = 0
        ds.RescaleSlope = 1
        ds.PixelData = np.full((2, 2), value, dtype=np.int16).tobytes()
        ds.save_as(tmp_path / filename)

    image = load_ct_image(tmp_path)
    assert image.GetSize() == (2, 2, 3)
    assert image.GetSpacing()[2] == pytest.approx(2)
    assert image.GetOrigin()[2] == pytest.approx(0)
    assert sitk.GetArrayFromImage(image)[:, 0, 0].tolist() == [10, 20, 30]

from pathlib import Path

import numpy as np


ELEMENT_DTYPES = {
    "MET_SHORT": np.int16,
    "MET_USHORT": np.uint16,
    "MET_FLOAT": np.float32,
}


def parse_mhd(path):
    meta = {}
    for line in Path(path).read_text(encoding="ascii", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def _float_tuple(value):
    return tuple(float(x) for x in value.split())


def _int_tuple(value):
    return tuple(int(x) for x in value.split())


class MetaImageVolume:
    def __init__(self, path):
        self.path = Path(path)
        self.meta = parse_mhd(self.path)
        self.dim_size = _int_tuple(self.meta["DimSize"])
        self.spacing = _float_tuple(self.meta["ElementSpacing"])
        self.origin = _float_tuple(self.meta.get("Offset", self.meta.get("Position", "0 0 0")))
        self.direction = np.array(_float_tuple(self.meta.get("TransformMatrix", "1 0 0 0 1 0 0 0 1"))).reshape(3, 3)
        dtype = ELEMENT_DTYPES[self.meta["ElementType"]]
        raw_path = self.path.parent / self.meta["ElementDataFile"]
        self.array = np.memmap(raw_path, dtype=dtype, mode="r", shape=(self.dim_size[2], self.dim_size[1], self.dim_size[0]))

    @property
    def size(self):
        return self.dim_size

    def physical_to_continuous_index(self, point_xyz):
        point = np.array(point_xyz, dtype=np.float64)
        origin = np.array(self.origin, dtype=np.float64)
        spacing = np.array(self.spacing, dtype=np.float64)
        local = np.linalg.inv(self.direction).dot(point - origin)
        return tuple(local / spacing)

    def summary(self):
        return {
            "seriesuid": self.path.stem,
            "path": str(self.path),
            "size_x": self.dim_size[0],
            "size_y": self.dim_size[1],
            "size_z": self.dim_size[2],
            "spacing_x": self.spacing[0],
            "spacing_y": self.spacing[1],
            "spacing_z": self.spacing[2],
            "origin_x": self.origin[0],
            "origin_y": self.origin[1],
            "origin_z": self.origin[2],
        }

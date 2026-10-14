import time
import torch
import numpy as np
import SimpleITK as sitk
from scipy.ndimage import zoom
from skimage.measure import label, regionprops
from models import AttentionVNet_v6_7, ResNet18_3D_CBAM, DualBranchResNet
from dicom_io import load_ct_image


class DiagnosisEngine:
    def __init__(self, vnet_w, resnet_w, malig_w, device):
        self.device = device

        # 1. VNet 检测
        self.vnet = AttentionVNet_v6_7().to(device)
        self.vnet.load_state_dict(torch.load(vnet_w, map_location=device, weights_only=True), strict=False)
        self.vnet.eval()

        # 2. ResNet 精筛 (32px)
        self.resnet = ResNet18_3D_CBAM().to(device)
        self.resnet.load_state_dict(torch.load(resnet_w, map_location=device, weights_only=True))
        self.resnet.eval()

        # 3. 双分支平衡判别
        self.model_dual = DualBranchResNet().to(device)
        self.model_dual.load_state_dict(torch.load(malig_w, map_location=device, weights_only=True))
        self.model_dual.eval()

    def load_itk(self, path):
        return load_ct_image(path)

    def get_vol_1mm(self, itk_img):
        spacing = itk_img.GetSpacing()
        new_size = [int(round(itk_img.GetSize()[i] * spacing[i])) for i in range(3)]

        resample = sitk.ResampleImageFilter()
        resample.SetOutputSpacing((1.0, 1.0, 1.0))
        resample.SetSize(new_size)
        resample.SetOutputOrigin(itk_img.GetOrigin())
        resample.SetOutputDirection(itk_img.GetDirection())

        vol_1mm = sitk.GetArrayFromImage(resample.Execute(itk_img)).astype(np.float32)
        vol_1mm = (np.clip(vol_1mm, -1200, 600) + 1200) / 1800.0
        return vol_1mm, spacing

    def resampled_1mm_index_to_physical(self, itk_img, x_idx, y_idx, z_idx):
        origin = np.array(itk_img.GetOrigin(), dtype=np.float64)
        direction = np.array(itk_img.GetDirection(), dtype=np.float64).reshape(3, 3)
        continuous_index = np.array([x_idx, y_idx, z_idx], dtype=np.float64)
        return origin + direction.dot(continuous_index)

    def extract_and_resize(self, vol, center, size_voxel, target_px=32):
        cz, cy, cx = center
        half = size_voxel // 2

        zs, ze = max(0, int(cz - half)), min(vol.shape[0], int(cz + half))
        ys, ye = max(0, int(cy - half)), min(vol.shape[1], int(cy + half))
        xs, xe = max(0, int(cx - half)), min(vol.shape[2], int(cx + half))

        crop = vol[zs:ze, ys:ye, xs:xe]
        if crop.size == 0:
            return np.zeros((target_px, target_px, target_px), dtype=np.float32)

        rf = [
            target_px / crop.shape[0],
            target_px / crop.shape[1],
            target_px / crop.shape[2]
        ]
        return zoom(crop, rf, mode='nearest').astype(np.float32)

    def run_inference(
        self,
        itk_img,
        prob_threshold=0.15,
        resnet_threshold=0.4,
        patch_size=64,
        stride=32,
        return_all_candidates=False,
    ):
        t_total_start = time.perf_counter()

        # 1. 预处理
        t0 = time.perf_counter()
        vol_1mm, spacing = self.get_vol_1mm(itk_img)
        t1 = time.perf_counter()

        pz = patch_size
        nz, ny, nx = vol_1mm.shape
        prob_map = np.zeros_like(vol_1mm)
        count_map = np.zeros_like(vol_1mm)

        # 2. VNet 检测
        with torch.no_grad():
            for z in range(0, max(1, nz - pz + 1), stride):
                for y in range(0, max(1, ny - pz + 1), stride):
                    for x in range(0, max(1, nx - pz + 1), stride):
                        patch = np.zeros((pz, pz, pz), dtype=np.float32)
                        sub = vol_1mm[z:z + pz, y:y + pz, x:x + pz]
                        patch[:sub.shape[0], :sub.shape[1], :sub.shape[2]] = sub

                        t = torch.from_numpy(patch).unsqueeze(0).unsqueeze(0).to(self.device)
                        out = torch.sigmoid(self.vnet(t)).squeeze().cpu().numpy()

                        prob_map[z:z + pz, y:y + pz, x:x + pz] += out[:sub.shape[0], :sub.shape[1], :sub.shape[2]]
                        count_map[z:z + pz, y:y + pz, x:x + pz] += 1
        t2 = time.perf_counter()

        # 3. 候选提取
        prob_map /= np.maximum(count_map, 1)
        v_cands = [prop.centroid for prop in regionprops(label(prob_map > prob_threshold))]
        t3 = time.perf_counter()

        # 4. ResNet 精筛
        results = []
        for cz, cy, cx in v_cands:
            p = np.zeros((32, 32, 32), dtype=np.float32)
            zs, ys, xs = int(cz) - 16, int(cy) - 16, int(cx) - 16
            sub = vol_1mm[
                max(0, zs):min(nz, zs + 32),
                max(0, ys):min(ny, ys + 32),
                max(0, xs):min(nx, xs + 32)
            ]
            p[:sub.shape[0], :sub.shape[1], :sub.shape[2]] = sub

            prob = torch.softmax(
                self.resnet(torch.from_numpy(p).unsqueeze(0).unsqueeze(0).to(self.device)),
                dim=1
            )[0, 1].item()

            passed_filter = prob > resnet_threshold
            if passed_filter or return_all_candidates:
                coord_x, coord_y, coord_z = self.resampled_1mm_index_to_physical(itk_img, cx, cy, cz)
                results.append({
                    "z_idx": cz,
                    "y_idx": cy,
                    "x_idx": cx,
                    "coordX": round(float(coord_x), 4),
                    "coordY": round(float(coord_y), 4),
                    "coordZ": round(float(coord_z), 4),
                    "slice_idx": int(round(cz * (1.0 / spacing[2]))),
                    "x": int(round(cx * (1.0 / spacing[0]))),
                    "y": int(round(cy * (1.0 / spacing[1]))),
                    "prob": round(prob, 4),
                    "resnet_prob": round(prob, 4),
                    "passed_filter": passed_filter,
                    "status": "pending",
                    "area": int(np.sum(prob_map[int(cz)] > prob_threshold) / (spacing[0] * spacing[1]))
                })
        t4 = time.perf_counter()

        timing = {
            "preprocess_sec": round(t1 - t0, 4),
            "vnet_detect_sec": round(t2 - t1, 4),
            "candidate_extract_sec": round(t3 - t2, 4),
            "resnet_filter_sec": round(t4 - t3, 4),
            "prob_threshold": prob_threshold,
            "resnet_threshold": resnet_threshold,
            "patch_size": patch_size,
            "stride": stride,
            "candidate_count_before_filter": len(v_cands),
            "candidate_count_after_filter": len(results),
            "total_run_inference_sec": round(t4 - t_total_start, 4)
        }

        print(f"[ENGINE DETECT TIMING] {timing}")
        return results, timing

    def identify_malignancy(self, itk_img, findings):
        t_total_start = time.perf_counter()

        # 1. 预处理
        t0 = time.perf_counter()
        vol_1mm, _ = self.get_vol_1mm(itk_img)
        t1 = time.perf_counter()

        patch_extract_time = 0.0
        dual_infer_time = 0.0

        # 2. 双分支识别
        for f in findings:
            center = (f['z_idx'], f['y_idx'], f['x_idx'])

            tp0 = time.perf_counter()
            p_l = self.extract_and_resize(vol_1mm, center, 32, 32)
            p_g = self.extract_and_resize(vol_1mm, center, 64, 32)
            tp1 = time.perf_counter()
            patch_extract_time += (tp1 - tp0)

            t_l = torch.from_numpy(p_l).unsqueeze(0).unsqueeze(0).to(self.device)
            t_g = torch.from_numpy(p_g).unsqueeze(0).unsqueeze(0).to(self.device)

            ti0 = time.perf_counter()
            with torch.no_grad():
                out = self.model_dual(t_l, t_g)
                m_prob = torch.softmax(out, dim=1)[0, 1].item()
            ti1 = time.perf_counter()
            dual_infer_time += (ti1 - ti0)

            f['malignancy_prob'] = round(m_prob, 4)
            f['status'] = 'malignant' if m_prob > 0.45 else 'benign'

        t2 = time.perf_counter()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        n = len(findings)
        timing = {
            "preprocess_sec": round(t1 - t0, 4),
            "patch_extract_sec": round(patch_extract_time, 4),
            "dual_branch_infer_sec": round(dual_infer_time, 4),
            "nodule_count": n,
            "avg_patch_extract_per_nodule_sec": round(patch_extract_time / n, 4) if n > 0 else 0.0,
            "avg_dual_infer_per_nodule_sec": round(dual_infer_time / n, 4) if n > 0 else 0.0,
            "total_identify_sec": round(t2 - t_total_start, 4)
        }

        print(f"[ENGINE IDENTIFY TIMING] {timing}")
        return findings, timing

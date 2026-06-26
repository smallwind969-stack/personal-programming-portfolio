import torch
import torch.nn as nn
import torch.nn.functional as F

# ==========================================
# 1. VNet 检测模型组件 (用于第一步检测)
# ==========================================
class SEBlock3D(nn.Module):
    def __init__(self, channels, reduction=4):
        super().__init__()
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool3d(1),
            nn.Conv3d(channels, channels // reduction, 1),
            nn.ReLU(inplace=True),
            nn.Conv3d(channels // reduction, channels, 1),
            nn.Sigmoid()
        )
    def forward(self, x): return x * self.fc(x)

class LU_ResBlock_v6(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(channels, channels, 5, padding=2), nn.InstanceNorm3d(channels), nn.ReLU(True),
            nn.Conv3d(channels, channels, 5, padding=2), nn.InstanceNorm3d(channels)
        )
        self.se = SEBlock3D(channels)
    def forward(self, x): return F.relu(x + self.se(self.conv(x)))

class AttentionGate3D(nn.Module):
    def __init__(self, F_g, F_l, F_int):
        super().__init__()
        self.W_g = nn.Sequential(nn.Conv3d(F_g, F_int, 1), nn.InstanceNorm3d(F_int))
        self.W_l = nn.Sequential(nn.Conv3d(F_l, F_int, 1), nn.InstanceNorm3d(F_int))
        self.psi = nn.Sequential(nn.Conv3d(F_int, 1, 1), nn.InstanceNorm3d(1), nn.Sigmoid())
    def forward(self, g, x): return x * self.psi(F.relu(self.W_g(g) + self.W_l(x)))

class AttentionVNet_v6_7(nn.Module):
    def __init__(self):
        super().__init__()
        self.in_conv = nn.Conv3d(1, 16, 3, padding=1)
        self.down1 = nn.Conv3d(16, 32, 2, 2); self.res1 = LU_ResBlock_v6(32)
        self.down2 = nn.Conv3d(32, 64, 2, 2); self.res2 = LU_ResBlock_v6(64)
        self.down3 = nn.Conv3d(64, 128, 2, 2); self.res3 = LU_ResBlock_v6(128)
        self.up3 = nn.ConvTranspose3d(128, 64, 2, 2); self.ag3 = AttentionGate3D(64, 64, 32); self.res_up3 = LU_ResBlock_v6(128)
        self.up2 = nn.ConvTranspose3d(128, 32, 2, 2); self.ag2 = AttentionGate3D(32, 32, 16); self.res_up2 = LU_ResBlock_v6(64)
        self.up1 = nn.ConvTranspose3d(64, 16, 2, 2); self.ag1 = AttentionGate3D(16, 16, 8); self.res_up1 = LU_ResBlock_v6(32)
        self.out_conv = nn.Conv3d(32, 1, 1)
    def forward(self, x):
        x1 = F.relu(self.in_conv(x))
        x2 = self.res1(self.down1(x1)); x3 = self.res2(self.down2(x2)); x4 = self.res3(self.down3(x3))
        u3 = self.up3(x4); u3 = self.res_up3(torch.cat([u3, self.ag3(u3, x3)], 1))
        u2 = self.up2(u3); u2 = self.res_up2(torch.cat([u2, self.ag2(u2, x2)], 1))
        u1 = self.up1(u2); u1 = self.res_up1(torch.cat([u1, self.ag1(u1, x1)], 1))
        return self.out_conv(u1)

# ==========================================
# 2. ResNet18-3D + CBAM 模型组件
# ==========================================
class ChannelAttention3D(nn.Module):
    def __init__(self, in_planes, ratio=16):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Conv3d(in_planes, in_planes // ratio, 1, bias=False),
            nn.ReLU(True),
            nn.Conv3d(in_planes // ratio, in_planes, 1, bias=False)
        )
        self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        avg_out = self.fc(F.adaptive_avg_pool3d(x, 1))
        max_out = self.fc(F.adaptive_max_pool3d(x, 1))
        return x * self.sigmoid(avg_out + max_out)

class SpatialAttention3D(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv3d(2, 1, 7, padding=3, bias=False); self.sigmoid = nn.Sigmoid()
    def forward(self, x):
        avg_out = torch.mean(x, dim=1, keepdim=True); max_out, _ = torch.max(x, dim=1, keepdim=True)
        return x * self.sigmoid(self.conv1(torch.cat([avg_out, max_out], dim=1)))

class CBAM3D(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.ca = ChannelAttention3D(channels); self.sa = SpatialAttention3D()
    def forward(self, x): return self.sa(self.ca(x))

class BasicBlock3D_CBAM(nn.Module):
    def __init__(self, in_planes, planes, stride=1):
        super().__init__()
        self.conv1 = nn.Conv3d(in_planes, planes, 3, stride, 1, bias=False); self.bn1 = nn.BatchNorm3d(planes)
        self.conv2 = nn.Conv3d(planes, planes, 3, 1, 1, bias=False); self.bn2 = nn.BatchNorm3d(planes)
        self.cbam = CBAM3D(planes); self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != planes: self.shortcut = nn.Sequential(nn.Conv3d(in_planes, planes, 1, stride, bias=False), nn.BatchNorm3d(planes))
    def forward(self, x):
        out = self.cbam(self.bn2(self.conv2(F.relu(self.bn1(self.conv1(x))))))
        return F.relu(out + self.shortcut(x))

# ==========================================
# 3. 双分支专用架构 (Dual-Branch ResNet)
# ==========================================
class ResNetBackbone(nn.Module):
    """特征提取骨干，输出 512 维特征向量"""
    def __init__(self):
        super().__init__()
        self.in_planes = 64
        self.conv1 = nn.Conv3d(1, 64, 3, 1, 1, bias=False); self.bn1 = nn.BatchNorm3d(64)
        self.layer1 = nn.Sequential(BasicBlock3D_CBAM(64, 64, 1))
        self.layer2 = nn.Sequential(BasicBlock3D_CBAM(64, 128, 2))
        self.layer3 = nn.Sequential(BasicBlock3D_CBAM(128, 256, 2))
        self.layer4 = nn.Sequential(BasicBlock3D_CBAM(256, 512, 2))
        self.avgpool = nn.AdaptiveAvgPool3d(1)
    def forward(self, x):
        x = self.layer4(self.layer3(self.layer2(self.layer1(F.relu(self.bn1(self.conv1(x)))))))
        return self.avgpool(x).view(x.size(0), -1)

class DualBranchResNet(nn.Module):
    """最终的平衡判别模型：输入 Local + Global，输出 2 分类"""
    def __init__(self):
        super().__init__()
        self.local_branch = ResNetBackbone()
        self.global_branch = ResNetBackbone()
        self.fc = nn.Sequential(
            nn.Linear(1024, 256), nn.ReLU(True), nn.Dropout(0.5), nn.Linear(256, 2)
        )
    def forward(self, x_l, x_g):
        f_l, f_g = self.local_branch(x_l), self.global_branch(x_g)
        return self.fc(torch.cat((f_l, f_g), dim=1))

# 用于兼容老代码的单分支 ResNet (仅精筛使用)
class ResNet18_3D_CBAM(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        self.in_planes = 64
        self.conv1 = nn.Conv3d(1, 64, 3, 1, 1, bias=False); self.bn1 = nn.BatchNorm3d(64)
        self.layer1 = nn.Sequential(BasicBlock3D_CBAM(64, 64, 1))
        self.layer2 = nn.Sequential(BasicBlock3D_CBAM(64, 128, 2))
        self.layer3 = nn.Sequential(BasicBlock3D_CBAM(128, 256, 2))
        self.layer4 = nn.Sequential(BasicBlock3D_CBAM(256, 512, 2))
        self.avgpool = nn.AdaptiveAvgPool3d(1); self.fc = nn.Linear(512, num_classes)
    def forward(self, x):
        x = self.layer4(self.layer3(self.layer2(self.layer1(F.relu(self.bn1(self.conv1(x)))))))
        return self.fc(self.avgpool(x).view(x.size(0), -1))

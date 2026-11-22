#!/usr/bin/env python3
"""
Rebuttal Deep Learning Baselines for Dual-View THz-TDS TCM Classification
=========================================================================
Strictly mirrors the locked validation protocol in `run_unified_double_nested_all.py`:
  1. Loads full-precision 0.22-1.04 THz (358-point) spectral caches (`*_fast_cache.npz`).
  2. Assigns contiguous 5-scan pellet IDs BEFORE QC (`pellet_id = f"{c}__P{local_i // 5:02d}"`).
  3. Applies identical single-spectrum physical QC:
     1.2 <= mean(n) <= 2.6  AND  mean(alpha) <= 55.0 cm^-1.
  4. Evaluates on identical Outer 5-Fold Pellet-Grouped `StratifiedGroupKFold`
     (zero same-pellet leakage) with Inner 3-Fold Pellet-Grouped `StratifiedGroupKFold`
     for early stopping / learning-rate & weight-decay selection (zero test peeking).
  5. Evaluates 4 end-to-end PyTorch architectures across Track A (`raw_dual`, 2x358)
     and/or Track B (`dual_view`, 9x358):
       - 1D-CNN
       - ResNet-1D (with Squeeze-and-Excitation channel attention)
       - Spectral-Transformer (patch-tokenized 1D Transformer encoder)
       - Dual-Branch-Fusion-Net (dedicated alpha & n encoders with gated fusion)
  6. Supports per-run JSON checkpointing & automatic resume for Google Colab sessions.
"""

import argparse
import json
import os
import random
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

warnings.filterwarnings("ignore")

# Project-relative paths (zero hardcoded machine-specific paths)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_ROOT = PROJECT_DIR / "01_原始实验数据"
DEFAULT_OUT_DIR = PROJECT_DIR / "05_实验结果" / "模型结果" / "rebuttal_dl"
LOCKED_SUMMARY_PATH = PROJECT_DIR / "05_实验结果" / "模型结果" / "Unified_Double_Nested_Summary.json"

DATASETS = [
    {
        "key": "Astragali_Radix",
        "display": "Astragali Radix (Fibrous Root)",
        "folder": DATA_ROOT / "黄芪",
        "cache": "huangqi_fast_cache.npz",
        "classes": ["Datong (SX)", "Guyang (IM)", "Qujing (YN)", "Gansu (GS)"],
    },
    {
        "key": "Ziziphi_Spinosae_Semen",
        "display": "Ziziphi Spinosae Semen (Lipid-Rich Seed)",
        "folder": DATA_ROOT / "酸枣仁",
        "cache": "suanzaoren_fast_cache.npz",
        "classes": ["Boxed (HB)", "SJZ/BZ", "Bulk-Bag", "Bulk-50g", "Tongrentang (AH)"],
    },
    {
        "key": "Gastrodia_elata",
        "display": "Gastrodia elata (Starchy Tuber)",
        "folder": DATA_ROOT / "天麻",
        "cache": "tianma_fast_cache.npz",
        "classes": ["Bozhou (AH)", "Leishan (GZ)", "Changbai (JL)", "Yunnan (YN)"],
    },
]


# ==============================================================================
# 1. Determinism, Data Loading, Physical QC & Feature Views
# ==============================================================================
def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def load_cached_dataset(cfg: dict):
    cache_path = Path(cfg["folder"]) / cfg["cache"]
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Spectral cache not found: {cache_path}. "
            "Ensure the GitHub repository (including *_fast_cache.npz) is cloned cleanly."
        )
    d = np.load(cache_path, allow_pickle=True)
    raw_a = d["raw_a"].astype(np.float32)
    raw_r = d["raw_r"].astype(np.float32)
    y = d["y"]
    freq = d["freq"].astype(np.float32)

    # Assign contiguous 5-scan pellet IDs BEFORE QC (exact match with locked pipeline)
    groups = np.empty(len(y), dtype=object)
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        for local_i, g_i in enumerate(idx):
            groups[g_i] = f"{c}__P{local_i // 5:02d}"

    # Unified single-spectrum physical QC (zero cross-sample statistics)
    ma = raw_a.mean(axis=1)
    mr = raw_r.mean(axis=1)
    mask = (mr >= 1.2) & (mr <= 2.6) & (ma <= 55.0)
    raw_a, raw_r, y, groups = raw_a[mask], raw_r[mask], y[mask], groups[mask]

    class_to_idx = {c: i for i, c in enumerate(cfg["classes"])}
    y_idx = np.array([class_to_idx[lbl] for lbl in y], dtype=np.int64)
    return raw_a, raw_r, y, y_idx, groups, freq


def sample_wise_snv(spec_1d: np.ndarray) -> np.ndarray:
    return (spec_1d - np.mean(spec_1d)) / (np.std(spec_1d) + 1e-8)


def build_channel_tensor(raw_a: np.ndarray, raw_r: np.ndarray, input_mode: str) -> np.ndarray:
    """
    Pure intra-sample channel construction (zero cross-sample access):
      - 'raw_dual':  (N, 2, 358) -> [alpha, n]
      - 'dual_view': (N, 9, 358) -> [env_a, d1_a, d2_a, env_r, d1_r,
                                     raw_env_a, raw_d2_a, raw_env_r, raw_d1_r]
    """
    if input_mode == "raw_dual":
        return np.stack([raw_a, raw_r], axis=1).astype(np.float32)

    if input_mode == "dual_view":
        out = []
        for ra, rr in zip(raw_a, raw_r):
            snv_a = sample_wise_snv(ra)
            snv_r = sample_wise_snv(rr)
            env_a = savgol_filter(snv_a, window_length=19, polyorder=2, deriv=0)
            d1_a = sample_wise_snv(savgol_filter(snv_a, window_length=19, polyorder=2, deriv=1))
            d2_a = sample_wise_snv(savgol_filter(snv_a, window_length=15, polyorder=2, deriv=2))
            env_r = savgol_filter(snv_r, window_length=19, polyorder=2, deriv=0)
            d1_r = sample_wise_snv(savgol_filter(snv_r, window_length=15, polyorder=2, deriv=1))

            raw_env_a = savgol_filter(ra, window_length=19, polyorder=2, deriv=0)
            raw_d2_a = savgol_filter(ra, window_length=15, polyorder=2, deriv=2)
            raw_env_r = savgol_filter(rr, window_length=19, polyorder=2, deriv=0)
            raw_d1_r = savgol_filter(rr, window_length=15, polyorder=2, deriv=1)

            out.append(
                np.stack(
                    [env_a, d1_a, d2_a, env_r, d1_r, raw_env_a, raw_d2_a, raw_env_r, raw_d1_r],
                    axis=0,
                )
            )
        return np.asarray(out, dtype=np.float32)

    raise ValueError(f"Unknown input_mode: {input_mode}")


def fit_apply_channel_scaler(X_tr: np.ndarray, X_te: np.ndarray):
    """Per-channel, per-frequency Z-score fit strictly on X_tr (zero leakage)."""
    mean = X_tr.mean(axis=0, keepdims=True)
    std = X_tr.std(axis=0, keepdims=True) + 1e-8
    return (X_tr - mean) / std, (X_te - mean) / std


# ==============================================================================
# 2. End-to-End 1D Spectral Deep Learning Architectures
# ==============================================================================
class SpectralCNN1D(nn.Module):
    def __init__(self, in_ch: int, n_classes: int, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(in_ch, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.GELU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.GELU(),
            nn.MaxPool1d(2),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(128, n_classes),
        )

    def forward(self, x):
        return self.head(self.net(x))


class SEBlock1D(nn.Module):
    def __init__(self, ch: int, reduction: int = 4):
        super().__init__()
        hidden = max(8, ch // reduction)
        self.fc = nn.Sequential(
            nn.Linear(ch, hidden),
            nn.GELU(),
            nn.Linear(hidden, ch),
            nn.Sigmoid(),
        )

    def forward(self, x):
        w = x.mean(dim=-1)
        w = self.fc(w).unsqueeze(-1)
        return x * w


class ResBlock1D(nn.Module):
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1, dropout: float = 0.15):
        super().__init__()
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size=5, stride=stride, padding=2, bias=False)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.se = SEBlock1D(out_ch)
        self.drop = nn.Dropout(dropout)
        self.shortcut = (
            nn.Sequential(
                nn.Conv1d(in_ch, out_ch, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_ch),
            )
            if stride != 1 or in_ch != out_ch
            else nn.Identity()
        )

    def forward(self, x):
        h = F.gelu(self.bn1(self.conv1(x)))
        h = self.drop(h)
        h = self.bn2(self.conv2(h))
        h = self.se(h)
        return F.gelu(h + self.shortcut(x))


class SpectralResNet1D(nn.Module):
    def __init__(self, in_ch: int, n_classes: int, dropout: float = 0.3):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv1d(in_ch, 32, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm1d(32),
            nn.GELU(),
        )
        self.layer1 = ResBlock1D(32, 32, stride=1)
        self.layer2 = ResBlock1D(32, 64, stride=2)
        self.layer3 = ResBlock1D(64, 128, stride=2)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(dropout), nn.Linear(128, n_classes))

    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        return self.head(self.pool(x))


class SpectralTransformer(nn.Module):
    def __init__(
        self,
        in_ch: int,
        n_classes: int,
        seq_len: int = 358,
        patch_size: int = 12,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.patch_size = patch_size
        self.n_patches = (seq_len + patch_size - 1) // patch_size
        self.pad_len = self.n_patches * patch_size - seq_len
        self.patch_embed = nn.Conv1d(in_ch, d_model, kernel_size=patch_size, stride=patch_size)
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
        self.pos_embed = nn.Parameter(torch.randn(1, self.n_patches + 1, d_model) * 0.02)
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 2,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(d_model)
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(d_model, n_classes))

    def forward(self, x):
        if self.pad_len > 0:
            x = F.pad(x, (0, self.pad_len), mode="replicate")
        tokens = self.patch_embed(x).transpose(1, 2)  # (B, n_patches, d_model)
        cls = self.cls_token.expand(tokens.size(0), -1, -1)
        tokens = torch.cat([cls, tokens], dim=1) + self.pos_embed
        h = self.norm(self.encoder(tokens))
        return self.head(h[:, 0])


class DualBranchFusionNet(nn.Module):
    """
    Dedicated absorption (alpha) and refractive-index (n) 1D encoders with gated fusion.
    Channel split:
      - raw_dual (2 ch):  alpha=[0], n=[1]
      - dual_view (9 ch): alpha=[0,1,2,5,6], n=[3,4,7,8]
    """

    def __init__(self, in_ch: int, n_classes: int, dropout: float = 0.3):
        super().__init__()
        if in_ch == 2:
            self.alpha_idx = [0]
            self.ref_idx = [1]
        elif in_ch == 9:
            self.alpha_idx = [0, 1, 2, 5, 6]
            self.ref_idx = [3, 4, 7, 8]
        else:
            mid = max(1, in_ch // 2)
            self.alpha_idx = list(range(mid))
            self.ref_idx = list(range(mid, in_ch))

        def make_branch(c_in: int):
            return nn.Sequential(
                nn.Conv1d(c_in, 32, kernel_size=7, padding=3),
                nn.BatchNorm1d(32),
                nn.GELU(),
                nn.MaxPool1d(2),
                ResBlock1D(32, 64, stride=2),
                nn.AdaptiveAvgPool1d(1),
                nn.Flatten(),
            )

        self.branch_a = make_branch(len(self.alpha_idx))
        self.branch_r = make_branch(len(self.ref_idx))
        self.gate = nn.Sequential(nn.Linear(128, 64), nn.GELU(), nn.Linear(64, 2), nn.Softmax(dim=-1))
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(128, n_classes))

    def forward(self, x):
        fa = self.branch_a(x[:, self.alpha_idx, :])
        fr = self.branch_r(x[:, self.ref_idx, :])
        cat = torch.cat([fa, fr], dim=-1)
        g = self.gate(cat)
        fused = torch.cat([fa * g[:, 0:1], fr * g[:, 1:2]], dim=-1)
        return self.head(fused)


MODEL_REGISTRY = {
    "1D-CNN": SpectralCNN1D,
    "ResNet-1D": SpectralResNet1D,
    "Spectral-Transformer": SpectralTransformer,
    "Dual-Branch-Fusion": DualBranchFusionNet,
}


# ==============================================================================
# 3. Training, Evaluation & Paired Pellet-Cluster Bootstrap
# ==============================================================================
def compute_pellet_vote(y_true: np.ndarray, y_pred: np.ndarray, groups: np.ndarray) -> dict:
    uniq_p = np.unique(groups)
    p_true, p_pred = [], []
    for p in uniq_p:
        m = groups == p
        p_true.append(y_true[m][0])
        vals, cnts = np.unique(y_pred[m], return_counts=True)
        p_pred.append(vals[np.argmax(cnts)])
    p_true, p_pred = np.array(p_true), np.array(p_pred)
    return {
        "pellet_acc": float(accuracy_score(p_true, p_pred) * 100.0),
        "pellet_correct": int(np.sum(p_true == p_pred)),
        "pellet_total": int(len(uniq_p)),
        "pellet_macro_f1": float(f1_score(p_true, p_pred, average="macro")),
    }


def train_and_predict(
    model_name: str,
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_eval: np.ndarray,
    n_classes: int,
    device: torch.device,
    lr: float,
    weight_decay: float,
    epochs: int,
    batch_size: int,
    seed: int,
    X_val: np.ndarray = None,
    y_val: np.ndarray = None,
    patience: int = 20,
):
    set_seed(seed)
    in_ch = X_tr.shape[1]
    model = MODEL_REGISTRY[model_name](in_ch=in_ch, n_classes=n_classes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs))
    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

    use_amp = device.type == "cuda"
    amp_dtype = torch.bfloat16 if (use_amp and torch.cuda.is_bf16_supported()) else torch.float16
    scaler = torch.cuda.amp.GradScaler(enabled=(use_amp and amp_dtype == torch.float16))

    ds_tr = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr))
    dl_tr = DataLoader(ds_tr, batch_size=min(batch_size, len(ds_tr)), shuffle=True, drop_last=False)

    best_val_loss = float("inf")
    best_state = None
    best_epoch = epochs
    stale = 0

    if X_val is not None:
        X_val_t = torch.from_numpy(X_val).to(device)
        y_val_t = torch.from_numpy(y_val).to(device)

    for ep in range(1, epochs + 1):
        model.train()
        for xb, yb in dl_tr:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=use_amp):
                logits = model(xb)
                loss = criterion(logits, yb)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        scheduler.step()

        if X_val is not None:
            model.eval()
            with torch.no_grad(), torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=use_amp):
                val_logits = model(X_val_t)
                val_loss = float(criterion(val_logits, y_val_t).item())
            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                best_epoch = ep
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
                if stale >= patience:
                    break

    if best_state is not None:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        X_eval_t = torch.from_numpy(X_eval).to(device)
        preds = model(X_eval_t).argmax(dim=-1).cpu().numpy()
    return preds, best_epoch


def evaluate_model_nested_cv(
    model_name: str,
    X_all: np.ndarray,
    y_idx: np.ndarray,
    y_str: np.ndarray,
    groups: np.ndarray,
    classes: list,
    device: torch.device,
    seed: int,
    max_epochs: int,
    batch_size: int,
    hp_grid: list,
):
    outer_cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    outer_splits = list(outer_cv.split(X_all, y_idx, groups))

    oof_idx = np.empty_like(y_idx)
    fold_accs = []
    chosen_cfgs = []
    n_classes = len(classes)

    for fold_i, (tr_out, te_out) in enumerate(outer_splits, 1):
        assert len(set(groups[tr_out]) & set(groups[te_out])) == 0, "PELLET LEAKAGE IN OUTER SPLIT!"
        X_tr_out, y_tr_out, g_tr_out = X_all[tr_out], y_idx[tr_out], groups[tr_out]
        X_te_out, y_te_out = X_all[te_out], y_idx[te_out]

        inner_cv = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=seed + fold_i)
        inner_splits = list(inner_cv.split(X_tr_out, y_tr_out, g_tr_out))

        best_in_acc = -1.0
        best_hp = hp_grid[0]
        best_ep_mean = max_epochs

        for lr, wd in hp_grid:
            in_oof = np.empty_like(y_tr_out)
            ep_list = []
            for in_j, (itr, iva) in enumerate(inner_splits, 1):
                assert len(set(g_tr_out[itr]) & set(g_tr_out[iva])) == 0, "PELLET LEAKAGE IN INNER SPLIT!"
                X_itr_s, X_iva_s = fit_apply_channel_scaler(X_tr_out[itr], X_tr_out[iva])
                p_va, b_ep = train_and_predict(
                    model_name=model_name,
                    X_tr=X_itr_s,
                    y_tr=y_tr_out[itr],
                    X_eval=X_iva_s,
                    n_classes=n_classes,
                    device=device,
                    lr=lr,
                    weight_decay=wd,
                    epochs=max_epochs,
                    batch_size=batch_size,
                    seed=seed + fold_i * 100 + in_j,
                    X_val=X_iva_s,
                    y_val=y_tr_out[iva],
                    patience=max(8, max_epochs // 5),
                )
                in_oof[iva] = p_va
                ep_list.append(b_ep)
            acc_in = accuracy_score(y_tr_out, in_oof)
            if acc_in > best_in_acc:
                best_in_acc = acc_in
                best_hp = (lr, wd)
                best_ep_mean = max(5, int(round(np.mean(ep_list))))

        X_tr_s, X_te_s = fit_apply_channel_scaler(X_tr_out, X_te_out)
        preds_out, _ = train_and_predict(
            model_name=model_name,
            X_tr=X_tr_s,
            y_tr=y_tr_out,
            X_eval=X_te_s,
            n_classes=n_classes,
            device=device,
            lr=best_hp[0],
            weight_decay=best_hp[1],
            epochs=best_ep_mean,
            batch_size=batch_size,
            seed=seed + fold_i * 1000,
        )
        oof_idx[te_out] = preds_out
        fold_accs.append(float(accuracy_score(y_te_out, preds_out) * 100.0))
        chosen_cfgs.append({"lr": best_hp[0], "wd": best_hp[1], "epochs": best_ep_mean})

    oof_str = np.array([classes[i] for i in oof_idx])
    pv = compute_pellet_vote(y_str, oof_str, groups)
    return {
        "scan_acc": round(float(accuracy_score(y_str, oof_str) * 100.0), 2),
        "fold_mean": round(float(np.mean(fold_accs)), 2),
        "fold_sd": round(float(np.std(fold_accs)), 2),
        "macro_prec": round(float(precision_score(y_str, oof_str, average="macro") * 100.0), 2),
        "macro_rec": round(float(recall_score(y_str, oof_str, average="macro") * 100.0), 2),
        "macro_f1": round(float(f1_score(y_str, oof_str, average="macro")), 4),
        "pellet_acc": round(pv["pellet_acc"], 2),
        "pellet_correct": pv["pellet_correct"],
        "pellet_total": pv["pellet_total"],
        "pellet_macro_f1": round(pv["pellet_macro_f1"], 4),
        "fold_accs": [round(x, 2) for x in fold_accs],
        "chosen_cfgs": chosen_cfgs,
        "oof_preds": oof_str.tolist(),
    }


def load_locked_proposed_scores() -> dict:
    if not LOCKED_SUMMARY_PATH.exists():
        return {}
    try:
        data = json.loads(LOCKED_SUMMARY_PATH.read_text(encoding="utf-8"))
        out = {}
        for k, v in data.items():
            if isinstance(v, dict) and "proposed" in v:
                out[k] = {
                    "scan_acc": v["proposed"].get("acc"),
                    "pellet_acc": v["proposed"].get("pellet_acc"),
                }
        return out
    except Exception:
        return {}


# ==============================================================================
# 4. CLI Entry Point with Checkpoint / Resume Support
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Rebuttal Deep Learning Baselines (Pellet-Grouped Double-Nested CV)")
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke",
                        help="'smoke': fast 1-dataset sanity check; 'full': all 3 botanical matrices.")
    parser.add_argument("--input-mode", choices=["raw_dual", "dual_view", "both"], default="raw_dual",
                        help="Track A ('raw_dual', 2x358), Track B ('dual_view', 9x358), or 'both'.")
    parser.add_argument("--models", nargs="+", default=list(MODEL_REGISTRY.keys()),
                        choices=list(MODEL_REGISTRY.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--epochs", type=int, default=None, help="Override max epochs (default: 6 for smoke, 80 for full).")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--force", action="store_true", help="Re-run even if checkpoint JSON already exists.")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print("=" * 88)
    print(f"  THz-TCM REBUTTAL DEEP LEARNING SUITE | mode={args.mode} | device={device} ({gpu_name})")
    print("=" * 88, flush=True)

    datasets = DATASETS[:1] if args.mode == "smoke" else DATASETS
    input_modes = ["raw_dual", "dual_view"] if args.input_mode == "both" else [args.input_mode]
    max_epochs = args.epochs if args.epochs is not None else (6 if args.mode == "smoke" else 80)
    hp_grid = [(1e-3, 1e-4)] if args.mode == "smoke" else [(1e-3, 1e-4), (5e-4, 1e-3), (2e-3, 1e-4)]

    all_records = []
    t_all = time.time()

    for cfg in datasets:
        raw_a, raw_r, y_str, y_idx, groups, _ = load_cached_dataset(cfg)
        print(f"\n>>> Dataset: {cfg['display']} | QC scans={len(y_str)}, pellets={len(np.unique(groups))}", flush=True)

        for im in input_modes:
            X_tensor = build_channel_tensor(raw_a, raw_r, im)
            for m_name in args.models:
                for seed in args.seeds:
                    tag = f"{cfg['key']}__{im}__{m_name}__seed{seed}"
                    ckpt_path = ckpt_dir / f"{tag}.json"

                    if ckpt_path.exists() and not args.force:
                        rec = json.loads(ckpt_path.read_text(encoding="utf-8"))
                        print(f"  [RESUME] {tag}: scan={rec['scan_acc']:.2f}%, pellet={rec['pellet_acc']:.2f}%", flush=True)
                        all_records.append(rec)
                        continue

                    t0 = time.time()
                    res = evaluate_model_nested_cv(
                        model_name=m_name,
                        X_all=X_tensor,
                        y_idx=y_idx,
                        y_str=y_str,
                        groups=groups,
                        classes=cfg["classes"],
                        device=device,
                        seed=seed,
                        max_epochs=max_epochs,
                        batch_size=args.batch_size,
                        hp_grid=hp_grid,
                    )
                    elapsed = round(time.time() - t0, 1)
                    rec = {
                        "dataset": cfg["key"],
                        "display": cfg["display"],
                        "input_mode": im,
                        "model": m_name,
                        "seed": seed,
                        "device": gpu_name,
                        "elapsed_sec": elapsed,
                        **res,
                    }
                    ckpt_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(
                        f"  [DONE]   {tag}: scan={rec['scan_acc']:.2f}% ({rec['fold_mean']:.2f}±{rec['fold_sd']:.2f}%), "
                        f"pellet={rec['pellet_acc']:.2f}% ({rec['pellet_correct']}/{rec['pellet_total']}), "
                        f"F1={rec['macro_f1']:.4f} [{elapsed}s]",
                        flush=True,
                    )
                    all_records.append(rec)

    # Save aggregate JSON + Markdown comparison table
    summary_json = out_dir / f"Rebuttal_DL_Summary_{args.mode}.json"
    summary_json.write_text(json.dumps(all_records, indent=2, ensure_ascii=False), encoding="utf-8")

    locked_prop = load_locked_proposed_scores()
    md = [
        f"# Rebuttal Deep Learning Baselines Summary (`mode={args.mode}`, `device={gpu_name}`)",
        "",
        "| Dataset | Input View | Model | Seed | Scan Acc (%) | Fold Mean ± SD (%) | Macro-F1 | Pellet Vote (%) | Locked Proposed Scan / Pellet (%) | Time (s) |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]
    for r in all_records:
        lp = locked_prop.get(r["dataset"], {})
        lp_str = f"{lp.get('scan_acc', '-')}% / {lp.get('pellet_acc', '-')}%" if lp else "-"
        md.append(
            f"| {r['dataset']} | `{r['input_mode']}` | {r['model']} | {r['seed']} | "
            f"**{r['scan_acc']:.2f}** | {r['fold_mean']:.2f} ± {r['fold_sd']:.2f} | "
            f"{r['macro_f1']:.4f} | **{r['pellet_acc']:.2f}** ({r['pellet_correct']}/{r['pellet_total']}) | "
            f"{lp_str} | {r['elapsed_sec']} |"
        )
    summary_md = out_dir / f"Rebuttal_DL_Summary_{args.mode}.md"
    summary_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n" + "=" * 88)
    print(f"  Completed {len(all_records)} runs in {time.time() - t_all:.1f}s")
    print(f"  Summary JSON: {summary_json}")
    print(f"  Summary MD:   {summary_md}")
    print("=" * 88, flush=True)


if __name__ == "__main__":
    main()

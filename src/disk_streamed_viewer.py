#!/usr/bin/env python3
"""
Disk-Streamed Viewer — Lazy Frame Loading
==========================================

Provides a viewer backend that reads raw microscopy frames directly from
disk on demand, using dask arrays.  This allows browsing arbitrarily
large recordings with constant memory usage.

No Gaussian filtering is applied in this mode (can be added later).

Usage (standalone):
    python disk_streamed_viewer.py /path/to/data_folder

Author: AI Assistant
Date: June 2026
"""

import os
import sys
import glob
import threading
import numpy as np
import dask
import dask.array as da
import xml.etree.ElementTree as ET
from os.path import getsize

from qtpy.QtCore import QObject, Signal

import napari
from skimage.io import imread


# ---------------------------------------------------------------------------
# Shared helpers (duplicated from thorlabs_live_viewer_simple to avoid
# import coupling; could be refactored into a shared module later).
# ---------------------------------------------------------------------------

FILENAME = "Image_001_001.raw"


def parse_experiment_xml(folder):
    """Parse Experiment.xml to extract frame dimensions and rate."""
    xml_path = os.path.join(folder, "Experiment.xml")
    if not os.path.exists(xml_path):
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        lsm = root.find("LSM")
        if lsm is not None:
            width = int(lsm.get("pixelX"))
            height = int(lsm.get("pixelY"))
            frame_rate = float(lsm.get("frameRate", 0))
            return {"width": width, "height": height, "frame_rate": frame_rate}
    except Exception as e:
        print(f"⚠️  Error parsing Experiment.xml: {e}")
    return None


def find_preview_files(folder):
    """Search for all ChanX_Preview.tif files (A, B, C, or D)."""
    pattern = os.path.join(folder, "Chan*_Preview.tif")
    return sorted(glob.glob(pattern))


# ---------------------------------------------------------------------------
# Qt signal helper (emitted from background ROI thread)
# ---------------------------------------------------------------------------

class DiskROIUpdater(QObject):
    """Thread-safe signals for ROI computation progress."""
    progress = Signal(int, int)       # (current_frame, total_frames)
    finished = Signal(dict)           # {roi_name: [values...]}
    cancelled = Signal()


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class DiskStreamedViewer:
    """Lazy, disk-backed viewer for completed raw recordings.

    Frames are read from disk on demand via dask arrays.  Memory usage
    stays constant regardless of recording length.
    """

    def __init__(self, folder, viewer=None, avg_every=1):
        """Initialise the disk-streamed viewer.

        Args:
            folder: Path to the experiment data folder.
            viewer: Optional existing ``napari.Viewer`` instance.
            avg_every: Number of logical frames to average together.
        """
        print("💾 Initializing Disk-Streamed Viewer")

        self.folder = folder
        self.fullpath = os.path.join(folder, FILENAME)
        self.frame_rate = 0.0
        self.avg_every = avg_every

        # --- Detect channels ---
        preview_files = find_preview_files(folder)
        self.num_channels = min(len(preview_files), 2) if preview_files else 1
        self.channel_names = [f"Ch{i + 1}" for i in range(self.num_channels)]

        # --- Frame dimensions ---
        xml_meta = parse_experiment_xml(folder)
        if xml_meta is not None:
            self.width = xml_meta["width"]
            self.height = xml_meta["height"]
            self.frame_rate = xml_meta["frame_rate"]
            print(f"📄 Metadata from Experiment.xml: {self.width}×{self.height}, "
                  f"{self.frame_rate:.1f} fps")
        else:
            if not preview_files:
                raise FileNotFoundError(
                    f"No Experiment.xml or Chan*_Preview.tif in {folder}"
                )
            prev = imread(preview_files[0])
            self.width = prev.shape[1]
            self.height = prev.shape[0]
            print(f"📄 Dimensions from {os.path.basename(preview_files[0])}: "
                  f"{self.width}×{self.height}")

        print(f"📡 Channels: {self.num_channels} ({', '.join(self.channel_names)})")

        # --- Raw file info ---
        if not os.path.exists(self.fullpath):
            raise FileNotFoundError(f"Raw file not found: {self.fullpath}")

        nbytes = getsize(self.fullpath)
        self.frameSize = self.width * self.height * 2  # uint16
        n_raw_total = nbytes // self.frameSize
        n_logical_total = n_raw_total // self.num_channels
        self.nFrames = n_logical_total // self.avg_every

        print(f"📊 {self.width}×{self.height}, {self.nFrames} logical frames "
              f"({nbytes / 1024 / 1024:.1f} MB)")

        # --- Build lazy dask arrays (one per channel) ---
        self.dask_arrays = self._build_dask_arrays()

        # --- Napari viewer ---
        if viewer is not None:
            self.app = viewer
            self.app.title = (f"Disk-Streamed Viewer — "
                              f"{os.path.basename(folder)}")
        else:
            self.app = napari.Viewer(
                title=f"Disk-Streamed Viewer — {os.path.basename(folder)}"
            )

        self.image_layers = {ch: None for ch in self.channel_names}

        # Add shapes layer for annotations if it doesn't exist
        self._setup_napari_layers()

        # ROI background thread control
        self._roi_stop = threading.Event()
        self._roi_thread = None
        self.roi_updater = DiskROIUpdater()

        # Compatibility attributes expected by ThorlabsGUI
        self.monitoring_active = False
        self.currentLastFrame = self.nFrames

        print("✅ Disk-Streamed Viewer ready")

    # Number of logical frames per dask chunk (controls read granularity)
    CHUNK_FRAMES = 400

    def _build_dask_arrays(self):
        """Build one dask array per channel using chunked reads.

        Each dask chunk covers CHUNK_FRAMES logical frames, reading them
        in a single I/O operation and deinterleaving channels.  This is
        far faster for interactive scrolling than per-frame reads.
        """
        chunk = self.CHUNK_FRAMES
        arrays = {ch: [] for ch in self.channel_names}

        for start in range(0, self.nFrames, chunk):
            end = min(start + chunk, self.nFrames)
            n = end - start  # frames in this chunk

            for ch_idx, ch_name in enumerate(self.channel_names):
                d = dask.delayed(self._read_chunk)(start, end, ch_idx)
                arr = da.from_delayed(
                    d, shape=(n, self.height, self.width), dtype=np.uint16
                )
                arrays[ch_name].append(arr)

        result = {}
        for ch_name in self.channel_names:
            if arrays[ch_name]:
                result[ch_name] = da.concatenate(arrays[ch_name], axis=0)
            else:
                result[ch_name] = da.zeros(
                    (0, self.height, self.width), dtype=np.uint16
                )
        return result

    def _read_chunk(self, logical_start, logical_end, channel_index):
        """Read a chunk of deinterleaved frames for one channel.

        logical_start and logical_end are in AVERAGED frame indices.
        Reads all raw frames in a single I/O call, then extracts and averages.
        """
        raw_logical_start = logical_start * self.avg_every
        raw_logical_end = logical_end * self.avg_every

        n_logical = raw_logical_end - raw_logical_start
        n_raw = n_logical * self.num_channels
        raw_start = raw_logical_start * self.num_channels
        offset = raw_start * self.frameSize

        with open(self.fullpath, "rb") as f:
            f.seek(offset)
            buf = f.read(n_raw * self.frameSize)

        all_frames = np.frombuffer(buf, dtype=np.uint16).reshape(
            (n_logical, self.num_channels, self.height, self.width)
        )
        
        # Select channel
        ch_frames = all_frames[:, channel_index, :, :]
        
        if self.avg_every > 1:
            n_avg = ch_frames.shape[0] // self.avg_every
            ch_frames = ch_frames.reshape(n_avg, self.avg_every, self.height, self.width).mean(axis=1).astype(np.uint16)
            
        return ch_frames

    # ------------------------------------------------------------------
    # Single-frame and range readers (for snapshot, ROI, etc.)
    # ------------------------------------------------------------------

    def read_frame(self, logical_index, channel_index=0):
        """Read one averaged logical frame for a given channel."""
        return self._read_chunk(logical_index, logical_index + 1, channel_index)[0]

    def read_frames_range(self, start, end, channel_index=0):
        """Read a contiguous range of averaged logical frames for one channel."""
        return self._read_chunk(start, end, channel_index)

    # ------------------------------------------------------------------
    # Smart ROI extraction
    # ------------------------------------------------------------------

    def read_roi_values(self, channel_index, roi_pixel_coords,
                        frame_start=0, frame_end=None,
                        progress_callback=None, stop_event=None):
        """Read mean intensity of an ROI across frames using byte-level reads.

        For small ROIs (< 20 % of frame area) this reads only the ROI
        pixels from disk.  For large ROIs it falls back to reading full
        frames and masking.

        Args:
            channel_index:    0-based channel.
            roi_pixel_coords: Sequence of (row, col) tuples, *or* a 2-D
                              boolean mask of shape (H, W).
            frame_start:      First logical frame (inclusive, default 0).
            frame_end:        Last logical frame (exclusive, default nFrames).
            progress_callback: Optional ``callable(current, total)``.
            stop_event:       Optional ``threading.Event`` — if set, abort.

        Returns:
            1-D np.ndarray of float64 mean intensities, length
            ``frame_end - frame_start``.
        """
        if frame_end is None:
            frame_end = self.nFrames

        n_frames = frame_end - frame_start

        # Normalise roi_pixel_coords → list of (row, col)
        if isinstance(roi_pixel_coords, np.ndarray) and roi_pixel_coords.dtype == bool:
            rows, cols = np.where(roi_pixel_coords)
            pixel_coords = list(zip(rows.tolist(), cols.tolist()))
        else:
            pixel_coords = list(roi_pixel_coords)

        n_pixels = len(pixel_coords)
        if n_pixels == 0:
            return np.zeros(n_frames, dtype=np.float64)

        frame_area = self.width * self.height
        use_smart = n_pixels < int(0.20 * frame_area)

        means = np.empty(n_frames, dtype=np.float64)

        if use_smart:
            # Pre-compute byte offsets within a single raw frame
            # Each pixel is 2 bytes (uint16), stored row-major
            intra_offsets = np.array(
                [(r * self.width + c) * 2 for r, c in pixel_coords],
                dtype=np.int64,
            )
            # Sort offsets to enable sequential reads / coalescing
            intra_offsets.sort()

            # Coalesce contiguous byte ranges for efficiency
            read_ranges = self._coalesce_offsets(intra_offsets)

            with open(self.fullpath, "rb") as f:
                for i, logical_idx in enumerate(range(frame_start, frame_end)):
                    if stop_event and stop_event.is_set():
                        return means[:i]

                    raw_logical_start = logical_idx * self.avg_every
                    
                    frame_sum = 0.0
                    for avg_i in range(self.avg_every):
                        raw_idx = (raw_logical_start + avg_i) * self.num_channels + channel_index
                        frame_base = raw_idx * self.frameSize

                        # Read coalesced ranges and extract pixel values
                        values = np.empty(n_pixels, dtype=np.uint16)
                        pixel_idx = 0
                        for r_start, r_end in read_ranges:
                            f.seek(frame_base + r_start)
                            chunk = f.read(r_end - r_start)
                            
                            # Convert chunk to uint16
                            arr = np.frombuffer(chunk, dtype=np.uint16)
                            n_arr = len(arr)
                            values[pixel_idx : pixel_idx + n_arr] = arr
                            pixel_idx += n_arr

                        frame_sum += np.mean(values[:pixel_idx])
                    
                    means[i] = frame_sum / self.avg_every

                    if progress_callback and i % 200 == 0:
                        progress_callback(i, n_frames)

        else:
            # Fallback: read full frames and mask
            if isinstance(roi_pixel_coords, np.ndarray) and roi_pixel_coords.dtype == bool:
                mask = roi_pixel_coords
            else:
                mask = np.zeros((self.height, self.width), dtype=bool)
                for r, c in pixel_coords:
                    mask[r, c] = True

            with open(self.fullpath, "rb") as f:
                for i, logical_idx in enumerate(range(frame_start, frame_end)):
                    if stop_event and stop_event.is_set():
                        return means[:i]

                    raw_logical_start = logical_idx * self.avg_every
                    offset = raw_logical_start * self.num_channels * self.frameSize
                    n_raw_to_read = self.avg_every * self.num_channels
                    
                    f.seek(offset)
                    buf = f.read(n_raw_to_read * self.frameSize)
                    all_frames = np.frombuffer(buf, dtype=np.uint16).reshape(
                        (self.avg_every, self.num_channels, self.height, self.width)
                    )
                    
                    ch_frames = all_frames[:, channel_index, :, :]
                    if self.avg_every > 1:
                        frame = ch_frames.mean(axis=0)
                    else:
                        frame = ch_frames[0]
                    
                    means[i] = np.mean(frame[mask])

                    if progress_callback and i % 200 == 0:
                        progress_callback(i, n_frames)

        if progress_callback:
            progress_callback(n_frames, n_frames)

        return means

    @staticmethod
    def _coalesce_offsets(sorted_offsets, gap_threshold=64):
        """Merge sorted byte offsets into contiguous read ranges.

        Two offsets are merged if the gap between the end of one 2-byte
        read and the start of the next is ≤ *gap_threshold* bytes.

        Returns:
            List of (start_byte, end_byte) tuples (end exclusive).
        """
        if len(sorted_offsets) == 0:
            return []

        ranges = []
        rng_start = int(sorted_offsets[0])
        rng_end = rng_start + 2  # one uint16

        for off in sorted_offsets[1:]:
            off = int(off)
            if off <= rng_end + gap_threshold:
                rng_end = off + 2
            else:
                ranges.append((rng_start, rng_end))
                rng_start = off
                rng_end = off + 2

        ranges.append((rng_start, rng_end))
        return ranges

    # ------------------------------------------------------------------
    # Background-threaded ROI computation
    # ------------------------------------------------------------------

    def compute_roi_traces_async(self, channel_index, roi_masks,
                                 roi_names, finished_callback=None):
        """Compute ROI traces in a background thread.

        Reads each frame **once** and computes all ROI means from it,
        so total I/O is N_frames (not N_rois × N_frames).

        Args:
            channel_index:    0-based channel.
            roi_masks:        List of boolean masks (H, W).
            roi_names:        Corresponding ROI names.
            finished_callback: Optional extra callback(dict) on completion.

        The results are also emitted via ``self.roi_updater.finished``.
        """
        self.cancel_roi_computation()  # stop any previous run

        self._roi_stop.clear()

        def _worker():
            total = self.nFrames
            n_rois = len(roi_masks)

            # Ensure all masks are boolean numpy arrays
            bool_masks = []
            for m in roi_masks:
                if isinstance(m, np.ndarray) and m.dtype == bool:
                    bool_masks.append(m)
                else:
                    mask = np.zeros((self.height, self.width), dtype=bool)
                    for r, c in m:
                        mask[r, c] = True
                    bool_masks.append(mask)

            # Pre-allocate result arrays
            traces = {name: np.empty(total, dtype=np.float64)
                      for name in roi_names}

            # Single pass: read each averaged frame once, compute all ROIs
            with open(self.fullpath, "rb") as f:
                for i in range(total):
                    if self._roi_stop.is_set():
                        self.roi_updater.cancelled.emit()
                        return

                    raw_logical_start = i * self.avg_every
                    offset = raw_logical_start * self.num_channels * self.frameSize
                    n_raw_to_read = self.avg_every * self.num_channels
                    
                    f.seek(offset)
                    buf = f.read(n_raw_to_read * self.frameSize)
                    all_frames = np.frombuffer(buf, dtype=np.uint16).reshape(
                        (self.avg_every, self.num_channels, self.height, self.width)
                    )
                    
                    ch_frames = all_frames[:, channel_index, :, :]
                    if self.avg_every > 1:
                        frame = ch_frames.mean(axis=0)
                    else:
                        frame = ch_frames[0]

                    for mask, name in zip(bool_masks, roi_names):
                        traces[name][i] = np.mean(frame[mask])

                    if i % 200 == 0:
                        self.roi_updater.progress.emit(i, total)

            self.roi_updater.progress.emit(total, total)

            result = {name: vals.tolist() for name, vals in traces.items()}
            self.roi_updater.finished.emit(result)
            if finished_callback:
                finished_callback(result)

        self._roi_thread = threading.Thread(target=_worker, daemon=True)
        self._roi_thread.start()

    def cancel_roi_computation(self):
        """Cancel any running background ROI computation."""
        if self._roi_thread is not None and self._roi_thread.is_alive():
            self._roi_stop.set()
            self._roi_thread.join(timeout=3)
            self._roi_thread = None

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def add_to_viewer(self):
        """Add dask arrays as Napari image layers."""
        _ch_colormaps = {"Ch1": "green", "Ch2": "red"}
        for ch_name, darr in self.dask_arrays.items():
            cmap = _ch_colormaps.get(ch_name, "gray")

            # Check if layer already exists
            existing = None
            for layer in self.app.layers:
                if layer.name == ch_name:
                    existing = layer
                    break

            if existing is not None:
                existing.data = darr
            else:
                self.image_layers[ch_name] = self.app.add_image(
                    darr, name=ch_name,
                    colormap=cmap, blending="additive",
                )

    def _setup_napari_layers(self):
        """Add the Annotations shapes layer if it doesn't exist."""
        try:
            exists = any(l.name == "Annotations" for l in self.app.layers)
            if not exists:
                self.app.add_shapes(
                    None, shape_type="rectangle", name="Annotations",
                    edge_width=3,
                    face_color=np.array([0, 0, 0, 0]),
                    edge_color="red",
                )
        except Exception as e:
            print(f"⚠️  Could not setup shapes layer: {e}")

    # ------------------------------------------------------------------
    # Compatibility stubs
    # ------------------------------------------------------------------

    def get_status(self):
        """Return status dict compatible with ThorlabsGUI.refresh_status."""
        return {
            "active": False,
            "frames_loaded": self.nFrames,
            "total_frames": self.nFrames,
            "remaining": 0,
        }

    def stop_monitoring(self):
        """No-op (no background monitoring in disk-stream mode)."""
        self.cancel_roi_computation()

    def close(self):
        """Clean up resources."""
        self.cancel_roi_computation()
        print("✅ Disk-Streamed Viewer closed")


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Disk-Streamed Viewer")
    parser.add_argument("folder", help="Path to data folder")
    args = parser.parse_args()

    viewer = DiskStreamedViewer(args.folder)
    viewer.add_to_viewer()
    napari.run()


if __name__ == "__main__":
    main()

"""Fix the angular velocity bug in existing recordings.

Recomputes world_angular_vel from root quaternion finite differences,
replacing the buggy values that were ~8-12x too small.
"""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
from glob import glob
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--recordings", type=str, default="recordings")
args = parser.parse_args()

files = sorted(glob(f"{args.recordings}/*.json"))
print(f"Fixing angular velocity in {len(files)} recordings...")

for filepath in files:
    with open(filepath) as f:
        data = json.load(f)

    frames = data["Frames"]
    offsets = data["Frame_offset"][0]
    quat_start = offsets["root_quat"]
    wav_start = offsets["world_angular_vel"]
    fps = data["FPS"]
    dt = 1.0 / fps

    for i in range(len(frames)):
        if i == 0:
            prev_quat = frames[i][quat_start:quat_start + 4]
        else:
            prev_quat = frames[i - 1][quat_start:quat_start + 4]

        curr_quat = frames[i][quat_start:quat_start + 4]

        r0 = R.from_quat(prev_quat)
        r1 = R.from_quat(curr_quat)
        r_rel = r0.inv() * r1
        ang_vel = r_rel.as_rotvec() / dt

        frames[i][wav_start] = float(ang_vel[0])
        frames[i][wav_start + 1] = float(ang_vel[1])
        frames[i][wav_start + 2] = float(ang_vel[2])

    # Also fix the Yaw metadata
    skip_frames = int(2.0 * fps)
    yaw_vels = [frames[i][wav_start + 2] for i in range(skip_frames, len(frames))]
    data["Yaw"] = float(np.mean(yaw_vels))

    with open(filepath, "w") as f:
        json.dump(data, f)

    basename = os.path.basename(filepath)
    if "0.0_0.0_1.037" in basename or "0.0_0.0_0.0" in basename:
        print(f"  {basename}: Yaw={data['Yaw']:.4f} rad/s")

print("Done.")

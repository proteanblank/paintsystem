# .github/make-tests-matrix.py
import json
import re
from urllib import request

# --- Verified Blender Versions to Test ---
# These URLs point to the latest stable patch releases for each version.

jobs = [
    # -- LTS Releases --
    {
        "version": "3.3.18",  # Latest LTS
        "version_x_y": "3.3",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender3.3/blender-3.3.18-linux-x64.tar.xz",
    },
    {
        "version": "3.6.11",  # Latest LTS
        "version_x_y": "3.6",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender3.6/blender-3.6.11-linux-x64.tar.xz",
    },
    # -- Stable Releases --
    {
        "version": "4.1.1",
        "version_x_y": "4.1",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz",
    },
    {
        # Corrected URL for the latest official Blender 4.2 release
        "version": "4.2.0",
        "version_x_y": "4.2",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender4.2/blender-4.2.0-linux-x64.tar.xz",
    },
]


def get_daily_builds(jobs: list):
    """Fetches the latest daily builds and adds them to the jobs list."""
    try:
        resp = request.urlopen("https://builder.blender.org/download/daily/")
        page = resp.read().decode("utf-8")
        releases = re.findall(
            r"(https://cdn.builder.blender.org/download/daily/blender-(((?:4|5)\.\d)\.\d-\w+)\+\S{1,6}\.(\S{12})-linux\.x86_64-release\.tar\.xz)",
            page,
        )

        daily_builds = {}
        for release in releases:
            version_x_y = release[2]
            new_job = {
                "version": release[1],
                "version_x_y": version_x_y,
                "download_url": release[0],
                "sha": release[3],
            }
            if version_x_y not in daily_builds:
                daily_builds[version_x_y] = new_job

        for job in daily_builds.values():
             if job["version"].removesuffix("-stable") not in [j["version"] for j in jobs]:
                jobs.append(job)
        print("Successfully added daily builds to the test matrix.")

    except Exception as e:
        print(f"Warning: Could not fetch daily builds: {e}")


get_daily_builds(jobs)

matrix = {"include": jobs}
print(f"matrix={json.dumps(matrix)}")
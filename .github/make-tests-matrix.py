# .github/make-tests-matrix.py
import json
import re
from urllib import request

# --- Blender Versions to Test ---
# You can customize this list with the specific Blender versions you want to support.
# It's a good practice to include recent stable releases, Long-Term Support (LTS) versions,
# and potentially the latest daily build to catch issues with upcoming changes.

jobs = [
    # -- LTS Releases --
    {
        "version": "3.3.18",  # LTS
        "version_x_y": "3.3",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender3.3/blender-3.3.18-linux-x64.tar.xz",
    },
    {
        "version": "3.6.8",  # LTS
        "version_x_y": "3.6",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender3.6/blender-3.6.8-linux-x64.tar.xz",
    },
    # -- Stable Releases --
    {
        "version": "4.1.1",
        "version_x_y": "4.1",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender4.1/blender-4.1.1-linux-x64.tar.xz",
    },
    {
        "version": "4.2.0",
        "version_x_y": "4.2",
        "sha": "released",
        "download_url": "https://download.blender.org/release/Blender4.2/blender-4.2-stable+v42.0.25a078b17b2e-linux.x86_64-release.tar.xz",
    },
]


def get_daily_builds(jobs: list):
    """Fetches the latest daily builds and adds them to the jobs list."""
    try:
        # The official source for daily build information
        resp = request.urlopen("https://builder.blender.org/download/daily/")
        page = resp.read().decode("utf-8")

        # Regex to find Blender 4.x and 5.x daily builds for Linux
        releases = re.findall(
            r"(https://cdn.builder.blender.org/download/daily/blender-(((?:4|5)\.\d)\.\d-\w+)\+\S{1,6}\.(\S{12})-linux\.x86_64-release\.tar\.xz)",
            page,
        )

        daily_builds = {}
        for release in releases:
            # Keep only the latest daily build for each minor version (e.g., 4.3, 4.4)
            version_x_y = release[2]
            new_job = {
                "version": release[1],
                "version_x_y": version_x_y,
                "download_url": release[0],
                "sha": release[3],
            }
            # Only add if it's a newer build for that version
            if version_x_y not in daily_builds:
                daily_builds[version_x_y] = new_job

        # Add the collected latest daily builds to the main jobs list
        for job in daily_builds.values():
             if job["version"].removesuffix("-stable") not in [j["version"] for j in jobs]:
                jobs.append(job)

    except Exception as e:
        print(f"Could not fetch daily builds: {e}")


# Fetch and add daily builds to our list
get_daily_builds(jobs)

# The output must be a JSON string in a specific format for GitHub Actions
matrix = {"include": jobs}
print(f"matrix={json.dumps(matrix)}")
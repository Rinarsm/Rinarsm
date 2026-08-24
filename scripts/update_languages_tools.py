#!/usr/bin/env python3

import base64
import json
import os
import pathlib
import re
import urllib.request
import urllib.error

# =========================================================
# CONFIG
# =========================================================

USERNAME = os.environ.get("GITHUB_USERNAME", "Rinarsm")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

README_PATH = pathlib.Path("README.md")

START_MARKER = "<!-- LANGUAGES_TOOLS_START -->"
END_MARKER = "<!-- LANGUAGES_TOOLS_END -->"

# =========================================================
# TOOL DEFINITIONS
# =========================================================

TOOLS = {
    "python": {
        "name": "Python",
        "category": "AI / Machine Learning",
        "order": 1,
        "skill_icon": "py",
        "badge": "https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white",
    },
    "tensorflow": {
        "name": "TensorFlow",
        "category": "AI / Machine Learning",
        "order": 2,
        "skill_icon": "tensorflow",
        "badge": "https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white",
    },
    "sklearn": {
        "name": "Scikit--Learn",
        "category": "AI / Machine Learning",
        "order": 3,
        "skill_icon": "sklearn",
        "badge": "https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white",
    },
    "pytorch": {
        "name": "PyTorch",
        "category": "AI / Machine Learning",
        "order": 4,
        "skill_icon": "pytorch",
        "badge": "https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white",
    },

    "jupyter": {
        "name": "Jupyter",
        "category": "Data & Notebook",
        "order": 1,
        "skill_icon": None,
        "badge": "https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white",
    },
    "colab": {
        "name": "Google Colab",
        "category": "Data & Notebook",
        "order": 2,
        "skill_icon": None,
        "badge": "https://img.shields.io/badge/Google%20Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white",
    },
    "pandas": {
        "name": "Pandas",
        "category": "Data & Notebook",
        "order": 3,
        "skill_icon": None,
        "badge": "https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white",
    },
    "numpy": {
        "name": "NumPy",
        "category": "Data & Notebook",
        "order": 4,
        "skill_icon": None,
        "badge": "https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white",
    },

    "git": {
        "name": "Git",
        "category": "Development Tools",
        "order": 1,
        "skill_icon": "git",
        "badge": "https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white",
    },
    "github": {
        "name": "GitHub",
        "category": "Development Tools",
        "order": 2,
        "skill_icon": "github",
        "badge": "https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white",
    },
    "vscode": {
        "name": "VS%20Code",
        "category": "Development Tools",
        "order": 3,
        "skill_icon": "vscode",
        "badge": "https://img.shields.io/badge/VS%20Code-007ACC?style=for-the-badge&logo=visualstudiocode&logoColor=white",
    },
}

CATEGORY_ORDER = [
    "AI / Machine Learning",
    "Data & Notebook",
    "Development Tools",
]

DEPENDENCY_FILENAMES = {
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "pipfile",
    "environment.yml",
    "environment.yaml",
}

NOTEBOOK_LIMIT = 8
TEXT_FILE_LIMIT = 30


# =========================================================
# HTTP HELPERS
# =========================================================

def github_get_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "rina-languages-tools-generator",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def github_paginate(url):
    results = []
    page = 1

    while True:
        separator = "&" if "?" in url else "?"
        paged_url = f"{url}{separator}per_page=100&page={page}"

        data = github_get_json(paged_url)
        if not data:
            break

        results.extend(data)

        if len(data) < 100:
            break

        page += 1

    return results


# =========================================================
# GITHUB REPO ACCESS
# =========================================================

def get_repositories():
    repos = github_paginate(
        f"https://api.github.com/users/{USERNAME}/repos?type=owner&sort=updated"
    )

    result = []
    for repo in repos:
        if repo.get("archived"):
            continue
        if repo.get("fork"):
            continue
        result.append(repo)

    return result


def get_repo_tree(owner, repo_name, default_branch):
    url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{default_branch}?recursive=1"
    try:
        data = github_get_json(url)
        tree = data.get("tree", [])
        return [item["path"] for item in tree if item.get("type") == "blob"]
    except urllib.error.HTTPError:
        return []


def get_file_content(owner, repo_name, path, ref):
    encoded_path = urllib.parse.quote(path)
    url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{encoded_path}?ref={ref}"

    try:
        data = github_get_json(url)
    except urllib.error.HTTPError:
        return ""

    if isinstance(data, dict) and data.get("encoding") == "base64" and data.get("content"):
        try:
            raw = base64.b64decode(data["content"])
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    return ""


# =========================================================
# DETECTION
# =========================================================

def detect_tools():
    detected = set()
    repos = get_repositories()

    if repos:
        detected.add("git")
        detected.add("github")

    for repo in repos:
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")
        primary_language = (repo.get("language") or "").lower()

        paths = get_repo_tree(owner, repo_name, default_branch)
        lower_paths = [p.lower() for p in paths]

        # Basic file-based detection
        if primary_language == "python" or any(p.endswith(".py") for p in lower_paths):
            detected.add("python")

        if any(p.endswith(".ipynb") for p in lower_paths):
            detected.add("jupyter")

        if any(".vscode/" in p or p.startswith(".vscode/") for p in lower_paths):
            detected.add("vscode")

        # Candidate files to inspect
        dependency_files = []
        notebook_files = []

        for path in paths:
            lower = path.lower()
            filename = lower.split("/")[-1]

            if filename in DEPENDENCY_FILENAMES:
                dependency_files.append(path)

            if lower.endswith(".ipynb"):
                notebook_files.append(path)

        # Limit requests
        dependency_files = dependency_files[:TEXT_FILE_LIMIT]
        notebook_files = notebook_files[:NOTEBOOK_LIMIT]

        # Read dependency files
        dependency_texts = []
        for dep_path in dependency_files:
            content = get_file_content(owner, repo_name, dep_path, default_branch)
            if content:
                dependency_texts.append(content.lower())

        all_dependency_text = "\n".join(dependency_texts)

        # Library detection from dependency files
        if re.search(r"\btensorflow\b", all_dependency_text):
            detected.add("tensorflow")

        if re.search(r"\bscikit-learn\b|\bsklearn\b", all_dependency_text):
            detected.add("sklearn")

        if re.search(r"\btorch\b|\bpytorch\b", all_dependency_text):
            detected.add("pytorch")

        if re.search(r"\bpandas\b", all_dependency_text):
            detected.add("pandas")

        if re.search(r"\bnumpy\b", all_dependency_text):
            detected.add("numpy")

        # Notebook content detection
        for nb_path in notebook_files:
            nb_content = get_file_content(owner, repo_name, nb_path, default_branch).lower()

            if not nb_content:
                continue

            if "colab" in nb_content or "colab.research.google.com" in nb_content:
                detected.add("colab")

            if "import pandas" in nb_content or "from pandas" in nb_content:
                detected.add("pandas")

            if "import numpy" in nb_content or "from numpy" in nb_content:
                detected.add("numpy")

            if "import tensorflow" in nb_content or "from tensorflow" in nb_content:
                detected.add("tensorflow")

            if "import sklearn" in nb_content or "from sklearn" in nb_content:
                detected.add("sklearn")

            if "import torch" in nb_content or "from torch" in nb_content:
                detected.add("pytorch")

        # Extra fallback based on path names
        if any("colab" in p for p in lower_paths):
            detected.add("colab")

    return detected


# =========================================================
# RENDER README SECTION
# =========================================================

def generate_section(detected_tools):
    categories = {category: [] for category in CATEGORY_ORDER}

    for tool_key in detected_tools:
        tool = TOOLS.get(tool_key)
        if not tool:
            continue
        categories[tool["category"]].append(tool_key)

    lines = []
    lines.append("## 🛠️ Languages & Tools")
    lines.append("")
    lines.append('<div align="center">')
    lines.append("")

    for category in CATEGORY_ORDER:
        tools_in_category = categories[category]
        if not tools_in_category:
            continue

        tools_in_category = sorted(
            tools_in_category,
            key=lambda key: TOOLS[key]["order"]
        )

        lines.append(f"### {category}")
        lines.append("")

        # skill icons row (only if available)
        icon_keys = [TOOLS[key]["skill_icon"] for key in tools_in_category if TOOLS[key]["skill_icon"]]
        if icon_keys:
            icon_string = ",".join(icon_keys)
            lines.append(f'<img src="https://skillicons.dev/icons?i={icon_string}&theme=dark" />')
            lines.append("")
            lines.append("<br><br>")

        # badge row
        for key in tools_in_category:
            badge_url = TOOLS[key]["badge"]
            lines.append(f'<img src="{badge_url}"/>')

        lines.append("")
        lines.append("<br><br>")
        lines.append("")

    lines.append("</div>")
    return "\n".join(lines).strip()


def update_readme(section_text):
    if not README_PATH.exists():
        raise FileNotFoundError("README.md tidak ditemukan.")

    content = README_PATH.read_text(encoding="utf-8")

    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError(
            "Marker LANGUAGES_TOOLS tidak ditemukan di README.md.\n"
            "Tambahkan:\n"
            "<!-- LANGUAGES_TOOLS_START -->\n"
            "<!-- LANGUAGES_TOOLS_END -->"
        )

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL
    )

    replacement = f"{START_MARKER}\n{section_text}\n{END_MARKER}"
    updated = pattern.sub(replacement, content)

    README_PATH.write_text(updated, encoding="utf-8")


# =========================================================
# MAIN
# =========================================================

def main():
    print(f"Mendeteksi tools dari repo milik {USERNAME}...")
    detected_tools = detect_tools()

    print("Tools terdeteksi:")
    for item in sorted(detected_tools):
        print("-", item)

    section_text = generate_section(detected_tools)
    update_readme(section_text)

    print("README.md berhasil diperbarui.")


if __name__ == "__main__":
    main()

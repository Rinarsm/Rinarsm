#!/usr/bin/env python3

import json
import math
import os
import pathlib
import urllib.request

# =========================================================
# CONFIG
# =========================================================

USERNAME = os.environ.get("GITHUB_USERNAME", "Rinarsm")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

OUTPUT_DIR = pathlib.Path("assets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Warna kartu
CARD_BG = "#141321"
RING_BG = "#252237"

# Warna teks
TITLE_COLOR = "#A855F7"
TEXT_COLOR = "#03D8F3"
PERCENT_COLOR = "#C4B5FD"

# Palet donut ungu tua -> ungu muda
PURPLE_PALETTE = [
    "#6D28D9",
    "#7C3AED",
    "#8B5CF6",
    "#A855F7",
    "#C084FC",
]

CARD_WIDTH = 420
CARD_HEIGHT = 180


# =========================================================
# HELPERS
# =========================================================

def svg_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "rina-language-donut-generator",
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

        data = github_get(paged_url)

        if not data:
            break

        results.extend(data)

        if len(data) < 100:
            break

        page += 1

    return results


# =========================================================
# GITHUB DATA
# =========================================================

def get_repositories():
    repos = github_paginate(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?type=owner&sort=updated"
    )

    result = []

    for repo in repos:
        if repo.get("fork"):
            continue

        if repo.get("archived"):
            continue

        result.append(repo)

    return result


def get_repository_languages(languages_url):
    data = github_get(languages_url)

    return {
        language: float(bytes_count)
        for language, bytes_count in data.items()
        if bytes_count > 0
    }


def get_user_contributions(owner, repository):
    contributors = github_paginate(
        f"https://api.github.com/repos/{owner}/{repository}/contributors?anon=1"
    )

    for contributor in contributors:
        if contributor.get("login", "").lower() == USERNAME.lower():
            return int(contributor.get("contributions", 0))

    return 0


# =========================================================
# LANGUAGE CALCULATION
# =========================================================

def calculate_repo_languages(repositories):
    totals = {}

    for repo in repositories:
        languages = get_repository_languages(repo["languages_url"])

        for language, amount in languages.items():
            totals[language] = totals.get(language, 0) + amount

    return totals


def calculate_commit_languages(repositories):
    totals = {}

    for repo in repositories:
        languages = get_repository_languages(repo["languages_url"])

        if not languages:
            continue

        language_total = sum(languages.values())

        if language_total <= 0:
            continue

        contributions = get_user_contributions(
            repo["owner"]["login"],
            repo["name"],
        )

        if contributions <= 0:
            continue

        for language, amount in languages.items():
            language_ratio = amount / language_total

            totals[language] = (
                totals.get(language, 0)
                + (language_ratio * contributions)
            )

    return totals


# =========================================================
# SVG DONUT
# =========================================================

def create_donut_segments(items, cx, cy, radius, stroke_width):
    total = sum(value for _, value, _ in items)

    if total <= 0:
        return ""

    circumference = 2 * math.pi * radius
    offset = 0

    result = []

    for language, value, color in items:
        ratio = value / total

        dash_length = circumference * ratio
        gap_length = circumference - dash_length

        result.append(
            f"""
  <circle
    cx="{cx}"
    cy="{cy}"
    r="{radius}"
    fill="none"
    stroke="{color}"
    stroke-width="{stroke_width}"
    stroke-dasharray="{dash_length:.2f} {gap_length:.2f}"
    stroke-dashoffset="{-offset:.2f}"
    transform="rotate(-90 {cx} {cy})"
  />"""
        )

        offset += dash_length

    return "\n".join(result)


# =========================================================
# SVG CARD
# =========================================================

def create_card(title, language_data, output_file):
    top_languages = sorted(
        language_data.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]

    if not top_languages:
        empty_svg = f"""
<svg
  width="{CARD_WIDTH}"
  height="{CARD_HEIGHT}"
  viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}"
  xmlns="http://www.w3.org/2000/svg"
>
  <rect
    width="{CARD_WIDTH}"
    height="{CARD_HEIGHT}"
    rx="8"
    fill="{CARD_BG}"
  />

  <text
    x="18"
    y="30"
    fill="{TITLE_COLOR}"
    font-family="Segoe UI, Arial, sans-serif"
    font-size="17"
  >
    {svg_escape(title)}
  </text>

  <text
    x="18"
    y="65"
    fill="{TEXT_COLOR}"
    font-family="Segoe UI, Arial, sans-serif"
    font-size="12"
  >
    No language data found
  </text>
</svg>
"""

        output_file.write_text(empty_svg, encoding="utf-8")
        return

    total_top = sum(value for _, value in top_languages)

    colored_languages = []

    for index, (language, value) in enumerate(top_languages):
        colored_languages.append(
            (
                language,
                value,
                PURPLE_PALETTE[index % len(PURPLE_PALETTE)],
            )
        )

    # Legend
    legend = []

    start_y = 55
    gap = 21

    for index, (language, value, color) in enumerate(colored_languages):
        y = start_y + (index * gap)

        percentage = (
            value / total_top * 100
            if total_top > 0
            else 0
        )

        legend.append(
            f"""
  <rect
    x="22"
    y="{y - 9}"
    width="10"
    height="10"
    rx="2"
    fill="{color}"
  />

  <text
    x="40"
    y="{y}"
    fill="{TEXT_COLOR}"
    font-family="Segoe UI, Arial, sans-serif"
    font-size="11"
  >
    {svg_escape(language)}
  </text>

  <text
    x="190"
    y="{y}"
    text-anchor="end"
    fill="{PERCENT_COLOR}"
    font-family="Segoe UI, Arial, sans-serif"
    font-size="10"
  >
    {percentage:.1f}%
  </text>
"""
        )

    donut = create_donut_segments(
        colored_languages,
        cx=315,
        cy=95,
        radius=43,
        stroke_width=18,
    )

    svg = f"""
<svg
  width="{CARD_WIDTH}"
  height="{CARD_HEIGHT}"
  viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}"
  xmlns="http://www.w3.org/2000/svg"
  role="img"
  aria-label="{svg_escape(title)}"
>

  <!-- Background -->
  <rect
    width="{CARD_WIDTH}"
    height="{CARD_HEIGHT}"
    rx="8"
    fill="{CARD_BG}"
  />

  <!-- Title -->
  <text
    x="18"
    y="30"
    fill="{TITLE_COLOR}"
    font-family="Segoe UI, Arial, sans-serif"
    font-size="17"
  >
    {svg_escape(title)}
  </text>

  <!-- Legend -->
  {''.join(legend)}

  <!-- Donut background -->
  <circle
    cx="315"
    cy="95"
    r="43"
    fill="none"
    stroke="{RING_BG}"
    stroke-width="18"
  />

  <!-- Donut -->
  {donut}

</svg>
"""

    output_file.write_text(svg, encoding="utf-8")


# =========================================================
# MAIN
# =========================================================

def main():
    print(f"Getting repositories for {USERNAME}...")

    repositories = get_repositories()

    print(f"Found {len(repositories)} repositories.")

    print("Calculating repository languages...")
    repo_languages = calculate_repo_languages(repositories)

    print("Calculating contribution-weighted languages...")
    commit_languages = calculate_commit_languages(repositories)

    create_card(
        "Top Languages by Repo",
        repo_languages,
        OUTPUT_DIR / "top-languages-repo.svg",
    )

    create_card(
        "Top Languages by Commit",
        commit_languages,
        OUTPUT_DIR / "top-languages-commit.svg",
    )

    print("Done.")
    print("Generated:")
    print("assets/top-languages-repo.svg")
    print("assets/top-languages-commit.svg")


if __name__ == "__main__":
    main()

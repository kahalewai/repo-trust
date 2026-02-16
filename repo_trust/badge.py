"""
Badge generation module for Repo Trust.

Generates an SVG badge that directs users to the verified download page.
The badge is a navigation link, not a verification indicator — the security
comes from the destination (GitHub Pages), not the badge itself.
"""

import os


def render_badge(repo_name=None):
    """
    Render a Repo Trust badge as SVG.

    This badge directs users to the verified download page on
    the maintainer's GitHub Pages domain.
    """
    if repo_name is None:
        repo_name = os.environ.get("GITHUB_REPOSITORY", "")

    label = "Repo Trust"
    action = "Verified Downloads"

    char_width = 7
    padding = 14

    label_width = int(len(label) * char_width + padding)
    action_width = int(len(action) * char_width + padding)
    total_width = label_width + action_width
    height = 24

    label_x = label_width / 2
    action_x = label_width + action_width / 2

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="{label}: {action}">
  <title>Repo Trust - Download from verified page</title>
  <defs>
    <linearGradient id="bg" x2="0" y2="100%">
      <stop offset="0" stop-color="#34d058"/>
      <stop offset="1" stop-color="#22863a"/>
    </linearGradient>
  </defs>
  <clipPath id="r">
    <rect width="{total_width}" height="{height}" rx="4" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="{height}" fill="#555"/>
    <rect x="{label_width}" width="{action_width}" height="{height}" fill="url(#bg)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="12" font-weight="600">
    <text x="{label_x}" y="16">🔒 {label}</text>
    <text x="{action_x}" y="16">{action}</text>
  </g>
  <rect width="{total_width}" height="{height}" rx="4" fill="none" stroke="#1b1f23" stroke-opacity="0.1"/>
</svg>'''

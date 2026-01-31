"""
Badge generation module for Repo Trust.

Generates SVG badges that prompt users to click for verification.
The badge is designed as a "Click to Verify" action button rather than
a static trust indicator, because:

1. Static badges can be copied/impersonated
2. The real verification happens on click (via Referer-based commit checking)
3. Users should be trained to CLICK, not just LOOK

SECURITY MODEL:
- Badge links to verification page on owner's GitHub Pages
- Verification page checks Referer header to detect repo squatting
- Commit hashes in URL are verified against official branch history
- Attackers cannot fake the Referer (browser-controlled)
"""

import os


# Badge colors
COLOR_PRIMARY = "#2ea44f"     # GitHub green - action button
COLOR_SECONDARY = "#24292f"   # Dark for repo name  
COLOR_LABEL = "#555"          # Dark gray for label


def render_badge(repo_name: str = None, action_text: str = "Click to Verify") -> str:
    """
    Render a Repo Trust verification badge as SVG.
    
    This badge is designed as a call-to-action, not a status indicator.
    The actual verification happens when the user clicks through to the
    verification page.
    
    Args:
        repo_name: Repository name (owner/repo) to embed in badge
        action_text: Text for the action button portion
        
    Returns:
        SVG string for the badge
    """
    # If no repo name provided, try to get from environment
    if repo_name is None:
        repo_name = os.environ.get("GITHUB_REPOSITORY", "")
    
    label = "Repo Trust"
    
    # Calculate dimensions
    char_width = 7
    padding = 12
    
    label_width = int(len(label) * char_width + padding)
    
    if repo_name:
        repo_width = int(len(repo_name) * char_width + padding)
    else:
        repo_width = 0
    
    action_width = int(len(action_text) * char_width + padding)
    
    total_width = label_width + repo_width + action_width
    height = 24
    
    # Calculate text positions (center of each section)
    label_x = label_width / 2
    repo_x = label_width + repo_width / 2
    action_x = label_width + repo_width + action_width / 2
    
    if repo_name:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="Repo Trust: {repo_name} - {action_text}">
  <title>Repo Trust: {repo_name} - Click to verify this is the official repository</title>
  <defs>
    <linearGradient id="buttonGrad" x2="0" y2="100%">
      <stop offset="0" stop-color="#34d058"/>
      <stop offset="1" stop-color="#22863a"/>
    </linearGradient>
  </defs>
  <clipPath id="r">
    <rect width="{total_width}" height="{height}" rx="4" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="{height}" fill="{COLOR_LABEL}"/>
    <rect x="{label_width}" width="{repo_width}" height="{height}" fill="{COLOR_SECONDARY}"/>
    <rect x="{label_width + repo_width}" width="{action_width}" height="{height}" fill="url(#buttonGrad)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="12" font-weight="600">
    <text x="{label_x}" y="16">{label}</text>
    <text x="{repo_x}" y="16">{repo_name}</text>
    <text x="{action_x}" y="16">🔒 {action_text}</text>
  </g>
  <rect width="{total_width}" height="{height}" rx="4" fill="none" stroke="#1b1f23" stroke-opacity="0.1"/>
</svg>'''
    else:
        # Simpler badge without repo name
        total_width = label_width + action_width
        action_x = label_width + action_width / 2
        
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="Repo Trust - {action_text}">
  <title>Repo Trust - Click to verify this is the official repository</title>
  <defs>
    <linearGradient id="buttonGrad" x2="0" y2="100%">
      <stop offset="0" stop-color="#34d058"/>
      <stop offset="1" stop-color="#22863a"/>
    </linearGradient>
  </defs>
  <clipPath id="r">
    <rect width="{total_width}" height="{height}" rx="4" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="{height}" fill="{COLOR_LABEL}"/>
    <rect x="{label_width}" width="{action_width}" height="{height}" fill="url(#buttonGrad)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="12" font-weight="600">
    <text x="{label_x}" y="16">{label}</text>
    <text x="{action_x}" y="16">🔒 {action_text}</text>
  </g>
  <rect width="{total_width}" height="{height}" rx="4" fill="none" stroke="#1b1f23" stroke-opacity="0.1"/>
</svg>'''


def render_verified_badge(repo_name: str = None) -> str:
    """Render a verification badge with repo name."""
    return render_badge(repo_name=repo_name, action_text="Click to Verify")


def render_unverified_badge(repo_name: str = None) -> str:
    """Render an unverified state badge."""
    return render_badge(repo_name=repo_name, action_text="Not Configured")


def render_error_badge(repo_name: str = None) -> str:
    """Render an error state badge."""
    return render_badge(repo_name=repo_name, action_text="Error")

"""
Badge generation module for Repo Trust.

Generates SVG badges indicating verification status.
"""

from jinja2 import Template


# Badge colors
COLOR_VERIFIED = "#2ea44f"    # GitHub green
COLOR_UNVERIFIED = "#d73a49"  # GitHub red
COLOR_ERROR = "#6e7681"       # Gray
COLOR_LABEL = "#555"          # Dark gray for label

# SVG badge template - shields.io style
SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{{ width }}" height="20" role="img" aria-label="Repo Trust: {{ status }}">
  <title>Repo Trust: {{ status }}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{{ width }}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{{ label_width }}" height="20" fill="{{ label_color }}"/>
    <rect x="{{ label_width }}" width="{{ status_width }}" height="20" fill="{{ status_color }}"/>
    <rect width="{{ width }}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{{ label_x }}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{{ label }}</text>
    <text x="{{ label_x }}" y="140" transform="scale(.1)" fill="#fff">{{ label }}</text>
    <text aria-hidden="true" x="{{ status_x }}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{{ status }}</text>
    <text x="{{ status_x }}" y="140" transform="scale(.1)" fill="#fff">{{ status }}</text>
  </g>
</svg>"""


def render_badge(verified: bool = True, error: bool = False) -> str:
    """
    Render a Repo Trust badge as SVG.
    
    Args:
        verified: Whether the distribution is verified
        error: Whether an error occurred during verification
        
    Returns:
        SVG string for the badge
    """
    label = "Repo Trust"
    
    if error:
        status = "ERROR"
        status_color = COLOR_ERROR
    elif verified:
        status = "VERIFIED"
        status_color = COLOR_VERIFIED
    else:
        status = "UNVERIFIED"
        status_color = COLOR_UNVERIFIED
    
    # Calculate dimensions (approximate character widths)
    label_width = len(label) * 7 + 10  # ~7px per char + padding
    status_width = len(status) * 7 + 10
    total_width = label_width + status_width
    
    # Calculate text positions (center of each section, scaled by 10 for SVG)
    label_x = (label_width / 2) * 10
    status_x = (label_width + status_width / 2) * 10
    
    template = Template(SVG_TEMPLATE)
    return template.render(
        width=total_width,
        label_width=label_width,
        status_width=status_width,
        label_color=COLOR_LABEL,
        status_color=status_color,
        label=label,
        status=status,
        label_x=int(label_x),
        status_x=int(status_x)
    )


def render_verified_badge() -> str:
    """Render a VERIFIED badge."""
    return render_badge(verified=True, error=False)


def render_unverified_badge() -> str:
    """Render an UNVERIFIED badge."""
    return render_badge(verified=False, error=False)


def render_error_badge() -> str:
    """Render an ERROR badge."""
    return render_badge(verified=False, error=True)


# For backwards compatibility
def render(verified: bool = True) -> str:
    """Render a badge based on verification status."""
    return render_badge(verified=verified)

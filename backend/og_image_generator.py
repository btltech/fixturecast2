"""
OG Image Generator
Generates beautiful share cards for social media (Open Graph images)

Features:
- Team logos
- Predicted score
- Win probabilities
- Branded FixtureCast design
- Cached for performance

Requirements:
    pip install pillow requests
"""

import hashlib
import io
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# Configuration
CACHE_DIR = Path("data/og_images")
CACHE_DURATION = timedelta(hours=6)  # Cache images for 6 hours
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 630  # Standard OG image size

# Create cache directory
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Colors (Midnight Sports theme)
COLOR_BG = "#0B0E14"
COLOR_SURFACE = "#151B28"
COLOR_PRIMARY = "#3B82F6"
COLOR_SECONDARY = "#6366F1"
COLOR_ACCENT = "#06b6d4"
COLOR_TEXT = "#FFFFFF"
COLOR_TEXT_SECONDARY = "#94A3B8"

# Try to load fonts (fallback to default if not available)
try:
    FONT_TITLE = ImageFont.truetype("arial.ttf", 60)
    FONT_SCORE = ImageFont.truetype("arial.ttf", 90)
    FONT_BODY = ImageFont.truetype("arial.ttf", 36)
    FONT_SMALL = ImageFont.truetype("arial.ttf", 28)
except:
    # Fallback to default font
    FONT_TITLE = ImageFont.load_default()
    FONT_SCORE = ImageFont.load_default()
    FONT_BODY = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()


def generate_prediction_og_image(
    fixture_id, home_team, away_team, prediction_data, league_name="League"
):
    """
    Generate OG image for a prediction

    Args:
        fixture_id: Fixture ID for caching
        home_team: Home team name
        away_team: Away team name
        prediction_data: Prediction dictionary
        league_name: League name

    Returns:
        bytes: PNG image data
    """
    # Check cache first
    cache_key = f"prediction_{fixture_id}"
    cached_image = get_cached_image(cache_key)
    if cached_image:
        return cached_image

    # Create image
    img = Image.new("RGB", (DEFAULT_WIDTH, DEFAULT_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Add gradient background
    for y in range(DEFAULT_HEIGHT):
        alpha = y / DEFAULT_HEIGHT
        r = int(11 + (21 - 11) * alpha)
        g = int(14 + (27 - 14) * alpha)
        b = int(20 + (40 - 20) * alpha)
        draw.line([(0, y), (DEFAULT_WIDTH, y)], fill=(r, g, b))

    # Add background pattern (subtle)
    draw_pattern(draw, img)

    # Header: FixtureCast branding
    brand_y = 40
    draw.text((60, brand_y), "FixtureCast", font=FONT_BODY, fill=COLOR_ACCENT)
    draw.text(
        (60, brand_y + 50), "AI-Powered Prediction", font=FONT_SMALL, fill=COLOR_TEXT_SECONDARY
    )

    # League badge area (top right)
    draw.text(
        (DEFAULT_WIDTH - 300, brand_y),
        league_name,
        font=FONT_SMALL,
        fill=COLOR_TEXT_SECONDARY,
        anchor="ra",
    )

    # Main content area starts
    content_y = 180

    # Home Team
    draw.text((60, content_y), home_team, font=FONT_TITLE, fill=COLOR_TEXT)

    # VS
    vs_y = content_y + 80
    draw.text((DEFAULT_WIDTH // 2, vs_y), "VS", font=FONT_BODY, fill=COLOR_PRIMARY, anchor="mm")

    # Away Team
    away_y = content_y + 140
    draw.text((60, away_y), away_team, font=FONT_TITLE, fill=COLOR_TEXT)

    # Prediction section
    pred_y = away_y + 120

    if prediction_data:
        # Predicted score (large and centered)
        score = prediction_data.get("predicted_scoreline", "N/A")
        score_bbox = draw.textbbox((0, 0), score, font=FONT_SCORE)
        score_width = score_bbox[2] - score_bbox[0]
        draw.text(
            (DEFAULT_WIDTH // 2 - score_width // 2, pred_y),
            score,
            font=FONT_SCORE,
            fill=COLOR_ACCENT,
        )

        # Win probabilities (below score)
        prob_y = pred_y + 120
        home_prob = f"{prediction_data.get('home_win_prob', 0) * 100:.0f}%"
        draw_prob = f"{prediction_data.get('draw_prob', 0) * 100:.0f}%"
        away_prob = f"{prediction_data.get('away_win_prob', 0) * 100:.0f}%"

        # Draw probability bars
        bar_width = 320
        bar_height = 12
        bar_spacing = 50
        bar_x = (DEFAULT_WIDTH - bar_width) // 2

        # Home win bar
        draw_probability_bar(
            draw,
            bar_x,
            prob_y,
            bar_width,
            bar_height,
            prediction_data.get("home_win_prob", 0),
            COLOR_PRIMARY,
            home_prob,
        )

        # Draw bar
        draw_probability_bar(
            draw,
            bar_x,
            prob_y + bar_spacing,
            bar_width,
            bar_height,
            prediction_data.get("draw_prob", 0),
            COLOR_SECONDARY,
            draw_prob,
        )

        # Away win bar
        draw_probability_bar(
            draw,
            bar_x,
            prob_y + bar_spacing * 2,
            bar_width,
            bar_height,
            prediction_data.get("away_win_prob", 0),
            COLOR_ACCENT,
            away_prob,
        )

    # Footer
    footer_y = DEFAULT_HEIGHT - 60
    draw.text(
        (DEFAULT_WIDTH // 2, footer_y),
        "Get detailed analysis at fixturecast.app",
        font=FONT_SMALL,
        fill=COLOR_TEXT_SECONDARY,
        anchor="mm",
    )

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", optimize=True)
    img_bytes.seek(0)
    image_data = img_bytes.read()

    # Cache the image
    cache_image(cache_key, image_data)

    return image_data


def draw_probability_bar(draw, x, y, width, height, probability, color, label):
    """Draw a probability bar with label"""
    # Background bar (gray)
    draw.rectangle([(x, y), (x + width, y + height)], fill=COLOR_SURFACE)

    # Filled bar (colored)
    fill_width = int(width * probability)
    draw.rectangle([(x, y), (x + fill_width, y + height)], fill=color)

    # Label
    draw.text(
        (x + width + 20, y + height // 2), label, font=FONT_BODY, fill=COLOR_TEXT, anchor="lm"
    )


def draw_pattern(draw, img):
    """Draw subtle background pattern"""
    # Add some circles for visual interest
    for i in range(5):
        x = (i + 1) * (DEFAULT_WIDTH // 6)
        y = DEFAULT_HEIGHT // 2
        radius = 150 + i * 20
        draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)], outline=COLOR_PRIMARY, width=1
        )


def generate_default_og_image(title="FixtureCast", subtitle="AI Football Predictions"):
    """Generate default OG image for non-prediction pages"""
    cache_key = f"default_{hashlib.md5(title.encode()).hexdigest()}"
    cached_image = get_cached_image(cache_key)
    if cached_image:
        return cached_image

    img = Image.new("RGB", (DEFAULT_WIDTH, DEFAULT_HEIGHT), COLOR_BG)
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(DEFAULT_HEIGHT):
        alpha = y / DEFAULT_HEIGHT
        r = int(11 + (21 - 11) * alpha)
        g = int(14 + (27 - 14) * alpha)
        b = int(20 + (40 - 20) * alpha)
        draw.line([(0, y), (DEFAULT_WIDTH, y)], fill=(r, g, b))

    # Large centered title
    title_bbox = draw.textbbox((0, 0), title, font=FONT_SCORE)
    title_width = title_bbox[2] - title_bbox[0]
    title_height = title_bbox[3] - title_bbox[1]

    draw.text(
        (DEFAULT_WIDTH // 2 - title_width // 2, DEFAULT_HEIGHT // 2 - title_height - 40),
        title,
        font=FONT_SCORE,
        fill=COLOR_TEXT,
    )

    # Subtitle
    draw.text(
        (DEFAULT_WIDTH // 2, DEFAULT_HEIGHT // 2 + 40),
        subtitle,
        font=FONT_BODY,
        fill=COLOR_TEXT_SECONDARY,
        anchor="mm",
    )

    # Save
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", optimize=True)
    img_bytes.seek(0)
    image_data = img_bytes.read()

    cache_image(cache_key, image_data)
    return image_data


def get_cached_image(cache_key):
    """Get image from cache if available and not expired"""
    cache_file = CACHE_DIR / f"{cache_key}.png"

    if cache_file.exists():
        # Check if expired
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age < CACHE_DURATION:
            with open(cache_file, "rb") as f:
                return f.read()

    return None


def cache_image(cache_key, image_data):
    """Save image to cache"""
    cache_file = CACHE_DIR / f"{cache_key}.png"
    with open(cache_file, "wb") as f:
        f.write(image_data)


def cleanup_cache():
    """Remove expired cache files"""
    now = datetime.now()
    for cache_file in CACHE_DIR.glob("*.png"):
        file_age = now - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > CACHE_DURATION:
            cache_file.unlink()
            print(f"Removed expired cache: {cache_file.name}")


if __name__ == "__main__":
    # Test image generation
    print("Testing OG image generation...")

    test_prediction = {
        "predicted_scoreline": "2-1",
        "home_win_prob": 0.58,
        "draw_prob": 0.24,
        "away_win_prob": 0.18,
    }

    image_data = generate_prediction_og_image(
        fixture_id=12345,
        home_team="Arsenal",
        away_team="Chelsea",
        prediction_data=test_prediction,
        league_name="Premier League",
    )

    # Save test image
    with open("test_og_image.png", "wb") as f:
        f.write(image_data)

    print("✅ Test image saved as test_og_image.png")

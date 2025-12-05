import streamlit as st
import base64
from pathlib import Path

# Create a simple avatar using ASCII art for now
# This can be replaced with an actual image file created by a team member later
def get_bot_avatar_svg():
    """
    Returns an SVG string for the chatbot avatar.
    This is a simple Greek amphora design that can be replaced with a custom image later.
    """
    svg = '''
    <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
        <style>
            .amphora { fill: #d9a066; stroke: #8b4513; stroke-width: 1.5; }
            .details { fill: none; stroke: #8b4513; stroke-width: 1; }
            .greek-pattern { fill: #8b4513; }
        </style>
        <!-- Amphora body -->
        <path class="amphora" d="M20,5 C15,5 12,10 12,15 C12,25 12,35 15,42 C18,45 32,45 35,42 C38,35 38,25 38,15 C38,10 35,5 30,5 Z" />
        
        <!-- Amphora neck -->
        <path class="amphora" d="M20,5 C22,3 28,3 30,5" />
        
        <!-- Amphora handles -->
        <path class="amphora" d="M15,15 C10,18 10,22 15,25" />
        <path class="amphora" d="M35,15 C40,18 40,22 35,25" />
        
        <!-- Greek pattern details -->
        <path class="details" d="M17,20 C25,18 33,20 33,20" />
        <path class="details" d="M17,25 C25,27 33,25 33,25" />
        <path class="details" d="M17,30 C25,32 33,30 33,30" />
        <path class="details" d="M17,35 C25,33 33,35 33,35" />
        
        <!-- Greek letters - Alpha -->
        <text x="22" y="28" font-family="serif" font-size="8" class="greek-pattern">Α</text>
        
        <!-- Face/Intelligence indicators -->
        <circle cx="25" cy="15" r="1.5" class="greek-pattern" />
    </svg>
    '''
    return svg

def get_bot_avatar_base64():
    """Returns the bot avatar as a base64 encoded string."""
    return base64.b64encode(get_bot_avatar_svg().encode('utf-8')).decode('utf-8')

def get_avatar_html():
    """Returns HTML code to display the avatar."""
    base64_avatar = get_bot_avatar_base64()
    return f'<img src="data:image/svg+xml;base64,{base64_avatar}" alt="AI Classics Assistant" style="width:50px; height:50px;">'

def create_avatar_file():
    """Creates a physical SVG file for the avatar if it doesn't exist."""
    avatar_dir = Path("./assets")
    avatar_dir.mkdir(exist_ok=True)
    
    avatar_path = avatar_dir / "bot_avatar.svg"
    if not avatar_path.exists():
        with open(avatar_path, "w") as f:
            f.write(get_bot_avatar_svg())
    
    return str(avatar_path)

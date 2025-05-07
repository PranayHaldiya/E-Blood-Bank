from html2image import Html2Image
import os

hti = Html2Image()
html_file = os.path.join(os.path.dirname(__file__), 'default-profile.html')
output_file = os.path.join(os.path.dirname(__file__), 'default-profile.png')

# Set a white background and specific size
hti.screenshot(
    html_file=html_file,
    save_as='default-profile.png',
    size=(200, 200)
)

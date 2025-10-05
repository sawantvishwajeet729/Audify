# 🏠_Home.py
import streamlit as st
import numpy as np
import cv2
import os
import base64
from app import *

#website url
website_url = "https://vishwajeetsawant.lovable.app"

# --- Page Configuration ---
st.set_page_config(
    page_title="Audify",
    page_icon="🎙️",
    layout="wide"
)

# --- Sidebar ---
with st.sidebar:
    st.image("artifacts/audfy logo.jpeg", width=120)
    st.header("How It Works")
    st.markdown("""
**Audify** is your personal AI audio producer. Here’s how you can create your audiobook snippet:

1.  **Choose Your Narrator:** Start by selecting the default voice you'd like for the story's narration from the gallery of characters.

2.  **Upload a Page:** Provide a clear image of a book page you want to bring to life.

3.  **AI Text Analysis:** The app performs Optical Character Recognition (OCR) to read the text, identifies any new characters, and corrects potential scanning errors.

4.  **Intelligent Voice Casting:** For any characters found in dialogue, the AI automatically assigns the best-fitting voices from its library, complementing the narrator you chose.

5.  **Audio Generation:** The story is converted to speech, with each character (and your chosen narrator) speaking their lines.

6.  **Final Audiobook:** All audio clips are seamlessly combined into your finished audiobook, ready to be played and downloaded.
""")

# --- Main Page ---
st.image("artifacts/audify banner.jpeg", width='stretch')
st.title("Audify 🎙️")
st.markdown("### Turn any book page into a multi-character audiobook snippet.")
st.write("---")


# Initialize session state
if 'final_audio_path' not in st.session_state:
    st.session_state.final_audio_path = None
if 'final_state_data' not in st.session_state:
    st.session_state.final_state_data = None

# Get the compiled LangGraph app and voice data (cached for performance)
app = get_compiled_graph()
voice_data = get_voices()

# HELPER FUNCTION to read an image file and convert it to a Base64 Data URL
def get_image_as_base64(path):
    """Reads an image file and returns its Base64 encoded string."""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    # The MIME type can be adjusted if you use other formats like jpg
    return f"data:image/png;base64,{encoded_string}"


# 1. DEFINE THE CSS FOR HOVER AND SELECTION EFFECTS
st.markdown("""
<style>
    /* Style for the image container */
    .image-container {
        text-align: center;
        margin-bottom: 10px;
    }
    /* Style for the image itself */
    .styled-image {
        width: 100%;
        border-radius: 10px;
        border: 3px solid transparent; /* Start with a transparent border */
        transition: transform .2s ease-in-out, border-color .2s ease-in-out;
        cursor: pointer;
    }
    .styled-image:hover {
        transform: scale(1.1); /* Enlarge image by 10% on hover */
    }
    /* Style for the selected image */
    .selected-image {
        border-color: #DFFF00; /* Add a blue border when selected */
        box-shadow: 0 0 30px #DFFF00;
    }
</style>
""", unsafe_allow_html=True)


# 2. PREPARE YOUR IMAGE DATA (using local paths)
# IMPORTANT: Create an 'assets' folder and place your images there.
characters = [
    {"name": "Sarah", "local_path": "artifacts/Sarah.png"},
    {"name": "Roger", "local_path": "artifacts/Roger.png"},
    {"name": "Rachel", "local_path": "artifacts/Rachel.png"},
    {"name": "Paul", "local_path": "artifacts/Paul.png"},
    {"name": "Fin", "local_path": "artifacts/Fin.png"},
    {"name": "Drew", "local_path": "artifacts/Drew.png"},
    {"name": "Domi", "local_path": "artifacts/Domi.png"},
    {"name": "Dave", "local_path": "artifacts/Dave.png"},
    {"name": "Aria", "local_path": "artifacts/Aria.png"},
    {"name": "Clyde", "local_path": "artifacts/Clyde.png"},
]

# Create placeholder images if assets don't exist (for demonstration)
for char in characters:
    if not os.path.exists(char["local_path"]):
        os.makedirs("assets", exist_ok=True)
        placeholder_url = f"https://placehold.co/200x200/grey/white?text={char['name']}"
        import requests
        with open(char["local_path"], 'wb') as f:
            f.write(requests.get(placeholder_url).content)


# 3. CREATE THE RADIO BUTTON WIDGET
st.subheader("Select Your Narrator")
character_names = [c['name'] for c in characters]
# The radio widget directly returns the name of the selected character
selected_character = st.radio(
    "Choose your character:",
    character_names,
    horizontal=True,
    label_visibility="collapsed" # Hides the "Choose your character:" label text
)

# --- DISPLAY IMAGES IN TWO ROWS ---
rows = [characters[:5], characters[5:]]
for row in rows:
    cols = st.columns(5)
    for i, character in enumerate(row):
        with cols[i]:
            # Convert local image to Base64
            base64_image = get_image_as_base64(character["local_path"])

            if base64_image:
                # Conditionally add the 'selected-image' class
                class_name = "styled-image"
                if character['name'] == selected_character:
                    class_name += " selected-image"

                # Create the HTML block with the image (no link needed)
                html_code = f"""
                <div class="image-container">
                    <img src="{base64_image}" class="{class_name}">
                </div>
                """
                st.markdown(html_code, unsafe_allow_html=True)
            else:
                st.error(f"Image not found for {character['name']}")
    st.write("") 


# 4. DISPLAY THE CONFIRMATION MESSAGE

if selected_character:
    st.success(f"You have selected: **{selected_character}**")
    selected_character_id = get_voice_id_by_name(selected_character, voice_data)
    
st.markdown("---")

#upload the image of book or novel
uploaded_file = st.file_uploader("Upload an image of a book page", type=["jpg", "png", "jpeg"])

#Copyright Warning
st.warning(
    """
    **⚠️ Copyright & Responsible Use Notice**

    Please be aware that the text from most books is protected by copyright law.

    * **You are responsible for the content you upload.** By using Audify, you affirm that you have the legal right to process the uploaded material.
    * **Only upload content that you own or that is in the public domain.**
    * This service is intended for personal, non-commercial, and educational purposes only.

    For a great source of copyright-free books to use with this app, check out **[Project Gutenberg](https://www.gutenberg.org/)**.
    """
)
st.write("---")

col1, col2 = st.columns(2)

with col1:
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Page", width='stretch')

with col2:
    if uploaded_file is not None:
        if st.button("Generate Audiobook", type="primary", width='stretch'):
            with st.spinner("🚀 The AI agents are at work... This may take a few minutes."):
                # Process image
                file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
                image = cv2.imdecode(file_bytes, 1)
                ocr_data = image_ocr(image)

                # Create initial state
                initial_state = {
                    "default_charachter": selected_character_id,
                    "ocr_text": ocr_data,
                    "voice_list": voice_data,
                    "charachter_list": {},  
                    "page_number": [],
                    "speakerXid": {},
                }
                
                # Run the workflow
                final_state = app.invoke(initial_state)

                # Store results in session state
                st.session_state.final_state_data = final_state
                st.session_state.final_audio_path = final_state.get("final_audio_path")

    if st.session_state.final_audio_path:
        print("final mp3 ready")
        st.write(st.session_state.final_audio_path)
        st.success("✨ Your audiobook is ready!")
        
        final_path = st.session_state.final_audio_path
        if os.path.exists(final_path):
            st.audio(final_path)
            with open(final_path, "rb") as f:
                st.download_button(
                    label="Download Audiobook (MP3)",
                    data=f,
                    file_name="final_audiobook.mp3",
                    mime="audio/mpeg",
                    width='stretch'
                )
        else:
            st.error("The final audio file could not be found.")

st.info("This is a free version of Audify and hence the generated audio is of limited lenght. Please reach out to me on my [website](%s) for extended version."  % website_url, icon="ℹ️", width='stretch')

if st.session_state.final_state_data:
    with st.expander("View Agent Workflow Data"):
        st.json(st.session_state.final_state_data)



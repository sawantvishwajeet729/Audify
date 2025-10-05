# Audify 🎙️

**Turn any book page into a multi-character audiobook snippet using AI.**

Audify is an intelligent audiobook generator that uses computer vision, natural language processing, and text-to-speech technology to transform scanned book pages into immersive audio experiences with distinct character voices.

![Audify Banner](artifacts/audify%20banner.jpeg)

## 🌟 Features

- **OCR Text Extraction**: Automatically extracts and corrects text from book page images using Tesseract OCR
- **Intelligent Character Detection**: Identifies new characters and their properties (gender, age, physical characteristics) using Google Gemini AI
- **Automated Voice Casting**: Matches characters to appropriate voices from ElevenLabs' voice library based on their attributes
- **Dialogue Parsing**: Separates narration from character dialogue and attributes speech to the correct speakers
- **Multi-Voice Audio Generation**: Creates audio with distinct voices for each character and narrator
- **Seamless Audio Merging**: Combines all audio segments into a single cohesive audiobook file

## 🏗️ Architecture

Audify uses a **LangGraph-based agentic workflow** with five specialized agents:

1. **Character Identifier Agent**: Extracts text via OCR, corrects spelling errors, identifies new characters and their properties
2. **Voice Selector Agent**: Intelligently assigns appropriate voices to characters based on their attributes
3. **Dialogue Splitter Agent**: Parses text to separate narration from dialogue and identifies speakers
4. **Voice Generator Agent**: Converts text to speech using ElevenLabs API with character-specific voices
5. **Audio Combiner Agent**: Merges individual audio clips into a final audiobook file using FFmpeg

```
┌─────────────────────┐
│  Upload Book Page   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Character          │
│  Identifier         │◄──── OCR + Gemini AI
└──────────┬──────────┘
           │
           ▼
    ┌─────────────┐
    │ New Char?   │
    └─────┬───┬───┘
          │   │
      Yes │   │ No
          │   │
          ▼   ▼
    ┌─────────────────┐
    │ Voice Selector  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Dialogue        │
    │ Splitter        │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Voice Generator │◄──── ElevenLabs API
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Audio Combiner  │◄──── FFmpeg
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Final Audiobook │
    └─────────────────┘
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- FFmpeg installed on your system
- Tesseract OCR installed
- API Keys:
  - [ElevenLabs API Key](https://elevenlabs.io/)
  - [Google Gemini API Key](https://ai.google.dev/)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/sawantvishwajeet729/Audify.git
cd audify
```

2. **Install system dependencies**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr ffmpeg
```

**macOS:**
```bash
brew install tesseract ffmpeg
```

**Windows:**
- Download and install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- Download and install [FFmpeg](https://ffmpeg.org/download.html)

3. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up API keys**

Create a `.streamlit/secrets.toml` file in the project root:
```toml
[default]
eleven_labs = "your_elevenlabs_api_key_here"
google_gemini = "your_google_gemini_api_key_here"
```

### Running the Application

```bash
streamlit run frontend.py
```

The application will open in your default web browser at `http://localhost:8501`

## 📖 Usage

1. **Select Your Narrator**: Choose a default voice for the story's narration from the character gallery
2. **Upload a Book Page**: Provide a clear image (JPG, PNG) of a book page
3. **Generate**: Click "Generate Audiobook" and wait for the AI agents to process
4. **Listen & Download**: Play the generated audiobook or download the MP3 file

### Example Workflow

```python
# The workflow processes through these states:
initial_state = {
    "default_charachter": selected_voice_id,
    "ocr_text": extracted_text,
    "voice_list": available_voices,
    "charachter_list": {},
    "page_number": [],
    "speakerXid": {},
}

# After processing, you get:
final_state = {
    "corrected_text": "Clean text...",
    "charachter_list": {"Alice": {"Gender": "Female", "Age": "Young"}},
    "dialogue": [{"speaker": "Alice", "text": "Hello!"}],
    "speakerXid": {"Alice": "voice_id_123"},
    "final_audio_path": "final_audiobook.mp3"
}
```

## 🛠️ Technologies Used

- **Frontend**: Streamlit
- **OCR**: Tesseract, OpenCV
- **LLM**: Google Gemini 2.5 Flash
- **Orchestration**: LangGraph
- **Text-to-Speech**: ElevenLabs API
- **Audio Processing**: FFmpeg
- **Image Processing**: OpenCV, NumPy

## 📁 Project Structure

```
audify/
├── app.py                 # Core LangGraph workflow and agent logic
├── frontend.py            # Streamlit UI and user interaction
├── requirements.txt       # Python dependencies
├── packages.txt          # System dependencies (Tesseract)
├── artifacts/            # UI assets (logos, character images)
│   ├── audfy logo.jpeg
│   ├── audify banner.jpeg
│   └── [character images]
├── audio_clips/          # Generated audio segments (temporary)
└── final_audiobook.mp3   # Final output
```

## ⚙️ Configuration

### Voice Selection
The application uses ElevenLabs' voice library. You can customize character voices by modifying the `voice_selector` agent in `app.py`.

### OCR Settings
OCR parameters can be adjusted in the `image_ocr` function:
```python
custom_config = r'--oem 3 --psm 6'  # OCR Engine Mode & Page Segmentation Mode
```

### Audio Limits
The free version limits audio generation. Modify the counter in `voice_generator`:
```python
counter = 0  # Change limit in the loop condition
```

## 🚨 Important Notes

### Copyright Compliance
- **Only upload content you have the legal right to process**
- Use public domain books from [Project Gutenberg](https://www.gutenberg.org/)
- This tool is for personal, educational, and non-commercial use only

### API Usage & Costs
- ElevenLabs: Free tier has character limits; paid plans available
- Google Gemini: Check current pricing and quotas
- Consider implementing rate limiting for production use

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🐛 Known Issues

- Free ElevenLabs tier limits audio generation length
- OCR accuracy depends on image quality and font clarity
- Character detection may struggle with unusual names or formats
- Browser storage (localStorage) not available in Streamlit artifacts

## 🔮 Future Enhancements

- [ ] Support for multiple pages/chapters
- [ ] Enhanced character emotion detection
- [ ] Custom voice cloning integration
- [ ] PDF direct upload support
- [ ] Background music and sound effects
- [ ] Multi-language support
- [ ] Voice fine-tuning per character
- [ ] Export to various audiobook formats

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Your Name**
- Website: [vishwajeetsawant.lovable.app](https://vishwajeetsawant.lovable.app)
- GitHub: [@sawantvishwajeet729](https://github.com/sawantvishwajeet729)

## 🙏 Acknowledgments

- [ElevenLabs](https://elevenlabs.io/) for the text-to-speech API
- [Google Gemini](https://ai.google.dev/) for the LLM capabilities
- [LangChain/LangGraph](https://www.langchain.com/) for the orchestration framework
- [Streamlit](https://streamlit.io/) for the web framework
- [Project Gutenberg](https://www.gutenberg.org/) for public domain books

## 📞 Support

For questions, issues, or extended version inquiries, please:
- Open an issue on GitHub
- Visit the [website](https://vishwajeetsawant.lovable.app)

---

⭐ **If you find Audify useful, please consider giving it a star on GitHub!** ⭐
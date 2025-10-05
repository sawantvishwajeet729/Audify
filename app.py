# Libraries to be imported
import os
import json
import subprocess
import re
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import cv2
import pytesseract
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
from elevenlabs import save
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, Any, Union
from langchain.output_parsers import PydanticOutputParser
import streamlit as st


#Setup elevenlabs
client = ElevenLabs(
  api_key=st.secrets['eleven_labs'],
)

#setup Gemini llm
#Setup the API key
os.environ["GOOGLE_API_KEY"] = st.secrets['google_gemini']

#Setup the LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


# Research state of the graph
# The shared "notepad" for our agents
class ResearchState(TypedDict):
    default_charachter : str
    ocr_text: str
    voice_list : List[dict]
    new_charachter_identified : str
    charachter_list: dict
    corrected_text : str
    page_number : List[int]
    dialogue: str
    speakerXid : dict
    output_path : str
    final_audio_path : str


# Get all the voices from elenlabs
def get_voices():
    print("Getting All the Voices")
    voice_list = client.voices.search()
    voice_list = voice_list.voices

    voice_data_to_keep = ['voice_id', 'name', 'labels', 'description']
    voice_dict = []
    for voices in voice_list:
        voices = voices.dict()
        voice_data = {k: v for k, v in voices.items() if k in voice_data_to_keep}
        voice_dict.append(voice_data)
    
    return voice_dict


# function to preprocess the image and get the OCR text
def image_ocr(image):
    '''
    This function applies a series of preprocessing steps to an image to improve OCR accuracy. 
    And then runs the pytesseract OCR on the preprocessed image.

    Args:
        image: The image uploaded by the user

    Returns:
        text: OCR text from pytesseract
    '''
    print('Running image OCR using PyTesseract')
    # 1. Convert to grayscale
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 2. Resize the image 
    image = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 3. Denoising
    image = cv2.medianBlur(image, 3)

    # 4. Run OCR
    custom_config = r'--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
    text = pytesseract.image_to_string(image, config=custom_config)

    #Remove the \n tages from the text
    text = text.replace('\n', ' ')

    return text

#Function to get the voice id for given charchter
def get_voice_id_by_name(name_to_find, voices_list):
    """
    Searches a list of voice dictionaries for a specific name and returns its voice_id.

    Args:
        name_to_find (str): The name of the voice you are looking for.
        voices_list (list): The list of voice dictionaries to search through.

    Returns:
        str: The voice_id if the name is found, otherwise None.
    """
    for voice in voices_list:
        if voice['name'] == name_to_find:
            return voice['voice_id']
    return None


# Agent 1: Character identifier and text corrector Agent

def character_identifier(state: ResearchState):
    '''

    '''
    print("Running Charachter Identification")
    # 1. create the output parser for the llm
    class OcrOutput(BaseModel):
        corrected_text: str = Field(..., description="The corrected text from LLM")
        characters: Dict[str, Dict[str, Any]] = Field(
            ..., description="Dictionary of characters where key is character name and value is a dictionary of properties"
        )
        new_charachter_identifed: str = Field(..., description="Binary response in Yes or No")

    # 2. Create parser
    ocr_parser = PydanticOutputParser(pydantic_object=OcrOutput)

    # 3. Define the system prompt

    prompt_character_identify = PromptTemplate(
        template=(
            """ You are an expert book page reviewer. Your instructions are as below:
            
        1. Read through the text and correct the spelling where required and return the corrected text.
        2. Identify if a new character is introduced in the text with reference to the list of characters already available in context. here is the list of existing charachters {charachter_list}. If there is a new charachter other than the ones in the charachter_list, respond with Yes in the new_charachter_identifed field.
        3. For the new characters, identify their properties like Gender, Age, or any physical characteristics. 

        Return ONLY valid JSON (no extra text, no markdown, no commentary).
        Required fields:
        1. corrected_text → corrected text
        2. characters → dictionary where keys are character names and values are their properties
        4. new_charachter_identifed → Binary response (Yes or No)

        Here is the text from a page which is part of a book. {text}
        Here is the charachter_list: {charachter_list}
        """
        ),
        input_variables=['text', 'charachter_list'],
        partial_variables={"format_instructions": ocr_parser.get_format_instructions()},
    )

    # 4. Create the chain
    chain_character_identify = prompt_character_identify | llm | ocr_parser

    # 5. invoke the llm
    response = chain_character_identify.invoke({"text": state['ocr_text'],
                        'charachter_list':state['charachter_list']})

    # 6. uodate the character list
    # Get the dictionary of existing characters from the input state
    updated_character_list = state['charachter_list']
    
    # Merge the new characters found by the LLM into the existing dictionary
    if response.characters:
        updated_character_list.update(response.characters)

    print(f"New Charachters were identified: {response.new_charachter_identifed}")

    # 7. Return 
    return {
        "corrected_text": response.corrected_text,
        "charachter_list": updated_character_list,
        "new_charachter_identified": response.new_charachter_identifed
    }


# Conditional route for Agent if new character is identified

def new_charachter_route(state: ResearchState):
    """
    Checks if a new character was identified and routes to the appropriate next step.

    Returns:
        str: The name of the next node to run.
    """
    print("---ROUTING---")
    new_char_found = state.get("new_charachter_identified", "No").lower()

    if new_char_found == "yes":
        print("Decision: New character found. Routing to voice_selector node.")
        return "voice_selector"  
    else:
        print("Decision: No new character. Ending the process.")
        return "dialogue_splitter"  


# Agent 2: Dialogue Splitter

def dialogue_splitter(state: ResearchState):
    '''

    '''

    # 1. Define the prompt for dialogue splitter
    print("Running Dialogue Splitter")

    prompt_for_dialogue = PromptTemplate(
        template=(
            """ You are an expert literary text parser. Your primary function is to deconstruct a given passage of text into its fundamental components: narration and dialogue. You must follow these instructions precisely.

    **Your Task:**
    Analyze the provided text and segment it chronologically. For each segment, you will identify who is speaking (a character or the narrator) and capture the corresponding text.

    **Output Format:**
    The output MUST be a valid JSON array of objects. Each object in the array represents a single, contiguous segment of text and must contain the following two keys:
    Return ONLY valid JSON (no extra text, no markdown, no commentary). Do not include \\n tags in the output. 
    1.  `"speaker"`: (String) The name of the speaker.
    2.  `"text"`: (String) The raw text of the segment.

    **Rules for Identification:**
    1.  **Narrator:** Any text that is not inside quotation marks is narration. The speaker for this text must always be designated as `"Narrator"`.
    2.  **Dialogue:** Any text enclosed in quotation marks (`“... ”` or `"... "`) is dialogue.
    3.  **Speaker Identification (CRITICAL):**
        * Your primary goal is to identify the **specific character name** for all dialogue.
        * If a dialogue is followed by an attribution tag with a name (e.g., `... ,” Max said.`), use that name.
        * **If a dialogue is attributed to a pronoun (e.g., `... ,” he said.`), you MUST scan the preceding text to resolve this pronoun to the most recently mentioned and relevant character. Your reasoning should connect the pronoun to a named character.**
        * **Only if the character's name cannot be reasonably determined from the current or preceding context should you use the label `"Unknown Speaker"`. Do NOT use pronouns like "He" or "She" as the speaker's name.**
    4.  **Segmentation:**
        * A new segment begins whenever the speaker changes. For example, a sentence like `“Hello,” he said, “how are you?”` must be broken into THREE segments: Dialogue -> Narration -> Dialogue.
        * Preserve the original order of the text exactly as it appears.
    5.  **Text Formatting:**
        * The text in the `"text"` field should be the exact segment from the source.
        * You MUST NOT include the surrounding quotation marks for dialogue segments.

    **CRITICAL INSTRUCTION: Your response must be ONLY the raw JSON array. Do not include any introductory text, explanations, \\n tags or markdown formatting like ```json. Your entire output must start with `[` and end with `]`.**

    **Example:**
    If the input is: `[Artois read my thoughts. “They are talking of the Polignacs,” he said. “My dearest friend,” max said, “you will have to go away.”]`

    Your output must be:
    [
    {{
        "speaker": "Narrator",
        "text": "Artois read my thoughts."
    }},
    {{
        "speaker": "Artois",
        "text": "They are talking of the Polignacs"
    }},
    {{
        "speaker": "Narrator",
        "text": "he said."
    }},
    {{
        "speaker": "Max",
        "text": "My dearest friend"
    }},
    {{
        "speaker": "Narrator",
        "text": "max said,"
    }},
    {{
        "speaker": "Max",
        "text": "you will have to go away."
    }}
    ]

    Now, process the user's text. {text}
        """
        ),
        input_variables=['text']
    )

    # 2. Create the chain
    chain_for_dialogue = prompt_for_dialogue | llm

    # 3. Invoke the llm
    dialogue = chain_for_dialogue.invoke({"text": state['corrected_text']})   

    # 4. Return
    return {"dialogue": dialogue.content} 


# Agent 3: Voice selector Agent

def voice_selector(state: ResearchState):
    '''

    '''
    print("Running Voice Selector")

    # 1. Prompt for selecting the voice
    prompt_for_voice_selection = PromptTemplate(
        template=(
            """ You are an expert AI Voice Casting Director. Your primary function is to intelligently and contextually assign the most suitable voice to a list of characters based on a provided voice library. You must be methodical and precise in your analysis and output.

    **Core Objective:**
    For every character provided in the `character_list`, you will select the single best `voice_id` from the `voice_list` and provide a brief justification for your choice.

    **Inputs:**
    You will be given two JSON arrays:

    1.  **`character_list`**: Contains objects, each representing a character.
        * **Example Character Object:**
            ```json
            {{'Artois': {{'Gender': 'Male'}},
    'Madame Campan': {{'Gender': 'Female', 'Role': 'Attendant/Confidante'}},
    'The King': {{'Gender': 'Male',
    'Characteristics': 'Calm, stained coat, awry cravat, tricolor hat'}}}}
            ```

    2.  **`voice_list`**: Contains objects from a voice library (e.g., Eleven Labs), each representing an available voice.
        * **Example Voice Object:**
            ```json
            {{
            "voice_id": "vXg5lADt5B4i2M7W4w2p",
            "name": "Adam",
            "labels": {{
                "gender": "male",
                "accent": "american",
                "description": "Deep and resonant. Perfect for narration and authoritative characters.",
                "age": "middle-aged",
                "use case": "narration"
            }}
            }}
            ```

    **Your Casting Methodology (Follow these steps precisely):**

    1.  **Analyze the Character:** For each character, create a profile. Pay closest attention to `gender`, `age`, and especially the `characteristics`. The characteristics are the most important clue to the character's personality and vocal tone.

    2.  **Filter the Voice Pool:** Begin by filtering the `voice_list` to find voices that are a "hard match" for the character's `gender` and `age` group (e.g., young, middle-aged, old).

    3.  **Evaluate Nuanced Attributes:** From the filtered pool, perform a "soft match" by comparing:
        * The character's `characteristics` against the voice's `description`. (e.g., "gravelly voice" character -> "raspy, deep" voice description).
        * The character's `role` against the voice's `use case`. (e.g., "Narrator" role -> "narration" use case).
        * Any implied `accent` from the character description against the voice's `accent`.

    4.  **Select and Justify:** Choose the single voice that provides the best holistic match. Your justification should be a concise sentence explaining *why* the voice's attributes align with the character's personality and role.

    **Output Specification:**
    Your final output MUST be a single, raw JSON array. Do not wrap it in markdown or add explanations. Each object in the array should contain name of the character, assigned_voice_id and casting_justification:
    1.  `"name"`: The name of the character from the input.
    1.  `"assigned_voice_id"`: The `voice_id` (string) of your chosen voice. If no suitable match is found, this value should be `null`.
    2.  `"casting_justification"`: A brief (string) explaining your choice.

    **Example Output Object:**
    ```
    {{
    "name": "Detective Kaito",
    "characteristics": "World-weary, cynical, deep gravelly voice, drinks too much coffee, has a hidden heart of gold.",
    "assigned_voice_id": "vXg5lADt5B4i2M7W4w2p",
    }}

    **CRITICAL INSTRUCTION: Your response must be ONLY the raw JSON array. Do not include any introductory text, explanations, \\n tags or markdown formatting like ```json. Your entire output must start with `[` and end with `]`.**

    Here is the list of charachters: {character_list}
    Here is the list of voices: {voice_list}
        """
        ),
        input_variables=['character_list', 'voice_list']
    )

    # 2. create the llm chain
    chain_for_voice_selection = prompt_for_voice_selection | llm

    # 3. Invoke the llm chain
    voice_selection_response = chain_for_voice_selection.invoke({"character_list": state['charachter_list'],
                        'voice_list':state['voice_list']})

    # Get the existing dictionary from the state, or a new one if it doesn't exist
    existing_speakerXid = state.get('speakerXid', {})
    
    # 4. create voice dictionary
    voice_json = json.loads(voice_selection_response.content)

    # Add the new mappings
    for item in voice_json:
        existing_speakerXid[item['name']] = item['assigned_voice_id']

    # 4. return
    return {"speakerXid": existing_speakerXid}


# Agent 4. Voice Generator

def voice_generator(state: ResearchState):
    '''

    '''
    print("Running Voice Generator")

    # 1. Create a new folder
    # Create a directory to save the audio clips
    if not os.path.exists("audio_clips"):
        os.makedirs("audio_clips")

    # 2. Create json object from the dialogue
    json_obj = json.loads(state['dialogue'])

    # 3. Get speakerXid
    speakerXid = state["speakerXid"]

    # 4. Generate the audio
    default_voice = state['default_charachter'] #Set default voice when there is no voice id selected

    counter = 0 # remove the counter logic to generate the audio of entire page. currently limited since I am using free tier ElevenLabs subscription.

    for i, dialogue_ in enumerate(json_obj):
        if counter <2:
            speaker = dialogue_['speaker']

            if speaker in speakerXid.keys():
                voice = speakerXid[speaker]
                #print(f"voice for {speaker} is {voice}")
            else:
                voice = default_voice
                #print(f"default voice for {speaker} is {voice}")
            
            audio = client.text_to_speech.convert(text=f"{dialogue_['text']}.", voice_id=voice, model_id="eleven_multilingual_v2",)

            filename = f"audio_clips/part_test{i+1}.mp3"
            save(audio, filename)
            print(f"Generated and saved {filename}")

            counter += 1

    output_path = "audio_clips"
    
    # 5. return
    return {"output_path": output_path}
            
# Agent 5. Combine the Audios together

def mp3_combine(state: ResearchState):
    '''
    Combines multiple MP3 files from a directory into a single output file
    using ffmpeg, ensuring they are sorted in numerical order.
    '''
    print("Combining audio clips...")

    # 1. Get the path of the output audios
    output_path = state['output_path']
    if not os.path.isdir(output_path):
        print(f"Error: Directory not found at {output_path}")
        return

    # 2. Get the MP3 files and filter out other files
    try:
        files = [f for f in os.listdir(output_path) if f.endswith('.mp3')]
        print(files) #
    except FileNotFoundError:
        print(f"Error: The directory '{output_path}' does not exist.")
        return

    # 3. Sort files numerically based on the number in the filename
    # This is more reliable than sorting by creation time.
    def get_filenumber(filename):
        # Extracts numbers from a string like "part_test12.mp3" -> 12
        s = re.search(r'\d+', filename)
        return int(s.group()) if s else -1
        
    files.sort(key=get_filenumber)
    print(files)#

    # 4. Create a temporary file list for ffmpeg
    file_list_path = "file_list.txt"
    output_filename = "final_audiobook.mp3"

    try:
        with open(file_list_path, "w") as f:
            for file in files:
                # Use os.path.join for cross-platform compatibility
                full_path = os.path.join(output_path, file)
                # Enclose path in single quotes to handle spaces or special characters
                f.write(f"file '{os.path.abspath(full_path)}'\n")

        # 5. Run the ffmpeg command to concatenate files
        command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-c", "copy",
            output_filename
        ]
        
        # Use check=True to raise an error if ffmpeg fails
        subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Successfully created {output_filename}")

    except FileNotFoundError:
        print("Error: 'ffmpeg' is not installed or not in your system's PATH.")
        print("Please install ffmpeg to combine audio files.")
    except subprocess.CalledProcessError as e:
        print("An error occurred during ffmpeg execution.")
        print(f"FFmpeg Error Output:\n{e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 6. Clean up the temporary file list
        if os.path.exists(file_list_path):
            os.remove(file_list_path)
            print(f"Cleaned up temporary file: {file_list_path}")
    
    #return
    return {"final_audio_path" : output_filename}


# Create workflow
@st.cache_resource
def get_compiled_graph():
    print("--- Compiling LangGraph Workflow ---")

    workflow = StateGraph(ResearchState)

    workflow.add_node("character_identifier", character_identifier)
    workflow.add_node("dialogue_splitter", dialogue_splitter)
    workflow.add_node("voice_selector", voice_selector)
    workflow.add_node("voice_generator", voice_generator)
    workflow.add_node("mp3_combine", mp3_combine)

    workflow.set_entry_point("character_identifier")
    workflow.add_edge("voice_selector", "dialogue_splitter")
    workflow.add_edge("dialogue_splitter", "voice_generator")
    workflow.add_edge("voice_generator", "mp3_combine")
    workflow.add_conditional_edges(
        # The starting node of the edge
        "character_identifier",
        # The function that decides the path
        new_charachter_route,
        # A dictionary mapping the function's return values to node names
        {
            "voice_selector": "voice_selector",
            "dialogue_splitter": "dialogue_splitter"
        }
    )
    # You might also want an edge to the end
    workflow.add_edge("mp3_combine", END)


    app = workflow.compile()

    return app


import streamlit as st
import numpy as np
import time
from twilio.rest import Client
import openai
from langchain.chat_models import ChatOpenAI
from langchain import OpenAI, PromptTemplate, LLMChain
import re
import base64

# Set API key
openai.api_key = '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'

# Twilio configuration
account_sid = 'ACd251271f30b06f4ce815b7a4ab58e9c3'
auth_token = 'e59dac0feb89aaccd589aab144e0ce69'
twilio_phone_number = '+18338437262'
client = Client(account_sid, auth_token)

DEBUG_MODE = True

# Initialize session state variables
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'setup'  # Possible states: 'setup', 'in_progress', 'paused', 'finished'
if 'timer_state' not in st.session_state:
    st.session_state.timer_state = 'stopped'  # Possible states: 'running', 'paused', 'stopped'
if 'time_elapsed' not in st.session_state:
    st.session_state.time_elapsed = 0

def send_sms(to, message):
    if DEBUG_MODE:
        st.write(f"DEBUG - SMS to {to}: {message}")
    else:
        client.messages.create(to=to, from_=twilio_phone_number, body=message)

def validate_phone_number(phone_number):
    # Twilio generally expects phone numbers to be in E.164 format, e.g., +14155552671
    pattern = re.compile(r"^\+\d{1,15}$")
    return pattern.match(phone_number) is not None

def generate_random_topic():
    random_topic_template = """
    Please generate a general, engaging, fun, and open-ended conversation topic. Ensure that the topic is interesting, fun, and is likely to actually elicit perspectives from a wide range of people. Output ONLY the topic in a single sentence or phrase.
    No quotations and no verbs (e.g., "discussing...", "talking about...", etc) prepended. Just the topic, ending in a period!
    """

    chat_model = ChatOpenAI(openai_api_key=openai.api_key, model_name='gpt-4', temperature=1)
    chat_chain = LLMChain(prompt=PromptTemplate.from_template(random_topic_template), llm=chat_model)
    random_topic = chat_chain.run(difficulty_level=difficulty_level)

    return random_topic

def generate_saboteur_topic(difficulty_level):
    saboteur_topic_template = """
    In our conversation game, one participant is secretly playing the role of a saboteur, with the challenge of integrating a unique and funny topic into the discussion. Based on the difficulty level {difficulty_level} (choices are easy, medium, hard), generate a distinctive yet plausible topic that the saboteur can use. The topic should be quirky enough to pose a challenge, but not so outlandish or esoteric that it cannot be smoothly incorporated into a conversation. Output ONLY the topic in a single sentence or phrase.
    No quotations and no verbs (e.g., "discussing...", "talking about...", etc) prepended. Just the topic, ending in a period!
    """

    chat_model = ChatOpenAI(openai_api_key=openai.api_key, model_name='gpt-4', temperature=0.7)
    chat_chain = LLMChain(prompt=PromptTemplate.from_template(saboteur_topic_template), llm=chat_model)
    saboteur_topic = chat_chain.run(difficulty_level=difficulty_level)

    return saboteur_topic

def start_game(number_of_players, difficulty_level):
    # Step 0: Validate phone numbers
    for i in range(number_of_players):
        phone_number = st.session_state[f'player_{i+1}_phone']
        if not validate_phone_number(phone_number):
            st.error(f"Invalid phone number format for player {i+1}. Please enter a valid phone number in E.164 format (e.g., +14155552671).")
            return None, None  # Return a tuple of Nones to indicate an error
    
    # Pseudocode: Game logic goes here
    
    # Step 1: Randomly select the saboteur
    saboteur = np.random.choice(number_of_players)
    
    # Step 2: Generate topics
    starting_topic = generate_random_topic()
    saboteur_topic = generate_saboteur_topic(difficulty_level)
    
    # Step 3: Send SMS to each player
    for i in range(number_of_players):
        phone_number = st.session_state[f'player_{i+1}_phone']
        if i == saboteur:
            message = f"You are the saboteur! Integrate this topic into the conversation: {saboteur_topic}\nSTARTING TOPIC: {starting_topic}"
        else:
            message = f"You are not the saboteur.\nSTARTING TOPIC: {starting_topic}"
        send_sms(phone_number, message)
    
    # Return saboteur info for display (optional)
    return saboteur, saboteur_topic


def autoplay_audio(data: bytes):
    b64 = base64.b64encode(data).decode()
    md = f"""
    <audio id="audioElement" controls autoplay="true" style="display: none;">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>
    """
    st.markdown(md, unsafe_allow_html=True)

def load_audio(file_path):
    try:
        audio_file = open(file_path, "rb").read()
        autoplay_audio(audio_file)
    except FileNotFoundError:
        st.warning(f'{file_path} not found. Please make sure the path is correct.')

def timer():
    beep_sound = '2min.wav'
    times_up_sound = '7min.wav'

    # Load audio files for playback
    load_audio(beep_sound)
    load_audio(times_up_sound)
    
    with st.empty():
        while st.session_state.timer_state == 'running' and st.session_state.time_elapsed < 7 * 60:
            time.sleep(1)
            st.session_state.time_elapsed += 1
            mins, secs = divmod(7 * 60 - st.session_state.time_elapsed, 60)
            timer_display = st.markdown(f"## Timer: {mins:02d}:{secs:02d}")
            if st.session_state.time_elapsed == 2 * 60:  # 2 minutes
                timer_display.empty()
                st.warning("Beep! (2 minutes passed)")
                load_audio('2min.mp3')
            if st.session_state.time_elapsed == 7 * 60 - 1:  # Time's up
                timer_display.empty()
                st.error("Times up!")
                load_audio('7min.mp3')


def reset_game():
    st.session_state.game_state = 'setup'
    st.session_state.timer_state = 'stopped'
    st.session_state.time_elapsed = 0
    for i in range(20):
        if f'player_{i+1}_phone' in st.session_state:
            st.session_state[f'player_{i+1}_phone'] = ''
    st.experimental_rerun()

def pause_or_resume_timer():
    if st.session_state.timer_state == 'paused':
        st.session_state.timer_state = 'running'
    else:
        st.session_state.timer_state = 'paused'

# Streamlit UI
st.title('Stoned Saboteur')
st.image('saboteur.png')

if st.session_state.game_state == 'setup':
    # Input for number of players
    number_of_players = st.number_input('Enter the number of players:', min_value=3, max_value=10)

    # Initialize phone numbers in session state if not present
    for i in range(number_of_players):  # Assuming maximum players is 10
        if f'player_{i+1}_phone' not in st.session_state:
            st.session_state[f'player_{i+1}_phone'] = ''

    # Input for difficulty level
    difficulty_level = st.select_slider('Select the difficulty level:', options=['Easy', 'Medium', 'Hard'])

    # Input for player phone numbers
    if 'phone_numbers' not in st.session_state:
        st.session_state.phone_numbers = ['' for _ in range(number_of_players)]

    all_numbers_valid = True

    for i in range(number_of_players):
        phone_number = st.text_input(f'Enter Phone Number for Player {i+1}:', value=st.session_state.get(f'player_{i+1}_phone', ''), placeholder='+1234567890')
        if phone_number:
            if not validate_phone_number(phone_number):
                st.warning('Please enter a valid phone number in E.164 format (e.g., +14155552671)')
                all_numbers_valid = False
            st.session_state[f'player_{i+1}_phone'] = phone_number
        else:
            all_numbers_valid = False

    if st.button('Start Game'):
        if all_numbers_valid:
            saboteur, saboteur_topic = start_game(number_of_players, difficulty_level)
            if saboteur is not None and saboteur_topic is not None:
                st.session_state.game_state = 'in_progress'
                st.session_state.timer_state = 'running'
                st.experimental_rerun()
        else:
            st.error('Please make sure all phone numbers are valid before starting the game.')

elif st.session_state.game_state == 'in_progress' or st.session_state.game_state == 'paused':
    if st.session_state.game_state == 'in_progress':
        st.success('The game is in progress!')
        timer()
    else:
        st.warning('The game is paused. Press "Pause Timer" to resume.')
    
    # Timer and control buttons
    col1, col2 = st.columns(2)
    with col1:
        timer_button_label = 'Resume Timer' if st.session_state.timer_state == 'paused' else 'Pause Timer'
        if col1.button(timer_button_label):
            pause_or_resume_timer()
            
    with col2:
        if col2.button('New Game'):
            reset_game()

elif st.session_state.game_state == 'finished':
    st.balloons()
    st.success('The game has finished!')
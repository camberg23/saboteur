import streamlit as st
import numpy as np
import time
from twilio.rest import Client
import openai
from langchain.chat_models import ChatOpenAI
from langchain import OpenAI, PromptTemplate, LLMChain
import re
import base64

# Set the page title, icon, and layout
st.set_page_config(
    page_title="Stoned Saboteur",
    page_icon="saboteur.png",
)

# Set API key
openai.api_key = st.secrets['OPENAI_API_KEY']

# Twilio configuration
account_sid = st.secrets['SID']
auth_token = st.secrets['AUTH']
twilio_phone_number = st.secrets['NUMBER']
client = Client(account_sid, auth_token)

DEBUG_MODE = False

# Initialize session state variables
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'setup'  # Possible states: 'setup', 'in_progress', 'paused', 'finished'
if 'timer_state' not in st.session_state:
    st.session_state.timer_state = 'stopped'  # Possible states: 'running', 'paused', 'stopped'
if 'time_elapsed' not in st.session_state:
    st.session_state.time_elapsed = 0
if 'debug_messages' not in st.session_state:
    st.session_state.debug_messages = []
if 'needs_rerun' not in st.session_state:
    st.session_state.needs_rerun = True

def send_sms(to, message):
    if DEBUG_MODE:
        st.session_state.debug_messages.append(f"DEBUG - SMS to {to}: {message}")
        st.write("Debug Message Added:", message)  # Debug print
    else:
        # print(to)
        # print(message)
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
    random_topic = chat_chain.run(difficulty_level=st.session_state.difficulty_level)

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
    saboteur_topic = generate_saboteur_topic(st.session_state.difficulty_level)
    
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

    timer_container = st.empty()
    warning_container = st.empty()
    default_text_container = st.empty()

    while st.session_state.timer_state == 'running' and st.session_state.time_elapsed < 7 * 60:
        time.sleep(1)
        st.session_state.time_elapsed += 1
        mins, secs = divmod(7 * 60 - st.session_state.time_elapsed, 60)

        timer_container.markdown(f"<h1 style='text-align: center;'>Time remaining in round: {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
        
        # 2-minute warning
        if st.session_state.time_elapsed == 120 and not st.session_state.get('two_minute_warning_shown'):
            st.session_state.two_minute_warning_shown = True
            warning_container.warning("Out of accelerated accusation period—players must wait until end of round to vote for Saboteur!")
            default_text_container.empty()  # Clear default text
            load_audio(beep_sound)

        # 7-minute mark
        if st.session_state.time_elapsed == 7 * 60:
            st.session_state.timer_state = 'stopped'
            st.session_state.game_state = 'finished'
            st.session_state.times_up_shown = True
            timer_container.empty()
            load_audio(times_up_sound)

    # Display warnings outside the loop to ensure they persist after a rerun
    if st.session_state.get('two_minute_warning_shown') and not st.session_state.get('times_up_shown'):
        warning_container.warning("Out of accelerated accusation period—players must wait until end of round to vote for Saboteur!")
    if st.session_state.get('times_up_shown'):
        warning_container.success("Time's up!")

    # Show default text if 2-minute warning hasn't been shown yet
    if not st.session_state.get('two_minute_warning_shown'):
        default_text_container.warning("In accelerated accusation period (anyone can formally accuse someone of being the Saboteur)!")


def pause_or_resume_timer():
    if st.session_state.timer_state == 'paused':
        st.session_state.timer_state = 'running'
    else:
        st.session_state.timer_state = 'paused'



def reset_game():
    st.session_state.game_state = 'setup'
    st.session_state.timer_state = 'stopped'
    st.session_state.time_elapsed = 0
    for i in range(20):
        if f'player_{i+1}_phone' in st.session_state:
            st.session_state[f'player_{i+1}_phone'] = ''
    st.experimental_rerun()

def main():
    # Title of the game
    st.markdown("""
                <style>
                    .big-title {
                        font-size: 4em;  # Adjust the size as needed
                        text-align: center;
                        margin-top: 3em;  # Adjust the top margin for vertical centering
                    }
                </style>
                <div class="big-title">Stoned Saboteur</div>
            """, unsafe_allow_html=True)

    # Injecting CSS styles into the head of the document
    st.markdown("""
        <style>
        .small-font {
            font-size: 0.6em;
        }
        </style>
        """, unsafe_allow_html=True)

    # Displaying the image in column 1
    st.image('saboteur.png', width=500)

    # st.markdown("""
    # <style>
    # .css-1wrcr25 { font-size: 2em; }
    # </style>
    # """, unsafe_allow_html=True)

    with st.expander("**How to play Stoned Saboteur**"):
        st.markdown("<div style='font-size: 0.8em; margin-bottom: 1em;'><strong>Note</strong>: The game is inherently designed for cannabis smoking. Enjoy responsibly!</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-bottom: 1em;'><strong>Objective</strong>: Have a great conversation while also trying to <strong>catch the saboteur</strong>, who must seamlessly integrate a secret topic into the conversation within the seven-minute round.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 1em; margin-bottom: 0.5em;'><strong>Rules</strong>:</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>1. <strong>Player Setup</strong>: Set your preferences on this page and put in everyone's numbers.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>2. <strong>Saboteur’s Task</strong>: The Saboteur will be assigned secretly. They will given a topic that they must smoothly introduce and discuss within the conversation during the round, trying to go unnoticed.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>3. <strong>Round Duration</strong>: Each round lasts for seven minutes.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>4. <strong>Accelerated Accusations</strong>: For the first 2 mins only, any player can unilaterally accuse anyone of being the Saboteur. \"I formally accuse _______!\"</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>- If the accusation is correct, the accused Saboteur takes two hits.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>- If the accusation is incorrect, the accuser takes two hits.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>5. <strong>End of Round Voting</strong>: After the round, players vote on who they believe the Saboteur is.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em;'>- If the majority guesses correctly, the Saboteur takes one hit.</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.8em; margin-left: 1em; margin-bottom: 0.5em'>- If the majority is incorrect, all players in the majority take one hit, and the Saboteur wins the round.</div>", unsafe_allow_html=True)

    if st.session_state.game_state == 'setup':
        setup_container = st.container()
        
        with setup_container:
            # Input for number of players and difficulty level in two cols
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.number_of_players = st.number_input('Enter the number of players:', min_value=3, max_value=10, value=3)
            with col2:
                st.session_state.difficulty_level = st.select_slider('Select the difficulty level:', options=['Easy', 'Medium', 'Hard'])

            # Initialize phone numbers in session state if not present
            for i in range(10):  # Assuming maximum players is 10
                if f'player_{i+1}_phone' not in st.session_state:
                    st.session_state[f'player_{i+1}_phone'] = ''

            # Input for player phone numbers
            all_numbers_valid = True

            for i in range(st.session_state.number_of_players):
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
                    saboteur, saboteur_topic = start_game(st.session_state.number_of_players, st.session_state.difficulty_level)
                    if saboteur is not None and saboteur_topic is not None:
                        st.session_state.game_state = 'in_progress'
                        st.session_state.timer_state = 'running'
                        setup_container.empty()  # Clear the setup container
                else:
                    st.error('Please make sure all phone numbers are valid before starting the game.')

    elif st.session_state.game_state == 'in_progress':
        if DEBUG_MODE and st.session_state.debug_messages:
            with st.expander("Debug Messages"):
                for msg in st.session_state.debug_messages:
                    st.write(msg)
        if st.button('Reset Game'):
            reset_game()
        if st.button('Start New Round'):
            # Start a new round with the same players
            st.session_state.time_elapsed = 0
            st.session_state.timer_state = 'running'
            st.session_state.needs_rerun = True
            saboteur, saboteur_topic = start_game(st.session_state.number_of_players, st.session_state.difficulty_level)
        timer()

    # Ensure this is at the end of your main function to avoid premature rerun
    if st.session_state.game_state == 'in_progress' and st.session_state.needs_rerun:
        st.session_state.needs_rerun = False  # Reset the rerun flag
        st.experimental_rerun()

    elif st.session_state.game_state == 'finished':
        st.balloons()
        st.success('The game has finished!')

        with st.expander("Show saboteur and topic"):
            st.write(f"Saboteur: Player {st.session_state.saboteur+1}")
            st.write(f"Saboteur's topic: {st.session_state.saboteur_topic}")

# Run the main function
main()

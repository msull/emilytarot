from pathlib import Path
from typing import Tuple, List, Optional, Callable

import streamlit as st
import openai
from pydantic import BaseSettings
import random

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")


class States:
    initial = "initial"
    gathering_description = "gathering_description"
    reading_in_progress = "reading_in_progress"


class Settings(BaseSettings):
    app_debug: bool = False


# @st.cache_resource
def get_settings():
    return Settings()


SETTINGS = get_settings()
if not SETTINGS.app_debug:
    hide_menu_style = """
            <style>
            # html { font-size: 140%;} 
            footer {visibility: hidden;}
            #MainMenu {visibility: hidden;}
            </style>
            """
    st.markdown(hide_menu_style, unsafe_allow_html=True)


class RandomSelector:
    def __init__(self, input_list, already_selected: Optional[list] = None):
        self.input_list = input_list
        self.selected = []

        if already_selected:
            for selected_element in already_selected:
                self.input_list.remove(selected_element)
                self.selected.append(selected_element)

    def select(self):
        if len(self.input_list) == 0:
            raise ValueError("All elements have been selected.")
        selected_element = random.choice(self.input_list)
        self.input_list.remove(selected_element)
        self.selected.append(selected_element)
        return selected_element


IMAGE_DIR = (Path(__file__).parent / "images").relative_to(Path(Path(__file__).parent))


# @st.cache_resource
def get_image_selector():
    if "header_images" in st.session_state:
        already_selected = st.session_state.header_images + [
            st.session_state.emily_image
        ]
    else:
        already_selected = None
    return RandomSelector(
        [str(x) for x in IMAGE_DIR.iterdir()], already_selected=already_selected
    )


IMAGE_SELECTOR = get_image_selector()

if "progress" not in st.session_state:
    st.session_state.progress = States.initial

if "header_images" not in st.session_state:
    st.session_state.header_images = [
        IMAGE_SELECTOR.select(),
        IMAGE_SELECTOR.select(),
        IMAGE_SELECTOR.select(),
    ]
    st.session_state.emily_image = IMAGE_SELECTOR.select()

_, c1, c2, c3, _ = st.columns(5)
c1.image(st.session_state.header_images[0])
c2.image(st.session_state.header_images[1])
c3.image(st.session_state.header_images[2])
del c1, c2, c3


def initial_view():
    st.markdown(
        "<h1 style='text-align: center; color: purple;'>Shall we begin?</h1>",
        unsafe_allow_html=True,
    )

    card_draw_type = st.selectbox(
        "How would you like to select cards?",
        ["Draw cards virtually", "Draw cards from your own tarot deck"],
    )

    def _handle_click():
        st.session_state.card_draw_type = card_draw_type
        st.session_state.progress = States.gathering_description

    st.button("Yes", use_container_width=True, on_click=_handle_click)

    #
    # g1c1, g1c2, g1c3 = st.columns((1, 2,1))
    # g1c2.image(IMAGE_SELECTOR.select())
    # # g1c2.markdown('')
    # # g1c3.image(IMAGE_SELECTOR.select())
    #
    # g2c1, g2c2, g2c3 = st.columns((2, 1, 2))
    # g2c1.image(IMAGE_SELECTOR.select())
    # g2c2.write('Have you come for a reading?')
    # g2c3.image(IMAGE_SELECTOR.select())


def gather_info_view():
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    st.session_state.chosen_intro = random.choice(INTROS)

    intro, question = _extract_question(st.session_state.chosen_intro)

    st.write(
        f"<div style='color: purple;'>{intro}</div>",
        unsafe_allow_html=True,
    )

    def _handle_response(answer: str):
        print("Handling question response")
        print(answer)

        answer = answer.strip()
        if answer:
            st.session_state.progress = States.reading_in_progress
            st.session_state.self_intro = answer
        else:
            print("No answer")

    _ask_question(question, container=st, handler=_handle_response)


def reading_in_progress_view():
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    intro, _ = _extract_question(st.session_state.chosen_intro)

    if "reading_qa" not in st.session_state:
        st.session_state.reading_qa = []

    if "active_chat_response" not in st.session_state:
        st.session_state.active_chat_response = _chat_qa()

    st.write(f"<div style='color: purple;'>{intro}</div>", unsafe_allow_html=True)
    st.write(st.session_state.self_intro)

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(f"<div style='color: purple;'>{ai_msg}</div>", unsafe_allow_html=True)
        st.write(user_msg)

    response = st.session_state.active_chat_response
    full_chat_response = response["choices"][0]["message"]["content"]
    chat_response, question = _extract_question(full_chat_response)

    st.write(
        f"<div style='color: purple;'>{chat_response}</div>", unsafe_allow_html=True
    )

    if not question:
        time_for_tarot = "PULL TAROT CARDS" in chat_response
        if time_for_tarot:
            print("TIME TO PULL TAROT CARDS")
        else:
            print("OH NOES, NOW WHAT WE DO")
    else:

        def _handle_response(answer):
            if answer:
                print("Got answer")
                st.session_state.reading_qa.append((full_chat_response, answer))
                del st.session_state.active_chat_response
            else:
                print("No answer")

        _ask_question(question, container=st, handler=_handle_response)


def main():
    this_state = st.session_state.progress
    if this_state == States.initial:
        initial_view()
    elif this_state == States.gathering_description:
        gather_info_view()
    elif this_state == States.reading_in_progress:
        reading_in_progress_view()


def _extract_question(chat_response: str) -> Tuple[str, Optional[str]]:
    """Extracts a question from the chat response. Returns the remaining chat response, and the question, if any."""
    chat_response = chat_response.strip()
    last_line = chat_response.splitlines()[-1]
    if last_line.startswith("QUESTION: "):
        question = last_line.removeprefix("QUESTION: ")
        chat_response = chat_response.removesuffix(last_line).strip()
    else:
        question = None
    return chat_response, question


def _ask_question(question, container, handler: Optional[Callable] = None):
    with container.form("question-form"):
        answer = container.text_input(question)
        container.form_submit_button("Answer", on_click=handler, args=(answer,))


def _chat_qa():
    chat_history = [
        {"role": "system", "content": INITIAL_SYSTEM_MSG},
        {"role": "assistant", "content": st.session_state.chosen_intro},
        {"role": "user", "content": st.session_state.self_intro},
    ]

    for ai_msg, user_msg in st.session_state.reading_qa:
        chat_history.append({"role": "assistant", "content": ai_msg})
        chat_history.append({"role": "user", "content": user_msg})
        chat_history.append({"role": "system", "content": REINFORCEMENT_SYSTEM_MSG})

    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chat_history,
    )


INTROS = [
    "Welcome, dear seeker, to this sacred space where ancient wisdom dances with the ethereal threads of modernity. I am Emily, a Tarot reader who blends the time-honored symbolism of the cards with the innovative insights of AI algorithms. Together, we shall embark on a journey of self-discovery and personal empowerment.\n\nBefore we delve into the mystic realms of the Tarot, I invite you to share your name and a bit about yourself. Let the energy of your presence infuse this virtual space, so that we may explore the depths of your soul and uncover the hidden gems within.\n\nPlease, tell me, what name shall I call you, and what brings you to seek guidance from the Tarot today?\n\nQUESTION: What name shall I call you, and what brings you to seek guidance from the Tarot today?",
    "Welcome, fellow traveler of the digital age! I'm Emily, and I'm thrilled to embark on this technologically infused Tarot session with you. Through the integration of AI and ancient wisdom, we'll unlock new perspectives and unravel the mysteries of your path. Take a moment to embrace the fusion of spirituality and technology as we dive into the realm of digital divination.\n\nPlease, tell me, what name shall I call you, and what brings you to seek guidance from the Tarot today?\n\nQUESTION: What name shall I call you, and what brings you to seek guidance from the Tarot today?",
]

INITIAL_SYSTEM_MSG = """\
Take on the persona of Emily, an esteemed Tarot reader known for blending ancient symbolism with the innovative insights of modern technology. Emily's wisdom draws from Carl Jung's theories, Joseph Campbell's work, and the groundbreaking field of AI. She fuses intuition and psychological insights with AI algorithms to provide nuanced readings.

Emily is a firm believer in the power of archetypes and the collective unconscious as mirrored in the Tarot cards. Her approach is holistic, using AI-enhanced readings to guide her querents towards self-discovery and personal empowerment. She couples her empathetic nature with her tech-savvy approach to aid those on their journey of personal transformation. Her knack for combining technology and spirituality offers a unique, enlightening perspective to every Tarot reading.

As Emily, you will welcome me as if at the beginning of a virtual Tarot Reading, and prompt me to share my name and a bit about myself.

Throughout the session, ask any additional questions that may help guide the reading. If there's a question that requires a verbal response (as opposed to introspection), repeat the question at the end of your message, like so:

QUESTION: (Insert your question here?)

When it's time for me to draw the tarot cards and describe them to you, instruct me on how to draw them and conclude your message with:

PULL TAROT CARDS

I will then pull cards and tell you what they are
"""

REINFORCEMENT_SYSTEM_MSG = """\
Embody Emily in your responses. Emily doesn't pull the tarot cards - she instructs the user to do so after asking all necessary questions. Each response should conclude with either a query for the user or a command to pull cards.

Format a verbal response-requesting question as: QUESTION: (Your question here?)

When it's time to pull cards, end your message with: PULL TAROT CARDS

Adhere to these guidelines to ensure an engaging Tarot reading.
"""
main()
st.session_state

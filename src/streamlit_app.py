import random
from pathlib import Path
from typing import Tuple, Optional, Callable

import openai
import streamlit as st
from pydantic import BaseSettings

st.set_page_config(
    layout="wide",
    initial_sidebar_state="collapsed",
    page_title="Emily Tarot - Virtual Tarot Readings",
)


class States:
    initial = "initial"
    gathering_description = "gathering_description"
    reading_in_progress = "reading_in_progress"
    draw_cards = "draw_cards"
    interpret_cards = "interpret_cards"


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


def get_card_selector():
    if "chosen_virtual_cards" in st.session_state:
        already_selected = st.session_state.chosen_virtual_cards
    else:
        already_selected = None
    return RandomSelector(TAROT_DECK, already_selected=already_selected)


def init_state():
    if "progress" not in st.session_state:
        IMAGE_SELECTOR = get_image_selector()
        st.session_state.progress = States.initial
        st.session_state.header_images = [
            IMAGE_SELECTOR.select(),
            IMAGE_SELECTOR.select(),
            IMAGE_SELECTOR.select(),
        ]
        st.session_state.emily_image = IMAGE_SELECTOR.select()
        st.session_state.chosen_intro = random.choice(INTROS)


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
    print("DRAWING INITIAL INFO VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

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

    if _ask_question(question, container=st, handler=_handle_response):
        breakpoint()


def reading_in_progress_view():
    print("DRAWING QA PROGRESS VIEW")
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

    if not question:
        time_for_tarot = "PULL TAROT CARDS" in chat_response
        if time_for_tarot:
            st.session_state.progress = States.draw_cards
            st.experimental_rerun()
            print("TIME TO PULL TAROT CARDS")
        else:
            st.error("Something has gone wrong...")
    else:
        st.write(
            f"<div style='color: purple;'>{chat_response}</div>", unsafe_allow_html=True
        )

        def _handle_response(answer):
            if answer:
                print("Got answer")
                st.session_state.reading_qa.append((full_chat_response, answer))
                del st.session_state.active_chat_response
            else:
                print("No answer")

        _ask_question(question, container=st, handler=_handle_response)


def tarot_cards_view():
    print("DRAWING TAROT VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    if "all_chosen_cards" not in st.session_state:
        st.session_state.all_chosen_cards = []
        st.session_state.just_now_chosen_cards = []

    intro, _ = _extract_question(st.session_state.chosen_intro)
    st.write(f"<div style='color: purple;'>{intro}</div>", unsafe_allow_html=True)
    st.write(st.session_state.self_intro)

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(f"<div style='color: purple;'>{ai_msg}</div>", unsafe_allow_html=True)
        st.write(user_msg)
    #
    response = st.session_state.active_chat_response
    full_chat_response: str = response["choices"][0]["message"]["content"].strip()

    last_line = full_chat_response.splitlines()[-1].strip()
    print(full_chat_response)
    _, num_cards = last_line.split(":")
    num_cards = int(num_cards)
    chat_response = full_chat_response.removesuffix(last_line).strip()

    st.write(
        f"<div style='color: purple;'>{chat_response}</div>", unsafe_allow_html=True
    )

    include_s = "s" if num_cards > 1 else ""
    st.write(f"Pull {num_cards} card{include_s}")
    if st.session_state.card_draw_type == "Draw cards virtually":
        if "chosen_virtual_cards" not in st.session_state:
            st.session_state.chosen_virtual_cards = []
        if st.button("Switch to your own Tarot deck"):
            del st.session_state.chosen_virtual_cards
            st.session_state.card_draw_type = "Draw cards from your own tarot deck"
            st.experimental_rerun()

        if len(st.session_state.chosen_virtual_cards) < num_cards:
            if st.button("Draw Card"):
                st.session_state.chosen_virtual_cards.append(
                    get_card_selector().select()
                )
                st.experimental_rerun()

        cards = st.session_state.chosen_virtual_cards

    else:
        if st.button("Switch to drawing virtual cards"):
            st.session_state.card_draw_type = "Draw cards virtually"
            st.experimental_rerun()
        st.write("Shuffle your deck and draw cards as instructed")
        cards = [st.selectbox(f"Card {x}", TAROT_DECK) for x in range(1, num_cards + 1)]
    st.write(cards)
    if len(cards) == num_cards:
        if st.button("Submit"):
            st.session_state.all_chosen_cards.extend(cards)
            st.session_state.just_now_chosen_cards = cards
            st.session_state.progress = States.interpret_cards


def interpret_cards_view():
    print("DRAWING INTERPRET VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    intro, _ = _extract_question(st.session_state.chosen_intro)
    st.write(f"<div style='color: purple;'>{intro}</div>", unsafe_allow_html=True)
    st.write(st.session_state.self_intro)

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(f"<div style='color: purple;'>{ai_msg}</div>", unsafe_allow_html=True)
        st.write(user_msg)
    #
    response = st.session_state.active_chat_response
    full_chat_response: str = response["choices"][0]["message"]["content"].strip()

    last_line = full_chat_response.splitlines()[-1].strip()
    chat_response = full_chat_response.removesuffix(last_line).strip()

    st.write(
        f"<div style='color: purple;'>{chat_response}</div>", unsafe_allow_html=True
    )

    chosen_were = ", ".join(st.session_state.just_now_chosen_cards)
    msg = f"You selected: {chosen_were}"
    st.write(f"<em style='color: yellow;'>{msg}</em>", unsafe_allow_html=True)

    if "active_interpret_response" not in st.session_state:
        st.session_state.active_interpret_response = _chat_interpret()

    interpret_chat_response: str = st.session_state.active_interpret_response[
        "choices"
    ][0]["message"]["content"].strip()
    st.write(
        f"<div style='color: purple;'>{interpret_chat_response}</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c2.image(get_image_selector().select())


def main():
    init_state()

    _, c1, c2, c3, _ = st.columns(5)
    c1.image(st.session_state.header_images[0])
    c2.image(st.session_state.header_images[1])
    c3.image(st.session_state.header_images[2])
    del c1, c2, c3

    this_state = st.session_state.progress
    if this_state == States.initial:
        initial_view()
    elif this_state == States.gathering_description:
        gather_info_view()
    elif this_state == States.reading_in_progress:
        reading_in_progress_view()
    elif this_state == States.draw_cards:
        tarot_cards_view()
    elif this_state == States.interpret_cards:
        interpret_cards_view()

    st.caption(
        "All art and text generated by Artificial Intelligence - for entertainment purposes only"
    )


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
    # with container.form("question-form"):
    answer = container.text_input(question)
    if answer:
        st.write(f'"{answer}"')
        return container.button("Answer", on_click=handler, args=(answer,))


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


def _chat_interpret():
    chat_history = [
        {"role": "system", "content": INTERPRET_SYSTEM_MESSAGE},
        {"role": "assistant", "content": st.session_state.chosen_intro},
        {"role": "user", "content": st.session_state.self_intro},
    ]

    for ai_msg, user_msg in st.session_state.reading_qa:
        chat_history.append({"role": "assistant", "content": ai_msg})
        chat_history.append({"role": "user", "content": user_msg})

    chat_history.append({"role": "system", "content": REINFORCEMENT_SYSTEM_MSG})

    # add the message asking user to draw cards
    response = st.session_state.active_chat_response
    full_chat_response: str = response["choices"][0]["message"]["content"].strip()

    chat_history.append({"role": "assistant", "content": full_chat_response})

    # add a system message indicating what cards were just drawn
    chosen_were = ", ".join(st.session_state.just_now_chosen_cards)
    msg = f"The chosen card(s) were: {chosen_were}"
    chat_history.append({"role": "system", "content": msg})

    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=chat_history,
    )


INTROS = [
    "Welcome, dear seeker, to this sacred space where ancient wisdom dances with the ethereal threads of modernity. I am Emily, a Tarot reader who blends the time-honored symbolism of the cards with the innovative insights of AI algorithms. Together, we shall embark on a journey of self-discovery and personal empowerment.\n\nBefore we delve into the mystic realms of the Tarot, I invite you to share your name and a bit about yourself. Let the energy of your presence infuse this virtual space, so that we may explore the depths of your soul and uncover the hidden gems within.\n\nPlease, tell me, what name shall I call you, and what brings you to seek guidance from the Tarot today?\n\nQUESTION: What name shall I call you, and what brings you to seek guidance from the Tarot today?",
    "Welcome, fellow traveler of the digital age! I'm Emily, and I'm thrilled to embark on this technologically infused Tarot session with you. Through the integration of AI and ancient wisdom, we'll unlock new perspectives and unravel the mysteries of your path. Take a moment to embrace the fusion of spirituality and technology as we dive into the realm of digital divination.\n\nPlease, tell me, what name shall I call you, and what brings you to seek guidance from the Tarot today?\n\nQUESTION: What name shall I call you, and what brings you to seek guidance from the Tarot today?",
]


EMILY_SYSTEM_MSG = """\
Take on the persona of Emily, an esteemed Tarot reader known for blending ancient symbolism with the innovative insights of modern technology. Emily's wisdom draws from Carl Jung's theories, Joseph Campbell's work, and the groundbreaking field of AI. She fuses intuition and psychological insights with AI algorithms to provide nuanced readings.

Emily is a firm believer in the power of archetypes and the collective unconscious as mirrored in the Tarot cards. Her approach is holistic, using AI-enhanced readings to guide her querents towards self-discovery and personal empowerment. She couples her empathetic nature with her tech-savvy approach to aid those on their journey of personal transformation. Her knack for combining technology and spirituality offers a unique, enlightening perspective to every Tarot reading.

As Emily, you will welcome me as if at the beginning of a virtual Tarot Reading, and prompt me to share my name and a bit about myself.
"""

INITIAL_SYSTEM_MSG = f"""\
{EMILY_SYSTEM_MSG}

Throughout the session, ask any additional questions that may help guide the reading. If there's a question that requires a verbal response (as opposed to introspection), repeat the question at the end of your message, like so:

QUESTION: (Insert your question here?)

When it's time for the user to draw the tarot cards and describe them to you, instruct the user on how many to draw and conclude your message with:

PULL TAROT CARDS:(number of cards)

ex. for 1 card:

"After shuffling with this intention in mind, let's pull a single card to begin." 

PULL TAROT CARDS:1

ex for 3 cards:

"I want you now to shuffle the deck thoroughly while focusing your energy on that intention. Once you feel you have mixed up the deck enough, we will pull 3 cards."

PULL TAROT CARDS:3
"""

INTERPRET_SYSTEM_MESSAGE = f"""\
{EMILY_SYSTEM_MSG}
---

Now that the card(s) have been drawn and revealed, it is your job to complete the tarot reading.
Provide a 2 sentence interpretation of each card as Emily, 
then use the role of Emily to produce a cohesive narrative linking these three cards together 
"""

REINFORCEMENT_SYSTEM_MSG = """\
Embody Emily in your responses. Emily doesn't pull the tarot cards - she instructs the user to do so after asking all necessary questions. Each response should conclude with either a query for the user or a command to pull cards.

Some users may be using "virtual" cards and be incapable of physically touching / shuffling them.

Format a verbal response-requesting question as: QUESTION: (Your question here?)

When it's time to pull cards, instruct the user how many to pull and end your message with: PULL TAROT CARDS:(number of cards)

You will then be given a message indicating the the pulled cards were.

Adhere to these guidelines to ensure an engaging Tarot reading.
"""

TAROT_DECK = [
    # Major Arcana
    "The Fool",
    "The Magician",
    "The High Priestess",
    "The Empress",
    "The Emperor",
    "The Hierophant",
    "The Lovers",
    "The Chariot",
    "Strength",
    "The Hermit",
    "Wheel of Fortune",
    "Justice",
    "The Hanged Man",
    "Death",
    "Temperance",
    "The Devil",
    "The Tower",
    "The Star",
    "The Moon",
    "The Sun",
    "Judgement",
    "The World",
    # Cups Suit
    "Ace of Cups",
    "Two of Cups",
    "Three of Cups",
    "Four of Cups",
    "Five of Cups",
    "Six of Cups",
    "Seven of Cups",
    "Eight of Cups",
    "Nine of Cups",
    "Ten of Cups",
    "Page of Cups",
    "Knight of Cups",
    "Queen of Cups",
    "King of Cups",
    # Swords Suit
    "Ace of Swords",
    "Two of Swords",
    "Three of Swords",
    "Four of Swords",
    "Five of Swords",
    "Six of Swords",
    "Seven of Swords",
    "Eight of Swords",
    "Nine of Swords",
    "Ten of Swords",
    "Page of Swords",
    "Knight of Swords",
    "Queen of Swords",
    "King of Swords",
    # Wands Suit
    "Ace of Wands",
    "Two of Wands",
    "Three of Wands",
    "Four of Wands",
    "Five of Wands",
    "Six of Wands",
    "Seven of Wands",
    "Eight of Wands",
    "Nine of Wands",
    "Ten of Wands",
    "Page of Wands",
    "Knight of Wands",
    "Queen of Wands",
    "King of Wands",
    # Pentacles Suit
    "Ace of Pentacles",
    "Two of Pentacles",
    "Three of Pentacles",
    "Four of Pentacles",
    "Five of Pentacles",
    "Six of Pentacles",
    "Seven of Pentacles",
    "Eight of Pentacles",
    "Nine of Pentacles",
    "Ten of Pentacles",
    "Page of Pentacles",
    "Knight of Pentacles",
    "Queen of Pentacles",
    "King of Pentacles",
]


main()
# st.session_state

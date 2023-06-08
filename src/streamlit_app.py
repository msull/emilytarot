"""

TODO:

* Support more than one question per AI Statement
* Support questions that occur at the same time as a card draw
* Continue the session aftera card draw if the AI would like to do so

"""

import json
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from string import ascii_lowercase
from typing import Tuple, Optional, Callable

import openai
import streamlit as st

from utils.messages import (
    INTERPRET_SYSTEM_MESSAGE,
    REINFORCEMENT_SYSTEM_MSG,
    INITIAL_SYSTEM_MSG,
    INTROS,
)
from utils.tarot import TAROT_DECK

SESSION_DIR = os.environ["SESSION_DIR"]

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


@dataclass
class RandomSelector:
    elements: list
    used_elements: set = field(default_factory=set)

    def select(self):
        if len(self.used_elements) == len(self.elements):
            raise ValueError("All elements have been selected.")

        while True:
            element = random.choice(self.elements)
            if element not in self.used_elements:
                self.used_elements.add(element)
                return element


IMAGE_DIR = (Path(__file__).parent / "images").relative_to(Path(__file__).parent)


def get_image_selector():
    if "header_images" in st.session_state:
        already_selected = st.session_state.header_images + [
            st.session_state.emily_image
        ]
    else:
        already_selected = []
    return RandomSelector(
        [str(x) for x in IMAGE_DIR.iterdir()], used_elements=set(already_selected)
    )


def get_card_selector():
    if "chosen_virtual_cards" in st.session_state:
        already_selected = st.session_state.chosen_virtual_cards
    else:
        already_selected = []
    return RandomSelector(TAROT_DECK, used_elements=set(already_selected))


def save_session():
    path = Path(SESSION_DIR) / (st.session_state.session_id + ".json")
    path.write_text(json.dumps(st.session_state.to_dict()))


def init_state():
    query_session = st.experimental_get_query_params().get("s")
    if query_session:
        query_session = query_session[0]

        if (
            "session_id" in st.session_state
            and st.session_state.session_id != query_session
        ):
            st.session_state.clear()

    if "progress" not in st.session_state:
        start_new_session = True
        if query_session:
            path = Path(SESSION_DIR) / (query_session + ".json")
            try:
                loaded_session_data = json.loads(path.read_text())
            except:
                pass
            else:
                for k, v in loaded_session_data.items():
                    st.session_state[k] = v
                start_new_session = False

        if start_new_session:
            print("Starting new session")
            session_id = _date_id()
            st.session_state.session_id = session_id
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
        st.experimental_set_query_params(s=st.session_state.session_id)

    st.button("Yes", use_container_width=True, on_click=_handle_click)


def gather_info_view():
    print("DRAWING INITIAL INFO VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    intro, question = _extract_question(st.session_state.chosen_intro)
    st.write(intro)

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
    print("DRAWING QA PROGRESS VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    intro, _ = _extract_question(st.session_state.chosen_intro)

    if "reading_qa" not in st.session_state:
        st.session_state.reading_qa = []

    if "active_chat_response" not in st.session_state:
        with st.spinner("Generating AI response"):
            st.session_state.active_chat_response = _chat_qa()

    st.write(intro)
    st.write(
        f"<div style='color: yellow;'> &gt; {st.session_state.self_intro}</div>",
        unsafe_allow_html=True,
    )

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(ai_msg)
        st.write(
            f"<div style='color: yellow;'> &gt; {user_msg}</div>",
            unsafe_allow_html=True,
        )

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
        st.write(chat_response)

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
    st.write(intro)
    st.write(
        f"<div style='color: yellow;'> &gt; {st.session_state.self_intro}</div>",
        unsafe_allow_html=True,
    )

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(ai_msg)
        st.write(
            f"<div style='color: yellow;'> &gt; {user_msg}</div>",
            unsafe_allow_html=True,
        )

    response = st.session_state.active_chat_response
    full_chat_response: str = response["choices"][0]["message"]["content"].strip()

    last_line = full_chat_response.splitlines()[-1].strip()
    print(full_chat_response)
    _, num_cards = last_line.split(":")
    num_cards = int(num_cards)
    chat_response = full_chat_response.removesuffix(last_line).strip()

    st.write(chat_response)

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
            st.experimental_rerun()


def interpret_cards_view():
    print("DRAWING INTERPRET VIEW")
    _, c1, _ = st.columns(3)
    c1.image(st.session_state.emily_image)
    del c1

    intro, _ = _extract_question(st.session_state.chosen_intro)
    st.write(intro)
    st.write(
        f"<div style='color: yellow;'> &gt; {st.session_state.self_intro}</div>",
        unsafe_allow_html=True,
    )

    for ai_msg, user_msg in st.session_state.reading_qa:
        ai_msg, _ = _extract_question(ai_msg)
        st.write(ai_msg)
        st.write(
            f"<div style='color: yellow;'> &gt; {user_msg}</div>",
            unsafe_allow_html=True,
        )

    response = st.session_state.active_chat_response
    full_chat_response: str = response["choices"][0]["message"]["content"].strip()

    last_line = full_chat_response.splitlines()[-1].strip()
    chat_response = full_chat_response.removesuffix(last_line).strip()
    _, num_cards = last_line.split(":")
    num_cards = int(num_cards)

    st.write(chat_response)
    include_s = "s" if num_cards > 1 else ""
    st.caption(f"Pull {num_cards} card{include_s}")

    chosen_were = ", ".join(st.session_state.just_now_chosen_cards)
    msg = f"You selected: {chosen_were}"
    st.write(f"<em style='color: yellow;'>{msg}</em>", unsafe_allow_html=True)

    if "active_interpret_response" not in st.session_state:
        with st.spinner("Generating AI response"):
            st.session_state.active_interpret_response = _chat_interpret()

    interpret_chat_response: str = st.session_state.active_interpret_response[
        "choices"
    ][0]["message"]["content"].strip()
    st.write(interpret_chat_response)
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
        save_session()
    elif this_state == States.draw_cards:
        tarot_cards_view()
        save_session()
    elif this_state == States.interpret_cards:
        interpret_cards_view()
        save_session()

    st.caption(
        "All art and text generated by Artificial Intelligence - for entertainment purposes only"
    )
    st.caption("View on [Github](https://github.com/msull/emilytarot)")


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
    container.divider()
    answer = container.text_area(question)

    if answer:
        st.write(f'"{answer}"')
    return container.button(
        "Answer", on_click=handler, args=(answer,), disabled=not answer
    )


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


def _date_id(now=None):
    now = now or datetime.utcnow()
    return now.strftime("%Y%m%d%H") + "".join(random.choices(ascii_lowercase, k=6))


main()

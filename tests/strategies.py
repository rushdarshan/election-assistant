"""Hypothesis strategies for election-assistant.

Each strategy models the valid input space for a function or group of
functions. Strategies are named after the domain concept they represent,
not the function they're used with.
"""

from hypothesis import strategies as st
from app.models import ReadinessProgress, RegistrationStatus, QuizQuestion, QuizAttempt

# -- Atomic strategies --

valid_state = st.text(min_size=2, max_size=50)
valid_country = st.text(min_size=2, max_size=50)

# ISO timestamp strategy
iso_timestamp = st.datetimes().map(lambda dt: dt.isoformat())

# ISO date strategy (YYYY-MM-DD) or None
iso_date = st.one_of(st.none(), st.dates().map(lambda d: d.isoformat()))

# -- Composed / domain strategies --

readiness_progress_strategy = st.builds(
    ReadinessProgress,
    country=valid_country,
    state=valid_state,
    registration_status=st.one_of(st.none(), st.sampled_from(list(RegistrationStatus))),
    voting_method=st.one_of(st.none(), st.sampled_from(["in-person", "early", "mail-in"])),
    timeline_viewed=st.booleans(),
    questions_asked=st.integers(min_value=0, max_value=100),
    quiz_attempts=st.integers(min_value=0, max_value=100),
    quiz_best_score=st.one_of(st.none(), st.floats(min_value=0, max_value=100)),
    checklist_items_completed=st.integers(min_value=0, max_value=20),
    last_updated=iso_timestamp
)

@st.composite
def deadline_validator_inputs(draw):
    # Anchor dates dictionary
    anchor_dates = draw(st.dictionaries(
        keys=st.sampled_from(["General Election", "Primary Election", "Registration"]),
        values=st.dates().map(lambda d: d.isoformat()),
        max_size=3
    ))
    
    state = draw(valid_state)
    api_date = draw(iso_date)
    deadline_type = draw(st.sampled_from(["General Election", "Primary Election", "Registration", "Other"]))
    
    return {
        "anchor_dates": anchor_dates,
        "state": state,
        "api_date": api_date,
        "deadline_type": deadline_type
    }

quiz_question_strategy = st.builds(
    QuizQuestion,
    id=st.text(min_size=1, max_size=10),
    question=st.text(min_size=10, max_size=100),
    category=st.sampled_from(["registration", "voting", "deadline", "security", "civics"]),
    difficulty=st.sampled_from(["easy", "medium", "hard"]),
    options=st.lists(st.text(min_size=1, max_size=50), min_size=2, max_size=4),
    correct_answer_idx=st.integers(min_value=0, max_value=3),
    explanation=st.text(min_size=10, max_size=200),
    source=st.text(min_size=5, max_size=50)
)

# Ensure correct_answer_idx is within bounds of options
@st.composite
def valid_quiz_question(draw):
    options = draw(st.lists(st.text(min_size=1, max_size=50), min_size=2, max_size=4))
    correct_answer_idx = draw(st.integers(min_value=0, max_value=len(options)-1))
    return draw(st.builds(
        QuizQuestion,
        id=st.text(min_size=1, max_size=10),
        question=st.text(min_size=10, max_size=100),
        category=st.sampled_from(["registration", "voting", "deadline", "security", "civics"]),
        difficulty=st.sampled_from(["easy", "medium", "hard"]),
        options=st.just(options),
        correct_answer_idx=st.just(correct_answer_idx),
        explanation=st.text(min_size=10, max_size=200),
        source=st.text(min_size=5, max_size=50)
    ))

@st.composite
def quiz_grading_inputs(draw):
    questions = draw(st.lists(valid_quiz_question(), min_size=1, max_size=10))
    attempts = []
    for q in questions:
        selected_idx = draw(st.integers(min_value=0, max_value=len(q.options)-1))
        attempts.append(QuizAttempt(
            question_id=q.id,
            selected_idx=selected_idx,
            is_correct=selected_idx == q.correct_answer_idx
        ))
    return {
        "questions": questions,
        "attempts": attempts
    }

# -- Type registrations --

st.register_type_strategy(ReadinessProgress, readiness_progress_strategy)
st.register_type_strategy(QuizQuestion, valid_quiz_question())

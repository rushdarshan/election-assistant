"""
Quiz System - Educational engagement & knowledge verification
"""
import random
from typing import List, Optional, Dict
from app.models import QuizQuestion, QuizResult, QuizSession, QuizAttempt


# Comprehensive quiz bank (by country/state/category)
QUIZ_BANK: Dict[str, List[QuizQuestion]] = {
    "US_GENERAL": [
        QuizQuestion(
            id="q1_reg_01",
            question="What is the earliest you can register to vote?",
            category="registration",
            difficulty="easy",
            options=[
                "On election day",
                "15 days before election",
                "30 days before election",
                "Anytime, but votes count only after 18"
            ],
            correct_answer_idx=2,
            explanation="Most US states require registration 15-30 days before the election. Some allow registration on election day. Check your state's specific deadline.",
            source="Election.gov"
        ),
        QuizQuestion(
            id="q1_voting_01",
            question="Which voting method requires a postage stamp in some states?",
            category="voting",
            difficulty="easy",
            options=[
                "Early voting",
                "Mail-in ballots",
                "Election day voting",
                "None - all are free"
            ],
            correct_answer_idx=1,
            explanation="Mail-in ballot postage varies by state. Some cover postage, others require voters to pay. Check your state's rules.",
            source="Ballotpedia"
        ),
        QuizQuestion(
            id="q1_deadline_01",
            question="When are election day ballots typically due?",
            category="deadline",
            difficulty="easy",
            options=[
                "3 days after election",
                "By end of election day",
                "Within 2 weeks after election",
                "No deadline - ballots count for 30 days"
            ],
            correct_answer_idx=1,
            explanation="Election day ballots must be submitted by the time polls close on election day. Mail-in ballots have extended deadlines (typically 10 days after).",
            source="Election.gov"
        ),
        QuizQuestion(
            id="q1_id_01",
            question="Do you always need photo ID to vote?",
            category="voting",
            difficulty="medium",
            options=[
                "Yes, always",
                "No, never",
                "It depends on your state",
                "Only if you're voting for the first time"
            ],
            correct_answer_idx=2,
            explanation="ID requirements vary significantly by state. Some require photo ID, others accept other proof of identity, and a few have no ID requirement. Know your state's rules.",
            source="IfIthen.org"
        ),
        QuizQuestion(
            id="q1_provisional_01",
            question="What is a provisional ballot?",
            category="voting",
            difficulty="medium",
            options=[
                "A temporary ballot before you're officially registered",
                "A backup ballot if you lose your original",
                "A ballot used when there's a question about your eligibility",
                "A ballot for new voters"
            ],
            correct_answer_idx=2,
            explanation="A provisional ballot is used when election officials question your eligibility. Your vote is typically counted after verification, which takes 10-20 days.",
            source="Vote.org"
        ),
        QuizQuestion(
            id="q1_chain_custody_01",
            question="What does 'chain of custody' mean in voting?",
            category="security",
            difficulty="hard",
            options=[
                "Keeping ballots away from children",
                "Recording who handled ballots at each step",
                "Storing ballots in a secure location",
                "The order in which ballots are counted"
            ],
            correct_answer_idx=1,
            explanation="Chain of custody documents exactly who handled ballots at each step - from collection through counting. This prevents tampering and provides accountability.",
            source="Election.gov"
        ),
    ],
    "IN_GENERAL": [
        QuizQuestion(
            id="q2_eci_01",
            question="What is the ECI?",
            category="civics",
            difficulty="easy",
            options=[
                "Election Commission of India",
                "Electronic Counting Interface",
                "Early Civic Institution",
                "Electoral Committee of India"
            ],
            correct_answer_idx=0,
            explanation="The Election Commission of India (ECI) is the independent constitutional authority responsible for administering elections in India.",
            source="eci.gov.in"
        ),
        QuizQuestion(
            id="q2_parliament_01",
            question="How many seats are in the Lok Sabha?",
            category="civics",
            difficulty="easy",
            options=["500", "545", "600", "700"],
            correct_answer_idx=1,
            explanation="The Lok Sabha (House of the People) has 545 seats - 543 elected and 2 nominated by the President.",
            source="eci.gov.in"
        ),
        QuizQuestion(
            id="q2_reg_01",
            question="What is the minimum age to register as a voter in India?",
            category="registration",
            difficulty="easy",
            options=["16 years", "18 years", "21 years", "25 years"],
            correct_answer_idx=1,
            explanation="In India, any citizen who is 18 years or older on the qualifying date is eligible to register as a voter.",
            source="eci.gov.in"
        ),
        QuizQuestion(
            id="q2_voting_01",
            question="What is an EVM?",
            category="voting",
            difficulty="easy",
            options=[
                "Electronic Verification Module",
                "Electronic Voting Machine",
                "Election Validity Mechanism",
                "Electoral Vote Manager"
            ],
            correct_answer_idx=1,
            explanation="Electronic Voting Machines (EVMs) are used across India for casting votes. They replaced paper ballots to reduce fraud and speed up counting.",
            source="eci.gov.in"
        ),
        QuizQuestion(
            id="q2_vvpat_01",
            question="What does VVPAT stand for?",
            category="security",
            difficulty="medium",
            options=[
                "Voter Verified Paper Audit Trail",
                "Valid Vote Processing And Tallying",
                "Verified Voting Process Audit Tool",
                "Vote Validation And Printing Terminal"
            ],
            correct_answer_idx=0,
            explanation="VVPAT (Voter Verified Paper Audit Trail) is attached to EVMs to allow voters to verify that their vote was recorded correctly by printing a paper slip.",
            source="eci.gov.in"
        ),
        QuizQuestion(
            id="q2_deadline_01",
            question="What is the voter registration form for new voters called?",
            category="deadline",
            difficulty="medium",
            options=["Form 1", "Form 6", "Form 8", "Form 11"],
            correct_answer_idx=1,
            explanation="Form 6 is used for new voter registration in India. It can be submitted online through the National Voters' Service Portal (NVSP).",
            source="nvsp.in"
        ),
    ]
}


async def get_quiz_questions(
    country: str,
    state: Optional[str],
    category: Optional[str],
    difficulty: Optional[str],
    count: int = 5
) -> List[QuizQuestion]:
    """Fetch quiz questions matching criteria."""
    # Build key: {COUNTRY}_{STATE or GENERAL}
    country_upper = country.upper()
    key_base = f"{country_upper}_{(state or 'general').upper()}"
    
    # Collect matching questions
    candidates = []
    for key, questions in QUIZ_BANK.items():
        key_upper = key.upper()
        if key_base == key_upper or key_upper.startswith(country_upper + "_"):
            for q in questions:
                if category and q.category != category:
                    continue
                if difficulty and difficulty != "mixed" and q.difficulty != difficulty:
                    continue
                candidates.append(q)
    
    # Fallback to general questions if none found (no category filter)
    if not candidates:
        general_key = f"{country_upper}_GENERAL"
        for key, questions in QUIZ_BANK.items():
            if key.upper() == general_key:
                candidates = list(questions)
                break
    
    # Shuffle and return requested count
    random.shuffle(candidates)
    return candidates[:count]


async def grade_quiz(
    session: QuizSession,
    attempts: List[QuizAttempt],
    questions: List[QuizQuestion]
) -> QuizResult:
    """Score quiz and provide breakdown."""
    score = 0
    category_breakdown = {}
    
    for attempt, question in zip(attempts, questions):
        is_correct = attempt.selected_idx == question.correct_answer_idx
        if is_correct:
            score += 1
        
        # Track by category
        if question.category not in category_breakdown:
            category_breakdown[question.category] = {"correct": 0, "total": 0}
        
        category_breakdown[question.category]["total"] += 1
        if is_correct:
            category_breakdown[question.category]["correct"] += 1
    
    total = len(questions)
    percentage = (score / total * 100) if total > 0 else 0
    
    return QuizResult(
        score=score,
        total=total,
        percentage=round(percentage, 1),
        category_breakdown=category_breakdown,
        time_taken_seconds=0,  # Client will track this
        passed=percentage >= 70
    )


async def get_quiz_recommendations(result: QuizResult) -> List[str]:
    """Generate personalized learning recommendations based on quiz performance."""
    recommendations = []
    
    if result.percentage < 70:
        recommendations.append("📚 Review the timeline to solidify key deadlines")
        recommendations.append("❓ Use Ask Why to get detailed explanations")
    
    # Category-specific
    for category, scores in result.category_breakdown.items():
        if scores["total"] == 0:
            continue
        
        pct = scores["correct"] / scores["total"] * 100
        if pct < 60:
            if category == "registration":
                recommendations.append(f"🔴 {category.title()}: Check your state's registration deadline (varies 15-30 days before)")
            elif category == "voting":
                recommendations.append(f"🔴 {category.title()}: Review voting methods and requirements for your situation")
            elif category == "deadline":
                recommendations.append(f"🔴 {category.title()}: Mark critical deadlines on your calendar now")
    
    if result.passed:
        recommendations.append("✅ Great job! You're voting-ready. Review the timeline once more before election day.")
    
    return recommendations or ["You're all set! Review the timeline regularly as election day approaches."]


async def calculate_knowledge_score(
    total_quizzes_taken: int,
    best_score_percentage: float,
    questions_asked: int
) -> float:
    """Calculate knowledge readiness as percentage (0-100)."""
    if total_quizzes_taken == 0:
        return 0.0
    
    # Base: quiz performance (60%)
    base_score = best_score_percentage * 0.6
    
    # Engagement: questions asked (20%)
    engagement_score = min(questions_asked / 10, 1.0) * 20  # Max out at 10 questions
    
    # Attempt count: shows persistence (20%)
    attempt_score = min(total_quizzes_taken / 3, 1.0) * 20  # Max out at 3 attempts
    
    return round(base_score + engagement_score + attempt_score, 1)
